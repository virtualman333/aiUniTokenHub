# 多充值入口功能说明

## 功能概述

多充值入口功能采用**第三方网站支付 → 卡密充值**的流程：
- 后台配置充值套餐的跳转URL（每个套餐可配置不同的第三方充值网站）
- 用户选择套餐后跳转到第三方充值网站
- 在第三方网站完成支付后获取卡密
- 返回本平台使用卡密完成充值

## 业务流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                        充值流程                                  │
├─────────────────────────────────────────────────────────────────┤
│  1. 用户选择充值渠道和套餐                                        │
│  2. 点击"立即充值" → 跳转到第三方充值网站                          │
│  3. 在第三方网站完成支付                                         │
│  4. 获取卡密                                                     │
│  5. 返回本平台 → 输入卡密 → 完成充值                              │
└─────────────────────────────────────────────────────────────────┘
```

## 新增数据模型

### 1. RechargeChannel (充值渠道)

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BigAutoField | 主键 |
| `name` | CharField(100) | 渠道名称，如"官方充值"、"活动充值" |
| `code` | CharField(50) | 渠道代码（唯一），用于API标识 |
| `description` | CharField(500) | 渠道描述 |
| `icon` | CharField(255) | 图标URL或CSS类名 |
| `is_active` | BooleanField | 是否启用 |
| `sort_order` | IntegerField | 排序顺序 |
| `created_at` | DateTimeField | 创建时间 |
| `updated_at` | DateTimeField | 更新时间 |

### 2. RechargePackage (充值套餐)

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BigAutoField | 主键 |
| `channel` | ForeignKey | 关联的充值渠道 |
| `amount` | DecimalField | 充值金额 |
| `bonus` | DecimalField | 赠送金额 |
| `redirect_url` | URLField | 第三方跳转URL（必填，支持占位符） |
| `callback_url` | URLField | 第三方回调URL（可选） |
| `is_active` | BooleanField | 是否启用 |
| `sort_order` | IntegerField | 排序顺序 |
| `description` | CharField(500) | 套餐说明 |
| `created_at` | DateTimeField | 创建时间 |
| `updated_at` | DateTimeField | 更新时间 |

### 3. 跳转URL占位符说明

套餐的 `redirect_url` 支持以下占位符，会在用户点击充值时自动替换：

| 占位符 | 说明 | 示例 |
|--------|------|------|
| `{amount}` | 充值金额 | 100.00 |
| `{bonus}` | 赠送金额 | 10.00 |
| `{total}` | 总到账金额 | 110.00 |
| `{order_id}` | 订单号 | R12026051016001234 |
| `{user_id}` | 用户ID | 1 |
| `{channel_id}` | 渠道ID | 1 |
| `{package_id}` | 套餐ID | 1 |

### 4. 模型关联更新

#### CardPassword (卡密) 新增字段
- `channel`: ForeignKey → RechargeChannel（可选），标识卡密所属渠道

#### Bill (账单) 新增字段
- `channel`: ForeignKey → RechargeChannel（可选），记录充值所属渠道

## API 接口

### 用户端接口

#### 1. 获取充值渠道列表
- **URL**: `GET /api/users/recharge/channels/`
- **权限**: 需要登录
- **响应**:
```json
{
  "code": 0,
  "data": [
    {
      "id": 1,
      "name": "官方充值",
      "code": "official",
      "description": "官方渠道，安全可靠",
      "icon": "",
      "is_active": true,
      "sort_order": 0,
      "package_count": 3,
      "created_at": "2026-05-10T10:00:00Z"
    }
  ],
  "message": "获取成功"
}
```

#### 2. 获取充值套餐列表
- **URL**: `GET /api/users/recharge/packages/?channel_id=1`
- **权限**: 需要登录
- **参数**: `channel_id` (可选) - 筛选特定渠道的套餐
- **响应**:
```json
{
  "code": 0,
  "data": [
    {
      "id": 1,
      "channel": 1,
      "channel_name": "官方充值",
      "amount": 100.00,
      "bonus": 10.00,
      "actual_amount": 110.00,
      "redirect_url": "https://pay.xxx.com?money={amount}&order={order_id}",
      "callback_url": "",
      "is_active": true,
      "sort_order": 0,
      "description": "充100送10",
      "created_at": "2026-05-10T10:00:00Z"
    }
  ],
  "message": "获取成功"
}
```

#### 3. 提交充值（跳转第三方）
- **URL**: `POST /api/users/recharge/submit/`
- **权限**: 需要登录
- **请求体**:
```json
{
  "channel_id": 1,
  "package_id": 1
}
```
- **响应**:
```json
{
  "code": 0,
  "data": {
    "order_id": "R12026051016001234",
    "redirect_url": "https://pay.xxx.com?money=100.00&order=R12026051016001234",
    "amount": 100.00,
    "bonus": 10.00,
    "total": 110.00,
    "channel_name": "官方充值",
    "package_name": "¥100+赠¥10",
    "hint": "即将跳转到第三方支付页面，请在完成支付后获取卡密进行充值"
  },
  "message": "即将跳转到第三方充值页面"
}
```

### 管理员接口

#### 1. 获取充值渠道列表
- **URL**: `GET /api/users/admin/recharge/list_channels/`
- **权限**: 管理员

#### 2. 创建充值渠道
- **URL**: `POST /api/users/admin/recharge/create_channel/`
- **权限**: 管理员
- **请求体**:
```json
{
  "name": "官方充值",
  "code": "official",
  "description": "官方充值渠道",
  "icon": "icon-official",
  "is_active": true,
  "sort_order": 0
}
```

#### 3. 更新充值渠道
- **URL**: `PUT /api/users/admin/recharge/update_channel/{id}/`
- **权限**: 管理员

#### 4. 删除充值渠道
- **URL**: `DELETE /api/users/admin/recharge/delete_channel/{id}/`
- **权限**: 管理员
- **注意**: 有套餐的渠道无法删除

#### 5. 获取充值套餐列表
- **URL**: `GET /api/users/admin/recharge/list_packages/?channel_id=1`
- **权限**: 管理员

#### 6. 创建充值套餐
- **URL**: `POST /api/users/admin/recharge/create_package/`
- **权限**: 管理员
- **请求体**:
```json
{
  "channel_id": 1,
  "amount": 100.00,
  "bonus": 10.00,
  "redirect_url": "https://pay.xxx.com?money={amount}&order={order_id}",
  "callback_url": "",
  "is_active": true,
  "sort_order": 0,
  "description": "充100送10"
}
```

#### 7. 更新充值套餐
- **URL**: `PUT /api/users/admin/recharge/update_package/{id}/`
- **权限**: 管理员

#### 8. 删除充值套餐
- **URL**: `DELETE /api/users/admin/recharge/delete_package/{id}/`
- **权限**: 管理员

## 数据库迁移

执行迁移命令:
```bash
cd backend
python manage.py migrate users
```

## 配置示例

### 场景1: 创建官方充值渠道
1. 进入管理后台 → 充值管理 → 充值渠道 → 添加
2. 填写信息:
   - 名称: "官方充值"
   - 代码: "official"
   - 描述: "官方充值渠道"
   - 是否启用: ✓
3. 保存

### 场景2: 创建充值套餐（配置跳转URL）
1. 进入管理后台 → 充值管理 → 充值套餐 → 添加
2. 填写信息:
   - 所属渠道: "官方充值"
   - 充值金额: 100.00
   - 赠送金额: 10.00
   - **跳转URL**: `https://pay.xxx.com/recharge?amount={amount}&order={order_id}&uid={user_id}`
   - 套餐说明: "充100送10"
   - 是否启用: ✓
