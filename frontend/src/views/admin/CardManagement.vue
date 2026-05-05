<template>
  <div class="card-management">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h2>卡密管理</h2>
        <span class="card-count">共 {{ pagination.total }} 张卡密</span>
      </div>
      <el-button type="primary" @click="showGenerateDialog = true">
        <Plus /> 生成卡密
      </el-button>
    </div>

    <!-- 搜索栏 -->
    <el-card class="search-card">
      <el-form inline :model="queryParams">
        <el-form-item label="状态">
          <el-select v-model="queryParams.status" placeholder="全部" clearable @change="loadCards" style="width: 120px">
            <el-option label="未使用" value="unused" />
            <el-option label="已使用" value="used" />
          </el-select>
        </el-form-item>
        <el-form-item label="批次号">
          <el-input v-model="queryParams.batch_no" placeholder="输入批次号" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadCards">
            <Search /> 搜索
          </el-button>
          <el-button @click="resetQuery">
            <RefreshLeft /> 重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 卡密表格 -->
    <el-card class="table-card">
      <el-table :data="cards" v-loading="loading" stripe @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="code" label="卡密码" min-width="280">
          <template #default="{ row }">
            <div class="code-cell">
              <span class="code-text">{{ row.code }}</span>
              <el-button size="small" link @click="copyCode(row.code)">
                <CopyDocument />
              </el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="面值" width="120" align="right">
          <template #default="{ row }">
            <span class="amount">¥{{ Number(row.amount).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'unused' ? 'success' : 'info'" size="small">
              {{ row.status === 'unused' ? '未使用' : '已使用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="batch_no" label="批次号" width="150" show-overflow-tooltip />
        <el-table-column prop="used_by_username" label="使用者" width="120" show-overflow-tooltip />
        <el-table-column prop="used_at" label="使用时间" width="160">
          <template #default="{ row }">
            {{ row.used_at ? formatDate(row.used_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip />
      </el-table>

      <div class="table-footer">
        <el-button
          type="danger"
          :disabled="selectedCards.length === 0"
          @click="handleDeleteSelected"
        >
          删除选中 ({{ selectedCards.length }})
        </el-button>
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadCards"
          @current-change="loadCards"
        />
      </div>
    </el-card>

    <!-- 生成卡密对话框 -->
    <el-dialog v-model="showGenerateDialog" title="生成卡密" width="500px">
      <el-form :model="generateForm" label-width="100px" :rules="generateRules" ref="generateFormRef">
        <el-form-item label="面值" prop="amount">
          <el-input-number v-model="generateForm.amount" :min="1" :max="10000" :precision="2" />
          <span style="margin-left: 8px;">元</span>
        </el-form-item>
        <el-form-item label="数量" prop="count">
          <el-input-number v-model="generateForm.count" :min="1" :max="1000" />
          <span style="margin-left: 8px;">张</span>
        </el-form-item>
        <el-form-item label="批次号">
          <el-input v-model="generateForm.batch_no" placeholder="留空自动生成" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="generateForm.remark" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showGenerateDialog = false">取消</el-button>
        <el-button type="primary" :loading="generating" @click="handleGenerate">
          确认生成
        </el-button>
      </template>
    </el-dialog>

    <!-- 生成结果对话框 -->
    <el-dialog v-model="showResultDialog" title="生成成功" width="600px">
      <div class="result-info">
        <p>批次号：<strong>{{ generatedBatchNo }}</strong></p>
        <p>共生成 <strong>{{ generatedCount }}</strong> 张卡密</p>
      </div>
      <el-table :data="generatedCards" max-height="400" stripe>
        <el-table-column prop="code" label="卡密码">
          <template #default="{ row }">
            <span class="code-text">{{ row.code }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="面值" width="120" align="right">
          <template #default="{ row }">
            ¥{{ Number(row.amount).toFixed(2) }}
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="copyAllCodes">复制全部卡密</el-button>
        <el-button type="primary" @click="showResultDialog = false">完成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, RefreshLeft, CopyDocument } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import api from '@/stores'

interface Card {
  id: number
  code: string
  amount: number
  status: 'unused' | 'used'
  batch_no: string
  used_by: number | null
  used_by_username: string | null
  used_at: string | null
  remark: string
  created_at: string
}

const loading = ref(false)
const cards = ref<Card[]>([])
const selectedCards = ref<Card[]>([])
const showGenerateDialog = ref(false)
const showResultDialog = ref(false)
const generating = ref(false)
const generateFormRef = ref()

const queryParams = reactive({
  status: '',
  batch_no: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const generateForm = reactive({
  amount: 100,
  count: 10,
  batch_no: '',
  remark: ''
})

const generateRules = {
  amount: [{ required: true, message: '请输入面值', trigger: 'blur' }],
  count: [{ required: true, message: '请输入数量', trigger: 'blur' }]
}

const generatedCards = ref<Card[]>([])
const generatedBatchNo = ref('')
const generatedCount = ref(0)

onMounted(() => {
  loadCards()
})

async function loadCards() {
  loading.value = true
  try {
    const res: any = await api.get('/users/cards/list_cards/', {
      params: {
        page: pagination.page,
        page_size: pagination.pageSize,
        status: queryParams.status || undefined,
        batch_no: queryParams.batch_no || undefined
      }
    })
    const data = res.data || res
    cards.value = data.results || []
    pagination.total = data.total || 0
  } catch (e) {
    console.error('加载卡密失败:', e)
    cards.value = []
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  queryParams.status = ''
  queryParams.batch_no = ''
  pagination.page = 1
  loadCards()
}

function handleSelectionChange(selection: Card[]) {
  selectedCards.value = selection
}

async function handleGenerate() {
  generating.value = true
  try {
    const res: any = await api.post('/users/cards/generate/', {
      amount: generateForm.amount,
      count: generateForm.count,
      batch_no: generateForm.batch_no || undefined,
      remark: generateForm.remark || undefined
    })
    const data = res.data || res
    generatedCards.value = data.cards || []
    generatedBatchNo.value = data.batch_no || ''
    generatedCount.value = data.count || 0
    showGenerateDialog.value = false
    showResultDialog.value = true
    ElMessage.success(`成功生成 ${generatedCount.value} 张卡密`)
    loadCards()
  } catch (e: any) {
    ElMessage.error(e.message || '生成失败')
  } finally {
    generating.value = false
  }
}

async function handleDeleteSelected() {
  if (selectedCards.value.length === 0) return
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${selectedCards.value.length} 张卡密？已使用的卡密不会被删除。`,
      '确认删除',
      { type: 'warning' }
    )
    const ids = selectedCards.value.map(c => c.id)
    await api.delete('/users/cards/delete/', { data: { ids } })
    ElMessage.success('删除成功')
    loadCards()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.message || '删除失败')
    }
  }
}

function copyCode(code: string) {
  navigator.clipboard.writeText(code).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

function copyAllCodes() {
  const text = generatedCards.value.map(c => `${c.code}\t${c.amount}`).join('\n')
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制全部卡密')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

function formatDate(date: string) {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}
</script>

<style scoped>
.card-management {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.header-left h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.card-count {
  color: #909399;
  font-size: 14px;
}

.search-card {
  margin-bottom: 16px;
}

.table-card {
  margin-bottom: 16px;
}

.table-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
}

.code-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.code-text {
  font-family: monospace;
  font-size: 13px;
  color: #303133;
}

.amount {
  font-weight: 600;
  color: #409EFF;
}

.result-info {
  margin-bottom: 16px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.result-info p {
  margin: 4px 0;
}
</style>
