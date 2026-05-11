<template>
  <div class="image-gen-page">
    <!-- 左侧：生成面板 -->
    <div class="gen-panel">
      <div class="panel-card">
        <h2 class="panel-title">AI 图像生成</h2>

        <!-- 模式切换 -->
        <div class="mode-switch">
          <div
            class="mode-tab"
            :class="{ active: mode === 'generate' }"
            @click="mode = 'generate'"
          >
            <el-icon><Plus /></el-icon> 生成图像
          </div>
          <div
            class="mode-tab"
            :class="{ active: mode === 'edit' }"
            @click="mode = 'edit'"
          >
            <el-icon><Edit /></el-icon> 编辑图像
          </div>
        </div>

        <!-- 模型选择 -->
        <div class="form-group">
          <label class="form-label">模型</label>
          <el-select v-model="form.model_code" placeholder="选择模型" style="width: 100%">
            <el-option
              v-for="m in imageModels"
              :key="m.code"
              :label="m.name"
              :value="m.code"
            />
          </el-select>
        </div>

        <!-- 编辑模式：图片上传 -->
        <div v-if="mode === 'edit'" class="form-group">
          <label class="form-label">参考图片</label>
          <el-upload
            class="image-upload"
            drag
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            accept="image/*"
          >
            <el-icon v-if="!editFile" class="upload-icon"><UploadFilled /></el-icon>
            <div v-if="!editFile" class="upload-text">
              拖拽图片到此处，或<em>点击上传</em>
            </div>
            <img v-else :src="editPreview" class="upload-preview" />
          </el-upload>
        </div>

        <!-- 提示词 -->
        <div class="form-group">
          <label class="form-label">提示词</label>
          <el-input
            v-model="form.prompt"
            type="textarea"
            :rows="4"
            :placeholder="mode === 'generate' ? '描述你想要生成的图像...' : '描述你希望对图像进行的修改...'"
          />
        </div>

        <!-- 参数设置 -->
        <div class="params-row">
          <div class="form-group">
            <label class="form-label">尺寸</label>
            <el-select v-model="form.size" style="width: 100%">
              <el-option label="自动" value="auto" />
              <el-option label="1024x1024 (方形)" value="1024x1024" />
              <el-option label="1536x1024 (横版)" value="1536x1024" />
              <el-option label="1024x1536 (竖版)" value="1024x1536" />
            </el-select>
          </div>
          <div class="form-group">
            <label class="form-label">质量</label>
            <el-select v-model="form.quality" style="width: 100%">
              <el-option label="自动" value="auto" />
              <el-option label="高" value="high" />
              <el-option label="中" value="medium" />
              <el-option label="低" value="low" />
            </el-select>
          </div>
          <div class="form-group">
            <label class="form-label">数量</label>
            <el-input-number
              v-model="form.n"
              :min="1"
              :max="5"
              style="width: 100%"
            />
          </div>
        </div>

        <!-- 费用提示 -->
        <div class="cost-hint">
          预计费用：¥{{ estimatedCost }}（{{ form.n }} 张 x ¥{{ unitPrice }}/张）
        </div>

        <!-- 生成按钮 -->
        <el-button
          type="primary"
          size="large"
          class="gen-btn"
          :loading="generating"
          :disabled="!canGenerate"
          @click="handleGenerate"
        >
          {{ generating ? '生成中...' : '开始生成' }}
        </el-button>

        <!-- 5天提醒 -->
        <el-alert
          type="warning"
          :closable="false"
          show-icon
          class="expire-alert"
        >
          生成的图片将在 <b>5 天后自动删除</b>，请及时保存到本地
        </el-alert>
      </div>
    </div>

    <!-- 右侧：结果 + 历史 -->
    <div class="result-panel">
      <!-- 生成结果 -->
      <div v-if="currentResult" class="result-card">
        <div class="result-header">
          <h3>生成结果</h3>
          <el-button size="small" @click="downloadAll">
            <el-icon><Download /></el-icon> 全部下载
          </el-button>
        </div>
        <div class="result-images">
          <div
            v-for="(img, idx) in currentResult.images"
            :key="idx"
            class="result-img-wrap"
          >
            <img :src="img.image_url" class="result-img" @click="previewImage(img.image_url)" />
            <div class="result-img-actions">
              <el-button size="small" circle @click="downloadImage(img.image_url, idx)">
                <el-icon><Download /></el-icon>
              </el-button>
              <el-button size="small" circle @click="previewImage(img.image_url)">
                <el-icon><ZoomIn /></el-icon>
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="!currentResult && !generating" class="empty-state">
        <el-icon :size="64"><Picture /></el-icon>
        <p>输入提示词开始创作</p>
      </div>

      <!-- 生成中 -->
      <div v-if="generating" class="loading-state">
        <el-icon :size="48" class="is-loading"><Loading /></el-icon>
        <p>正在生成图像，请稍候...</p>
      </div>

      <!-- 历史记录 -->
      <div class="history-card">
        <div class="history-header">
          <h3>历史记录</h3>
          <el-tag size="small" type="info">{{ historyTotal }} 条</el-tag>
        </div>
        <div class="history-list" v-loading="historyLoading">
          <div
            v-for="record in history"
            :key="record.id"
            class="history-item"
            :class="{ active: currentResult?.id === record.id }"
            @click="viewHistory(record)"
          >
            <div class="history-thumb">
              <img
                v-if="record.images.length > 0"
                :src="record.images[0].image_url"
                class="thumb-img"
              />
              <div v-else class="thumb-empty">
                <el-icon><Picture /></el-icon>
              </div>
            </div>
            <div class="history-info">
              <div class="history-prompt">{{ record.prompt }}</div>
              <div class="history-meta">
                <span>{{ record.model_code }}</span>
                <span>{{ formatDate(record.created_at) }}</span>
              </div>
            </div>
            <el-button
              size="small"
              link
              type="danger"
              class="history-delete"
              @click.stop="deleteHistory(record)"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
          <div v-if="history.length === 0 && !historyLoading" class="history-empty">
            暂无历史记录
          </div>
          <div v-if="history.length < historyTotal" class="history-more">
            <el-button link @click="loadMoreHistory">加载更多</el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 图片预览弹窗 -->
    <el-dialog v-model="previewVisible" width="auto" :show-close="true" center>
      <img :src="previewUrl" class="preview-img" />
      <template #footer>
        <el-button type="primary" @click="downloadImage(previewUrl, 0)">
          <el-icon><Download /></el-icon> 下载
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus, Edit, Download, ZoomIn, Delete, Picture,
  UploadFilled, Loading,
} from '@element-plus/icons-vue'
import api from '@/stores'

