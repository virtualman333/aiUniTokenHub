import base64
import logging
import uuid
from decimal import Decimal
from io import BytesIO

import httpx
from django.core.files.base import ContentFile
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.ai_models.models import AIModel
from apps.ai_models.upstream_models import ModelUpstreamAccount
from apps.users.models import Bill, UsageLog
from apps.api_proxy.models import APIAccessLog
from apps.utils.response import APIResponse

from .models import GeneratedImage, ImageGeneration
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
    """按张数扣费"""
    model = AIModel.objects.filter(code=model_code, status='active').first()
    unit_price = model.per_image_price if model and model.per_image_price else Decimal('0.08')
    cost = unit_price * n
    if user.balance < cost:
        return cost, False
    user.balance -= cost
    user.save(update_fields=['balance'])
    generation.cost = cost
    generation.save(update_fields=['cost'])
    Bill.objects.create(
        user=user, type='consume', amount=-cost,
        balance=user.balance,
        description=f'图像生成 {model_code} x{n}',
    )
    return cost, True


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

        # 校验余额
        model_obj = AIModel.objects.filter(code=model_code, status='active').first()
        unit_price = model_obj.per_image_price if model_obj and model_obj.per_image_price else Decimal('0.08')
        total_cost = unit_price * n
        if request.user.balance < total_cost:
            return APIResponse.error(
                f'余额不足，需要 ¥{total_cost}，当前余额 ¥{request.user.balance}', 400)

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

        # 保存图片
        for img_data in result_images:
            img_bytes = img_data['bytes']
            revised = img_data.get('revised_prompt', '')
            cf = ContentFile(img_bytes, name=f'{uuid.uuid4().hex}.png')
            GeneratedImage.objects.create(
                generation=generation, image=cf, revised_prompt=revised)

        # 扣费
        cost, success = _deduct_cost(request.user, model_code, n, generation)
        if not success:
            generation.status = 'failed'
            generation.error_message = '余额不足'
            generation.save(update_fields=['status', 'error_message'])
            return APIResponse.error('余额不足', 400)

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
