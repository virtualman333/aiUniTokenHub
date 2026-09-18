# uniTokenHub 后端

## 环境要求
- Python 3.10+
- MySQL 5.7+
- Redis 6+

## 安装

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件配置数据库和Redis

# 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 创建管理员账号
python manage.py createsuperuser

# 运行服务器
python manage.py runserver
```

## 测试

后端单测是**纯 Python** 的：不连数据库、不读 Django settings，秒级跑完。照着敲的命令**只有一条**（在 `backend/` 下）：

```bash
python run_tests.py
```

它自己扫 `apps/*/tests/`、打印每个包的用例数、跑完全部用例，最后还会点名「哪些 app 一条测试都没有」。扫描面为什么必须是它而不是一串包名，见文件头。

**这里刻意不写「只跑某一个包」的命令。** 按包写命令就是把扫描面悄悄收窄（`AGENTS.md` 的规矩原话是 Never enumerate test packages by hand in docs or scripts），而收窄之后输出仍然是 `OK` —— 本仓库栽过这件事：`apps/dashboard/` 没有 `__init__.py`，`python -m unittest discover -s apps -t .` 不报错地跳过整个包，21 个用例因此长期没被跑过，文档却写着跑了。想单独看某个包，自己在本地敲即可，别把包名写进文档；`apps/docs/tests/test_docs_contract.py` 会盯着这件事（文档里再出现收窄到单个包的 `unittest discover` 命令就红）。

各组测试在测什么：

- **协议适配与流式状态机**（`apps/api_proxy/tests/`）：`anthropic_to_openai` 必须把
  `cache_creation_input_tokens` 与 `cache_read_input_tokens` 一并计入 `prompt_tokens`，否则缓存命中会漏计费。
  `streaming_adapter.py` 的两个状态机（Chat Completions → Response API、Anthropic → Chat Completions）锁住三条
  容易回归的约束：多字节字符跨 chunk 不得被切坏（所以必须用 `IncrementalUtf8Decoder`，不能
  `chunk.decode(..., errors='replace')`）、`response.completed.output` 的顺序必须与公布的 `output_index` 一致、
  标准流下收尾事件只能发一次。改动 `apps/api_proxy/adapters/` 或 `views_openai.py` / `views_responses.py`
  的流式分支后都要跑一遍。
- **用量解析只有一处**：`parse_usage_dict` / `parse_usage`（`apps/utils/billing.py`）是唯一认识三种上游形态
  （OpenAI 的 `prompt_tokens`、Responses API 的 `input_tokens`、Anthropic 的 `cache_read_input_tokens`）
  与缓存命中字段的地方，两个端点的收尾都走 `views_openai.update_usage_log`。这段解析此前有**四份**副本，
  而且各自认得的字段不同 —— 同一个上游换个端点就可能算出不同的 token 数，也就是不同的钱；缓存命中
  （`cached_tokens`）漏读则等于按全价收费，用户看不见、对账时也对不出来。
  行为由 `apps/utils/tests/test_billing_usage.py` 覆盖，结构由
  `apps/api_proxy/tests/test_usage_single_source.py` 读源码钉住。
- **余额续航预测**（`apps/dashboard/tests/`）：算的是一句「你的钱还能用几天」，用户会直接照着它决定要不要充值，
  所以边界钉得很死：余额为 0（**包括一条消耗记录都还没有的新用户**）、窗口内没消耗、账号刚用两天
  （窗口被摊薄会让续航虚高）、分级临界值。改 `runway.py` 的窗口或分级逻辑前先看这组测试。
- **邀请返利**（`apps/users/tests/`）：发钱那条线上的判定抽在 `apps/users/invite_reward.py` —— 纯 Python、不 import Django，
  两次查询以惰性取值函数传进来，于是判定本身可测（`every` 与「金额为 0」一次查询都不发）。金额统一量化到 2 位、
  与 `InviteReward` 的两个金额列一致：记录里的充值额乘比例必须等于记录里的返利，否则审计时复算会得到第二个数；
  量化后不足 1 分的充值不写记录，审核阈值也按量化后的金额比 —— 拿未量化的乘积去比时，`999.99` 这笔充值算出的
  `99.999` 会既绕过审核、又写下与到账不一致的数。落库那两条入口（`apps/users/utils.py::process_invite_reward`、
  `apps/dashboard/views.py::approve_reward`）的加锁由这组测试**读源码**钉住：判定的查询必须在
  `select_for_update()` 之内，否则两次充值会各拿一笔返利、两个管理员能点出两份钱。
- **工单附件**（`apps/tickets/tests/`）：一次能带几张、什么样的 id 才算 id、上传落在哪个目录，三件事都收在
  `apps/tickets/attachments.py`（纯 Python、不 import Django）；这也是 `apps/tickets/` 的第一份用例。从前它们散在
  `views.py` 里，于是：`image_ids` 传成字符串 `"12"` 会被 `id__in` **按字符拆开**、绑到第 1、2 张图上（`len("12")` 只有
  2，连 5 张的上限都碰不到）；「最多关联 5 张」判在 `serializer.save()` **之后**，那句 400 里夹着一条已经落库的工单；
  绑定用 `update()`，影响 0 行不报错 —— 用户看到「提交成功」，而工单里一张图都没有。现在 id 清单先收先判，建单/回复
  与绑图在同一个事务里（绑不满整笔回滚，差额由 `partial_binding_error` 说出来），上传目录是 `tickets/unassigned/`
  而不是 `tickets/None/`（`upload_to` 只在保存那一刻求值，那时工单还不存在，老路径一直在谎报一个工单号）。
  上传白名单与大小上限在前端 `ImageUpload.vue` 里还有一份，两边的对账由这组测试**从 .vue 源码里读出来**比。
- **文档契约**（`apps/docs/tests/`）：文档是唯一没人验证过的产物 —— 这几个文件分别锁住「文档里写的命令必须真的存在、
  数据库只能有一种说法」「环境变量的声明与读取必须对得上」「测试入口自己不许回归」。改动 `README.md` /
  `AGENTS.md` / `.env.example` / `frontend/.env.*` 之后都会走到它们。

## API文档
启动服务后访问: http://localhost:8000/admin/
