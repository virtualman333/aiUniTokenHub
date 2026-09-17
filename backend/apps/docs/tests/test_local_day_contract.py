# -*- coding: utf-8 -*-
"""仓库级契约：**按本地日查统计不许在 SQL 里做时区转换**（读文件，不调代码）。

这条缺陷长什么样
----------------
`created_at__date=X` / `TruncDate('created_at')` 在 MySQL 上会被 Django 编译成

    WHERE DATE(CONVERT_TZ(`created_at`, 'UTC', 'Asia/Shanghai')) = %s

`CONVERT_TZ` 的二三参数是**时区名**，走 MySQL 的时区表（`mysql.time_zone_name`）。
MySQL 默认不装这张表 → `CONVERT_TZ` 返回 **NULL** → 整个谓词恒为 NULL：
**一条都不匹配，而且不报错**。实测（`backend/.env` 指向的那个库）：

    SELECT CONVERT_TZ(NOW(), 'UTC', 'Asia/Shanghai');   -- NULL
    SELECT CONVERT_TZ(NOW(), '+00:00', '+08:00');       -- 2026-09-18 14:11:24

当时 `api_access_logs` 里有 **1616 条**记录，而这些数字全是 0 / 空：

| 位置 | 症状 |
| --- | --- |
| `dashboard.token_stats` 今日 token | 恒 0 |
| `dashboard.active_users` 今日活跃 / 近 7 天活跃 | 恒 0 |
| `dashboard.error_analysis` 错误码分布 | 恒空 |
| `dashboard.balance_runway` 余额续航 | **恒「暂无消耗记录」**（这个功能上线起就是死的） |
| `api_proxy.access_stats` 按天分组 | 分组键全 NULL，所有行塌成一组，`DateField()` 接不住 → **500** |

还有第二种、同一次发作的缺陷：`timezone.now().date()`。`now()` 是 UTC，
它的 `.date()` 是 **UTC 日期** —— 北京时间 0 点到 8 点之间它仍停在昨天，
于是「今天」整整错一天（数据没错，是槽位放错，看起来像「今天的还没出」），
跨月首日还会让「本月」错一整个月。正确的名字是 `timezone.localdate()`。

为什么不靠「代码评审」和「记得别这么写」
----------------------------------------
这两条在同一个仓库里各写过 9 处和 7 处，每一处单看都毫无破绽 ——
它们**跑得通、不报错、结果恒定**。所以这里把判据变成可执行的：

  1. 全仓源码里不许出现 `__date` / `TruncDate` / `TruncDay` 这些
     「让数据库来算时区」的写法；
  2. 不许出现 `timezone.now().date()`；
  3. 反向（只禁不引的话，把整个模块删掉也能全绿）：真正按本地日统计的那几个文件
     必须真的用 `apps/utils/timerange.py`。

扫描前**必须剥注释与 docstring**
--------------------------------
这条差点让我写出一个假红：`apps/utils/timerange.py` 的模块 docstring 与
`apps/dashboard/views.py` 的注释里**逐字**写着 `created_at__date`（用来解释
为什么不能这么写）。不剥的话这条检查会在**完全正确**的代码上判红，
然后被下一个人当成误报删掉。剥的实现见 `code_only()`，它把注释与 docstring
换成**等长空格**（保留行号与偏移，且不碰换行符）。

刻意**不**锁的东西
------------------
- 不锁 `date.today()`：`apps/utils/analytics.py` 与 `apps/dashboard/analytics_views.py`
  用它当 Redis key 的日期，**读和写用的是同一个函数**，自洽；它与 `settings.TIME_ZONE`
  的对齐是另一件事（见台账候选）。这一条只锁「同一个事实被写了两遍、其中一遍错」。
- 不锁 `apps/api_proxy/views.py::access_logs` 的 `__gte` / `__lte`：调用方传的是
  `dayjs().startOf('day')` / `.endOf('day')` 的完整 ISO **瞬间**，两端一开一闭，
  现在是对的（那两行有注释说明为什么和账单接口不一样）。
- 不锁措辞、顺序、空白。
"""
import ast
import io
import re
import tokenize
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]
APPS = BACKEND / 'apps'

#: 让数据库去算时区的写法。SQL 里出现 `CONVERT_TZ` 就是在赌「这台 MySQL 装了时区表」。
BANNED_SQL_TZ = {
    '__date': 'Django 会编译成 DATE(CONVERT_TZ(col, \'UTC\', tz))，本库的 MySQL 没装时区表 → 恒 NULL',
    'TruncDate': '同上：TruncBase 也走 CONVERT_TZ',
    'TruncDay': '同上',
    'TruncWeek': '同上',
    'TruncMonth': '同上',
    'ExtractDate': '同上',
}

