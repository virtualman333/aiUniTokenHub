# -*- coding: utf-8 -*-
"""工单附件的用例（纯函数，不连数据库）—— `apps/tickets/` 的第一份测试。

这一份为什么存在
----------------
`run_tests.py` 的 `NO_TESTS_YET['tickets']` 里原本写着：不碰库的只有
`models.py` 的 `ticket_image_upload_path`，「要测它得先抽成无 Django 依赖的模块
（照 `apps/utils/api_errors.py` 的做法），待补」。那句「待补」就是没人扛的承诺
—— 468 行的 app 一直零覆盖，而全仓输出始终是 `OK —— N 例全部通过`。

现在那个模块是 `apps/tickets/attachments.py`，这份用例钉的就是它，以及它把三处
缺陷从视图里顶出来的结果：

  1. `image_ids="12"` 从前会被 `id__in` **按字符拆开**，绑到第 1、2 张图上
     （而 `len("12") == 2`，上限也拦不住）；
  2. 「最多关联 5 张」从前判在**写库之后** —— 400 里夹着一条已经落库的工单；
  3. 绑定 `update()` 影响 0 行不报错 —— 「提交成功」但工单里一张图都没有。

第 2、3 条必须连数据库才能真跑（本机没有可用的 MySQL，也不该往真库上打），
所以它们用 **AST 读源码** 钉形状：锚点是「同一个方法里，`parse_image_ids` 的
行号必须早于第一处写库」与「绑图只有一条路径」。这类检查比行为检查弱，
但它至少是**可证伪**的 —— 见本轮负向验证（把 parse 挪到 save 后面，这两条立刻红）。

跑法（在 backend/ 下）：python run_tests.py
"""
import ast
import re
import unittest
from pathlib import Path

from apps.tickets.attachments import (
    ALLOWED_IMAGE_TYPES,
    IMAGE_FORMAT_LABELS,
    MAX_IMAGE_BYTES,
    MAX_IMAGES,
    UNASSIGNED_DIR,
    allowed_types_message,
    max_size_message,
    parse_image_ids,
    partial_binding_error,
    upload_dir,
    upload_path,
)

BACKEND = Path(__file__).resolve().parents[3]
ROOT = BACKEND.parent
VIEWS = BACKEND / 'apps/tickets/views.py'
MODELS = BACKEND / 'apps/tickets/models.py'
UPLOAD_COMPONENT = ROOT / 'frontend/src/components/ImageUpload.vue'


def read(path):
    """按字节读再解码 —— 文本模式会把 CRLF 翻成 LF，比对时凭空不等。"""
    return path.read_bytes().decode('utf-8')


class 收图片idTest(unittest.TestCase):
    """`parse_image_ids` —— 请求体 → 可信 id 清单。"""

    def test_缺省与None都是空清单(self):
        for raw in (None, []):
            with self.subTest(raw=raw):
                ids, error = parse_image_ids(raw)
                self.assertEqual(ids, [])
                self.assertIsNone(error)

    def test_数字数组(self):
        self.assertEqual(parse_image_ids([3, 1, 2]), ([3, 1, 2], None))

    def test_数字字符串也认(self):
        # 表单与 query 里拿到的都是字符串，不认它等于前端一传就 400
        self.assertEqual(parse_image_ids(['7', '8']), ([7, 8], None))

    def test_混着来(self):
        self.assertEqual(parse_image_ids(['3', 4]), ([3, 4], None))

    def test_元组也认(self):
        self.assertEqual(parse_image_ids((1, 2)), ([1, 2], None))

    def test_首尾空白不算错(self):
        self.assertEqual(parse_image_ids([' 7 ']), ([7], None))

    def test_去重且保持顺序(self):
        # 前端把同一张图塞两次不该报错，也不该绑两次
        self.assertEqual(parse_image_ids([3, 1, 3, 2, 1]), ([3, 1, 2], None))

    def test_刚好5张可以(self):
        self.assertEqual(parse_image_ids([1, 2, 3, 4, 5]), ([1, 2, 3, 4, 5], None))

    def test_全部重复也算一张不算超限(self):
        # 上限按**去重后**算：点两次同一张不该被拒
        self.assertEqual(parse_image_ids([4] * 9), ([4], None))


