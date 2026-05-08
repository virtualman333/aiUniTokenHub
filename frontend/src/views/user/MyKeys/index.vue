<template>
  <div class="my-keys">
    <!-- 头部 -->
    <div class="header">
      <div>
        <h1>我的密钥</h1>
        <p class="subtitle">管理您的 API 访问密钥</p>
      </div>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        创建密钥
      </el-button>
    </div>

    <!-- 密钥列表 -->
    <el-card v-loading="loading">
      <el-table :data="keys">
        <el-table-column prop="name" label="名称" />
        <el-table-column label="密钥" width="320">
          <template #default="{ row }">
            <div class="key-display">
              <code>{{ row.show ? row.key : maskedKey(row.key) }}</code>
              <el-button size="small" text @click="row.show = !row.show">
                <el-icon><View v-if="!row.show" /><Hide v-else /></el-icon>
              </el-button>
              <el-button size="small" text @click="copyKey(row.key)">
                <el-icon><DocumentCopy /></el-icon>
              </el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="rate_limit" label="限流(/min)" width="100" align="center" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.is_expired ? 'danger' : row.is_active ? 'success' : 'info'"
              size="small"
            >
              {{ row.is_expired ? '已过期' : row.is_active ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center">
          <template #default="{ row }">
            <el-button size="small" type="danger" text @click="handleRevoke(row)">
              撤销
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && keys.length === 0" description="暂无密钥" />
    </el-card>

    <!-- 创建密钥对话框 -->
    <CreateKeyDialog
      v-model="showCreateDialog"
      @submit="handleCreate"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, View, Hide, DocumentCopy } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import CreateKeyDialog from './components/CreateKeyDialog.vue'
import { useMyKeys } from './composables/useMyKeys'
import { copyToClipboard } from '@/utils/clipboard'

const { loading, keys, loadKeys, createKey, revokeKey } = useMyKeys()

const showCreateDialog = ref(false)

onMounted(() => {
  loadKeys()
})

function maskedKey(key: string) {
  return key.substring(0, 8) + '...' + key.substring(key.length - 4)
}

function formatDate(date: string) {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

async function copyKey(key: string) {
  const success = await copyToClipboard(key)
  if (success) {
    ElMessage.success('密钥已复制')
  } else {
    ElMessage.error('复制失败，请手动复制')
  }
}

async function handleCreate(data: any) {
  try {
    await createKey(data)
    ElMessage.success('密钥创建成功')
  } catch {
    ElMessage.error('创建失败')
  }
}

async function handleRevoke(row: any) {
  try {
    await ElMessageBox.confirm('确定要撤销此密钥吗？撤销后无法恢复。', '提示', {
      type: 'warning'
    })
    await revokeKey(row.id)
    ElMessage.success('密钥已撤销')
  } catch {
    // 取消操作
  }
}
</script>

<style scoped>
.my-keys {
  max-width: 1200px;
  margin: 0 auto;
  animation: fadeIn 0.5s ease-out;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-6);
}

.header-content h1 {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin-bottom: var(--space-2);
  letter-spacing: -0.025em;
}

.subtitle {
  color: var(--text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--font-normal);
}

.key-display {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.key-display code {
  font-family: var(--font-mono);
  color: var(--primary-600);
  background: var(--primary-50);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  border: 1px solid var(--primary-100);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header {
    flex-direction: column;
    gap: var(--space-4);
  }
  
  .header-content h1 {
    font-size: var(--text-2xl);
  }
}
</style>
