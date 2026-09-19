# -*- coding: utf-8 -*-
"""前端调的每个后端接口都真实存在 —— 这条此前**没有任何东西在扛**。

为什么要有它
------------
`frontend/src/` 有 107 处调后端的调用（103 处 `api.*` + 2 处 `axios.*` + 2 处 `fetch(`），
后端有 219 条 `api/` 路由（其中 75 条是 DRF 运行时生成的 `<format>` 后缀族），两边
**从来没有对过一次账**。而前端唯一的检查是 `check:seo.js`（只管 SEO 产物与路由表），
后端这 573 例都在 `apps/*/tests/` 里、不读前端一个字。于是：

  · 前端调一个后端没有的路径 → 用户点到那一刻才 404，而构建、测试、类型检查**全绿**；
  · 这不是假设。本轮实测有 5 处这样的调用，其中 `/forgot-password` 整条链是断的 ——
    `ForgotPassword.vue` 从 `4888032` 起就在调 `/users/auth/send_reset_code/` 与
    `/users/auth/reset_password/`，**这两个端点从来没有被实现过**，而忘记密码页还在
    sitemap 里当公开页提交。

判据是什么
----------
前端每一次调用都要在后端路由表里找到落点。找不到 = 失败，**除非**在 `KNOWN_UNRESOLVED`
里登记了理由 —— 登记表本身两向校验（登记了却已经能解析 = 僵尸条目，会红）。

刻意**不**锁的方向：后端有、前端没调的，不算失败。那是正常且大量的 ——
`/api/proxy/v1/*` 那组 OpenAI 兼容端点的调用方是**外部用户**，不是本仓库前端；
DRF router 生成的 `list` / `detail` 路由也大多没有前端调用者。只锁一个方向的理由是
**「多一条没人调的路由」从来不是缺陷，「调一个不存在的路由」才是**。

真值从哪来（以及为什么不用 Django）
-----------------------------------
后端路由表是**读源码**得来的（`ast` 解析 `config/urls.py`、各 `apps/*/urls.py`、以及被
`router.register` 指到的 viewset 类），**不启动 Django**：

  1. 这一层的约定是「纯标准库、不碰数据库、不碰 Django settings」—— `run_tests.py` 写明
     「均不需要数据库」。而本仓 `apps/ai_models/apps.py::ready()` 会在**每次** Django 启动
     时连库，并在发现「迁移文件名 ≠ 已应用名」时**自动跑 `migrate --run-syncdb`**；
     本机 `.env` 的 `DB_HOST` 是生产 IP，所以任何 `django.setup()` 都等于在生产库上启动
     一次应用。一个「检查前端路径写没写对」的用例没有资格碰那台机器。
  2. 这个解析器**在 Django 之外被验过两次**（2026-09-19，`DB_HOST=127.0.0.1 DB_PORT=1`
     即拒连地址；`ready()` 里的 `except: pass` 会吞掉连接失败）：
       · **修之前**：用 `django.urls.resolve()` 逐条判定 106 处 `api.*` 调用 —— 101 条通过、
         5 条 404，**那 5 条与本文件报出来的完全是同一批**（这就是它的第一次「响」）；
       · **修之后**：107 处调用逐条比对判决，**分歧 0**；再把本解析器从源码展开出的
         134 条路由逐条丢给 `resolve()`（动态段填探测值），**幻影路由 0 条** ——
         也就是「多认路由」这个假绿方向也被堵住了。
     路由形状（`<path:path>` 兜底、`re_path` 命名组、多段 `url_path`）见 `ParserShape`。

判错的方向是有意设计的：**只往「说某条调用没有落点」这一侧偏**（漏认路由 = 响），
绝不往「明明没有落点却说有」那一侧偏（多认路由 = 假绿）。这也是为什么 viewset 的
`list` / `detail` 路由要**按类里真的定义了哪些动作**来展开：`AdminDashboardViewSet` 被
`router.register(r"overview", ...)` 注册过，但它没有 `list`，所以 `/api/dashboard/overview/`
**不存在** —— 只按 `router.register` 的存在就生成路由，会把这个真实 404 判成绿。
"""
import ast
import re
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]
REPO = BACKEND.parent
FRONTEND = REPO / 'frontend'
SRC = FRONTEND / 'src'

