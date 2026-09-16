import base64
import logging
import uuid
from decimal import Decimal
from io import BytesIO

import httpx
from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.ai_models.models import AIModel
from apps.ai_models.upstream_models import ModelUpstreamAccount
from apps.users.models import Bill, UsageLog, User
from apps.api_proxy.models import APIAccessLog
from apps.utils.response import APIResponse

from .billing import DEDUCT_OK, deduct_failure, insufficient_message, refund_amount_of, refund_message
from .models import GeneratedImage, ImageGeneration
from .pricing import image_cost
from .serializers import (
    ImageGenerationCreateSerializer,
    ImageGenerationSerializer,
    GeneratedImageSerializer,
)

logger = logging.getLogger('api_proxy')

def _select_upstream_account(model_code):
    """选择可用的上游账号（加权随机）"""
    import random
    model = AIModel.objects.filter(code=model_code, status='active').first()
    if not model:
        return None, '模型不存在或已下架'
    bindings = ModelUpstreamAccount.objects.filter(
        model=model, is_enabled=True,
        account__is_active=True, account__is_available=True,
    )
    if not bindings.exists():
        return None, '没有可用的上游账号'
    total_weight = sum(b.weight for b in bindings)
    rand_val = random.randint(1, total_weight)
    cumsum = 0
    selected = bindings.first()
    for b in bindings:
        cumsum += b.weight
        if rand_val <= cumsum:
            selected = b
            break
    return selected.account, None


def _deduct_cost(user, model_code, n, generation):
    """按张数扣费：在行锁内「重读余额 → 判断 → 扣款 → 记账」。

    这段以前是裸的读-改-写：

        if user.balance < cost:
            return cost, False
        user.balance -= cost
        user.save(update_fields=['balance'])
        ...
        Bill.objects.create(...)          # 还不在同一个事务里

    两个问题：
      1. 并发下两个请求会各自读到同一个旧余额、双双通过校验、各扣一次，
         少扣的部分平台再也收不回来（用户余额越用越多）；
      2. 扣款与记账不在同一事务里，记账那步失败就会出现「钱扣了、账单没有」。

    LLM 那条扣费路径（`views_openai.calculate_and_deduct_cost`）早就改成了
    `select_for_update` + `transaction.atomic`，这里向它对齐 —— 同一件事
    （扣费）两处实现，一处修好了、另一处没跟上就是活生生的漂移。

    语义上：仍然要求「余额足够付本次」，不足则一分不扣。

    返回值是**三档结果**（`billing.DEDUCT_OK / DEDUCT_INSUFFICIENT /
    DEDUCT_ERROR`）而不是布尔值 —— 以前这里统一返回 False，调用方于是把
    「数据库出错了」也回成「余额不足」：余额充足的用户被告知去充值，
    真正的问题被伪装成 400，前端既不提示异常也不重试。
    """
    model = AIModel.objects.filter(code=model_code, status='active').first()
    cost = image_cost(model, n)

    try:
        with transaction.atomic():
            locked = User.objects.select_for_update().get(pk=user.pk)
            if locked.balance < cost:
                return cost, DEDUCT_INSUFFICIENT
            locked.balance = locked.balance - cost
            locked.save(update_fields=['balance'])
            generation.cost = cost
            generation.save(update_fields=['cost'])
            Bill.objects.create(
                user=locked, type='consume', amount=-cost,
                balance=locked.balance,
                description=f'图像生成 {model_code} x{n}',
            )
        # 同步内存对象余额，供上层日志/展示使用
        user.balance = locked.balance
    except Exception as e:
        logger.error(f'[ImageGen] 扣费出错 user_id={getattr(user, "id", None)}: {e}')
        return cost, DEDUCT_ERROR

    return cost, DEDUCT_OK


