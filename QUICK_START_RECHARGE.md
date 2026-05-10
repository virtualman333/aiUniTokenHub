# 多充值入口功能 - 快速入门指南

## 一、5分钟快速上手

### 步骤1：执行数据库迁移
```bash
cd backend
python manage.py migrate users
```

### 步骤2：启动服务
```bash
# 后端
cd backend
python manage.py runserver

# 前端（新终端）
cd frontend
npm run dev
```

### 步骤3：配置充值渠道
1. 登录管理后台: `http://localhost:5173/admin`
2. 进入"充值管理"页面
3. 点击"添加渠道"，填写信息：
   - 名称：官方充值
   - 代码：official
   - 描述：官方充值渠道
4. 保存

### 步骤4：配置充值套餐
1. 切换到"充值套餐"标签
2. 点击"添加套餐"，填写信息：
   - 所属渠道：官方充值
   - 充值金额：100
   - 赠送金额：10
   - 套餐说明：充100送10
3. 保存

### 步骤5：测试用户充值
1. 登录用户端: `http://localhost:5173/app`
2. 进入"账单中心"
3. 点击"立即充值"
4. 选择"套餐充值"标签
5. 选择渠道和套餐
6. 点击"立即充值"
7. 看到充值成功提示

## 二、管理员操作指南

### 创建充值渠道
1. 进入"充值管理 → 充值渠道"
2. 点击"添加渠道"
3. 填写表单：
   - **渠道名称**: 如"官方充值"、"活动充值"、"代理商充值"
   - **渠道代码**: 唯一的英文标识，如"official"、"promo"、"agent"
   - **描述**: 渠道说明（可选）
   - **图标**: 图标URL或CSS类名（可选）
   - **排序**: 数字越小越靠前（可选）
   - **启用**: 是否启用该渠道
4. 点击"确定"

### 创建充值套餐
1. 进入"充值管理 → 充值套餐"
2. 点击"添加套餐"
3. 填写表单：
   - **所属渠道**: 选择一个已创建的渠道
   - **充值金额**: 用户需要支付的金额
   - **赠送金额**: 额外赠送的金额（如充100送10）
   - **套餐说明**: 如"限时优惠"、"新人专享"等
   - **排序**: 数字越小越靠前（可选）
   - **启用**: 是否启用该套餐
4. 点击"确定"

### 编辑或删除
- **编辑**: 点击对应行的"编辑"按钮
- **删除**: 点击对应行的"删除"按钮（套餐可直接删除；渠道需先删除关联套餐）

## 三、常见问题

### Q1: 充值渠道无法删除？
**A**: 删除充值渠道前，必须先删除该渠道下的所有充值套餐。

### Q2: 用户看不到充值套餐？
**A**: 检查以下几点：
1. 渠道是否启用（is_active=true）
2. 套餐是否启用（is_active=true）
3. 套餐是否关联了渠道

### Q3: 充值后余额没有增加？
**A**: 检查：
1. API 请求是否成功（查看浏览器控制台）
2. 服务器日志是否有错误
3. 邀请返利功能是否抛出异常

### Q4: 如何查看充值统计？
**A**: 
- 在账单管理页面按渠道筛选
- 账单记录的 description 字段包含渠道信息
- 可导出账单数据进行分析

## 四、高级功能

### 1. 多渠道运营
```javascript
// 示例：创建多个渠道
// 渠道1：官方充值
{ name: "官方充值", code: "official" }

// 渠道2：活动充值
{ name: "活动充值", code: "promo" }

// 渠道3：代理商充值
{ name: "代理商充值", code: "agent" }
```

### 2. 阶梯套餐
```javascript
// 示例：创建阶梯套餐
// 基础套餐
{ amount: 100, bonus: 10, description: "充100送10" }

// 中级套餐
{ amount: 500, bonus: 75, description: "充500送75（15%赠送）" }

// 高级套餐
{ amount: 1000, bonus: 200, description: "充1000送200（20%赠送）" }
```

