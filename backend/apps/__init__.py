"""
uniTokenHub - 聚合API接口中转服务
"""

#: 产品版本 —— 与发版 tag、以及 `frontend/package.json` 的 `version` 同一个号。
#: 这三处曾经各说各的（这里是 `1.0.0`、tag 已经到 `v1.2.0`），而**没有任何东西在读它**，
#: 所以谁也没发现。现在 `apps/docs/tests/test_version_contract.py` 把它和
#: `frontend/package.json` 钉在一起：同一个产品一个版本号，单独改一边直接红。
__version__ = '1.3.0'
