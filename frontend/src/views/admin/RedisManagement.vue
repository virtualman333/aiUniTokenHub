<template>
  <div class="redis-management">
    <!-- Redis信息卡片 -->
    <el-row :gutter="20" class="info-cards">
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="info-item">
            <div class="info-label">Redis版本</div>
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
      <el-button type="primary" @click="loadRedisInfo">
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
              placeholder="搜索键名（支持通配符）"
              clearable
              style="width: 300px"
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

      <el-table :data="keys" stripe v-loading="loading">
        <el-table-column prop="key" label="键名" min-width="200" />
        <el-table-column prop="type" label="类型" width="100" align="center" />
        <el-table-column prop="ttl" label="TTL" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.ttl < 0 ? 'info' : row.ttl < 60 ? 'warning' : 'success'">
              {{ row.ttl < 0 ? '永久' : `${row.ttl}s` }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="size" label="大小" width="100" align="center" />
        <el-table-column label="操作" width="200" align="center">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewKeyDetail(row.key)">
              查看
            </el-button>
            <el-button type="danger" link @click="confirmDeleteKey(row.key)">
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
          layout="total, sizes, prev, pager, next"
          @size-change="loadKeys"
          @current-change="loadKeys"
        />
      </div>
    </el-card>

    <!-- 键详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="键详情"
      width="800px"
    >
      <div v-if="keyDetail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="键名">{{ keyDetail.key }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ keyDetail.type }}</el-descriptions-item>
          <el-descriptions-item label="TTL">
            {{ keyDetail.ttl < 0 ? '永久' : `${keyDetail.ttl}秒` }}
          </el-descriptions-item>
        </el-descriptions>

        <div style="margin-top: 20px">
          <h4>值：</h4>
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { RefreshRight, Delete, Search } from '@element-plus/icons-vue'
import api from '@/stores'

// Redis信息
const redisInfo = ref({})

// 键列表
const keys = ref([])
const loading = ref(false)
const searchPattern = ref('*')
const currentPage = ref(1)
const pageSize = ref(20)
const totalKeys = ref(0)

// 键详情
const detailDialogVisible = ref(false)
const keyDetail = ref(null)

// 加载Redis信息
async function loadRedisInfo() {
  try {
    const res = await api.get('/api/redis/info/')
    redisInfo.value = res
  } catch (error) {
    ElMessage.error('加载Redis信息失败')
    console.error(error)
  }
}

// 加载键列表
async function loadKeys() {
  loading.value = true
  try {
    const res = await api.get('/api/redis/keys/', {
      params: {
        pattern: searchPattern.value,
        cursor: (currentPage.value - 1) * pageSize.value,
        count: pageSize.value,
      }
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

// 查看键详情
async function viewKeyDetail(key) {
  try {
    const res = await api.get('/api/redis/key-detail/', {
      params: { key }
    })
    keyDetail.value = res
    detailDialogVisible.value = true
  } catch (error) {
    ElMessage.error('加载键详情失败')
    console.error(error)
  }
}

// 确认删除键
function confirmDeleteKey(key) {
  ElMessageBox.confirm(
    `确定要删除键 "${key}" 吗？`,
    '删除确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(async () => {
    try {
      await api.post('/api/redis/delete-key/', { key })
      ElMessage.success('删除成功')
      loadKeys()
    } catch (error) {
      ElMessage.error('删除失败')
      console.error(error)
    }
  }).catch(() => {})
}

// 确认清空数据库
function confirmFlushDB() {
  ElMessageBox.confirm(
    '确定要清空整个数据库吗？此操作不可逆！',
    '清空确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(async () => {
    try {
      await api.post('/api/redis/flush-db/')
      ElMessage.success('清空成功')
      loadRedisInfo()
      loadKeys()
    } catch (error) {
      ElMessage.error('清空失败')
      console.error(error)
    }
  }).catch(() => {})
}

// 格式化运行时间
function formatUptime(seconds) {
  if (!seconds) return '0秒'
  
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  
  let result = ''
  if (days > 0) result += `${days}天`
  if (hours > 0) result += `${hours}小时`
  if (minutes > 0) result += `${minutes}分钟`
  
  return result || '0秒'
}

// 格式化数字
function formatNumber(num) {
  if (!num) return '0'
  if (num >= 1000000) {
    return (num / 1000000).toFixed(2) + 'M'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(2) + 'K'
  }
  return num.toString()
}

// 格式化值
function formatValue(value) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2)
  }
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
</style>
