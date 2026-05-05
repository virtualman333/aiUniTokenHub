<template>
  <div class="image-upload">
    <el-upload
      ref="uploadRef"
      :action="uploadUrl"
      :headers="uploadHeaders"
      :file-list="fileList"
      :before-upload="beforeUpload"
      :on-success="handleSuccess"
      :on-remove="handleRemove"
      :on-exceed="handleExceed"
      :on-error="handleError"
      :limit="maxCount"
      :multiple="true"
      accept="image/jpeg,image/png,image/gif,image/webp"
      list-type="picture-card"
      :auto-upload="autoUpload"
      name="image"
    >
      <el-icon><Plus /></el-icon>
      <template #tip>
        <div class="upload-tip">
          支持 JPG、PNG、GIF、WebP 格式，单张不超过 5MB，最多 {{ maxCount }} 张
        </div>
      </template>
    </el-upload>

    <!-- 图片预览 -->
    <el-dialog v-model="previewVisible" title="图片预览" width="600px">
      <img :src="previewUrl" style="width: 100%;" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import Cookies from 'js-cookie'

interface UploadFile {
  id?: number
  name: string
  url?: string
  response?: {
    code: number
    data: {
      id: number
      url: string
    }
  }
  status?: string
}

const props = defineProps({
  modelValue: {
    type: Array as () => number[],
    default: () => []
  },
  maxCount: {
    type: Number,
    default: 5
  },
  autoUpload: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['update:modelValue'])

const uploadRef = ref()
const fileList = ref<UploadFile[]>([])
const previewVisible = ref(false)
const previewUrl = ref('')

const uploadUrl = computed(() => {
  return '/api/tickets/upload-image/'
})

const uploadHeaders = computed(() => {
  const token = Cookies.get('token')
  return {
    Authorization: token ? `Bearer ${token}` : ''
  }
})

// 监听外部值变化
watch(() => props.modelValue, (newVal) => {
  if (newVal.length === 0) {
    fileList.value = []
  }
}, { deep: true })

function beforeUpload(file: File) {
  const isImage = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'].includes(file.type)
  if (!isImage) {
    ElMessage.error('只能上传 JPG、PNG、GIF、WebP 格式的图片')
    return false
  }
  const isLt5M = file.size / 1024 / 1024 < 5
  if (!isLt5M) {
    ElMessage.error('图片大小不能超过 5MB')
    return false
  }
  return true
}

function handleSuccess(response: any, file: UploadFile) {
  if (response.code === 201) {
    const imageId = response.data.id
    const currentIds = [...props.modelValue]
    currentIds.push(imageId)
    emit('update:modelValue', currentIds)
    ElMessage.success('图片上传成功')
  } else {
    ElMessage.error(response.msg || '上传失败')
    // 移除失败的文件
    const index = fileList.value.indexOf(file)
    if (index > -1) {
      fileList.value.splice(index, 1)
    }
  }
}

function handleRemove(file: UploadFile) {
  if (file.response?.data?.id) {
    const imageId = file.response.data.id
    const currentIds = props.modelValue.filter(id => id !== imageId)
    emit('update:modelValue', currentIds)
  }
}

function handleExceed() {
  ElMessage.warning(`最多只能上传 ${props.maxCount} 张图片`)
}

function handleError() {
  ElMessage.error('图片上传失败')
}

function clearFiles() {
  fileList.value = []
  emit('update:modelValue', [])
}

defineExpose({
  clearFiles
})
</script>

<style scoped>
.image-upload {
  width: 100%;
}

.upload-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}

:deep(.el-upload--picture-card) {
  width: 100px;
  height: 100px;
}

:deep(.el-upload-list__item) {
  width: 100px;
  height: 100px;
}
</style>