class 坏形状一律拒Test(unittest.TestCase):
    """坏输入必须拿到一句能看懂的话，而且**必须在写库之前**。"""

    def assertRejected(self, raw):
        ids, error = parse_image_ids(raw)
        self.assertEqual(ids, [], f'{raw!r} 不该被收下')
        self.assertIsNotNone(error, f'{raw!r} 不该被收下')
        return error

    def test_整体是字符串(self):
        # ★ 本轮缺陷 1：'12' 从前会让 id__in 变成 IN ('1','2')，绑错图
        error = self.assertRejected('12')
        self.assertIn('按字符拆开', error)

    def test_单个数字的字符串也是字符串(self):
        # '1' 拆开还是 ['1']，看上去没事；但形状是错的，照样拒
        self.assertRejected('1')

    def test_set不接受(self):
        # 顺序不定，且 JSON 里没有这种形状
        self.assertRejected({1, 2})

    def test_整数不接受(self):
        self.assertRejected(12)

    def test_布尔不接受(self):
        # True 是 int 的子类，放过去等于 id=1
        self.assertRejected([True])
        self.assertRejected([False])

    def test_零与负数不接受(self):
        self.assertRejected([0])
        self.assertRejected([-1])

    def test_非数字字符串不接受(self):
        self.assertRejected(['abc'])
        self.assertRejected(['1.5'])
        self.assertRejected(['1,2'])

    def test_全角数字不接受(self):
        # '１２'.isdigit() 是 True，int('１２') 也收得下 —— 但不收，口径统一为 ASCII
        self.assertRejected(['１２'])

    def test_None元素不接受(self):
        self.assertRejected([None])
        self.assertRejected([1, None])

    def test_超过5张(self):
        error = self.assertRejected([1, 2, 3, 4, 5, 6])
        self.assertEqual(error, f'最多关联{MAX_IMAGES}张图片')

    def test_超限的提示语与从前逐字一致(self):
        # 老接口就回的这句，前端按 msg 展示 —— 措辞不许漂
        _, error = parse_image_ids([1, 2, 3, 4, 5, 6])
        self.assertEqual(error, '最多关联5张图片')


class 绑定之后的核对Test(unittest.TestCase):
    """`partial_binding_error` —— 「绑了几张」必须有人看。"""

    def test_全绑上不报(self):
        self.assertIsNone(partial_binding_error(3, 3))

    def test_一张都没有时不算失败(self):
        self.assertIsNone(partial_binding_error(0, 0))

    def test_少一张要说清少几张(self):
        error = partial_binding_error(3, 2)
        self.assertIsNotNone(error)
        self.assertIn('有 1 张', error)

    def test_一张都没绑上(self):
        # ★ 本轮缺陷 3 的形状：update() 影响 0 行，从前这里返回 None
        error = partial_binding_error(3, 0)
        self.assertIsNotNone(error)
        self.assertIn('有 3 张', error)

    def test_绑多了不报负数(self):
        # 正常不该发生；真发生了也不该说「有 -2 张」
        self.assertIsNone(partial_binding_error(3, 5))


class 上传路径Test(unittest.TestCase):
    """`upload_path` / `upload_dir` —— 上传目录的单一来源。"""

    def test_没有归属时是unassigned而不是None(self):
        # ★ 本轮缺陷 5：upload_to 在保存那一刻求值，而工单那时还不存在，
        #   于是老代码永远算出 tickets/None/xxxx.png —— 目录名在谎报一个工单号
        self.assertEqual(
            upload_path(None, 'a.png', 'tok'), f'tickets/{UNASSIGNED_DIR}/tok.png'
        )
        self.assertNotIn('/None/', upload_path(None, 'a.png', 'tok'))

    def test_有归属时用工单号(self):
        self.assertEqual(upload_path(7, 'a.png', 'tok'), 'tickets/7/tok.png')

    def test_没有扩展名(self):
        self.assertEqual(upload_path(7, 'README', 'tok'), 'tickets/7/tok')

    def test_扩展名原样保留不改大小写(self):
        # 有意为之：不偷偷改写用户给的扩展名
        self.assertEqual(upload_path(7, 'Shot.PNG', 'tok'), 'tickets/7/tok.PNG')

    def test_原名里的目录不进入路径(self):
        # 原名只取尾部扩展名，路径里不该出现用户提供的任何目录片段
        path = upload_path(7, '../../../etc/passwd.png', 'tok')
        self.assertEqual(path, 'tickets/7/tok.png')
        self.assertNotIn('..', path)
        self.assertNotIn('etc', path)

    def test_文件名只有后缀时也安全(self):
        self.assertEqual(upload_path(7, '.bashrc', 'tok'), 'tickets/7/tok')

    def test_非法归属时退回unassigned(self):
        for bad in (0, -3, True, '7', None, ''):
            with self.subTest(ticket_id=bad):
                self.assertEqual(upload_dir(bad), f'tickets/{UNASSIGNED_DIR}')

    def test_dir与path同源(self):
        # path 必须真的走 dir，而不是各拼一遍
        self.assertTrue(upload_path(12, 'x.png', 't').startswith(upload_dir(12) + '/'))


