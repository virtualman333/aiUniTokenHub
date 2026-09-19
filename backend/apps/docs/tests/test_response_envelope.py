# -*- coding: utf-8 -*-
"""「响应统一走 `{code, msg, data}` 信封」这句话，谁在扛 —— 此前的落点是空的。

为什么要有它
------------
`AGENTS.md` 里写着 API 响应走 `apps.utils.response.APIResponse` 的信封，而且写死了
「**The only deliberate exception** is the OpenAI/Anthropic-compatible surface under
`/api/proxy/v1/...`」。这是一句**覆盖面声明**，而它此前没有任何东西在扛：

  · `apps/users/views_usage_log.py::APIAccessLogViewSet` 没重写 `list` → 走 DRF 默认
    实现 → `/api/users/usage-logs/` 返回**裸数组**（没有 `total`、没有 `page_size` 上限），
    前端只能写 `res.results || res || []` 去猜；
  · `apps/ai_models/upstream_views.py::UpstreamAccountViewSet` 同一个洞；
  · 两次都是**手工**发现的。AGENTS.md 甚至把结论写下来了 ——
    "'which viewsets never override `list()`' is a question grep answers, not one you
    should assume" —— 但**把它写成一句话不等于有人问**。

本轮（2026-09-20）实测 `router.register` 注册的 21 个视图：6 个有**继承来的标准动作**
（共 17 个端点），另有 8 个 `@action` 直接 `return Response(...)`。其中唯一落在**读路径**
上的是 `ModelCategoryViewSet.list`（`AllowAny` 的公开接口、返回裸数组），本轮已修；其余
登记在 `ENVELOPE_DEBT` 里，表与实测两向对账。

这一层能静态回答什么
--------------------
只回答一个问题：**服务这个端点的是本仓写的代码，还是 DRF 悄悄补上的默认实现。**
后者返回的一定不是信封（`Response(serializer.data)` / `Response(status=204)`），
这不是猜的，是 DRF 的默认实现本身。

刻意**不**做的：不检查本仓写的那些动作**正文里**用了哪个 helper。那要跑起来才知道形状，
而这一层的约定是纯标准库、不碰数据库、不碰 Django（`run_tests.py` 抬头）；假装能查
只会给出一种「看着像有人在查」的错觉。所以这里只钉「有没有人写」+「写了没走信封的要登记」。

扫描面（宇宙）刻意收在 `router.register` 上：`path(..., X.as_view({...}))` 挂的视图，
动作是**写出来**的，DRF 不会凭空补 —— 那类里没有这个洞。
"""
import ast
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]


#: DRF 里「会凭空长出动作」的基类：定义在它上面的动作，子类不重写就会用 DRF 的默认实现。
#: `ModelViewSet` / `ReadOnlyModelViewSet` 是它们的组合，拆开列是为了让「只继承了某一个
#: mixin」这种写法也能被看见。
STANDARD_ACTIONS = {
    'ModelViewSet': {'list', 'create', 'retrieve', 'update', 'partial_update', 'destroy'},
    'ReadOnlyModelViewSet': {'list', 'retrieve'},
    'ListModelMixin': {'list'},
    'CreateModelMixin': {'create'},
    'RetrieveModelMixin': {'retrieve'},
    'UpdateModelMixin': {'update', 'partial_update'},
    'DestroyModelMixin': {'destroy'},
}

#: 明确**不带**标准动作的基类。写在这里的唯一理由是让「没见过的基类」能**报错**：
#: 默认当成「不带」就是假绿那一侧 —— 一个拼错的基类名会让整组端点凭空消失，而全绿。
PLAIN_BASES = {
    'APIView', 'GenericAPIView', 'ViewSet', 'GenericViewSet', 'View',
}

#: 解析面下限 —— 解析器走空（glob 变了、`urls.py` 改名）时，下面每一条「没有差异」都恒真。
#: 数值按实测写（2026-09-20：21 个 `router.register` 视图），留一点余量给正常的增删。
MIN_VIEWSETS = 12

