<template>
  <div class="redis-management">
    <!-- Redis 信息卡片 -->
    <el-row :gutter="20" class="info-cards">
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="info-item">
            <div class="info-label">Redis 版本</div>
            <div class="info-value">{{ redisInfo.version || '-' }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="info-item">
            <div class="info-label">运行时间</div>
            <div class="info-value">{{ formatUptime(redisInfo.uptime_in_seconds) }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="info-item">
            <div class="info-label">连接客户端数</div>
            <div class="info-value">{{ redisInfo.connected_clients || 0 }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="info-cards" style="margin-top: 20px">
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="info-item">
            <div class="info-label">已用内存</div>
            <div class="info-value">{{ redisInfo.used_memory_human || '0B' }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="info-item">
            <div class="info-label">峰值内存</div>
            <div class="info-value">{{ redisInfo.used_memory_peak_human || '0B' }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="info-item">
            <div class="info-label">总键数</div>
            <div class="info-value">{{ redisInfo.keys || 0 }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="info-cards" style="margin-top: 20px">
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="info-item">
            <div class="info-label">总连接数</div>
            <div class="info-value">{{ redisInfo.total_connections_received || 0 }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="info-item">
            <div class="info-label">总命令处理数</div>
            <div class="info-value">{{ formatNumber(redisInfo.total_commands_processed) }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="info-item">
            <div class="info-label">每秒操作数</div>
            <div class="info-value">{{ redisInfo.instantaneous_ops_per_sec || 0 }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 操作栏 -->
    <div class="action-bar">
      <el-button type="primary" @click="showCreateDialog">
        <CirclePlus /> 新增键
      </el-button>
      <el-button type="danger" :disabled="selectedKeys.length === 0" @click="confirmBatchDelete">
        <Delete /> 批量删除
      </el-button>
      <el-button @click="loadRedisInfo">
        <RefreshRight /> 刷新信息
      </el-button>
      <el-button type="danger" @click="confirmFlushDB">
        <Delete /> 清空数据库
      </el-button>
    </div>

    <!-- 键列表 -->
    <el-card style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <span>键列表</span>
          <div class="header-actions">
            <el-input
              v-model="searchPattern"
              placeholder="搜索键名（支持通配符，如 user:*）"
              clearable
              style="width: 320px"
              @clear="loadKeys"
              @keyup.enter="loadKeys"
            >
              <template #append>
                <el-button @click="loadKeys">
                  <Search /> 搜索
                </el-button>
              </template>
            </el-input>
          </div>
        </div>
      </template>

      <el-table
        :data="keys"
        stripe
        v-loading="loading"
        @selection-change="handleSelectionChange"
        style="width: 100%"
      >
        <el-table-column type="selection" width="45" />
        <el-table-column prop="key" label="键名" min-width="220" show-overflow-tooltip />
        <el-table-column prop="type" label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="TTL" width="130" align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.ttl < 0 ? 'info' : row.ttl < 60 ? 'warning' : 'success'"
              size="small"
            >
              {{ row.ttl < 0 ? '永久' : `${row.ttl}s` }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="size" label="大小" width="100" align="center" />
        <el-table-column label="操作" width="280" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="viewKeyDetail(row.key)">
              查看
            </el-button>
            <el-button type="warning" link size="small" @click="showSetTTLDialog(row.key, row.ttl)">
              设TTL
            </el-button>
            <el-button type="info" link size="small" @click="showRenameDialog(row.key)">
              重命名
            </el-button>
            <el-button type="danger" link size="small" @click="confirmDeleteKey(row.key)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination" style="margin-top: 20px; display: flex; justify-content: center">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="totalKeys"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadKeys"
          @current-change="loadKeys"
        />
      </div>
    </el-card>

    <!-- 键详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="键详情" width="800px">
      <div v-if="keyDetail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="键名">{{ keyDetail.key }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ keyDetail.type }}</el-descriptions-item>
          <el-descriptions-item label="TTL">
            {{ keyDetail.ttl < 0 ? '永久' : `${keyDetail.ttl} 秒` }}
          </el-descriptions-item>
        </el-descriptions>
        <div style="margin-top: 20px">
          <h4 style="margin-bottom: 8px">值：</h4>
          <el-input
            type="textarea"
            :rows="10"
            :model-value="formatValue(keyDetail.value)"
            readonly
          />
        </div>
      </div>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 新增/修改键对话框 -->
    <el-dialog v-model="editDialogVisible" :title="editForm.key ? '修改键' : '新增键'" width="700px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="键名" required>
          <el-input v-model="editForm.key" placeholder="请输入键名" :disabled="!!editingKey" />
        </el-form-item>
        <el-form-item label="类型" required>
          <el-select v-model="editForm.type" style="width: 100%">
            <el-option label="String" value="string" />
            <el-option label="Hash" value="hash" />
            <el-option label="List" value="list" />
            <el-option label="Set" value="set" />
            <el-option label="ZSet" value="zset" />
          </el-select>
        </el-form-item>
        <el-form-item label="值" required>
          <el-input
            v-if="editForm.type === 'string'"
            v-model="editForm.value"
            type="textarea"
            :rows="4"
            placeholder="请输入字符串值"
          />
          <el-input
            v-else
            v-model="editForm.value"
            type="textarea"
            :rows="4"
            placeholder="请输入 JSON 格式，如 Hash: {&quot;field1&quot;: &quot;value1&quot;}，List/Set: [&quot;item1&quot;, &quot;item2&quot;]，ZSet: [[&quot;member&quot;, 1]]"
          />
          <div class="form-tip">
            <template v-if="editForm.type === 'hash'">Hash 格式：{"field1": "value1", "field2": "value2"}</template>
            <template v-else-if="editForm.type === 'list' || editForm.type === 'set'">List/Set 格式：["item1", "item2"]</template>
            <template v-else-if="editForm.type === 'zset'">ZSet 格式：[["member1", 1], ["member2", 2]]</template>
          </div>
        </el-form-item>
        <el-form-item label="过期时间">
          <el-input-number v-model="editForm.ttl" :min="-1" :max="31536000" style="width: 200px" />
          <span style="margin-left: 8px; color: #909399">秒（-1 表示永久）</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveKey">保存</el-button>
      </template>
    </el-dialog>

    <!-- 设置 TTL 对话框 -->
    <el-dialog v-model="ttlDialogVisible" title="设置过期时间" width="500px">
      <el-form label-width="100px">
        <el-form-item label="键名">
          <el-input :model-value="ttlForm.key" disabled />
        </el-form-item>
        <el-form-item label="TTL" required>
          <el-input-number v-model="ttlForm.ttl" :min="-1" :max="31536000" style="width: 200px" />
          <span style="margin-left: 8px; color: #909399">秒（-1 表示永久）</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ttlDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSetTTL">确认</el-button>
      </template>
    </el-dialog>

    <!-- 重命名键对话框 -->
    <el-dialog v-model="renameDialogVisible" title="重命名键" width="500px">
      <el-form label-width="100px">
        <el-form-item label="原键名">
          <el-input :model-value="renameForm.oldKey" disabled />
        </el-form-item>
        <el-form-item label="新键名" required>
          <el-input v-model="renameForm.newKey" placeholder="请输入新键名" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="renameDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleRename">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  RefreshRight,
  Delete,
  Search,
  CirclePlus,
} from '@element-plus/icons-vue'
import api from '@/stores'

// ---------- Redis 信息 ----------
const redisInfo = ref({})

// ---------- 键列表 ----------
const keys = ref([])
const loading = ref(false)
const searchPattern = ref('*')
const currentPage = ref(1)
const pageSize = ref(20)
const totalKeys = ref(0)
const selectedKeys = ref([])
const editingKey = ref('')

// ---------- 键详情 ----------
const detailDialogVisible = ref(false)
const keyDetail = ref(null)

// ---------- 新增/修改键 ----------
const editDialogVisible = ref(false)
const editForm = ref({
  key: '',
  type: 'string',
  value: '',
  ttl: -1,
})

// ---------- 设置 TTL ----------
const ttlDialogVisible = ref(false)
const ttlForm = ref({ key: '', ttl: -1 })

// ---------- 重命名 ----------
const renameDialogVisible = ref(false)
const renameForm = ref({ oldKey: '', newKey: '' })

// ---------- 加载 Redis 信息 ----------
async function loadRedisInfo() {
  try {
    const res = await api.get('/api/redis/info/')
    redisInfo.value = res
  } catch (error) {
    ElMessage.error('加载 Redis 信息失败')
    console.error(error)
  }
}

// ---------- 加载键列表 ----------
async function loadKeys() {
  loading.value = true
  try {
    const res = await api.get('/api/redis/keys/', {
      params: {
        pattern: searchPattern.value || '*',
        cursor: (currentPage.value - 1) * pageSize.value,
        count: pageSize.value,
      },
    })
    keys.value = res.keys || []
    totalKeys.value = res.total || 0
  } catch (error) {
    ElMessage.error('加载键列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// ---------- 查看键详情 ----------
async function viewKeyDetail(key) {
  try {
    const res = await api.get('/api/redis/key-detail/', { params: { key } })
    keyDetail.value = res
    detailDialogVisible.value = true
  } catch (error) {
    ElMessage.error('加载键详情失败')
    console.error(error)
  }
}

// ---------- 表格多选 ----------
function handleSelectionChange(selection) {
  selectedKeys.value = selection.map((item) => item.key)
}

// ========== 新增/修改键 ==========
function showCreateDialog() {
  editingKey.value = ''
  editForm.value = { key: '', type: 'string', value: '', ttl: -1 }
  editDialogVisible.value = true
}

function handleSaveKey() {
  if (!editForm.value.key.trim()) {
    ElMessage.warning('请输入键名')
    return
  }
  if (editForm.value.value === '' || editForm.value.value === undefined) {
    ElMessage.warning('请输入值')
    return
  }

  ElMessageBox.confirm('确认保存该键？', '提示', { type: 'info' })
    .then(async () => {
      try {
        let value = editForm.value.value
        if (editForm.value.type !== 'string') {
          try {
            value = JSON.parse(editForm.value.value)
          } catch {
            ElMessage.error('值不是合法的 JSON 格式')
            return
          }
        }
        await api.post('/api/redis/set-key/', {
          key: editForm.value.key.trim(),
          value,
          type: editForm.value.type,
          ttl: editForm.value.ttl,
        })
        ElMessage.success('保存成功')
        editDialogVisible.value = false
        loadKeys()
        loadRedisInfo()
      } catch (error) {
        ElMessage.error('保存失败')
        console.error(error)
      }
    })
    .catch(() => {})
}

// ========== 设置 TTL ==========
function showSetTTLDialog(key, currentTTL) {
  ttlForm.value = { key, ttl: currentTTL < 0 ? -1 : currentTTL }
  ttlDialogVisible.value = true
}

async function handleSetTTL() {
  try {
    await api.post('/api/redis/set-ttl/', ttlForm.value)
    ElMessage.success('设置 TTL 成功')
    ttlDialogVisible.value = false
    loadKeys()
  } catch (error) {
    ElMessage.error('设置 TTL 失败')
    console.error(error)
  }
}

// ========== 重命名键 ==========
function showRenameDialog(key) {
  renameForm.value = { oldKey: key, newKey: '' }
  renameDialogVisible.value = true
}

async function handleRename() {
  if (!renameForm.value.newKey.trim()) {
    ElMessage.warning('请输入新键名')
    return
  }
  try {
    await api.post('/api/redis/rename-key/', renameForm.value)
    ElMessage.success('重命名成功')
    renameDialogVisible.value = false
    loadKeys()
  } catch (error) {
    ElMessage.error('重命名失败')
    console.error(error)
  }
}

// ========== 删除 ==========
function confirmDeleteKey(key) {
  ElMessageBox.confirm(`确定要删除键 "${key}" 吗？`, '删除确认', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(async () => {
      try {
        await api.post('/api/redis/delete-key/', { key })
        ElMessage.success('删除成功')
        loadKeys()
        loadRedisInfo()
      } catch (error) {
        ElMessage.error('删除失败')
        console.error(error)
      }
    })
    .catch(() => {})
}

async function confirmBatchDelete() {
  if (selectedKeys.value.length === 0) return
  ElMessageBox.confirm(
    `确定要批量删除选中的 ${selectedKeys.value.length} 个键吗？`,
    '批量删除确认',
    { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
  )
    .then(async () => {
      try {
        const res = await api.post('/api/redis/batch-delete/', {
          keys: selectedKeys.value,
        })
        ElMessage.success(`成功删除 ${res.deleted_count || selectedKeys.value.length} 个键`)
        selectedKeys.value = []
        loadKeys()
        loadRedisInfo()
      } catch (error) {
        ElMessage.error('批量删除失败')
        console.error(error)
      }
    })
    .catch(() => {})
}

function confirmFlushDB() {
  ElMessageBox.confirm('确定要清空整个数据库吗？此操作不可逆！', '清空确认', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(async () => {
      try {
        await api.post('/api/redis/flush-db/')
        ElMessage.success('清空成功')
        loadRedisInfo()
        loadKeys()
      } catch (error) {
        ElMessage.error('清空失败')
        console.error(error)
      }
    })
    .catch(() => {})
}

// ---------- 工具函数 ----------
function formatUptime(seconds) {
  if (!seconds) return '0 秒'
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  let s = ''
  if (d > 0) s += `${d} 天 `
  if (h > 0) s += `${h} 小时 `
  if (m > 0) s += `${m} 分钟`
  return s.trim() || '0 秒'
}

function formatNumber(num) {
  if (!num) return '0'
  if (num >= 1_000_000) return (num / 1_000_000).toFixed(2) + 'M'
  if (num >= 1_000) return (num / 1_000).toFixed(2) + 'K'
  return num.toString()
}

function formatValue(value) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}

onMounted(() => {
  loadRedisInfo()
  loadKeys()
})
</script>

<style scoped>
.redis-management {
  padding: 20px;
}

.info-cards {
  margin-bottom: 0;
}

.info-item {
  text-align: center;
}

.info-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.info-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.action-bar {
  margin-top: 20px;
  display: flex;
  gap: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