3. 保存

### 场景3: 用户充值流程
1. 用户登录 → 进入账单中心 → 点击"立即充值"
2. 选择"套餐充值"标签页
3. 选择充值渠道（如"官方充值"）
4. 选择充值套餐（如"¥100+赠¥10"）
5. 点击"立即充值" → 跳转到第三方充值网站
6. 用户在第三方网站完成支付，获取卡密
7. 返回本平台 → 输入卡密 → 完成充值

## 批量生成卡密时指定渠道

生成卡密时可以通过 `channel_id` 参数指定所属渠道:
```python
POST /api/users/cards/generate/
{
  "amount": 100.00,
  "count": 10,
  "batch_no": "BATCH001",
  "channel_id": 1,  # 指定渠道
  "remark": "官方渠道卡密"
}
```

## 账单记录改进

充值和卡密兑换的账单记录现在会包含充值渠道信息，便于统计各渠道的充值情况。

## 安全考虑

1. 所有接口都需要用户登录或管理员权限
2. 金额验证：必须大于0
3. 套餐和渠道有启用/禁用开关
4. 删除渠道前检查是否有套餐关联
5. 邀请返利机制继续有效
6. 跳转URL由后台管理员配置，确保可信第三方来源

## 后续优化建议

1. **支付网关集成**: 扩展支持更多第三方充值平台
2. **充值统计报表**: 添加各渠道充值金额统计
3. **充值优惠活动**: 支持限时优惠、节日活动等
4. **充值限额**: 可配置单次/每日/每月充值限额
5. **支付超时**: 添加订单超时机制