#: `api.<verb>()` 的 baseURL（`src/stores/index.js` 的 `axios.create`）
API_BASE = '/api'

#: 模板串开头那些「不是字面量」的前缀表达式 → 它们实际指向的后端前缀。
#: 表外的表达式**直接失败**而不是猜一个 —— 猜错的方向是假绿。
BASE_EXPR = {
    'apiBase': API_BASE,                  # Home.vue 的 `import.meta.env.VITE_API_BASE_URL || '/api'`
    'apiBaseUrl.value': '/api/proxy/v1',  # APIDoc.vue 的 `window.location.origin + '/api/proxy/v1'`
}

#: 前端调了、后端确实没有 —— 每条都必须写明理由，且**必须仍然真的解析不到**（僵尸条目会红）。
#: 本轮把实测的 5 条全修了，所以它是空的；留着这张表是为了下次有正当例外时不必改判据。
KNOWN_UNRESOLVED: dict = {}

#: 解析面下限 —— 解析器被改坏（正则失效、AST 走空）时，下面所有「没有差异」都会恒真。
#: 数值按实测写（2026-09-19：134 条路由、107 处调用），留一点余量给正常的增删。
MIN_ROUTES = 120
MIN_CALLS = 100


# --------------------------------------------------------------------------- 通用


def _lines_without_whole_line_comments(text):
    """把**整行**注释挖空（保持行号），行内 `//` 不动。

    本仓的既定风格是「在注释里写一句『不能这么写』的反面示例」，而这些注释里会**原样出现**
    `api.post('/users/auth/send_reset_code/', ...)` 这种已经修掉的路径（本轮 `stores/index.js`
    里就刚写了一条）。不剥注释，检查会对着**修好的**代码变红 —— 本仓已栽过四次。

    刻意只处理**整行**注释：`api.get('/x')  // 说明` 这种行尾注释挖不掉，但它不可能
    「注释掉一个调用」（调用本身还在行首，仍然真的会执行）。这条窄化是有意的 ——
    要剥行尾注释就得处理字符串里的 `//`（URL！），那是另一个会静默失步的解析器。
    """
    out = []
    for line in text.split('\n'):
        out.append('' if line.lstrip().startswith(('//', '*', '/*')) else line)
    return '\n'.join(out)


def _parse(path):
    return ast.parse(path.read_text(encoding='utf-8'))


def _const_str(node):
    """`ast` 节点 → 字符串字面量（只认真正写字面量的那种，变量名一律返回 None）。"""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _call_name(node):
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
    return None


# --------------------------------------------------------------------------- 后端路由表

#: DRF 的基类各自生成了哪些标准动作：动作名 → `'collection'`（挂在集合上）/ `'detail'`（带 pk）
STANDARD_ACTIONS = {
    'ModelViewSet': {'list': 'collection', 'create': 'collection',
                     'retrieve': 'detail', 'update': 'detail',
                     'partial_update': 'detail', 'destroy': 'detail'},
    'ReadOnlyModelViewSet': {'list': 'collection', 'retrieve': 'detail'},
}


def included_app_urls():
    """`config/urls.py` → `{'/api/users': 'apps/users/urls.py', ...}`"""
    out = {}
    for node in ast.walk(_parse(BACKEND / 'config' / 'urls.py')):
        if _call_name(node) != 'path' or len(node.args) < 2:
            continue
        prefix = _const_str(node.args[0])
        target = node.args[1]
        if prefix is None or _call_name(target) != 'include' or not target.args:
            continue
        module = _const_str(target.args[0])
        if module is None or not prefix.startswith('api/'):
            continue
        out['/' + prefix.strip('/')] = module.replace('.', '/') + '.py'
    return out


def _imported_classes(tree):
    """`from .views import AuthViewSet` → `{'AuthViewSet': 'views'}`（相对导入，限本应用内）"""
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            for alias in node.names:
                out[alias.asname or alias.name] = node.module
    return out


