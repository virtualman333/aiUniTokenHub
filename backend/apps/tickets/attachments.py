# -*- coding: utf-8 -*-
"""工单附件的**全部**规矩：什么样的 id 才算 id、一次能带几张、上传落在哪个目录。

为什么单独一个模块
------------------
`apps/tickets/` 从来零覆盖，`run_tests.py` 的 `NO_TESTS_YET['tickets']` 里写的
原因是「不碰库的只有 models.py 的 `ticket_image_upload_path`，但它在 models.py 里
—— 纯 unittest import 不到（那个模块顶层 import Django）」。那句「待补」就是没人
扛的承诺：这层规矩一直散在 views.py 里，而 views 只能连着数据库一起测。

于是把不碰库的部分整体搬到这里：视图与模型都从这里取规矩，测试直接 import 这里
—— 不需要数据库，也不需要 Django settings。

搬的过程中露出三处缺陷（每条都有用例钉住，见 tests/test_attachments.py）：

1. `image_ids` 从前是**原样**丢给 `filter(id__in=...)` 的。请求体里传一个字符串
   `"12"`，Django 会把它**当可迭代对象按字符拆开** → `IN ('1','2')` → 绑的是
   第 1、2 张图，而不是第 12 张；`len("12") == 2` 又只有 2，连 5 张的上限都没
   碰到。前端一直传数组，所以线上没炸 —— 但契约是假的，换一个客户端就会静默
   绑错图。
2. 「最多关联 5 张图片」从前是在**写库之后**才判的（`views.py` 里 `serializer.save()`
   与 `TicketReply.objects.create()` 都排在它前面）→ 400 回去了，工单/回复却已经
   落库。用户看到失败、再点一次，就有了两条。
3. 绑定用 `filter(...).update(...)`，**影响 0 行也不报错**。图片若已不在可绑定状态
   （比如上一次提交已经把它用掉了），这次提交会静默地不带任何图 —— 前端弹
   「提交成功」，工单里一张图都没有。所以绑定之后的核对（``partial_binding_error``）
   不是可选项。

为什么上传目录里是 ``unassigned`` 而不是工单号
--------------------------------------------
`upload_to` 只在**保存图片的那一刻**求值，而此刻工单还不存在（前端的顺序是：
先传图拿 id → 再带着 id 提交工单）。所以 `f"tickets/{instance.ticket_id}/"`
永远算出 `tickets/None/` —— 目录名声称自己是一个工单号，实际那串字符是
``None``。现流程下目录只能表达「有没有归属」，表达不了「属于谁」，
所以这里如实叫 ``unassigned``。已有磁盘文件与库里旧路径不受影响（路径是落库的
字符串，改的只是新文件）。
"""
import os

#: 一次请求最多能带几张图（工单与回复同一上限）。
MAX_IMAGES = 5

#: 单张图上限。
MAX_IMAGE_BYTES = 5 * 1024 * 1024

#: 允许的图片类型 → 提示语里的写法。**顺序就是提示语里的顺序**。
#:
#: 这张表在仓库里有两份：这里，以及 `frontend/src/components/ImageUpload.vue`
#: 的 `beforeUpload`（浏览器端先拦一道，省一次白传）。两份必须逐项一致 ——
#: 由 `tests/test_attachments.py` 里的对账用例盯着（它从 .vue 源码里把数组读出来
#: 跟这里比，而不是拿一份抄来的字面量比）。
IMAGE_FORMAT_LABELS = {
    'image/jpeg': 'JPG',
    'image/png': 'PNG',
    'image/gif': 'GIF',
    'image/webp': 'WebP',
}
ALLOWED_IMAGE_TYPES = tuple(IMAGE_FORMAT_LABELS)

#: 上传落在这个子目录 —— 图还没有归属（工单/回复都还不存在）。
UNASSIGNED_DIR = 'unassigned'


def allowed_types_message():
    """整句提示语，由 `IMAGE_FORMAT_LABELS` 生成。

    写死成 '只支持 JPG、PNG、GIF、WebP 格式的图片' 的话，哪天表里加一种类型，
    拦截逻辑认了、提示语还在说老四样 —— 同一件事写两处必然漂移。
    """
    return '只支持 ' + '、'.join(IMAGE_FORMAT_LABELS.values()) + ' 格式的图片'