#: 还没收进信封的地方 —— 这是**债**，不是豁免区。
#:
#:   · 键 = (定义文件, 类名)；
#:   · 值必须写明「为什么这一轮没收」。写成空话没有意义：本表的用处就是在下次有人
#:     碰这些类时，让他看到「这里知道自己欠着账」。
#:   · 表与实测**两向**对账：收干净了还留着 = 僵尸条目，会红（防止它变成一块记着
#:     陈年旧事的墓碑）。
ENVELOPE_DEBT = {
    ('apps/ai_models/views.py', 'AIModelViewSet'): (
        '标准动作里 create / update / partial_update / destroy 是继承来的；'
        '前端 3 处写操作（ModelManagement.vue 的 submitForm 与 deleteModel）都只 await '
        '后弹提示、不读响应体，所以形状此刻不影响用户。'
        '另有 5 个 @action（search / toggle_status / set_featured / batch_delete / '
        'batch_toggle_status）直接 return Response(...)。'
        '本轮只收「DRF 会凭空补上」这一类里已经影响读路径的那个类，'
        '没有顺手改这些端点的响应形状 —— 这一层没有集成测试兜底，改形状要靠一轮专门的活。'
    ),
    ('apps/ai_models/views.py', 'ModelProviderViewSet'): (
        '标准动作六个全部本地定义（本类就是参照实现），只剩 @action `active` 直接 '
        'return Response(...)，返回裸数组；前端 0 处调用（`providers/active` 无命中）。'
    ),
    ('apps/ai_models/upstream_views.py', 'UpstreamAccountViewSet'): (
        '标准动作里 retrieve / update / partial_update / destroy 是继承来的；'
        '前端 2 处落在继承动作上（ChannelManagement.vue 的 PATCH 与 DELETE），'
        '两处都只 await 后弹提示、不读响应体。@action `active` 同样直接 return Response(...)。'
    ),
    ('apps/tickets/views.py', 'TicketCategoryViewSet'): (
        '标准动作里 retrieve / partial_update 是继承来的；前端 0 处调用'
        '（`/tickets/categories/` 只有两处 GET 列表，list 是本地定义的）。'
    ),
    ('apps/tickets/views.py', 'TicketViewSet'): (
        '标准动作里 destroy 是继承来的；前端没有删除工单的入口（`grep "delete.*tickets"` '
        '在 `frontend/src` 下 0 命中），用户侧只有建单与读单，所以这个端点此刻没有消费者。'
    ),
    ('apps/users/views.py', 'APIKeyViewSet'): (
        '标准动作里 retrieve / update / partial_update 是继承来的；前端只调 `list`'
        '（本地定义）、`create`（本地定义）与 `revoke`（本地 @action），0 处落在继承动作上。'
    ),
}


def _parse(path):
    return ast.parse(path.read_text(encoding='utf-8'))


def _call_name(node):
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
    return None


def _const_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _decorator_name(node):
    if isinstance(node, ast.Call):
        return _call_name(node)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _base_names(node):
    """类声明的基类名 —— `viewsets.ModelViewSet` 与 `ModelViewSet` 都取末段。"""
    out = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            out.append(base.id)
        elif isinstance(base, ast.Attribute):
            out.append(base.attr)
    return out


def _relative_imports(tree):
    """`from .views import X` → `{'X': 'views'}`（只认应用内相对导入）。"""
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            for alias in node.names:
                out[alias.asname or alias.name] = node.module
    return out