def _class_facts(path, class_name):
    """一个 viewset 类提供了哪些动作、每个 `@action` 的段名与 detail 归属。

    返回 `(methods, bases)`；类不存在时返回 `None` —— 那是**解析失败**，调用方必须报错，
    不能当成「这个类没有任何路由」：那会静默少一批路由，方向恰好是假绿。
    """
    for node in _parse(path).body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        methods = {}
        for item in node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            action = None
            for dec in item.decorator_list:
                if _call_name(dec) != 'action':
                    continue
                kwargs = {kw.arg: kw.value for kw in dec.keywords}
                detail = kwargs.get('detail')
                action = {
                    'detail': isinstance(detail, ast.Constant) and detail.value is True,
                    'segment': _const_str(kwargs.get('url_path')) or item.name,
                }
            methods[item.name] = action
        bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
        bases += [b.attr for b in node.bases if isinstance(b, ast.Attribute)]
        return methods, bases
    return None


def _segments(route):
    """路由串 → 段元组。动态段（转换器 / 命名组）→ `None`；`<path:...>` 兜底 → `'**'`。

    `'redis/info/'`            → `('redis', 'info')`
    `'conversations/<int:pk>/'`→ `('conversations', None)`
    `'v1/<path:path>'`         → `('v1', '**')`
    `r'^v1/models/(?P<x>[^/]+)$'` → `('v1', 'models', None)`

    ⚠ 正则路由里的 `/` 可能落在 `[^/]` 这种字符类里（`re_path` 那两条就是），
    按 `/` 硬切会把它切成两段、凭空多出一条永远匹配不上的假路由 —— 所以先在
    「括号内 / 字符类内」把 `/` 换成占位符，切完再换回来。（这个坑当场踩到了：
    `(?P<model_id>[^/]+)` 被切成 `(?P<model_id>[^` 与 `]+)` 两段。）
    """
    route = route.strip()
    if route.startswith('^'):
        route = route[1:]
    if route.endswith('$'):
        route = route[:-1]

    buf = []
    depth = 0
    in_class = False
    i = 0
    while i < len(route):
        ch = route[i]
        if ch == '\\' and i + 1 < len(route):      # 转义对（`\.` / `\/`）整体放过
            buf.append(ch)
            buf.append(route[i + 1])
            i += 2
            continue
        if ch == '[':
            in_class = True
        elif ch == ']':
            in_class = False
        elif ch == '(':
            depth += 1
        elif ch == ')':
            depth = max(0, depth - 1)
        buf.append('\x00' if (ch == '/' and (depth > 0 or in_class)) else ch)
        i += 1

    out = []
    for raw in ''.join(buf).strip('/').split('/'):
        raw = raw.replace('\x00', '/').strip()
        if not raw:
            continue
        if raw.startswith('<') and raw.endswith('>'):
            out.append('**' if raw[1:].split(':')[0] == 'path' else None)
        elif '(' in raw:
            out.append(None)
        else:
            out.append(raw)
    return tuple(out)