def max_size_message():
    """同上：MB 数从 `MAX_IMAGE_BYTES` 算，不手抄。"""
    return f'图片大小不能超过{MAX_IMAGE_BYTES // (1024 * 1024)}MB'


def parse_image_ids(raw):
    """把请求体里的 `image_ids` 收成一份可信的 id 清单。

    返回 `(ids, error)`：``error`` 非 None 时调用方**必须**在写库之前回 400 ——
    这个函数的全部意义就是把「校验」摆在「写库」前面，从前它是反的。

    接受的形状：``None`` / 缺省（→ 空清单）、``list`` / ``tuple``，元素是正整数
    或纯数字字符串（axios 把 query/表单值都变成字符串，所以数字字符串得认）。

    不接受：整体是字符串（``"12"`` 会被 `id__in` 按字符拆成 1 和 2）、``set``
    （顺序不定，JSON 里也没有这种形状）、``bool``（``True`` 是 ``int`` 的子类，
    放过去等于 id=1）、0 与负数（并不存在这样的主键）。
    """
    if raw is None:
        return [], None
    if isinstance(raw, str):
        return [], (
            'image_ids 必须是数组，不能是字符串 —— '
            '传成字符串时后端会把它按字符拆开当成一串图片 id'
        )
    if not isinstance(raw, (list, tuple)):
        return [], 'image_ids 必须是数组'

    ids = []
    for item in raw:
        if isinstance(item, bool):
            return [], f'image_ids 里有非法值：{item!r}'
        if isinstance(item, int):
            value = item
        elif isinstance(item, str):
            text = item.strip()
            # isdigit() 对全角数字（'１２'）也返回 True，而 int() 收得下它；
            # 这里不打算收，统一要求 ASCII 数字，判断口径与 int() 一致。
            if not (text.isascii() and text.isdigit()):
                return [], f'image_ids 里有非法值：{item!r}'
            value = int(text)
        else:
            return [], f'image_ids 里有非法值：{item!r}'
        if value <= 0:
            return [], f'image_ids 里有非法值：{item!r}'
        if value in ids:
            continue
        if len(ids) == MAX_IMAGES:
            # 上限按**去重后**算：[4, 4, 4] 是一张图而不是三张，到第 6 张才拒。
            # 顺带也就不必为了「先数一数」把整个数组走完。
            return [], f'最多关联{MAX_IMAGES}张图片'
        ids.append(value)

    return ids, None


def partial_binding_error(requested, bound):
    """绑定之后核对：该绑几张、实际绑上几张。

    **必须调用它**，别只看 `update()` 没抛异常 —— `update()` 返回的是受影响行数，
    0 行也是「成功」。少一张就整笔回滚，让用户重新上传，而不是收下一张没有图的
    工单。
    """
    missing = requested - bound
    if missing <= 0:
        return None
    return (
        f'有 {missing} 张图片已经不在可关联状态（可能已被别处使用），'
        '本次未提交，请重新上传后再试'
    )


def upload_dir(ticket_id):
    """上传目录。找不到归属就如实说 `unassigned`，不编一个 id 出来。"""
    if isinstance(ticket_id, int) and not isinstance(ticket_id, bool) and ticket_id > 0:
        return f'tickets/{ticket_id}'
    return f'tickets/{UNASSIGNED_DIR}'


def upload_path(ticket_id, filename, token):
    """上传路径的单一来源。

    `token` 由调用方给（models.py 传 `uuid4().hex`）—— 把随机数挡在外面，
    这个函数才是可断言的纯函数：同样的入参永远同样的字符串。

    扩展名只从**文件名尾部**取（`os.path.splitext` 不看目录部分），原名不会进入
    路径，所以不需要额外防穿越。扩展名可能为空串（原名没有点）。
    """
    return f'{upload_dir(ticket_id)}/{token}{os.path.splitext(filename)[1]}'