interface ImageItem {
  id: number
  image_url: string
  revised_prompt: string
}
interface HistoryRecord {
  id: number
  model_code: string
  mode: string
  prompt: string
  size: string
  quality: string
  n: number
  status: string
  cost: number
  created_at: string
  images: ImageItem[]
}

const mode = ref<'generate' | 'edit'>('generate')
const form = ref({
  model_code: '',
  prompt: '',
  size: 'auto',
  quality: 'auto',
  n: 1,
})
const editFile = ref<File | null>(null)
const editPreview = ref('')
const generating = ref(false)
const currentResult = ref<HistoryRecord | null>(null)

const imageModels = ref<any[]>([])
const history = ref<HistoryRecord[]>([])
const historyTotal = ref(0)
const historyPage = ref(1)
const historyLoading = ref(false)

const previewVisible = ref(false)
const previewUrl = ref('')

const unitPrice = computed(() => {
  const model = imageModels.value.find(m => m.code === form.value.model_code)
  return model?.per_image_price ? Number(model.per_image_price) : 0.08
})
const estimatedCost = computed(() => (unitPrice.value * form.value.n).toFixed(2))

const canGenerate = computed(() => {
  if (!form.value.prompt.trim()) return false
  if (mode.value === 'edit' && !editFile.value) return false
  return true
})