def backend_routes():
    """后端 `api/` 下的全部路由（段元组的集合），以及解析过程中的问题清单。"""
    routes = set()
    problems = []
    for prefix, rel in sorted(included_app_urls().items()):
        file = BACKEND / rel
        if not file.is_file():
            problems.append(f'{rel} 不存在（config/urls.py 里 include 了它）')
            continue
        base = _segments(prefix)
        app_dir = file.parent
        tree = _parse(file)
        imports = _imported_classes(tree)

        # ① 字面量条目与 re_path 条目
        for node in ast.walk(tree):
            if _call_name(node) not in ('path', 're_path') or not node.args:
                continue
            route = _const_str(node.args[0])
            if route is not None:
                routes.add(base + _segments(route))

        # ② `router.register(r'<prefix>', <ViewSet>)` 展开成真实存在的那些动作
        for node in ast.walk(tree):
            if _call_name(node) != 'register' or len(node.args) < 2:
                continue
            sub = _const_str(node.args[0])
            target = node.args[1]
            if sub is None or not isinstance(target, ast.Name):
                continue
            mod = imports.get(target.id)
            if mod is None:
                problems.append(f'{rel}: router.register 指到 {target.id}，但相对 import 里没有它')
                continue
            facts = _class_facts(app_dir / (mod.replace('.', '/') + '.py'), target.id)
            if facts is None:
                problems.append(f'{rel}: 找不到类 {target.id}（应在 {mod}.py 里）'
                                f'—— 解析失败会让整组路由凭空消失')
                continue
            methods, bases = facts
            stem = base + _segments(sub)
            standard = {}
            for cls in bases:
                standard.update(STANDARD_ACTIONS.get(cls, {}))
            for kind in standard.values():
                routes.add(stem if kind == 'collection' else stem + (None,))
            for action in methods.values():
                if action is None:
                    continue
                # `url_path` 本身可以是**多段**、还可以带命名组：
                #   `url_path='update_channel/(?P<pk>[^/.]+)'`  → ('update_channel', None)
                #   `url_path='email_config/test'`              → ('email_config', 'test')
                # 当成一个段整块塞进去，这 6 条路由就会全部匹配不上（当场踩到）。
                frag = _segments(action['segment'])
                if not frag:
                    problems.append(f'{rel}: {target.id} 的 @action url_path 是空的'
                                    f'（{action["segment"]!r}），展开不出路由')
                    continue
                routes.add((stem + (None,) + frag) if action['detail'] else (stem + frag))
    return routes, problems


# --------------------------------------------------------------------------- 前端调用表

#: `api.get('x')` / `axios.post(`x`)` / `fetch(`x`)` —— 路径紧跟在开括号后
CALL_RE = re.compile(
    r"""(?P<kind>\bapi\.(?P<v1>get|post|put|patch|delete)\(
                     |\baxios\.(?P<v2>get|post|put|patch|delete)\(
                     |\bfetch\()
        \s*(?P<q>['"`])(?P<path>.+?)(?P=q)""",
    re.VERBOSE | re.DOTALL,
)

#: 模板串里的插值（不处理更深层嵌套，够用；不匹配的段会按字面量留下，判错方向是「响」）
INTERP_RE = re.compile(r'\$\{([^{}]*)\}')


def _frontend_files():
    files = list(SRC.rglob('*.vue')) + list(SRC.rglob('*.js'))
    return sorted(p for p in files if 'node_modules' not in p.parts)


def frontend_calls():
    """前端所有调后端的调用 → `[{'loc', 'verb', 'raw', 'segs'}]`，外加问题清单。"""
    calls = []
    problems = []
    for path in _frontend_files():
        rel = path.relative_to(FRONTEND).as_posix()
        text = _lines_without_whole_line_comments(path.read_text(encoding='utf-8'))
        for m in CALL_RE.finditer(text):
            line = text[: m.start()].count('\n') + 1
            loc = f'{rel}:{line}'
            raw = m.group('path')
            verb = (m.group('v1') or m.group('v2') or 'fetch').upper()
            # `kind` 抓的是 `api.get(` 这一整段，得把动词与括号剥掉才是实例名
            # （这里当场踩过：`kind == 'api'` 判不出来，于是 `api.*` 的调用全都少了
            #  `/api` 前缀，103 条调用一起变成「没有落点」）
            kind = m.group('kind').rstrip('(').split('.')[0]

            head = re.match(r'^\$\{([^}]*)\}', raw)
            if head:
                expr = head.group(1).strip()
                if expr not in BASE_EXPR:
                    problems.append(f'{loc} 路径前缀 `${{{expr}}}` 不在 BASE_EXPR 里，'
                                    f'无法判定它指向哪个后端前缀')
                    continue
                full = BASE_EXPR[expr] + raw[head.end():]
            elif kind == 'api':
                full = API_BASE + (raw if raw.startswith('/') else '/' + raw)
            elif raw.startswith('/'):
                full = raw
            else:
                problems.append(f'{loc} `{kind}` 的路径 `{raw}` 既不是绝对路径、也不以 '
                                f'BASE_EXPR 里的表达式开头，无法判定它指向哪个后端前缀')
                continue

            segs = tuple(None if INTERP_RE.search(s) else s
                         for s in full.split('?')[0].split('#')[0].strip('/').split('/') if s)
            # `full` 里的插值填一个探测值 —— 用来跟 Django 的 `resolve()` 做交叉验证
            # （见模块头「这个解析器在 Django 之外被验过一次」）。它不参与判据。
            concrete = INTERP_RE.sub('1', full.split('?')[0])
            calls.append({'loc': loc, 'verb': verb, 'raw': raw, 'segs': segs,
                          'full': concrete})
    return calls, problems


