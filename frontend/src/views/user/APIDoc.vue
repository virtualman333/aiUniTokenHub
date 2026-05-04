<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="title">API文档</h2>
      <el-button @click="$router.back()">返回</el-button>
    </div>
    
    <div v-if="endpoint" class="doc-container">
      <el-card class="doc-header">
        <div class="api-info">
          <el-tag :type="getMethodType(endpoint.method)" size="large">{{ endpoint.method }}</el-tag>
          <h1>{{ endpoint.name }}</h1>
        </div>
        <div class="api-path">{{ endpoint.path }}</div>
        <div class="api-desc">{{ endpoint.description }}</div>
      </el-card>
      
      <el-row :gutter="20">
        <el-col :span="16">
          <el-card header="请求示例" class="doc-section">
            <el-tabs v-model="activeTab">
              <el-tab-pane label="cURL" name="curl">
                <pre class="code-block">{{ getCurlExample() }}</pre>
              </el-tab-pane>
              <el-tab-pane label="Python" name="python">
                <pre class="code-block">{{ getPythonExample() }}</pre>
              </el-tab-pane>
              <el-tab-pane label="JavaScript" name="js">
                <pre class="code-block">{{ getJsExample() }}</pre>
              </el-tab-pane>
            </el-tabs>
          </el-card>
          
          <el-card header="在线测试" class="doc-section">
            <el-form label-width="80px">
              <el-form-item label="请求方法">
                <el-select v-model="testForm.method">
                  <el-option label="GET" value="GET" />
                  <el-option label="POST" value="POST" />
                  <el-option label="PUT" value="PUT" />
                  <el-option label="DELETE" value="DELETE" />
                </el-select>
              </el-form-item>
              <el-form-item label="参数">
                <el-input
                  v-model="testForm.params"
                  type="textarea"
                  :rows="4"
                  placeholder='{"key": "value"}'
                />
              </el-form-item>
              <el-form-item label="请求体">
                <el-input
                  v-model="testForm.data"
                  type="textarea"
                  :rows="4"
                  placeholder='{"key": "value"}'
                />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="testing" @click="handleTest">发送请求</el-button>
              </el-form-item>
            </el-form>
            
            <div v-if="testResult" class="test-result">
              <el-divider>响应结果</el-divider>
              <el-tag :type="testResult.success ? 'success' : 'danger'">
                {{ testResult.success ? '成功' : '失败' }}
              </el-tag>
              <pre>{{ JSON.stringify(testResult, null, 2) }}</pre>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="8">
          <el-card header="接口信息" class="doc-section">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="分类">{{ endpoint.category_name }}</el-descriptions-item>
              <el-descriptions-item label="限流">{{ endpoint.rate_limit }}/min</el-descriptions-item>
              <el-descriptions-item label="超时">{{ endpoint.timeout }}s</el-descriptions-item>
              <el-descriptions-item label="是否公开">
                <el-tag :type="endpoint.is_public ? 'success' : 'warning'" size="small">
                  {{ endpoint.is_public ? '公开' : '需认证' }}
                </el-tag>
              </el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
      </el-row>
    </div>
    
    <el-empty v-else description="加载中..." />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/stores'

const route = useRoute()
const endpoint = ref(null)
const activeTab = ref('curl')
const testing = ref(false)
const testResult = ref(null)

const testForm = ref({
  method: 'GET',
  params: '',
  data: ''
})

onMounted(async () => {
  const res = await api.get(`/proxy/endpoints/${route.params.id}/`)
  endpoint.value = res
  testForm.value.method = res.method
})

const getMethodType = (method) => {
  const types = { GET: '', POST: 'success', PUT: 'warning', DELETE: 'danger', PATCH: 'info' }
  return types[method] || ''
}

const getCurlExample = () => {
  const baseUrl = '/api/proxy/endpoints'
  return `curl -X ${endpoint.value?.method || 'GET'} \\
  '${window.location.origin}${baseUrl}/${route.params.id}/proxy/' \\
  -H 'Authorization: Bearer YOUR_API_KEY' \\
  -H 'Content-Type: application/json'`
}

const getPythonExample = () => {
  return `import requests

url = "${window.location.origin}/api/proxy/endpoints/${route.params.id}/proxy/"
headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json"
}

response = requests.${(endpoint.value?.method || 'GET').toLowerCase()}(url, headers=headers)
print(response.json())`
}

const getJsExample = () => {
  return `const response = await fetch('/api/proxy/endpoints/${route.params.id}/proxy/', {
  method: '${endpoint.value?.method || 'GET'}',
  headers: {
    'Authorization': 'Bearer YOUR_API_KEY',
    'Content-Type': 'application/json'
  }
});
const data = await response.json();
console.log(data);`
}

const handleTest = async () => {
  testing.value = true
  testResult.value = null
  try {
    const res = await api.post(`/proxy/endpoints/${route.params.id}/proxy/`, {
      method: testForm.value.method,
      params: testForm.value.params ? JSON.parse(testForm.value.params) : {},
      data: testForm.value.data ? JSON.parse(testForm.value.data) : null
    })
    testResult.value = res
  } catch (error) {
    testResult.value = { success: false, error: error.message }
  } finally {
    testing.value = false
  }
}
</script>

<style lang="scss" scoped>
.doc-header {
  margin-bottom: 20px;
  
  .api-info {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
    
    h1 {
      margin: 0;
      font-size: 20px;
    }
  }
  
  .api-path {
    font-family: monospace;
    background: #f5f7fa;
    padding: 12px;
    border-radius: 4px;
    margin-bottom: 12px;
  }
  
  .api-desc {
    color: #666;
  }
}

.doc-section {
  margin-bottom: 20px;
}

.code-block {
  background: #282c34;
  color: #abb2bf;
  padding: 16px;
  border-radius: 4px;
  overflow-x: auto;
  font-family: 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.5;
}

.test-result {
  margin-top: 16px;
  
  pre {
    background: #f5f7fa;
    padding: 12px;
    border-radius: 4px;
    margin-top: 12px;
    max-height: 300px;
    overflow: auto;
  }
}
</style>