#: `timezone.now()` 是 UTC，`.date()` 拿的是 UTC 日期 —— 北京时间 0~8 点之间错一天。
BANNED_UTC_DATE = re.compile(r'timezone\.now\(\)\s*\.\s*date\(\)')

#: 扫不到的目录。`tests/` 排除是因为本文件自己就在那里（否则它扫到自己 ——
#: 上面那些禁令字符串就写在它的 docstring 与常量里）。
SKIP_DIRS = {'__pycache__', 'migrations', 'tests', 'venv', '.git'}

#: 扫描面下限。收窄（比如改成写死的文件清单）会让下面几条断言变成恒真，
#: 而输出照样是 OK —— 本仓库为此栽过两次，所以这里钉一个下限。
MIN_FILES = 20
MIN_LINES = 2000

#: 定点探测：这几个文件一定要在扫描面里（它们正是本轮修过的地方）。
ANCHOR_FILES = (
    'apps/dashboard/views.py',
    'apps/api_proxy/views.py',
    'apps/users/views.py',
    'apps/utils/timerange.py',
)

#: 正向要求：按本地日统计的地方必须真的用 timerange，而不是自己算。
MUST_USE_TIMERANGE = (
    'apps/dashboard/views.py',
    'apps/api_proxy/views.py',
    'apps/users/views.py',
)


def source_files():
    for path in sorted(APPS.rglob('*.py')):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def code_only(src):
    """把注释与 docstring 换成**等长空格**，保留行号与偏移，不动换行符。

    为什么不用「先按行去掉 `#` 之后的内容」：`#` 会出现在字符串里
    （`APIAccessLog.objects.filter(path__startswith='#')` 这种）。
    为什么不用 `token/untokenize` 重建：那会重排空白，把行号弄乱，
    而下面的报告要按行号指出违规在哪。
    """
    masked = list(src)
    spans = []

    # docstring：Module / ClassDef / FunctionDef 的 body[0] 是裸字符串表达式
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, 'body', [])
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            spans.append((first.lineno, first.col_offset, first.end_lineno, first.end_col_offset))

    # 注释
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            spans.append((tok.start[0], tok.start[1], tok.end[0], tok.end[1]))

    offsets = [0]
    for line in src.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))

    for start_line, start_col, end_line, end_col in spans:
        begin = offsets[start_line - 1] + start_col
        stop = offsets[end_line - 1] + end_col
        for i in range(begin, min(stop, len(masked))):
            if masked[i] != '\n':
                masked[i] = ' '
    return ''.join(masked)


class TestCodeOnlyHelper(unittest.TestCase):
    """先证明「剥注释与 docstring」这一步真的在做事 —— 它是下面所有断言的地基。"""

    def test_注释被剥掉(self):
        src = 'x = 1  # created_at__date=y\n'
        self.assertNotIn('__date', code_only(src))

    def test_docstring_被剥掉(self):
        src = 'def f():\n    """别用 created_at__date。"""\n    return 1\n'
        self.assertNotIn('__date', code_only(src))

    def test_模块_docstring_被剥掉(self):
        src = '"""created_at__date 是坏的。"""\nimport os\n'
        self.assertNotIn('__date', code_only(src))

    def test_行号与换行保持不变(self):
        src = 'a = 1  # 注释\nb = 2\n"""\n多行\n"""\nc = 3\n'
        masked = code_only(src)
        self.assertEqual(masked.count('\n'), src.count('\n'))
        self.assertEqual(len(masked), len(src))
        self.assertEqual(masked.splitlines()[1], 'b = 2')

    def test_字符串里的井号不会被当成注释(self):
        src = "q = Model.objects.filter(path__startswith='#')\n__date = 1\n"
        masked = code_only(src)
        self.assertIn("path__startswith='#'", masked)
        self.assertIn('__date', masked, '真代码里的 __date 必须还在（否则这条检查是假的）')

    def test_真代码里的违规仍然可见(self):
        src = 'def f():\n    """别用 TruncDate。"""\n    return X.objects.filter(created_at__date=1)\n'
        masked = code_only(src)
        self.assertNotIn('TruncDate', masked)
        self.assertIn('created_at__date', masked)