def _refund_cost(generation):
    """把这笔扣费原路退回。只在「钱已经扣了、图却没存下来」时调用。

    为什么必须有
    ------------
    扣费现在排在保存图片之前（见 `post()` 里的说明），换来的是「余额不足时
    图不会落库」；代价是**扣费之后任何一步失败，用户的钱就白扣了** ——
    保存图片要写磁盘、写数据库，会失败。这条路径以前完全没人管：
    请求 500、钱照扣、记录还停在 `pending`，用户看到的是一个永远转圈的
    「生成中」。`Bill` 有 `refund` 类型、用户端账单页也早就把「退款」的
    样式写好了，但后端一条都没产生过。

    幂等
    ----
    退款与「把 `generation.cost` 归零」在同一个事务里完成，所以第二次调用
    读到的 cost 是 0、直接返回 —— 退不出第二遍。用已有字段当幂等标记，
    不为此加字段和迁移；而且「这笔生成净收费 0」也是真话。

    锁顺序
    ------
    **先 User 再 Generation**，与 `_deduct_cost` 完全一致（那里也是先锁
    User、再 save 那行 generation）。反过来写的话，两个并发请求一个走扣费、
    一个走退款，就可能互相等对方的行锁 —— 死锁。

    失败不抛异常：退款失败已经是最坏的情况，这时该把「没退成」如实写进日志
    和错误信息，而不是再抛一个异常把真正的失败原因盖掉。
    """
    try:
        with transaction.atomic():
            locked_user = User.objects.select_for_update().get(pk=generation.user_id)
            locked_gen = ImageGeneration.objects.select_for_update().get(pk=generation.pk)
            amount = refund_amount_of(locked_gen.cost)
            if amount <= 0:
                return amount
            locked_user.balance = locked_user.balance + amount
            locked_user.save(update_fields=['balance'])
            Bill.objects.create(
                user=locked_user, type='refund', amount=amount,
                balance=locked_user.balance,
                description=f'图像生成失败退款 {locked_gen.model_code}',
            )
            locked_gen.cost = Decimal('0')
            locked_gen.save(update_fields=['cost'])
        generation.cost = Decimal('0')
        return amount
    except Exception as e:
        logger.error(f'[ImageGen] 退款失败 generation_id={generation.pk}: {e}')
        return Decimal('0')


