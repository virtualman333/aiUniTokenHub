# -*- coding: utf-8 -*-
"""版本契约：`backend/apps/__init__.py` 的 `__version__` 与 `frontend/package.json`
的 `version` 必须是同一个号。

为什么要有它
------------
这两个数字在本轮之前各说各的 —— 而且**都停在 `1.0.0`**，同一时刻的 git tag 已经到
`v1.2.0`。谁也没发现，因为**全仓没有任何东西在读它们**：`__version__` 只被定义、
不被 import；`frontend/package.json` 是 `"private": true` 的前端壳，不发 npm，
`version` 也就没人看。

这正是本仓反复栽的那种形状：**一句话声称了覆盖面，而落点是空的**。
这里更隐蔽一点 —— 它不是「声称」，是「记着」：一个记着 `1.0.0` 的字段，
比一个不存在的字段更容易骗人，因为它看起来是有人维护过的。

锁什么
------
  - 两边都能解析成 `X.Y.Z`（而不是 `1.0`、`v1.0.0`、`1.0.0-beta.1` 混着写）；
  - 两边**相等**。同一个产品、同一个 tag 出的一套东西，不许一边一个号；
  - `backend/` 下 `__version__` 只许有一处定义 —— 多一处就是又开了一份会漂移的事实。

刻意**不**锁：跟 git tag 对不对得上。那需要测试里跑 `git`，而这一层的约定是
**纯标准库、不碰数据库、不碰 Django**，也不能假设跑测试的地方是个 git 检出
（打包进镜像就是没有 `.git` 的）。tag 与这两个数字的一致性靠发版流程保证，
在这里假装配平只会给出一种「看着像有人在查」的错觉。

真想让它们分开的那天，把这条删掉、并在 README 里写清为什么不一致 ——
而不是改一个数让它闭嘴。
"""
import ast
import json
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]
REPO = BACKEND.parent


def parse_semver(text):
    """`X.Y.Z` → `(X, Y, Z)`；不是三段纯数字就返回 None。"""
    if not isinstance(text, str):
        return None
    parts = text.split('.')
    if len(parts) != 3:
        return None
    if not all(part.isdigit() and part.isascii() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def backend_version():
    """`backend/` 下唯一那处 `__version__` 的值。"""
    tree = ast.parse((BACKEND / 'apps/__init__.py').read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == '__version__' for t in node.targets
        ):
            return node.value.value
    return None


def declared_versions():
    """`backend/` 下所有定义 `__version__` 的文件（相对 backend 的路径 → 值）。"""
    found = {}
    for path in sorted(BACKEND.glob('apps/**/*.py')):
        rel = path.relative_to(BACKEND).as_posix()
        if '__pycache__' in rel:
            continue
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == '__version__' for t in node.targets
            ):
                found[rel] = node.value.value
    return found


class VersionContractTests(unittest.TestCase):

    def test_后端版本号是三段数字(self):
        value = backend_version()
        self.assertIsNotNone(value, 'apps/__init__.py 里找不到 __version__')
        self.assertIsNotNone(parse_semver(value), f'{value!r} 不是 X.Y.Z 形状')

    def test_前端版本号是三段数字(self):
        value = json.loads((REPO / 'frontend/package.json').read_text(encoding='utf-8'))['version']
        self.assertIsNotNone(parse_semver(value), f'{value!r} 不是 X.Y.Z 形状')

    def test_前后端说的是同一个号(self):
        backend = backend_version()
        frontend = json.loads((REPO / 'frontend/package.json').read_text(encoding='utf-8'))['version']
        self.assertEqual(
            backend, frontend,
            f'后端 __version__ 是 {backend!r}，前端 package.json 是 {frontend!r} —— '
            '同一个产品、同一个 tag 出的一套东西，不许一边一个号。',
        )

    def test___version___在_backend_里只有一处(self):
        found = declared_versions()
        self.assertEqual(
            sorted(found), ['apps/__init__.py'],
            f'backend/ 下有这些地方各自定义 __version__：{sorted(found)} —— '
            '多一处就是又开了一份会漂移的事实。',
        )


if __name__ == '__main__':
    unittest.main()