class 提示语由表生成Test(unittest.TestCase):
    """白名单与上限只有一处，提示语从它生成。"""

    def test_格式提示语覆盖表里每一项且顺序一致(self):
        message = allowed_types_message()
        labels = list(IMAGE_FORMAT_LABELS.values())
        self.assertEqual(message, '只支持 ' + '、'.join(labels) + ' 格式的图片')
        for label in labels:
            self.assertIn(label, message)

    def test_格式提示语与从前逐字一致(self):
        # 前端与老文档里都是这句，措辞不许漂
        self.assertEqual(allowed_types_message(), '只支持 JPG、PNG、GIF、WebP 格式的图片')

    def test_白名单四项(self):
        self.assertEqual(
            list(ALLOWED_IMAGE_TYPES),
            ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
        )

    def test_上限提示语里的兆数从常量算(self):
        # 把句子里的数字**抠出来**跟常量比 —— 不是把同一个表达式再写一遍
        message = max_size_message()
        found = re.findall(r'\d+', message)
        self.assertEqual(len(found), 1, f'提示语里的数字不只一个：{message!r}')
        self.assertEqual(int(found[0]), MAX_IMAGE_BYTES // (1024 * 1024))

    def test_上限提示语与从前逐字一致(self):
        self.assertEqual(max_size_message(), '图片大小不能超过5MB')

    def test_一次的张数上限是5(self):
        self.assertEqual(MAX_IMAGES, 5)


class 前端那份白名单对账Test(unittest.TestCase):
    """同一件事在 `ImageUpload.vue` 里又写了一遍 —— 两份必须逐项一致。

    这条比「两边各自断言」值钱：两边各自看都对，只有放在一起才看得出漂移
    （比如后端收 WebP、前端拦掉 WebP，用户看到的是「只能上传 JPG、PNG、GIF」，
    而接口其实收得下 —— 谁也说不清哪个是 bug）。
    """

    def setUp(self):
        # 扫描面自证：文件没找到 / 正则没命中时，绝不能让下面几条**静默通过**
        self.assertTrue(
            UPLOAD_COMPONENT.exists(), f'找不到前端上传组件：{UPLOAD_COMPONENT}'
        )
        self.source = read(UPLOAD_COMPONENT)

    def test_两边认的格式逐项一致(self):
        found = re.findall(r"'(image/[a-z]+)'", self.source)
        self.assertTrue(found, '没在组件里找到格式白名单 —— 这条检查没在检查')
        self.assertEqual(
            found, list(ALLOWED_IMAGE_TYPES),
            f'{UPLOAD_COMPONENT.name} 的格式白名单与后端不一致',
        )

    def test_两边的大小上限一致(self):
        found = re.search(r'file\.size\s*/\s*1024\s*/\s*1024\s*<\s*(\d+)', self.source)
        self.assertIsNotNone(found, '没在组件里找到大小上限 —— 这条检查没在检查')
        self.assertEqual(
            int(found.group(1)), MAX_IMAGE_BYTES // (1024 * 1024),
            f'{UPLOAD_COMPONENT.name} 的大小上限与后端不一致',
        )

    def test_两边的一次张数上限一致(self):
        found = re.search(
            r'maxCount:\s*\{\s*type:\s*Number,\s*default:\s*(\d+)', self.source
        )
        self.assertIsNotNone(found, '没在组件里找到 maxCount 默认值 —— 这条检查没在检查')
        self.assertEqual(int(found.group(1)), MAX_IMAGES)


class 接线层Test(unittest.TestCase):
    """视图/模型有没有真的用上去 —— AST 读源码，比行为检查弱，但可证伪。

    行为检查需要数据库，本机没有可用的 MySQL；退而钉形状。每条锚点都要求
    「命中恰好一处 / 每条入口都要过」，并在测试里自证扫描面（入口数量、
    文件存在），免得写成一条永远不会红的检查。
    """

    def setUp(self):
        self.assertTrue(VIEWS.exists(), f'找不到 {VIEWS}')
        self.assertTrue(MODELS.exists(), f'找不到 {MODELS}')
        self.source = read(VIEWS)
        self.tree = ast.parse(self.source, filename=str(VIEWS))

    @staticmethod
    def _write_lines(sub):
        """一棵树里「写库」的行号：save / create / update / bulk_create。

        （`filter` 不算写，所以绑定可以被拆成单独一条路。）
        """
        return [
            child.lineno
            for child in ast.walk(sub)
            if isinstance(child, ast.Call)
            and isinstance(child.func, ast.Attribute)
            and child.func.attr in ('save', 'create', 'update', 'bulk_create')
        ]

    @staticmethod
    def _parse_lines(sub):
        """一棵树里 `parse_image_ids(...)` 的行号。"""
        return [
            child.lineno
            for child in ast.walk(sub)
            if isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id == 'parse_image_ids'
        ]

    def _entry_points(self):
        """**视图方法**里会写库、又碰 `image_ids` 的 —— 即「带图的入口」。

        返回 `[(方法名, 段内第一处写库行号, 段内第一次校验行号, 源码片段)]`。
        今天恰好两条：create / reply。

        只认类里的方法：模块级的 `_bind_images` 自己也碰 `image_ids`、也写库，
        但它不是入口，而是**入口共用的那一条路**。

        ⚠ 两个行号都从 `ast.parse(片段)` 里取 —— 都是**段内**行号。
        本轮第一次写这条检查时，写库行号取的是 `node.lineno`（文件里的绝对行号），
        校验行号取的是片段里的相对行号，两边坐标系不同，比出来的结果恒为「早于」
        —— 把 `parse_image_ids` 整段挪到 `serializer.save()` 后面去，它照样绿。
        负向验证（D11）当场抓出来的。
        """
        found = []
        for cls in ast.walk(self.tree):
            if not isinstance(cls, ast.ClassDef):
                continue
            for node in cls.body:
                if not isinstance(node, ast.FunctionDef):
                    continue
                segment = ast.get_source_segment(self.source, node) or ''
                if 'image_ids' not in segment:
                    continue
                sub = ast.parse(segment)
                writes = self._write_lines(sub)
                if not writes:
                    continue
                parses = self._parse_lines(sub)
                found.append((
                    node.name, min(writes), min(parses) if parses else None, segment,
                ))
        return found

    def _entry_names(self):
        return [name for name, _, _, _ in self._entry_points()]

    def test_带图入口至少两条且都在名单里(self):
        # 扫描面自证：一条都没找到（或方法改名）时，下面几条会全部静默通过
        names = self._entry_names()
        self.assertGreaterEqual(len(names), 2, f'带图入口只找到 {names}')
        self.assertIn('create', names)
        self.assertIn('reply', names)

    def test_校验必须早于写库(self):
        # ★ 本轮缺陷 2 的形状：从前 len(image_ids) > 5 判在 serializer.save() 后面
        for name, write_line, parse_line, _ in self._entry_points():
            with self.subTest(method=name):
                self.assertIsNotNone(parse_line, f'{name}() 没有先调 parse_image_ids')
                self.assertLess(
                    parse_line, write_line,
                    f'{name}() 先写了库再校验图片 id —— 400 里会夹着一条已经落库的记录',
                )

    def test_每条入口都要么全成要么全不成(self):
        for name, _, _, segment in self._entry_points():
            with self.subTest(method=name):
                self.assertIn('transaction.atomic', segment, f'{name}() 没有事务')
                self.assertIn('_bind_images', segment, f'{name}() 没走绑图入口')
                self.assertIn('set_rollback', segment, f'{name}() 绑不满时没有回滚')

    def test_绑图只有一条路径(self):
        # 绑图若散成多处，就又会有一处忘记核对 update() 的返回值
        self.assertEqual(
            self.source.count('TicketImage.objects.filter('), 1,
            '绑图不止一条路径 —— 核对「绑了几张」这件事会重新变成可选项',
        )
        self.assertEqual(
            self.source.count('partial_binding_error('), 1,
            'partial_binding_error 的调用点不止一处',
        )

    def test_视图里不再手抄上限与白名单(self):
        # 消息由 attachments.py 生成；视图里再抄一遍，改了上限就会两处不一致。
        # 只查**字符串字面量**，不查注释 —— 注释里的引用不参与拼装，不该被算进来。
        literals = [
            node.value for node in ast.walk(self.tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]
        self.assertTrue(literals, '一个字符串字面量都没读到 —— 这条检查没在检查')
        for fragment in ('最多关联', '只支持 ', '图片大小不能超过'):
            with self.subTest(fragment=fragment):
                offenders = [s for s in literals if fragment in s]
                self.assertEqual(
                    offenders, [],
                    f'视图里又出现了手抄的 {fragment!r} —— 它该由 attachments.py 生成',
                )
        # 兆数字面上的魔法数（不是字符串，单独查一次源码文本）
        self.assertNotIn('5 * 1024 * 1024', self.source)

    def test_模型把路径拼装交给attachments(self):
        models_source = read(MODELS)
        self.assertIn('upload_path(', models_source)
        self.assertNotIn(
            'f"tickets/', models_source,
            'models.py 又在自己拼路径了 —— 那样 upload_path 的用例就测不到真实逻辑',
        )


if __name__ == '__main__':
    unittest.main()
