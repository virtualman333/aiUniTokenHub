<template>
  <div class="ticket-management">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h2>工单管理</h2>
        <span class="ticket-count">共 {{ pagination.total }} 个工单</span>
      </div>
      <div class="header-right">
        <el-button @click="loadTickets" :loading="loading">
          <Refresh /> 刷新
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-label">全部工单</div>
          <div class="stat-value">{{ stats.total }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card pending">
          <div class="stat-label">待处理</div>
          <div class="stat-value">{{ stats.pending }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card processing">
          <div class="stat-label">处理中</div>
          <div class="stat-value">{{ stats.processing }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card resolved">
          <div class="stat-label">已解决</div>
          <div class="stat-value">{{ stats.resolved }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 搜索栏 -->
    <el-card class="search-card">
      <el-form inline :model="queryParams">
        <el-form-item label="状态">
          <el-select v-model="queryParams.status" placeholder="全部" clearable style="width: 120px;" @change="loadTickets">
            <el-option label="待处理" value="pending" />
            <el-option label="处理中" value="processing" />
            <el-option label="已解决" value="resolved" />
          </el-select>
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="queryParams.category" placeholder="全部" clearable style="width: 120px;" @change="loadTickets">
            <el-option
              v-for="cat in categories"
              :key="cat.id"
              :label="cat.name"
              :value="cat.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadTickets">
            <Search /> 搜索
          </el-button>
          <el-button @click="resetQuery">
            <RefreshLeft /> 重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 工单表格 -->
    <el-card class="table-card">
      <el-table :data="tickets" v-loading="loading" stripe @row-click="handleRowClick" style="cursor: pointer;">
        <el-table-column prop="id" label="工单号" width="80">
          <template #default="{ row }">
            #{{ row.id }}
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="username" label="用户" width="120" />
        <el-table-column label="分类" width="120">
          <template #default="{ row }">
            {{ row.category_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTag(row.status)" size="small">
              {{ row.status_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="100">
          <template #default="{ row }">
            <el-tag :type="getPriorityTag(row.priority)" size="small" effect="plain">
              {{ row.priority_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="回复数" width="80" align="center">
          <template #default="{ row }">
            {{ row.reply_count }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click.stop="handleReply(row)">
              回复
            </el-button>
            <el-button
              v-if="row.status !== 'resolved'"
              size="small"
              type="success"
              link
              @click.stop="handleResolve(row)"
            >
              解决
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @change="loadTickets"
        />
      </div>
    </el-card>

    <!-- 工单详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="工单详情" width="700px">
      <div v-if="currentTicket" class="ticket-detail">
        <div class="detail-header">
          <h3>#{{ currentTicket.id }} {{ currentTicket.title }}</h3>
          <div class="detail-meta">
            <el-tag :type="getStatusTag(currentTicket.status)" size="small">
              {{ currentTicket.status_display }}
            </el-tag>
            <el-tag :type="getPriorityTag(currentTicket.priority)" size="small" effect="plain">
              {{ currentTicket.priority_display }}
            </el-tag>
            <span class="meta-text">{{ currentTicket.category_name || '未分类' }}</span>
            <span class="meta-text">用户: {{ currentTicket.username }}</span>
            <span class="meta-text">{{ formatDate(currentTicket.created_at) }}</span>
          </div>
        </div>

        <div class="detail-content">
          <div class="content-label">问题描述</div>
          <div class="content-text">{{ currentTicket.content }}</div>
          <div v-if="currentTicket.images && currentTicket.images.length > 0" class="image-list">
            <div v-for="img in currentTicket.images" :key="img.id" class="image-item" @click="previewImage(img.url)">
              <img :src="img.url" :alt="img.original_name" />
            </div>
          </div>
        </div>

        <div class="replies-section" v-if="currentTicket.replies && currentTicket.replies.length > 0">
          <div class="content-label">回复记录</div>
          <div class="reply-list">
            <div
              v-for="reply in currentTicket.replies"
              :key="reply.id"
              class="reply-item"
              :class="{ 'staff-reply': reply.is_staff_reply }"
            >
              <div class="reply-header">
                <span class="reply-user">
                  {{ reply.username }}
                  <el-tag v-if="reply.is_staff_reply" type="warning" size="small">管理员</el-tag>
                </span>
                <span class="reply-time">{{ formatDate(reply.created_at) }}</span>
              </div>
              <div class="reply-content">{{ reply.content }}</div>
              <div v-if="reply.images && reply.images.length > 0" class="reply-images">
                <div v-for="img in reply.images" :key="img.id" class="image-item" @click="previewImage(img.url)">
                  <img :src="img.url" :alt="img.original_name" />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="reply-form" v-if="currentTicket.status !== 'resolved'">
          <div class="content-label">添加回复</div>
          <el-input v-model="replyContent" type="textarea" :rows="4" placeholder="请输入回复内容" />
          <div style="margin-top: 12px;">
            <ImageUpload v-model="replyImages" :max-count="5" ref="replyImageUploadRef" />
          </div>
          <div class="reply-actions">
            <el-button type="primary" :loading="replying" @click="handleReplySubmit">
              提交回复
            </el-button>
            <el-button type="success" @click="handleResolveFromDetail">
              标记为已解决
            </el-button>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 图片预览对话框 -->
    <el-dialog v-model="previewVisible" title="图片预览" width="600px">
      <img :src="previewImageUrl" style="width: 100%;" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, RefreshLeft, Refresh } from '@element-plus/icons-vue'
import api from '@/stores'
import dayjs from 'dayjs'
import ImageUpload from '@/components/ImageUpload.vue'

const tickets = ref([])
const categories = ref([])
const loading = ref(false)
const showDetailDialog = ref(false)
const currentTicket = ref(null)
const replying = ref(false)
const replyContent = ref('')
const replyImages = ref([])
const replyImageUploadRef = ref()
const previewVisible = ref(false)
const previewImageUrl = ref('')

const stats = reactive({
  total: 0,
  pending: 0,
  processing: 0,
  resolved: 0
})

const queryParams = reactive({
  status: '',
  category: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

onMounted(() => {
  loadCategories()
  loadTickets()
  loadStats()
})

const loadCategories = async () => {
  try {
    const res = await api.get('/tickets/categories/')
    categories.value = res.data || res || []
  } catch (e) {
    console.error('加载分类失败:', e)
  }
}

const loadTickets = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (queryParams.status) params.status = queryParams.status
    if (queryParams.category) params.category = queryParams.category

    const res = await api.get('/tickets/', { params })
    const data = res.data || res
    tickets.value = data.results || []
    pagination.total = data.total || 0
  } catch (error) {
    ElMessage.error('加载工单失败: ' + (error.message || ''))
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    const res = await api.get('/tickets/stats/')
    const data = res.data || res
    stats.total = data.total || 0
    stats.pending = data.pending || 0
    stats.processing = data.processing || 0
    stats.resolved = data.resolved || 0
  } catch (e) {
    console.error('加载统计失败:', e)
  }
}

const resetQuery = () => {
  queryParams.status = ''
  queryParams.category = ''
  pagination.page = 1
  loadTickets()
}

const formatDate = (date) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

const getStatusTag = (status) => {
  const map = {
    pending: 'warning',
    processing: 'primary',
    resolved: 'success'
  }
  return map[status] || 'info'
}

const getPriorityTag = (priority) => {
  const map = {
    low: 'info',
    medium: '',
    high: 'warning',
    urgent: 'danger'
  }
  return map[priority] || ''
}

const handleRowClick = async (row) => {
  try {
    const res = await api.get(`/tickets/${row.id}/`)
    currentTicket.value = res.data || res
    showDetailDialog.value = true
  } catch (e) {
    ElMessage.error('获取工单详情失败')
  }
}

const handleReply = async (row) => {
  try {
    const res = await api.get(`/tickets/${row.id}/`)
    currentTicket.value = res.data || res
    showDetailDialog.value = true
  } catch (e) {
    ElMessage.error('获取工单详情失败')
  }
}

const handleReplySubmit = async () => {
  if (!replyContent.value.trim()) {
    ElMessage.warning('请输入回复内容')
    return
  }
  if (!currentTicket.value) return
  replying.value = true
  try {
    await api.post(`/tickets/${currentTicket.value.id}/reply/`, {
      content: replyContent.value.trim(),
      image_ids: replyImages.value
    })
    ElMessage.success('回复成功')
    replyContent.value = ''
    replyImages.value = []
    if (replyImageUploadRef.value) {
      replyImageUploadRef.value.clearFiles()
    }
    const res = await api.get(`/tickets/${currentTicket.value.id}/`)
    currentTicket.value = res.data || res
    loadTickets()
    loadStats()
  } catch (e) {
    ElMessage.error(e.message || '回复失败')
  } finally {
    replying.value = false
  }
}

const previewImage = (url) => {
  previewImageUrl.value = url
  previewVisible.value = true
}

const handleResolve = async (row) => {
  try {
    await ElMessageBox.confirm('确定要将此工单标记为已解决吗？', '提示')
    await api.patch(`/tickets/${row.id}/`, { status: 'resolved' })
    ElMessage.success('工单已解决')
    loadTickets()
    loadStats()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '操作失败')
    }
  }
}

const handleResolveFromDetail = async () => {
  if (!currentTicket.value) return
  try {
    await ElMessageBox.confirm('确定要将此工单标记为已解决吗？', '提示')
    await api.patch(`/tickets/${currentTicket.value.id}/`, { status: 'resolved' })
    ElMessage.success('工单已解决')
    showDetailDialog.value = false
    loadTickets()
    loadStats()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '操作失败')
    }
  }
}
</script>

<style scoped>
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
  color: #1f2937;
}

.ticket-count {
  font-size: 14px;
  color: #6b7280;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
  border-radius: 12px;
}

.stat-card.pending {
  background: #e6a23c !important;
}

.stat-card.processing {
  background: #409eff !important;
}

.stat-card.resolved {
  background: #67c23a !important;
}

.stat-label {
  font-size: 20px;
  color: #ffffff;
  margin-bottom: 16px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #ffffff;
}

.search-card {
  margin-bottom: 20px;
  border-radius: 12px;
}

.table-card {
  border-radius: 12px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.ticket-detail {
  max-height: 60vh;
  overflow-y: auto;
}

.detail-header {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #ebeef5;
}

.detail-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 12px;
}

.detail-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.meta-text {
  color: #909399;
  font-size: 13px;
}

.detail-content {
  margin-bottom: 20px;
}

.content-label {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.content-text {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 8px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.replies-section {
  margin-bottom: 20px;
}

.reply-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.reply-item {
  background: #f5f7fa;
  padding: 12px 16px;
  border-radius: 8px;
}

.reply-item.staff-reply {
  background: #ecf5ff;
  border-left: 3px solid #409eff;
}

.reply-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.reply-user {
  font-weight: 500;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
}

.reply-time {
  color: #909399;
  font-size: 12px;
}

.reply-content {
  line-height: 1.6;
  white-space: pre-wrap;
}

.reply-form {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

.reply-actions {
  display: flex;
  gap: 12px;
  margin-top: 12px;
}

.image-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.image-item {
  width: 80px;
  height: 80px;
  border-radius: 4px;
  overflow: hidden;
  cursor: pointer;
  border: 1px solid #ebeef5;
}

.image-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-item:hover {
  border-color: #409eff;
}

.reply-images {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}
</style>