### 3. 限时活动
```javascript
// 示例：创建限时活动渠道
{
  name: "618大促",
  code: "promo_618",
  description: "618限时活动，充200送50",
  is_active: true  // 活动结束后改为 false
}
```

### 4. 批量生成卡密指定渠道
```javascript
// 生成卡密时可指定渠道
POST /api/users/cards/generate/
{
  "amount": 100,
  "count": 10,
  "batch_no": "BATCH001",
  "channel_id": 1,  // 指定渠道
  "remark": "官方渠道卡密"
}
```

## 五、API 接口文档

详细 API 文档请查看 [FRONTEND_INTEGRATION.md](./FRONTEND_INTEGRATION.md)

### 快速参考

| 功能 | 接口 | 方法 |
|------|------|------|
| 获取充值渠道 | /users/recharge/channels/ | GET |
| 获取充值套餐 | /users/recharge/packages/ | GET |
| 提交充值 | /users/recharge/submit/ | POST |
| 管理员-渠道列表 | /users/admin/recharge/list_channels/ | GET |
| 管理员-创建渠道 | /users/admin/recharge/create_channel/ | POST |
| 管理员-更新渠道 | /users/admin/recharge/update_channel/{id}/ | PUT |
| 管理员-删除渠道 | /users/admin/recharge/delete_channel/{id}/ | DELETE |
| 管理员-套餐列表 | /users/admin/recharge/list_packages/ | GET |
| 管理员-创建套餐 | /users/admin/recharge/create_package/ | POST |
| 管理员-更新套餐 | /users/admin/recharge/update_package/{id}/ | PUT |
| 管理员-删除套餐 | /users/admin/recharge/delete_package/{id}/ | DELETE |

## 六、数据库表结构

### recharge_channels (充值渠道表)
```sql
CREATE TABLE recharge_channels (
  id BIGSERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,        -- 渠道名称
  code VARCHAR(50) UNIQUE NOT NULL,   -- 渠道代码
  description VARCHAR(500),          -- 描述
  icon VARCHAR(255),                 -- 图标
  is_active BOOLEAN DEFAULT TRUE,    -- 是否启用
  sort_order INTEGER DEFAULT 0,      -- 排序
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### recharge_packages (充值套餐表)
```sql
CREATE TABLE recharge_packages (
  id BIGSERIAL PRIMARY KEY,
  channel_id INTEGER REFERENCES recharge_channels(id),  -- 所属渠道
  amount DECIMAL(10,2) NOT NULL,     -- 充值金额
  bonus DECIMAL(10,2) DEFAULT 0,     -- 赠送金额
  is_active BOOLEAN DEFAULT TRUE,    -- 是否启用
  sort_order INTEGER DEFAULT 0,      -- 排序
  description VARCHAR(500),          -- 套餐说明
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### bills (账单表 - 新增字段)
```sql
ALTER TABLE bills ADD COLUMN channel_id INTEGER REFERENCES recharge_channels(id);
```

### card_passwords (卡密表 - 新增字段)
```sql
ALTER TABLE card_passwords ADD COLUMN channel_id INTEGER REFERENCES recharge_channels(id);
```

## 七、后续优化建议

1. **支付网关集成**: 集成支付宝、微信支付
2. **充值优惠活动**: 支持限时优惠、节日活动
3. **充值统计报表**: 各渠道充值金额统计
4. **充值限额**: 单次/每日/每月充值限额
5. **订单超时**: 支付订单超时机制
6. **退款功能**: 用户申请退款
7. **发票功能**: 用户申请充值发票

## 八、技术支持

如遇到问题，请：
1. 查看 [RECHARGE_FEATURE.md](./RECHARGE_FEATURE.md) 功能说明
2. 查看 [FRONTEND_INTEGRATION.md](./FRONTEND_INTEGRATION.md) 前端对接文档
3. 检查服务器日志
4. 查看数据库迁移状态

祝使用愉快！🎉
