# -*- coding: utf-8 -*-
"""分页参数 → 「第几页 / 每页多少」，以及「非法输入只报错、不抛异常」—— **全平台唯一来源**。

为什么要单独一个模块
--------------------
`page = int(request.query_params.get('page', 1))` 这一行在本仓**曾经手抄 11 遍**
（`apps/ai_models/views.py` 2、`apps/api_proxy/views.py` 1、`apps/dashboard/analytics_views.py` 1、
`apps/dashboard/views.py` 2、`apps/image_gen/views.py` 1、`apps/tickets/views.py` 1、
`apps/users/views.py` 3），下面那行 `page_size = int(request.query_params.get('page_size', 20))`
连默认值 `20` 都抄了 11 遍。第 23 轮全部收敛到本模块，
`apps/utils/tests/test_pagination.py::SingleSourceTests` 盯着「不许长回来」。

而 `config/settings.py` 里还写着第三份：

    REST_FRAMEWORK = {
        'PAGE_SIZE': 20,
        ...
    }

那一份**没有任何东西读它**。DRF 只有在配了 `DEFAULT_PAGINATION_CLASS` 时才看得见 `PAGE_SIZE`，
而本仓一个分页类都没配（每个视图各自手抄）。所以它一直是一条死配置：改它，分页行为一点不变。
同一个数字写三处、其中一处还是死的 —— 这正是「同一事实写两处必然漂移」的样子。

手抄 11 遍的代价不是多敲四行，而是这四行**假设了输入的形状**，而输入完全由客户端控制：

    /api/users/bills/?page=abc           → int('abc') 抛 ValueError → 500
    /api/users/bills/?page=0             → start = -20 → Django 负数切片 → 500
    /api/users/bills/?page_size=abc      → 同上
    /api/users/bills/?page_size=999999   → 一次把整张表拉回浏览器（无上限）

这几条都在「客户端拼参数」这条路径上，而这个仓是**对外卖 token 的公开 API**。
所以这里收敛成一处，并把口径写死：

  - 非法（不是正整数）→ 返回一句给用户看的话，调用方翻成 400；
  - 缺失 / 空串 → 用默认值（空串是「没传」的常见形态：`?page=&page_size=`）；
  - `page_size` 超过上限 → **夹到上限**，不报错。夹住只影响一次响应的体积，语义仍然正确；
    报错会把「翻到最后一页时顺手放大 page_size」的老客户端直接打断。

**永不抛异常** —— 与 `apps/utils/api_errors.py` 同一条理由：调用方全都站在
「用户传参有问题」这条路径上，那里不该再冒出一个 500。

为什么是纯 Python、模块顶层不 import Django
------------------------------------------
`settings.REST_FRAMEWORK['PAGE_SIZE']` 当然要读，但**读它的那一层在 `page_params()` / `paginate()` 里**
（函数内 import），模块顶层零依赖 —— 这样 `parse_page_args` / `slice_page` 这些纯逻辑可以在
`run_tests.py`（不配 Django settings、不连数据库）下被直接测。同一条理由让
`apps/utils/api_errors.py` 单独成文件。

跑法（在 backend/ 下）：python run_tests.py
"""

#: 从 settings 也读不出来时的兜底值。**这是本模块唯一允许出现这个字面量的地方** ——
#: 视图里再抄一个「20」就是又开了一处会漂移的事实（结构锁盯着这件事）。
DEFAULT_PAGE_SIZE = 20

#: `page_size` 的上限。API 是公开的，没有上限就等于「一次能把整张表拉走」。
#: 超过就夹到这里，**不报错**（理由见模块抬头）。
MAX_PAGE_SIZE = 100