onMounted(async () => {
  await Promise.all([fetchImageModels(), fetchHistory()])
})

async function fetchImageModels() {
  try {
    const res: any = await api.get('/models/models/', {
      params: { page: 1, page_size: 99, category: 'picture' },
    })
    imageModels.value = res.results || res || []
    if (imageModels.value.length > 0 && !form.value.model_code) {
      form.value.model_code = imageModels.value[0].code
    }
  } catch (e) {
    console.error('获取图像模型失败', e)
  }
}

async function fetchHistory() {
  historyLoading.value = true
  try {
    const res = await api.get('/image-gen/generations/', {
      params: { page: historyPage.value, page_size: 20 },
    })
    const data = res.data || res
    const items = data.results || data || []
    if (historyPage.value === 1) {
      history.value = items
    } else {
      history.value.push(...items)
    }
    historyTotal.value = data.total || history.value.length
  } catch (e) {
    console.error('获取历史记录失败', e)
  } finally {
    historyLoading.value = false
  }
}

function loadMoreHistory() {
  historyPage.value++
  fetchHistory()
}

function handleFileChange(file: any) {
  editFile.value = file.raw
  editPreview.value = URL.createObjectURL(file.raw)
}

function handleFileRemove() {
  editFile.value = null
  editPreview.value = ''
}

async function handleGenerate() {
  if (!canGenerate.value) return
  generating.value = true
  currentResult.value = null
  try {
    const formData = new FormData()
    formData.append('model_code', form.value.model_code)
    formData.append('mode', mode.value)
    formData.append('prompt', form.value.prompt)
    formData.append('size', form.value.size)
    formData.append('quality', form.value.quality)
    formData.append('n', String(form.value.n))
    if (mode.value === 'edit' && editFile.value) {
      formData.append('image', editFile.value)
    }
    const res = await api.post('/image-gen/generations/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 600000,
    })
    const data = res.data || res
    currentResult.value = data
    ElMessage.success('图像生成成功')
    historyPage.value = 1
    fetchHistory()
  } catch (e: any) {
    ElMessage.error(e.message || '生成失败')
  } finally {
    generating.value = false
  }
}

function viewHistory(record: HistoryRecord) {
  currentResult.value = record
}

async function deleteHistory(record: HistoryRecord) {
  try {
    await ElMessageBox.confirm('确定删除该记录？删除后不可恢复', '确认删除', { type: 'warning' })
    await api.delete(`/image-gen/generations/${record.id}/`)
    history.value = history.value.filter(h => h.id !== record.id)
    historyTotal.value--
    if (currentResult.value?.id === record.id) {
      currentResult.value = null
    }
    ElMessage.success('已删除')
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.message || '删除失败')
  }
}

function previewImage(url: string) {
  previewUrl.value = url
  previewVisible.value = true
}

function downloadImage(url: string, idx: number) {
  const a = document.createElement('a')
  a.href = url
  a.download = `image_${Date.now()}_${idx}.png`
  a.click()
}

