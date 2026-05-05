<template>
  <div class="tickets">
    <!-- 头部 -->
    <div class="header">
      <h1>工单中心</h1>
      <p class="subtitle">提交问题反馈和技术支持请求</p>
    </div>

    <!-- 操作栏 -->
    <div class="action-bar">
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon> 创建工单
      </el-button>
      <el-button @click="loadTickets" :loading="loading">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
    </div>

    <!-- 工单列表 -->
    <el-card v-loading="loading">
      <template #header>
        <span class="card-title">我的工单</span>
      </template>

      <el-table :data="tickets" @row-click="handleRowClick" style="cursor: pointer;">
        <el-table-column prop="id" label="工单号" width="80">
          <template #default="{ row }">
            #{{ row.id }}
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
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
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadTickets"
        @current-change="loadTickets"
        style="margin-top: 16px; justify-content: flex-end;"
      />

      <el-empty v-if="!loading && tickets.length === 0" description="暂无工单" />
    </el-card>

    <!-- 创建工单对话框 -->
    <el-dialog v-model="showCreateDialog" title="创建工单" width="600px">
      <el-form :model="createForm" :rules="createRules" ref="createFormRef" label-width="80px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="createForm.title" placeholder="请输入工单标题" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-select v-model="createForm.category" placeholder="请选择分类" clearable>
            <el-option
              v-for="cat in categories"
              :key="cat.id"
              :label="cat.name"
              :value="cat.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-select v-model="createForm.priority" placeholder="请选择优先级">
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
            <el-option label="紧急" value="urgent" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input v-model="createForm.content" type="textarea" :rows="6" placeholder="请详细描述您的问题或需求" maxlength="2000" show-word-limit />
        </el-form-item>
        <el-form-item label="图片">
          <ImageUpload v-model="createForm.images" :max-count="5" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">提交</el-button>
      </template>
    </el-dialog>

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
          <el-button type="primary" :loading="replying" @click="handleReply" style="margin-top: 12px;">
            提交回复
          </el-button>
        </div>
      </div>
    </el-dialog>

    <!-- 图片预览对话框 -->
    <el-dialog v-model="previewVisible" title="图片预览" width="600px">
      <img :src="previewImageUrl" style="width: 100%;" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { useTickets, type Ticket } from './composables/useTickets'
import ImageUpload from '@/components/ImageUpload.vue'

const {
  loading,
  tickets,
  categories,
  pagination,
  loadCategories,
  loadTickets,
  getTicketDetail,
  createTicket,
  replyTicket
} = useTickets()

const showCreateDialog = ref(false)
const showDetailDialog = ref(false)
const creating = ref(false)
const replying = ref(false)
const currentTicket = ref<Ticket | null>(null)
const replyContent = ref('')
const replyImages = ref<number[]>([])
const createFormRef = ref()
const replyImageUploadRef = ref()
const previewVisible = ref(false)
const previewImageUrl = ref('')

const createForm = reactive({
  title: '',
  content: '',
  category: null as number | null,
  priority: 'medium',
  images: [] as number[]
})

const createRules = {
  title: [{ required: true, message: '请输入工单标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入工单内容', trigger: 'blur' }],
  priority: [{ required: true, message: '请选择优先级', trigger: 'change' }]
}

onMounted(() => {
  loadCategories()
  loadTickets()
})

function formatDate(date: string) {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

function getStatusTag(status: string) {
  const map: Record<string, any> = {
    pending: 'warning',
    processing: 'primary',
    resolved: 'success'
  }
  return map[status] || 'info'
}

function getPriorityTag(priority: string) {
  const map: Record<string, any> = {
    low: 'info',
    medium: '',
    high: 'warning',
    urgent: 'danger'
  }
  return map[priority] || ''
}

async function handleCreate() {
  if (!createFormRef.value) return
  await createFormRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    creating.value = true
    try {
      await createTicket({
        title: createForm.title,
        content: createForm.content,
        category: createForm.category || undefined,
        priority: createForm.priority,
        image_ids: createForm.images
      })
      ElMessage.success('工单创建成功')
      showCreateDialog.value = false
      createForm.title = ''
      createForm.content = ''
      createForm.category = null
      createForm.priority = 'medium'
      createForm.images = []
      loadTickets()
    } catch (e: any) {
      ElMessage.error(e.message || '创建失败')
    } finally {
      creating.value = false
    }
  })
}

async function handleRowClick(row: Ticket) {
  const detail = await getTicketDetail(row.id)
  if (detail) {
    currentTicket.value = detail
    showDetailDialog.value = true
  }
}

async function handleReply() {
  if (!replyContent.value.trim()) {
    ElMessage.warning('请输入回复内容')
    return
  }
  if (!currentTicket.value) return
  replying.value = true
  try {
    await replyTicket(currentTicket.value.id, replyContent.value.trim(), replyImages.value)
    ElMessage.success('回复成功')
    replyContent.value = ''
    replyImages.value = []
    if (replyImageUploadRef.value) {
      replyImageUploadRef.value.clearFiles()
    }
    const detail = await getTicketDetail(currentTicket.value.id)
    if (detail) {
      currentTicket.value = detail
    }
    loadTickets()
  } catch (e: any) {
    ElMessage.error(e.message || '回复失败')
  } finally {
    replying.value = false
  }
}

function previewImage(url: string) {
  previewImageUrl.value = url
  previewVisible.value = true
}
</script>

<style scoped>
.tickets {
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  text-align: center;
  margin-bottom: 32px;
}

.header h1 {
  font-size: 28px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 4px;
}

.subtitle {
  color: #666;
  font-size: 14px;
}

.action-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.card-title {
  font-weight: 600;
  font-size: 16px;
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