def route_matches(route, call):
    """前端调用的段序列能否落到这条路由上。"""
    if route and route[-1] == '**':
        head = route[:-1]
        return len(call) >= len(head) and all(r is None or r == c for r, c in zip(head, call))
    if len(route) != len(call):
        return False
    return all(r is None or r == c for r, c in zip(route, call))


def unresolved_calls(routes, calls):
    return [c for c in calls if not any(route_matches(r, c['segs']) for r in routes)]


# --------------------------------------------------------------------------- 判据


class ParserIsNotVacuous(unittest.TestCase):
    """解析面自证 —— 解析器走空时，下面每一条「没有差异」都会恒真。"""

    def test_后端路由表不是空的(self):
        routes, problems = backend_routes()
        self.assertEqual(problems, [], '后端路由解析出了问题：' + str(problems))
        self.assertGreaterEqual(
            len(routes), MIN_ROUTES,
            f'只解析出 {len(routes)} 条路由（下限 {MIN_ROUTES}）—— 解析器多半没在干活',
        )

    def test_前端调用表不是空的(self):
        calls, problems = frontend_calls()
        self.assertEqual(problems, [], '前端调用解析出了问题：' + str(problems))
        self.assertGreaterEqual(
            len(calls), MIN_CALLS,
            f'只解析出 {len(calls)} 处调用（下限 {MIN_CALLS}）—— 解析器多半没在干活',
        )

    def test_路由表里没有_DRF_的_format_后缀族(self):
        """`\\.(?P<format>[a-z0-9]+)/?$` 是 DRF 运行时生成的，前端从不用它。

        它本来就不该出现 —— 这个解析器只从 `path()` / `re_path()` / `router.register()`
        这几处 AST 节点取路由，运行时生成的那一族不在源码里。这条锁的是「别哪天有人
        『顺手』把它按字符串切开塞进来」：那会多认一批永远匹配不上任何前端的假路由。
        """
        routes, _ = backend_routes()
        offenders = [r for r in routes if any('format' in (s or '') for s in r)]
        self.assertEqual(offenders, [], f'路由表里混进了 format 后缀族：{offenders}')