def _class_facts(path, class_name):
    """一个类 → `(基类名, 本地定义的方法名集合, 裸 Response 的 @action 名集合)`。

    类不存在时返回 `None` —— 那是**解析失败**，调用方必须报错，不能当成「这个类没有
    任何动作」：那会静默少一批端点，方向恰好是假绿。
    """
    if not path.is_file():
        return None
    for node in _parse(path).body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        methods = set()
        bare = set()
        for item in node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            methods.add(item.name)
            if not any(_decorator_name(d) == 'action' for d in item.decorator_list):
                continue
            # `return Response(...)` 而整个函数里没有 `APIResponse` —— 走的是裸 Response。
            # 用 AST 的调用节点而不是文本搜索：抬头/注释里引一句反面教材不该算。
            has_bare_response = any(
                isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'Response'
                for n in ast.walk(item)
            )
            uses_envelope = 'APIResponse' in ast.dump(item)
            if has_bare_response and not uses_envelope:
                bare.add(item.name)
        return _base_names(node), methods, bare
    return None


def repo_classes():
    """全仓 `apps/**/*.py`（跳过 `tests/` 与 `__pycache__`）→ `{类名: [(文件, 基类, 方法)]}`。

    「本仓自定义基类」要能穿透解析（`AdminDashboardViewSet(AnalyticsViewSet, GenericViewSet)`
    里的 `AnalyticsViewSet` 是本仓的一个纯 mixin），否则遇到它只能装作「不带标准动作」。
    """
    out = {}
    for path in sorted(BACKEND.glob('apps/**/*.py')):
        rel = path.relative_to(BACKEND).as_posix()
        if '/tests/' in rel or '__pycache__' in rel:
            continue
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.ClassDef):
                methods = {n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
                out.setdefault(node.name, []).append((rel, _base_names(node), methods))
    return out


def inherited_standard_actions(bases, methods, repo_bases):
    """**纯函数**：算出「继承来的标准动作」，以及「没见过的基类名」。

    `bases` 是这个类的基类名；`methods` 是类里已定义的方法名；`repo_bases` 是
    「本仓自定义基类 → 它自己的基类」的查表（用于穿透解析）。

    单独拆出来是为了让判据**可证伪**：合成样例能直接喂给它（见 `JudgeIsFalsifiable`），
    而不用去改仓库里的真实代码。
    """
    collected = set()
    unknown = set()
    seen = set()

    def walk(names):
        for name in names:
            if name in seen:
                continue
            seen.add(name)
            if name in STANDARD_ACTIONS:
                collected.update(STANDARD_ACTIONS[name])
            elif name in repo_bases:
                walk(repo_bases[name])
            elif name not in PLAIN_BASES:
                unknown.add(name)

    walk(bases)
    return collected - set(methods), unknown


def routed_viewsets():
    """→ `(清单, 问题清单)`。

    清单项：`{'rel', 'cls', 'file', 'inherited': 集合, 'bare_actions': 集合}`；
    问题清单非空时必须报错（找不到类 / 基类不认识 / 类名有歧义）—— 每一条都是
    「少算了一批端点」或「装作没有动作」的方向，即假绿。
    """
    registry = repo_classes()
    repo_bases = {name: entries[0][1] for name, entries in registry.items() if len(entries) == 1}
    items = []
    problems = []

    for path in sorted(BACKEND.glob('apps/*/urls.py')):
        rel = path.relative_to(BACKEND).as_posix()
        app_dir = path.parent
        tree = _parse(path)
        imports = _relative_imports(tree)
        for node in ast.walk(tree):
            if _call_name(node) != 'register' or len(node.args) < 2:
                continue
            sub = _const_str(node.args[0])
            target = node.args[1]
            if sub is None:
                problems.append(f'{rel}: router.register 的第一个参数不是字符串字面量')
                continue
            if isinstance(target, ast.Name):
                cls, mod = target.id, imports.get(target.id)
            elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                cls, mod = target.attr, target.value.id
            else:
                problems.append(f'{rel}: router.register({sub!r}, ...) 的视图不是名字/属性访问，解析不了')
                continue
            if mod is None:
                problems.append(f'{rel}: router.register 指到 {cls}，但相对 import 里没有它')
                continue
            file = app_dir / (mod.replace('.', '/') + '.py')
            facts = _class_facts(file, cls)
            if facts is None:
                problems.append(f'{rel}: 在 {mod}.py 里找不到类 {cls} —— 解析失败会让整组端点凭空消失')
                continue
            bases, methods, bare = facts
            inherited, unknown = inherited_standard_actions(bases, methods, repo_bases)
            for name in sorted(unknown):
                problems.append(f'{rel}: {cls} 的基类 {name} 既不在本仓、也不在已知的 '
                                f'DRF 基类名单里 —— 不敢默认它不带标准动作')
            items.append({'rel': rel, 'cls': cls,
                          'file': f'apps/{app_dir.name}/{mod.replace(".", "/")}.py',
                          'inherited': inherited, 'bare_actions': bare})
    return items, problems


def envelope_debt():
    """实测的债：`{(定义文件, 类名): {'inherited': …, 'bare_actions': …}}`。"""
    items, _ = routed_viewsets()
    out = {}
    for item in items:
        if item['inherited'] or item['bare_actions']:
            key = (item['file'], item['cls'])
            entry = out.setdefault(key, {'inherited': set(), 'bare_actions': set()})
            entry['inherited'] |= item['inherited']
            entry['bare_actions'] |= item['bare_actions']
    return out


class ParserIsNotVacuous(unittest.TestCase):
    """解析面自证 —— 解析器走空时，下面每一条「没有差异」都会恒真。"""

    def test_解析出的视图数过了下限(self):
        items, problems = routed_viewsets()
        self.assertEqual(problems, [], '路由/视图解析出了问题：\n  ' + '\n  '.join(problems))
        names = {f'{i["file"]}::{i["cls"]}' for i in items}
        self.assertGreaterEqual(
            len(names), MIN_VIEWSETS,
            f'只解析出 {len(names)} 个 router 注册的视图（下限 {MIN_VIEWSETS}）—— 解析器多半没在干活',
        )
        # 几个必须出现的落点：本轮的债表就是围着它们写的
        self.assertIn('apps/ai_models/views.py::AIModelViewSet', names)
        self.assertIn('apps/ai_models/views.py::ModelCategoryViewSet', names)
        self.assertIn('apps/ai_models/upstream_views.py::UpstreamAccountViewSet', names)


class JudgeIsFalsifiable(unittest.TestCase):
    """判据本身在**合成样例**上跑一遍 —— 证明它真的能抓到「继承来的动作」。

    只查仓库现状是不够的：万一哪天 `STANDARD_ACTIONS` 被改成空表，
    「没有任何视图继承动作」也会全绿，而那时判据已经死了。
    """

    def test_继承来的_list_会被抓到(self):
        inherited, unknown = inherited_standard_actions(
            ['ModelViewSet'], {'get_permissions', 'active'}, {},
        )
        self.assertIn('list', inherited, '继承来的 list 没被抓到 —— 判据是死的')
        self.assertEqual(inherited, {'list', 'create', 'retrieve',
                                     'update', 'partial_update', 'destroy'})
        self.assertEqual(unknown, set())

    def test_本地定义过的动作不算继承(self):
        inherited, _ = inherited_standard_actions(
            ['ModelViewSet'], {'list', 'create'}, {},
        )
        self.assertNotIn('list', inherited)
        self.assertNotIn('create', inherited)

    def test_本仓自定义基类要穿透解析(self):
        # `class X(AnalyticsViewSet, GenericViewSet)`：AnalyticsViewSet 是纯 mixin
        inherited, unknown = inherited_standard_actions(
            ['AnalyticsViewSet', 'GenericViewSet'], {'overview'}, {'AnalyticsViewSet': []},
        )
        self.assertEqual(inherited, set())
        self.assertEqual(unknown, set())
        # 反过来：自定义基类自己继承了 ModelViewSet，也必须穿透到
        inherited2, _ = inherited_standard_actions(
            ['MyBase'], set(), {'MyBase': ['ModelViewSet']},
        )
        self.assertIn('list', inherited2)

    def test_没见过的基类名会报出来而不是当成没有动作(self):
        _inherited, unknown = inherited_standard_actions(['ModelViewSetX'], set(), {})
        self.assertEqual(unknown, {'ModelViewSetX'},
                         '拼错的基类名被当成「不带标准动作」了 —— 那会让整组端点凭空消失')


class EnvelopeClaimHasAnOwner(unittest.TestCase):
    """正题：`router.register` 的视图，DRF 悄悄补上的动作必须有人管。"""

    def test_没有任何视图的_list_是继承来的(self):
        """`list` 单独拎出来说一句 —— AGENTS.md 点名的就是这个洞。

        继承来的 `list` 就是裸数组：没有 `total`、没有 `page_size` 上限、也没有信封。
        本仓已经手工修过两次（`APIAccessLogViewSet`、`UpstreamAccountViewSet`），
        都是**读路径**上的真实缺陷，所以这一类**零容忍**：连登记都不给。
        """
        items, _ = routed_viewsets()
        offenders = sorted(f'{i["file"]}::{i["cls"]}' for i in items if 'list' in i['inherited'])
        self.assertEqual(
            offenders, [],
            '这些视图的 list 走的是 DRF 默认实现 —— `/api/.../` 会返回裸数组'
            '（没有 total、没有 page_size 上限），而文档说走统一信封。'
            '照同文件里的 `ModelProviderViewSet` 补一个 `list()`：\n  ' + '\n  '.join(offenders),
        )

    def test_剩下的债与登记表两向对账(self):
        actual = envelope_debt()
        registered = {k: v for k, v in ENVELOPE_DEBT.items()}
        missing = sorted(f'{f}::{c}' for f, c in set(actual) - set(registered))
        stale = sorted(f'{f}::{c}' for f, c in set(registered) - set(actual))
        self.assertEqual(
            missing, [],
            '这些地方有继承来的标准动作（或裸 Response 的 @action）却没登记：\n  '
            + '\n  '.join(missing)
            + '\n\n要么按参照实现收进信封，要么在 ENVELOPE_DEBT 里写明为什么这一轮不收。',
        )
        self.assertEqual(
            stale, [],
            '这些类已经收干净了，登记表里还留着 —— 僵尸条目会让这张表慢慢变成一块'
            '记着陈年旧事的墓碑，请删掉：\n  ' + '\n  '.join(stale),
        )

    def test_每条债都写明了理由(self):
        for (file, cls), why in ENVELOPE_DEBT.items():
            with self.subTest(cls=cls):
                self.assertIsInstance(why, str)
                self.assertGreaterEqual(
                    len(why.strip()), 40,
                    f'{file}::{cls} 的登记理由只有 {len(why.strip())} 个字 —— '
                    '「还没做」不是理由，写清谁在消费它、为什么不影响用户。',
                )

    def test_登记表覆盖了实测的每一个动作(self):
        """对账不只对类名，还要对**动作名** —— 否则新出现的动作可以藏在已登记的类里。"""
        actual = envelope_debt()
        for (file, cls), entry in sorted(actual.items()):
            with self.subTest(cls=cls):
                registered = ENVELOPE_DEBT.get((file, cls))
                self.assertIsNotNone(registered, f'{file}::{cls} 没进登记表')
                for action in sorted(entry['inherited'] | entry['bare_actions']):
                    self.assertIn(
                        action, registered,
                        f'{file}::{cls} 的 `{action}` 是继承来的（或裸 Response），'
                        f'而登记理由里一个字都没提到它 —— 新欠的账要自己说出来。',
                    )


if __name__ == '__main__':
    unittest.main()