class ImageGenerationView(APIView):
    """图像生成列表 & 创建"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """获取当前用户的图像生成历史"""
        qs = ImageGeneration.objects.filter(user=request.user).prefetch_related('images')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        total = qs.count()
        start = (page - 1) * page_size
        records = qs[start:start + page_size]
        serializer = ImageGenerationSerializer(records, many=True, context={'request': request})
        return APIResponse.paginated(serializer.data, total, page, page_size)

    def post(self, request):
        """创建图像生成任务"""
        serializer = ImageGenerationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(str(serializer.errors), 400)

        data = serializer.validated_data
        model_code = data['model_code']
        mode = data['mode']
        prompt = data['prompt']
        size = data['size']
        quality = data['quality']
        n = data['n']
        image_file = data.get('image')

        # 校验余额（价格走 pricing.image_cost，与下面真正扣费是同一份规则；
        # 文案走 billing.insufficient_message，与扣费失败那条分支是同一句话 ——
        # 前置拦下和后置拦下对用户说的是同一件事，两处各写一份必然会有一处先漂移）
        model_obj = AIModel.objects.filter(code=model_code, status='active').first()
        total_cost = image_cost(model_obj, n)
        if request.user.balance < total_cost:
            return APIResponse.error(
                insufficient_message(total_cost, request.user.balance), 400)

        # 选择上游账号
        account, err = _select_upstream_account(model_code)
        if not account:
            return APIResponse.error(err, 400)

        # 创建记录
        generation = ImageGeneration.objects.create(
            user=request.user, model_code=model_code, mode=mode,
            prompt=prompt, size=size, quality=quality, n=n,
            status='pending',
        )

        try:
            if mode == 'edit' and image_file:
                result_images = self._call_edit_api(
                    account, prompt, image_file, size, quality, n)
            else:
                result_images = self._call_generate_api(
                    account, prompt, size, quality, n)
        except Exception as e:
            logger.error(f'[ImageGen] upstream error: {e}')
            generation.status = 'failed'
            generation.error_message = str(e)[:500]
            generation.save(update_fields=['status', 'error_message'])
            return APIResponse.error(f'图像生成失败: {str(e)[:200]}', 500)

        # 上游返回为空，不扣费，提示重试
        if not result_images:
            generation.status = 'failed'
            generation.error_message = '上游API未返回有效图片内容'
            generation.save(update_fields=['status', 'error_message'])
            return APIResponse.error('图像生成失败，未获取到图片内容，请稍后重试', 500)

        # 扣费 —— 必须排在「保存图片」之前。
        #
        # 原来顺序是反的（先存图、后扣费）。前置余额校验挡住的是「一开始就不够」，
        # 挡不住并发：两个请求各自读到同一个余额、双双通过校验、都去打了上游，
        # 其中后到的那一个会在这里因余额不足失败 —— 但它的图片**已经落库**了。
        # 请求返回 400，可历史列表用的是 `prefetch_related('images')`，
        # 用户照样能看到、能下载 —— 等于白拿，上游成本由平台付。
        # 调换顺序后，余额不足时图片从未落库，不需要任何删除动作。
        #
        # 代价是「扣费之后才存图」，所以下面保存图片那段必须自己兜住失败 ——
        # 否则就是扣了钱、图没到手。见 _refund_cost 与紧随其后的 try。
        cost, status = _deduct_cost(request.user, model_code, n, generation)
        if status != DEDUCT_OK:
            message, http_status = deduct_failure(status, cost, request.user.balance)
            generation.status = 'failed'
            generation.error_message = message
            generation.save(update_fields=['status', 'error_message'])
            return APIResponse.error(message, http_status)

        # 保存图片
        #
        # 这一步会写磁盘、写数据库，会失败（空间满、MEDIA_ROOT 权限、存储后端
        # 抽风、并发下的一次死锁……）。钱已经在上面扣掉了，所以失败时**必须退款**：
        #   - 不退款 → 用户付了钱、什么都没拿到，而且从记录上看不出发生过什么；
        #   - 不改成 failed → 记录永远停在 pending，前端一直显示「生成中」。
        try:
            for img_data in result_images:
                img_bytes = img_data['bytes']
                revised = img_data.get('revised_prompt', '')
                cf = ContentFile(img_bytes, name=f'{uuid.uuid4().hex}.png')
                GeneratedImage.objects.create(
                    generation=generation, image=cf, revised_prompt=revised)
        except Exception as e:
            logger.error(f'[ImageGen] 保存图片失败 generation_id={generation.pk}: {e}')
            refunded = _refund_cost(generation)
            message = refund_message(refunded, '图片保存失败')
            generation.status = 'failed'
            generation.error_message = message
            generation.save(update_fields=['status', 'error_message'])
            return APIResponse.error(message, 500)

        generation.status = 'completed'
        generation.save(update_fields=['status'])

        # 记录使用日志
        try:
            model_obj = AIModel.objects.filter(code=model_code).first()
            UsageLog.objects.create(
                user=request.user,
                method='POST',
                endpoint='/image-gen/generations',
                status_code=200,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                cost=float(cost),
            )
            APIAccessLog.objects.create(
                user=request.user,
                method='POST',
                path='/image-gen/generations',
                request_body={'model': model_code, 'prompt': prompt, 'n': n, 'size': size, 'quality': quality},
                response_body={'status': 'completed', 'images_count': generation.images.count()},
                response_status=200,
                response_time=0,
                model=model_obj,
                cost=float(cost),
            )
        except Exception as e:
            logger.warning(f'[ImageGen] 记录使用日志失败: {e}')

        result = ImageGenerationSerializer(generation, context={'request': request}).data
        return APIResponse.created(result, '图像生成成功')

    def _call_generate_api(self, account, prompt, size, quality, n):
        """调用上游图像生成API"""
        base = account.base_url.rstrip('/')
        if not base.lower().endswith('/v1'):
            base = f'{base}/v1'
        url = f'{base}/images/generations'
        headers = {
            'Authorization': f'Bearer {account.api_key}',
            'Content-Type': 'application/json',
        }
        body = {
            'model': 'gpt-image-2',
            'prompt': prompt,
            'n': n,
            'size': size if size != 'auto' else '1024x1024',
            'quality': quality if quality != 'auto' else 'standard',
        }
        logger.info(f'[ImageGen] Calling {url} with model={body["model"]}, n={n}, size={body["size"]}, quality={body["quality"]}')
        with httpx.Client(timeout=300) as client:
            resp = client.post(url, json=body, headers=headers)
            logger.info(f'[ImageGen] Response status: {resp.status_code}')
            if resp.status_code >= 400:
                raise Exception(f'上游API错误: {resp.status_code} {resp.text[:300]}')
            data = resp.json()
            # 上游返回200但body里包含错误信息
            if 'error' in data:
                err_msg = data['error'].get('message', str(data['error']))
                raise Exception(f'上游API错误: {err_msg}')

        images = []
        for item in data.get('data', []):
            if 'b64_json' in item:
                img_bytes = base64.b64decode(item['b64_json'])
            elif 'url' in item:
                try:
                    with httpx.Client(timeout=60) as client:
                        img_resp = client.get(item['url'])
                        img_resp.raise_for_status()
                        img_bytes = img_resp.content
                except Exception as dl_err:
                    logger.error(f'[ImageGen] 下载图片URL失败: {item["url"]}, error: {dl_err}')
                    continue
            else:
                logger.warning(f'[ImageGen] 上游返回的数据项缺少 b64_json 和 url: {list(item.keys())}')
                continue
            images.append({
                'bytes': img_bytes,
                'revised_prompt': item.get('revised_prompt', ''),
            })
        if not images:
            logger.error(f'[ImageGen] 上游API返回了 {len(data.get("data", []))} 项，但全部解析失败。原始响应: {str(data)[:500]}')
        return images

    def _call_edit_api(self, account, prompt, image_file, size, quality, n):
        """调用上游图像编辑API"""
        base = account.base_url.rstrip('/')
        if not base.lower().endswith('/v1'):
            base = f'{base}/v1'
        url = f'{base}/images/edits'
        headers = {'Authorization': f'Bearer {account.api_key}'}
        files = {'image': (image_file.name, image_file.read(), image_file.content_type)}
        data = {
            'model': 'gpt-image-2',
            'prompt': prompt,
            'n': str(n),
            'size': size if size != 'auto' else '1024x1024',
        }
        if quality and quality != 'auto':
            data['quality'] = quality
        with httpx.Client(timeout=300) as client:
            resp = client.post(url, data=data, files=files, headers=headers)
            if resp.status_code >= 400:
                raise Exception(f'上游API错误: {resp.status_code} {resp.text[:300]}')
            result = resp.json()
            # 上游返回200但body里包含错误信息
            if 'error' in result:
                err_msg = result['error'].get('message', str(result['error']))
                raise Exception(f'上游API错误: {err_msg}')

        images = []
        for item in result.get('data', []):
            if 'b64_json' in item:
                img_bytes = base64.b64decode(item['b64_json'])
            elif 'url' in item:
                try:
                    with httpx.Client(timeout=60) as client:
                        img_resp = client.get(item['url'])
                        img_resp.raise_for_status()
                        img_bytes = img_resp.content
                except Exception as dl_err:
                    logger.error(f'[ImageGen] 下载图片URL失败(edit): {item["url"]}, error: {dl_err}')
                    continue
            else:
                logger.warning(f'[ImageGen] 上游返回的数据项缺少 b64_json 和 url(edit): {list(item.keys())}')
                continue
            images.append({
                'bytes': img_bytes,
                'revised_prompt': item.get('revised_prompt', ''),
            })
        if not images:
            logger.error(f'[ImageGen] 上游API返回了 {len(result.get("data", []))} 项，但全部解析失败(edit)。原始响应: {str(result)[:500]}')
        return images


class ImageGenerationDetailView(APIView):
    """图像生成详情 & 删除"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            gen = ImageGeneration.objects.prefetch_related('images').get(
                pk=pk, user=request.user)
        except ImageGeneration.DoesNotExist:
            return APIResponse.error('记录不存在', 404)
        serializer = ImageGenerationSerializer(gen, context={'request': request})
        return APIResponse.success(serializer.data)

    def delete(self, request, pk):
        try:
            gen = ImageGeneration.objects.get(pk=pk, user=request.user)
        except ImageGeneration.DoesNotExist:
            return APIResponse.error('记录不存在', 404)
        # 删除图片文件
        for img in gen.images.all():
            if img.image:
                try:
                    img.image.delete(save=False)
                except Exception:
                    pass
        gen.delete()
        return APIResponse.success(msg='已删除')