class ParserShape(unittest.TestCase):
    """解析器的形状自证 —— 在**合成样例**上跑，不依赖仓库现状。

    每条都对着一个真的会踩的坑：`<path:path>` 兜底、`re_path` 命名组、整行注释里的反面
    示例、以及「`router.register` 了但类里没有 `list`」。
    """

    def test_路径切段(self):
        self.assertEqual(_segments('redis/info/'), ('redis', 'info'))
        self.assertEqual(_segments('v1/<path:path>'), ('v1', '**'))
        self.assertEqual(_segments('conversations/<int:pk>/'), ('conversations', None))
        self.assertEqual(_segments(r'^v1/models/(?P<model_id>[^/]+)$'), ('v1', 'models', None))
        self.assertEqual(_segments(''), ())

    def test_action_的_url_path_可以是多段也可以带命名组(self):
        """`url_path='update_channel/(?P<pk>[^/.]+)'` 与 `url_path='email_config/test'`。

        把整个 url_path 当成一个段，`/users/admin-recharge/update_channel/9/` 这类调用
        就会全部变成「没有落点」—— 本轮当场踩到，6 条路由一起失踪。
        """
        self.assertEqual(_segments('update_channel/(?P<pk>[^/.]+)'), ('update_channel', None))
        self.assertEqual(_segments('email_config/test'), ('email_config', 'test'))
        self.assertEqual(_segments('batch_delete'), ('batch_delete',))

    def test_兜底段能吃掉剩下一整串(self):
        self.assertTrue(route_matches(('v1', '**'), ('v1', 'chat', 'completions')))
        self.assertTrue(route_matches(('v1', '**'), ('v1',)))
        self.assertFalse(route_matches(('v1', 'models'), ('v1', 'models', 'x')))

    def test_动态段只匹配一段(self):
        self.assertTrue(route_matches(('conversations', None, 'clear'),
                                      ('conversations', '7', 'clear')))
        self.assertFalse(route_matches(('conversations', None),
                                       ('conversations', '7', 'clear')))

    def test_静态段必须逐字相等(self):
        self.assertTrue(route_matches(('users', 'auth'), ('users', 'auth')))
        self.assertFalse(route_matches(('users', 'auth'), ('users', 'authz')))

    def test_整行注释里的调用不被采集(self):
        fake = ("// api.post('/users/auth/send_reset_code/', { email })\n"
                "api.get('/users/keys/')\n")
        found = [m.group('path') for m in CALL_RE.finditer(_lines_without_whole_line_comments(fake))]
        self.assertEqual(found, ['/users/keys/'],
                         '整行注释里的调用被当成真调用了 —— 本仓注释里就写着已经修掉的路径')

    def test_行首不是_api_的不被采集(self):
        cleaned = _lines_without_whole_line_comments("notapi.get('/nope/')\n")
        self.assertEqual([m.group('path') for m in CALL_RE.finditer(cleaned)], [])

    def test_确实解析到了仓库里的三种调用形态(self):
        """`api.*` / `axios.*` / `fetch(` 三种形态都真的被采到了。

        只加 `api.*` 会漏掉 `Home.vue` 的 `fetch(`${apiBase}/models/models/public_pricing/`)`
        与 `APIDoc.vue` 的两处 `axios.*` —— 漏采集就是假绿那一侧。
        """
        calls, _ = frontend_calls()
        kinds = {(c['loc'].split(':')[0], c['verb']) for c in calls}
        paths = {c['raw'] for c in calls}
        self.assertIn('src/views/Home.vue', {k[0] for k in kinds},
                      'Home.vue 的 fetch 调用没被采集到')
        self.assertTrue(any('apiBaseUrl.value' in p for p in paths),
                        'APIDoc.vue 的 axios 调用没被采集到')


class FrontendNeverCallsAMissingEndpoint(unittest.TestCase):
    """正题：前端每一处调用都要有落点，例外必须登记。"""

    def test_每一处调用都落到一条真实路由上(self):
        routes, _ = backend_routes()
        calls, _ = frontend_calls()
        bad = unresolved_calls(routes, calls)
        unexplained = [f"{c['loc']} {c['verb']} {c['raw']}"
                       for c in bad if c['raw'] not in KNOWN_UNRESOLVED]
        self.assertEqual(
            unexplained, [],
            '前端在这些地方调了后端不存在的接口（用户点到那一刻才 404，构建与测试全绿）：\n  '
            + '\n  '.join(sorted(unexplained))
            + '\n\n要么修前端/补后端，要么在 KNOWN_UNRESOLVED 里写明为什么它就该没有落点。',
        )

    def test_登记表里没有僵尸条目(self):
        """登记过的例外必须**仍然**真的解析不到 —— 修好了却留在表里，等于开了个后门。"""
        routes, _ = backend_routes()
        calls, _ = frontend_calls()
        bad_raws = {c['raw'] for c in unresolved_calls(routes, calls)}
        stale = sorted(k for k in KNOWN_UNRESOLVED if k not in bad_raws)
        self.assertEqual(
            stale, [],
            f'这些例外已经不需要了（路径改了或后端补上了），请从 KNOWN_UNRESOLVED 删掉：{stale}',
        )


if __name__ == '__main__':
    unittest.main()