def default_page_size_from(rest_framework_config) -> int:
    """从 `REST_FRAMEWORK` 配置里取默认每页大小 —— settings 里那个 `PAGE_SIZE` 的唯一读法。

    取不到（配置缺失、键缺失、值是 `None` 或 `0`）时退到 `DEFAULT_PAGE_SIZE`。
    `0` 也退：每页 0 条既拉不到数据、又会让 `total` 与任何一页都对不上，
    那不是「用户想要的空列表」，是配置写错了。
    """
    if not isinstance(rest_framework_config, dict):
        return DEFAULT_PAGE_SIZE
    value = rest_framework_config.get('PAGE_SIZE')
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        return DEFAULT_PAGE_SIZE
    return value


def _positive_int(raw):
    """把查询串里的一个值转成正整数；转不出来返回 `None`。`bool` 是 `int` 的子类，这里不走 `bool`。"""
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw if raw > 0 else None
    text = str(raw).strip()
    if not text:
        return None
    # 只认十进制整数：`1.5` / `1e3` / `0x10` 都不接受（`int()` 接受后两者，会给人惊喜）
    if not (text.lstrip('+').isdigit()):
        return None
    value = int(text)
    return value if value > 0 else None


def _is_absent(raw) -> bool:
    """「没传」与「传了空串」算同一件事。`'   '` 也算 —— 它同样不是有效值。"""
    return raw is None or (isinstance(raw, str) and not raw.strip())


def parse_page_args(params, default_page_size: int = DEFAULT_PAGE_SIZE,
                    max_page_size: int = MAX_PAGE_SIZE):
    """`(page, page_size, error)` —— `error` 非空时前两个值无意义。

    `params` 只需要满足 `.get(key)`（`dict` 与 DRF 的 `QueryDict` 都满足）。
    只报**第一条**错误：客户端一次把两个参数都写错时，提示一个就够，两个会更难读。
    """
    raw_page = params.get('page')
    raw_size = params.get('page_size')

    if _is_absent(raw_page):
        page = 1
    else:
        page = _positive_int(raw_page)
        if page is None:
            return 0, 0, f'page 必须是大于 0 的整数（收到 {raw_page!r}）'

    if _is_absent(raw_size):
        page_size = default_page_size
    else:
        page_size = _positive_int(raw_size)
        if page_size is None:
            return 0, 0, f'page_size 必须是大于 0 的整数（收到 {raw_size!r}）'
        if max_page_size and page_size > max_page_size:
            page_size = max_page_size

    return page, page_size, ''


def page_params(request):
    """从请求里解析分页参数 —— 视图只该调这一个。默认值来自 `settings`，不自己写数字。

    返回 `(page, page_size, error)`，与 `parse_page_args` 一致；
    `error` 非空时视图应当 `return APIResponse.error(error, 400)`。
    """
    # 函数内 import：模块顶层保持零 Django 依赖，纯逻辑才测得了（见模块抬头）
    from django.conf import settings

    default_size = default_page_size_from(getattr(settings, 'REST_FRAMEWORK', None))
    return parse_page_args(request.query_params, default_size)


def slice_page(items, page: int, page_size: int):
    """取第 `page` 页 —— **切法只有这一处**。

    以前每处自己算 `start = (page - 1) * page_size; end = start + page_size`，
    于是「page 从 1 开始」这条约定在 11 个地方各写了一遍。接受查询集或普通列表。
    """
    start = (page - 1) * page_size
    return items[start:start + page_size]


def paginate(request, queryset, serializer, msg: str = '操作成功', context=None):
    """最常用的那个形状：查询集 + 序列化器 → `APIResponse.paginated`。

    `serializer` 传**可调用对象**：序列化器类（`BillSerializer`）、或 viewset 的
    `self.get_serializer`（它自己带 context）。只有原本就传了 `context` 的调用点才需要传
    `context=`（如 `image_gen` 那处）—— 这里不替调用方决定，免得把「要不要 request 上下文」
    这件事再藏一层。
    """
    from apps.utils.response import APIResponse

    page, page_size, error = page_params(request)
    if error:
        return APIResponse.error(error, 400)

    items = slice_page(queryset, page, page_size)
    if context is None:
        data = serializer(items, many=True).data
    else:
        data = serializer(items, many=True, context=context).data
    return APIResponse.paginated(data, queryset.count(), page, page_size, msg)