class TestNoSqlTimezoneConversion(unittest.TestCase):
    """全仓源码不许让数据库去算时区。"""

    @classmethod
    def setUpClass(cls):
        cls.files = list(source_files())
        cls.masked = {}
        for path in cls.files:
            try:
                cls.masked[path] = code_only(path.read_text(encoding='utf-8'))
            except (SyntaxError, UnicodeDecodeError):
                # 语法错的文件由别的检查去管，这里不误报成时区问题
                cls.masked[path] = ''

    def rel(self, path):
        return path.relative_to(BACKEND).as_posix()

    def test_扫描面不许为空(self):
        self.assertGreaterEqual(len(self.files), MIN_FILES, '扫到的 .py 太少，扫描面被收窄了')
        total = sum(len(text.splitlines()) for text in self.masked.values())
        self.assertGreaterEqual(total, MIN_LINES, '扫到的行数太少，扫描面被收窄了')

    def test_定点探测_锚点文件都在扫描面里(self):
        present = {self.rel(p) for p in self.files}
        for anchor in ANCHOR_FILES:
            self.assertIn(anchor, present, '锚点文件不在扫描面里：%s' % anchor)

    def test_不许出现让数据库算时区的写法(self):
        offenders = []
        for path, text in self.masked.items():
            for lineno, line in enumerate(text.splitlines(), 1):
                for token, why in BANNED_SQL_TZ.items():
                    if token in line:
                        offenders.append('%s:%d [%s] %s\n    ← %s'
                                         % (self.rel(path), lineno, token, line.strip(), why))
        self.assertEqual(
            offenders, [],
            '这些地方让数据库去算时区了（本库的 MySQL 没装时区表，谓词会恒 NULL）：\n  '
            + '\n  '.join(offenders)
            + '\n改用 apps/utils/timerange.py 的 local_day_bounds()/local_day_start()，'
              '让 SQL 里只剩 `created_at >= ? AND created_at < ?`。',
        )

    def test_按本地日统计必须走_timerange(self):
        """反向：只禁不引的话，把 `apps/utils/timerange.py` 换成一个返回 UTC 零点的
        桩函数也能全绿。这里要求那几处**真的**用上了它。"""
        missing = []
        for rel in MUST_USE_TIMERANGE:
            path = BACKEND / rel
            self.assertTrue(path.exists(), '锚点文件不见了：%s' % rel)
            text = self.masked[path]
            if 'timerange' not in text and 'local_day' not in text:
                missing.append(rel)
        self.assertEqual(missing, [], '这些文件按本地日统计却没有用 timerange：%r' % missing)

    def test_不许用_UTC_日期当今天(self):
        offenders = []
        for path, text in self.masked.items():
            for lineno, line in enumerate(text.splitlines(), 1):
                if BANNED_UTC_DATE.search(line):
                    offenders.append('%s:%d %s' % (self.rel(path), lineno, line.strip()))
        self.assertEqual(
            offenders, [],
            '`timezone.now()` 是 UTC，`.date()` 是 **UTC 日期** —— 北京时间 0~8 点之间'
            '错一天，跨月首日还会让「本月」错一整个月。请改用 `timezone.localdate()`：\n  '
            + '\n  '.join(offenders),
        )

    def test_本轮修过的文件里不许再出现这两个形态(self):
        """把「本轮修过的地方」单独再锁一遍 —— 上面两条是全仓扫，
        这条保证**具体这几处**没有回退（全仓断言在文件被删/被排除时可能变松）。"""
        checked = 0
        for rel in ANCHOR_FILES:
            path = BACKEND / rel
            text = self.masked[path]
            checked += 1
            for token, why in BANNED_SQL_TZ.items():
                self.assertNotIn(token, text, '%s 里又出现了 %s（%s）' % (rel, token, why))
            self.assertIsNone(
                BANNED_UTC_DATE.search(text),
                '%s 里又用 timezone.now().date() 当今天了' % rel,
            )
        self.assertEqual(checked, len(ANCHOR_FILES), '锚点文件没扫全')


    def test_账单接口的结束日不许直接用_lte(self):
        """`apps/users/views.py::admin-bills` 的日期筛选参数是 `YYYY-MM-DD`。

        把它直接丢给 `created_at__lte` 会被 Django 解释成「当天 00:00」——
        用户选 `2026-09-01 ~ 2026-09-18`，**结束日一整天的账单一条都查不出来**，
        而界面上看不出任何异常。上界必须是「次日零点」的半开区间。

        断言的是**缺陷形态不存在**（`created_at__lte=end_date`），不是「正确代码
        长什么样」—— 后者会被格式化 / 改名弄红。
        """
        text = self.masked[BACKEND / 'apps/users/views.py']
        self.assertIn('admin-bills', text, '锚点不见了：admin-bills 接口')
        self.assertGreater(len(text.splitlines()), 300, '扫描面异常小')
        self.assertNotIn(
            'created_at__lte=end_date', text,
            '账单接口的结束日又用上了 __lte —— 结束日一整天的数据会被切掉，'
            '请用 parse_day_bound(end_date, end=True) 后的 `<` 比较',
        )
        self.assertIn(
            'parse_day_bound', text,
            '账单接口必须用 apps/utils/timerange.parse_day_bound 解析日期参数'
            '（它也负责把非法日期变成 400 而不是 500）',
        )


if __name__ == '__main__':
    unittest.main()