function downloadAll() {
  if (!currentResult.value) return
  currentResult.value.images.forEach((img, idx) => {
    setTimeout(() => downloadImage(img.image_url, idx), idx * 200)
  })
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr)
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hour = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${month}-${day} ${hour}:${min}`
}
</script>

<style scoped>
.image-gen-page {
  display: grid;
  grid-template-columns: 420px 1fr;
  gap: var(--space-4);
  min-height: calc(100vh - var(--header-height) - var(--space-12));
  animation: fadeIn 0.5s ease-out;
}

/* 左侧生成面板 */
.gen-panel {
  position: sticky;
  top: calc(var(--header-height) + var(--space-6));
  height: fit-content;
  max-height: calc(100vh - var(--header-height) - var(--space-12));
  overflow-y: auto;
}

.panel-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-xl);
  padding: var(--space-5);
  box-shadow: var(--shadow-sm);
}

.panel-title {
  margin: 0 0 var(--space-4);
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}

.mode-switch {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
  background: var(--neutral-50);
  border-radius: var(--radius-lg);
  padding: var(--space-1);
}

.mode-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.mode-tab.active {
  background: var(--bg-primary);
  color: var(--primary-600);
  box-shadow: var(--shadow-xs);
}

.form-group {
  margin-bottom: var(--space-3);
}

.form-label {
  display: block;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  margin-bottom: var(--space-1);
}

.image-upload {
  width: 100%;
}

.image-upload :deep(.el-upload-dragger) {
  padding: var(--space-4);
  border-radius: var(--radius-lg);
}

.upload-icon {
  font-size: 40px;
  color: var(--text-tertiary);
  margin-bottom: var(--space-2);
}

.upload-text {
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}

.upload-text em {
  color: var(--primary-600);
  font-style: normal;
}

.upload-preview {
  max-width: 100%;
  max-height: 200px;
  border-radius: var(--radius-md);
  object-fit: contain;
}

.params-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.cost-hint {
  text-align: center;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: var(--space-3);
  padding: var(--space-2);
  background: var(--neutral-50);
  border-radius: var(--radius-md);
}

.gen-btn {
  width: 100%;
  height: 44px;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  margin-bottom: var(--space-3);
}

.expire-alert {
  margin-top: var(--space-2);
}

/* 右侧结果面板 */
.result-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-width: 0;
}

.result-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-xl);
  padding: var(--space-5);
  box-shadow: var(--shadow-sm);
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
}

.result-header h3 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
}

.result-images {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--space-3);
}

.result-img-wrap {
  position: relative;
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--border-light);
  background: var(--neutral-50);
}

.result-img {
  width: 100%;
  display: block;
  cursor: pointer;
  transition: transform var(--transition-base);
}

.result-img:hover {
  transform: scale(1.02);
}

.result-img-actions {
  position: absolute;
  bottom: var(--space-2);
  right: var(--space-2);
  display: flex;
  gap: var(--space-1);
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.result-img-wrap:hover .result-img-actions {
  opacity: 1;
}

.empty-state,
.loading-state {
  background: var(--bg-primary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-xl);
  padding: var(--space-12) var(--space-6);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  gap: var(--space-3);
}

.empty-state p,
.loading-state p {
  margin: 0;
  font-size: var(--text-sm);
}

/* 历史记录 */
.history-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-xl);
  padding: var(--space-5);
  box-shadow: var(--shadow-sm);
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
}

.history-header h3 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  max-height: 400px;
  overflow-y: auto;
}

.history-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-fast);
  border: 1px solid transparent;
}

.history-item:hover {
  background: var(--neutral-50);
}

.history-item.active {
  background: var(--primary-50);
  border-color: var(--primary-100);
}

.history-thumb {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  overflow: hidden;
  flex-shrink: 0;
  background: var(--neutral-100);
}

.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb-empty {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
}

.history-info {
  flex: 1;
  min-width: 0;
}

.history-prompt {
  font-size: var(--text-sm);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: var(--font-medium);
}

.history-meta {
  display: flex;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  margin-top: var(--space-1);
}

.history-delete {
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.history-item:hover .history-delete {
  opacity: 1;
}

.history-empty {
  text-align: center;
  padding: var(--space-6);
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}

.history-more {
  text-align: center;
  padding: var(--space-2);
}

/* 预览弹窗 */
.preview-img {
  max-width: 90vw;
  max-height: 80vh;
  display: block;
  margin: 0 auto;
  border-radius: var(--radius-lg);
}

/* 响应式 */
@media (max-width: 980px) {
  .image-gen-page {
    grid-template-columns: 1fr;
  }

  .gen-panel {
    position: static;
    max-height: none;
  }

  .params-row {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 480px) {
  .params-row {
    grid-template-columns: 1fr;
  }

  .result-images {
    grid-template-columns: 1fr;
  }
}
</style>
