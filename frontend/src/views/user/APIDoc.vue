<template>
  <div class="api-doc">
    <!-- 头部 -->
    <div class="header">
      <h1>API 接口文档</h1>
      <p class="subtitle">兼容 OpenAI 接口格式的统一 LLM API 服务</p>
    </div>

    <!-- 基础信息 -->
    <el-card class="info-card">
      <template #header>
        <div class="card-header">
          <span>基础信息</span>
        </div>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="API Base URL">
          <code>{{ apiBaseUrl }}</code>
          <el-button size="small" text @click="copyText(apiBaseUrl)">复制</el-button>
        </el-descriptions-item>
        <el-descriptions-item label="认证方式">Bearer Token (API Key)</el-descriptions-item>
        <el-descriptions-item label="模型列表">
          <el-tag size="small" v-for="model in availableModels" :key="model.code" style="margin-right: 4px;">
            {{ model.code }}
          </el-tag>
          <el-button size="small" text @click="refreshModels">刷新</el-button>
        </el-descriptions-item>
        <el-descriptions-item label="协议">OpenAI Compatible</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 认证说明 -->
    <el-card class="info-card">
      <template #header>
        <div class="card-header">
          <span>认证说明</span>
          <el-button type="primary" @click="$router.push('/app/tutorial')">
            快速接入教程 <el-icon class="el-icon--right"><ArrowRight /></el-icon>
          </el-button>
        </div>
      </template>
      <p>所有 API 请求都需要在 Header 中携带您的 API Key：</p>
      <CodeBlock :code="authHeaderCode" language="text" />
      <p class="tip">请在 <router-link to="/app/my-keys">我的密钥</router-link> 页面获取您的 API Key</p>
    </el-card>

    <!-- 在线测试 -->
    <el-card class="info-card">
      <template #header>
        <div class="card-header">
          <span>在线测试</span>
          <el-button type="primary" size="small" @click="showTestDialog = true">
            <el-icon><VideoPlay /></el-icon> 打开测试工具
          </el-button>
        </div>
      </template>
      <p>使用下方测试工具可以在线调试 API 接口</p>
    </el-card>

    <!-- 核心接口 -->
    <el-card class="info-card">
      <template #header>
        <div class="card-header">
          <span>核心接口</span>
        </div>
      </template>

      <!-- 模型列表 -->
      <div class="endpoint-section">
        <div class="endpoint-header">
          <el-tag type="success">GET</el-tag>
          <h3>/models - 获取模型列表</h3>
        </div>
        <p class="endpoint-desc">列出所有可用的模型</p>
        <div class="example-block">
          <el-tabs>
            <el-tab-pane label="cURL">
              <CodeBlock :code="modelsCurlCode" language="bash" />
            </el-tab-pane>
            <el-tab-pane label="Python">
              <CodeBlock :code="modelsPythonCode" language="python" />
            </el-tab-pane>
            <el-tab-pane label="JavaScript">
              <CodeBlock :code="modelsJsCode" language="javascript" />
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>

      <el-divider />

      <!-- 聊天完成 -->
      <div class="endpoint-section">
        <div class="endpoint-header">
          <el-tag type="success">POST</el-tag>
          <h3>/chat/completions - 聊天完成</h3>
        </div>
        <p class="endpoint-desc">创建聊天补全请求（支持流式输出）</p>
        
        <div class="params-table">
          <h4>请求参数</h4>
          <el-table :data="chatParams" size="small" border>
            <el-table-column prop="name" label="参数" width="180">
              <template #default="{ row }">
                <code>{{ row.name }}</code>
              </template>
            </el-table-column>
            <el-table-column prop="type" label="类型" width="100" />
            <el-table-column prop="required" label="必填" width="80">
              <template #default="{ row }">
                <el-tag v-if="row.required" type="danger" size="small">是</el-tag>
                <el-tag v-else size="small">否</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="说明" />
            <el-table-column prop="default" label="默认值" width="120" />
          </el-table>
        </div>

        <div class="example-block">
          <el-tabs>
            <el-tab-pane label="cURL">
              <CodeBlock :code="chatCurlCode" language="bash" />
            </el-tab-pane>
            <el-tab-pane label="Python">
              <CodeBlock :code="chatPythonCode" language="python" />
            </el-tab-pane>
            <el-tab-pane label="JavaScript">
              <CodeBlock :code="chatJsCode" language="javascript" />
            </el-tab-pane>
          </el-tabs>
        </div>

        <div class="response-example">
          <h4>响应示例</h4>
          <CodeBlock :code="chatResponseExample" language="json" />
        </div>
      </div>

      <el-divider />

      <!-- 文本完成 -->
      <div class="endpoint-section">
        <div class="endpoint-header">
          <el-tag type="success">POST</el-tag>
          <h3>/completions - 文本完成</h3>
        </div>
        <p class="endpoint-desc">创建文本补全请求（兼容旧版 GPT-3 接口）</p>
        
        <div class="example-block">
          <el-tabs>
            <el-tab-pane label="cURL">
              <CodeBlock :code="completionsCurlCode" language="bash" />
            </el-tab-pane>
            <el-tab-pane label="Python">
              <CodeBlock :code="completionsPythonCode" language="python" />
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>

      <el-divider />

      <!-- Embeddings -->
      <div class="endpoint-section">
        <div class="endpoint-header">
          <el-tag type="success">POST</el-tag>
          <h3>/embeddings - 向量嵌入</h3>
        </div>
        <p class="endpoint-desc">获取文本的向量嵌入表示</p>
        
        <div class="example-block">
          <el-tabs>
            <el-tab-pane label="cURL">
              <CodeBlock :code="embeddingsCurlCode" language="bash" />
            </el-tab-pane>
            <el-tab-pane label="Python">
              <CodeBlock :code="embeddingsPythonCode" language="python" />
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
    </el-card>

    <!-- 错误码 -->
    <el-card class="info-card">
      <template #header>
        <div class="card-header">
          <span>错误码</span>
        </div>
      </template>
      <el-table :data="errorCodes" size="small" border>
        <el-table-column prop="code" label="错误码" width="120" />
        <el-table-column prop="message" label="说明" />
        <el-table-column prop="solution" label="解决方案" />
      </el-table>
    </el-card>

    <!-- 使用限制 -->
    <el-card class="info-card">
      <template #header>
        <div class="card-header">
          <span>使用限制</span>
        </div>
      </template>
      <el-row :gutter="20">
        <el-col :span="8">
          <div class="limit-item">
            <el-icon size="32" color="#409eff"><Timer /></el-icon>
            <h4>速率限制</h4>
            <p>根据套餐不同，每分钟 60-300 次请求</p>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="limit-item">
            <el-icon size="32" color="#67c23a"><Document /></el-icon>
            <h4>Token 限制</h4>
            <p>单次请求最大 128K tokens</p>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="limit-item">
            <el-icon size="32" color="#e6a23c"><Coin /></el-icon>
            <h4>账户余额</h4>
            <p>余额不足时请求会被拒绝</p>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- API 测试对话框 -->
    <el-dialog v-model="showTestDialog" title="API 在线测试" width="900px" :close-on-click-modal="false">
      <div class="test-container">
        <!-- 快速选择密钥 -->
        <div v-if="userKeys.length > 0" class="quick-key-select">
          <span class="label">快速选择密钥：</span>
          <el-tag
            v-for="key in userKeys"
            :key="key.id"
            class="key-tag"
            :type="chatTestForm.apiKey === key.key ? 'primary' : 'info'"
            @click="selectKey(key.key)"
          >
            {{ key.name }}
          </el-tag>
        </div>

        <el-tabs v-model="testTab">
          <!-- Chat Completions -->
          <el-tab-pane label="Chat Completions" name="chat">
            <div class="test-form">
              <el-form :model="chatTestForm" label-width="120px">
                <el-form-item label="API Key">
                  <el-input v-model="chatTestForm.apiKey" type="password" placeholder="sk-..." show-password />
                </el-form-item>
                <el-form-item label="模型">
                  <el-select v-model="chatTestForm.model" placeholder="选择模型" filterable allow-create>
                    <el-option v-for="m in availableModels" :key="m.code" :label="m.name" :value="m.code" />
                  </el-select>
                </el-form-item>
                <el-form-item label="System Prompt">
                  <el-input v-model="chatTestForm.systemPrompt" type="textarea" :rows="2" placeholder="你是一个有用的助手" />
                </el-form-item>
                <el-form-item label="User Message">
                  <el-input v-model="chatTestForm.messages" type="textarea" :rows="3" placeholder="你好" />
                </el-form-item>
                <el-form-item label="Temperature">
                  <el-slider v-model="chatTestForm.temperature" :min="0" :max="2" :step="0.1" show-input />
                </el-form-item>
                <el-form-item label="Max Tokens">
                  <el-input-number v-model="chatTestForm.maxTokens" :min="1" :max="4096" />
                </el-form-item>
                <el-form-item label="Stream">
                  <el-switch v-model="chatTestForm.stream" />
                </el-form-item>
              </el-form>
              <div class="test-actions">
                <el-button type="primary" @click="testChat" :loading="chatLoading" :disabled="!chatTestForm.apiKey">
                  发送请求
                </el-button>
                <el-button @click="resetChatForm">重置</el-button>
              </div>
            </div>
          </el-tab-pane>

          <!-- Models List -->
          <el-tab-pane label="Models List" name="models">
            <div class="test-form">
              <el-form label-width="120px">
                <el-form-item label="API Key">
                  <el-input v-model="modelsTestForm.apiKey" type="password" placeholder="sk-..." show-password />
                </el-form-item>
              </el-form>
              <div class="test-actions">
                <el-button type="primary" @click="testModels" :loading="modelsLoading" :disabled="!modelsTestForm.apiKey">
                  获取模型列表
                </el-button>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>

        <!-- 响应结果 -->
        <div class="test-result">
          <div class="result-header">
            <span>响应结果</span>
            <el-button size="small" text @click="copyText(testResponse)" :disabled="!testResponse">
              复制
            </el-button>
          </div>
          <div v-if="chatLoading || modelsLoading" class="loading-state">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>{{ testTab === 'chat' ? '等待响应...' : '加载中...' }}</span>
          </div>
          <div v-else-if="testError" class="error-state">
            <el-icon><CircleClose /></el-icon>
            <span>{{ testError }}</span>
          </div>
          <div v-else-if="streamContent" class="stream-content">
            <pre>{{ streamContent }}</pre>
          </div>
          <pre v-else-if="testResponse" class="response-content">{{ testResponse }}</pre>
          <div v-else class="empty-state">
            响应将显示在这里
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Timer, Document, Coin, VideoPlay, Loading, CircleClose, ArrowRight } from '@element-plus/icons-vue'
import CodeBlock from '@/components/CodeBlock.vue'
import api from '@/stores'
import axios from 'axios'
import Cookies from 'js-cookie'
import { useUserStore } from '@/stores'
import { copyToClipboard } from '@/utils/clipboard'

const apiBaseUrl = ref(window.location.origin + '/api/proxy/v1')

const availableModels = ref([])

// 用户密钥列表
const userKeys = ref([])
const loadingKeys = ref(false)

// 测试相关
const showTestDialog = ref(false)
const testTab = ref('chat')
const chatLoading = ref(false)
const modelsLoading = ref(false)
const testResponse = ref('')
const testError = ref('')
const streamContent = ref('')

const chatTestForm = reactive({
  apiKey: '',
  model: 'gpt-5.5',
  systemPrompt: '你是一个有帮助的AI助手',
  messages: '你好',
  temperature: 1.0,
  maxTokens: 2048,
  stream: true
})

const modelsTestForm = reactive({
  apiKey: ''
})

// 检查是否已登录
const isLoggedIn = computed(() => !!Cookies.get('token'))

const chatParams = ref([
  { name: 'model', type: 'string', required: true, description: '模型标识符', default: '-' },
  { name: 'messages', type: 'array', required: true, description: '消息列表 [{role, content}]', default: '-' },
  { name: 'temperature', type: 'float', required: false, description: '采样温度 (0-2)', default: '1.0' },
  { name: 'max_tokens', type: 'integer', required: false, description: '最大生成 tokens', default: '模型上限' },
  { name: 'stream', type: 'boolean', required: false, description: '是否使用流式输出', default: 'false' },
  { name: 'top_p', type: 'float', required: false, description: '核采样概率', default: '1.0' },
  { name: 'frequency_penalty', type: 'float', required: false, description: '频率惩罚 (-2~2)', default: '0' },
  { name: 'presence_penalty', type: 'float', required: false, description: '存在惩罚 (-2~2)', default: '0' },
  { name: 'stop', type: 'array', required: false, description: '停止词列表', default: '-' },
  { name: 'response_format', type: 'object', required: false, description: '响应格式 {type: "json_object"}', default: '-' },
])

const chatResponseExample = ref(`{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1677858242,
  "model": "gpt-5.5",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "你好！有什么我可以帮助你的吗？"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 30,
    "total_tokens": 50
  }
}`)

const authHeaderCode = 'Authorization: Bearer YOUR_API_KEY'
const modelsCurlCode = computed(() => `curl ${apiBaseUrl.value}/models \\
  -H "Authorization: Bearer YOUR_API_KEY"`)
const modelsPythonCode = computed(() => `from openai import OpenAI

client = OpenAI(
    api_key="YOUR_API_KEY",
    base_url="${apiBaseUrl.value}"
)

# 获取模型列表
models = client.models.list()
for model in models.data:
    print(model.id)`)
const modelsJsCode = computed(() => `import OpenAI from 'openai';

const client = new OpenAI({
  apiKey: 'YOUR_API_KEY',
  baseURL: '${apiBaseUrl.value}'
});

const models = await client.models.list();
console.log(models.data);`)
const chatCurlCode = computed(() => `curl ${apiBaseUrl.value}/chat/completions \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "system", "content": "你是我的助手"},
      {"role": "user", "content": "你好"}
    ],
    "stream": false
  }'`)
const chatPythonCode = computed(() => `from openai import OpenAI

client = OpenAI(
    api_key="YOUR_API_KEY",
    base_url="${apiBaseUrl.value}"
)

# 非流式响应
completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "你是我的助手"},
        {"role": "user", "content": "你好"}
    ]
)
print(completion.choices[0].message.content)

# 流式响应
stream = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "讲个笑话"}],
    stream=True
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")`)
const chatJsCode = computed(() => `import OpenAI from 'openai';

const client = new OpenAI({
  apiKey: 'YOUR_API_KEY',
  baseURL: '${apiBaseUrl.value}'
});

// 非流式响应
const completion = await client.chat.completions.create({
  model: 'gpt-3.5-turbo',
  messages: [
    { role: 'system', content: '你是我的助手' },
    { role: 'user', content: '你好' }
  ]
});
console.log(completion.choices[0].message.content);

// 流式响应
const stream = await client.chat.completions.create({
  model: 'gpt-3.5-turbo',
  messages: [{ role: 'user', content: '讲个笑话' }],
  stream: true
});
for await (const chunk of stream) {
  process.stdout.write(chunk.choices[0].delta.content || '');
}`)
const completionsCurlCode = computed(() => `curl ${apiBaseUrl.value}/completions \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "gpt-3.5-turbo-instruct",
    "prompt": "The capital of France is",
    "max_tokens": 50
  }'`)
const completionsPythonCode = `completion = client.completions.create(
    model="gpt-3.5-turbo-instruct",
    prompt="The capital of France is",
    max_tokens=50
)
print(completion.choices[0].text)`
const embeddingsCurlCode = computed(() => `curl ${apiBaseUrl.value}/embeddings \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "text-embedding-ada-002",
    "input": "The food was delicious and the service"
  }'`)
const embeddingsPythonCode = `embedding = client.embeddings.create(
    model="text-embedding-ada-002",
    input="The food was delicious and the service"
)
print(embedding.data[0].embedding)`

const errorCodes = ref([
  { code: '401', message: 'Invalid API Key', solution: '检查 API Key 是否正确' },
  { code: '403', message: 'Forbidden', solution: '账户权限不足或已禁用' },
  { code: '429', message: 'Rate limit exceeded', solution: '降低请求频率或升级套餐' },
  { code: '500', message: 'Internal server error', solution: '服务端错误，稍后重试' },
  { code: '503', message: 'Service unavailable', solution: '服务暂时不可用' },
  { code: 'insufficient_quota', message: '账户余额不足', solution: '请前往账单中心充值' },
])

onMounted(async () => {
  refreshModels()
  if (isLoggedIn.value) {
    loadUserKeys()
  }
})

async function loadUserKeys() {
  loadingKeys.value = true
  try {
    const userStore = useUserStore()
    const res = await userStore.fetchApiKeys()
    // 提取密钥列表
    userKeys.value = res.results || res || []
    // 如果有密钥且当前未输入，自动填入第一个并获取模型列表
    if (userKeys.value.length > 0 && !chatTestForm.apiKey) {
      const firstKey = userKeys.value[0].key
      chatTestForm.apiKey = firstKey
      modelsTestForm.apiKey = firstKey
      await refreshModels(firstKey)
    }
  } catch (e) {
    console.warn('获取用户密钥失败')
  } finally {
    loadingKeys.value = false
  }
}

async function selectKey(key) {
  chatTestForm.apiKey = key
  modelsTestForm.apiKey = key
  ElMessage.success('已选择密钥')
  // 选择密钥后自动获取模型列表
  await refreshModels(key)
}

async function refreshModels(apiKey = null) {
  try {
    const response = await axios.get(`${apiBaseUrl.value}/models`, {
      headers: apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {}
    })
    const res = response.data
    if (res && res.data && res.data.length > 0) {
      availableModels.value = res.data.map(m => ({
        code: m.id,
        name: m.id
      }))
    } else {
      availableModels.value = []
    }
  } catch (e) {
    console.warn('获取模型列表失败')
    availableModels.value = []
  }
}

async function testChat() {
  if (!chatTestForm.apiKey) {
    ElMessage.warning('请输入 API Key')
    return
  }
  
  chatLoading.value = true
  testResponse.value = ''
  testError.value = ''
  streamContent.value = ''
  
  try {
    const messages = []
    if (chatTestForm.systemPrompt) {
      messages.push({ role: 'system', content: chatTestForm.systemPrompt })
    }
    messages.push({ role: 'user', content: chatTestForm.messages })
    
    const requestData = {
      model: chatTestForm.model,
      messages: messages,
      temperature: chatTestForm.temperature,
      max_tokens: chatTestForm.maxTokens,
      stream: chatTestForm.stream
    }
    
    if (chatTestForm.stream) {
      // 流式响应
      const response = await fetch(`${apiBaseUrl.value}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${chatTestForm.apiKey}`
        },
        body: JSON.stringify(requestData)
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error?.message || `HTTP ${response.status}`)
      }
      
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      streamContent.value = ''
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') {
              chatLoading.value = false
              return
            }
            try {
              const parsed = JSON.parse(data)
              const content = parsed.choices?.[0]?.delta?.content || ''
              if (content) {
                streamContent.value += content
              }
            } catch (e) {}
          }
        }
      }
    } else {
      // 非流式响应
      const response = await axios.post(`${apiBaseUrl.value}/chat/completions`, requestData, {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${chatTestForm.apiKey}`
        }
      })
      testResponse.value = JSON.stringify(response.data, null, 2)
    }
  } catch (e) {
    testError.value = e.message || '请求失败'
    ElMessage.error(testError.value)
  } finally {
    chatLoading.value = false
  }
}

async function testModels() {
  if (!modelsTestForm.apiKey) {
    ElMessage.warning('请输入 API Key')
    return
  }
  
  modelsLoading.value = true
  testResponse.value = ''
  testError.value = ''
  
  try {
    const response = await axios.get(`${apiBaseUrl.value}/models`, {
      headers: {
        'Authorization': `Bearer ${modelsTestForm.apiKey}`
      }
    })
    testResponse.value = JSON.stringify(response.data, null, 2)
  } catch (e) {
    testError.value = e.response?.data?.error?.message || e.message || '请求失败'
    ElMessage.error(testError.value)
  } finally {
    modelsLoading.value = false
  }
}

function resetChatForm() {
  chatTestForm.messages = ''
  chatTestForm.stream = false
  testResponse.value = ''
  testError.value = ''
  streamContent.value = ''
}

async function copyText(text) {
  const success = await copyToClipboard(text)
  if (success) {
    ElMessage.success('已复制到剪贴板')
  } else {
    ElMessage.error('复制失败')
  }
}
</script>

<style scoped>
.api-doc {
  max-width: 1000px;
  margin: 0 auto;
  min-width: 0;
}

.header {
  text-align: center;
  margin-bottom: 32px;
}

.header h1 {
  font-size: 28px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 8px;
}

.subtitle {
  color: #666;
  font-size: 16px;
}

.info-card {
  margin-bottom: 24px;
}

.card-header {
  font-weight: 600;
  font-size: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.endpoint-section {
  padding: 16px 0;
}

.endpoint-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  min-width: 0;
}

.endpoint-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.endpoint-desc {
  color: #666;
  margin-bottom: 16px;
}

.params-table {
  margin-bottom: 16px;
}

.params-table h4 {
  margin-bottom: 8px;
  font-size: 14px;
  color: #333;
}

.example-block {
  margin-bottom: 16px;
}

.response-example h4 {
  margin-bottom: 8px;
  font-size: 14px;
}



.tip {
  color: #666;
  font-size: 14px;
  margin-top: 12px;
}

.tip a {
  color: #607bfa;
  text-decoration: none;
}

.tip a:hover {
  text-decoration: underline;
}

.limit-item {
  text-align: center;
  padding: 20px;
}

.limit-item h4 {
  margin: 12px 0 8px;
  font-size: 16px;
}

.limit-item p {
  color: #666;
  font-size: 14px;
  margin: 0;
}

/* 测试对话框样式 */
.test-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.quick-key-select {
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 16px;
}

.quick-key-select .label {
  font-size: 14px;
  color: #666;
  margin-right: 12px;
}

.quick-key-select .key-tag {
  cursor: pointer;
  margin-right: 8px;
}

.test-form {
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.test-actions {
  margin-top: 16px;
  display: flex;
  gap: 12px;
}

.test-result {
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  min-height: 300px;
  max-height: 400px;
  overflow: auto;
}

.result-header {
  padding: 12px 16px;
  background: #fafafa;
  border-bottom: 1px solid #dcdfe6;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  position: sticky;
  top: 0;
}

.response-content {
  padding: 16px;
  margin: 0;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-all;
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 200px;
  color: #909399;
}

.error-state {
  color: #f56c6c;
}

.stream-content {
  padding: 16px;
}

.stream-content pre {
  margin: 0;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

@media (max-width: 768px) {
  .header {
    text-align: left;
    margin-bottom: 24px;
  }

  .header h1 {
    font-size: 24px;
  }

  .card-header {
    flex-direction: column;
    align-items: stretch;
  }

  .card-header .el-button {
    width: 100%;
  }

  .endpoint-header {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .endpoint-header h3 {
    line-height: 1.4;
  }

  .response-content,
  .stream-content pre {
    font-size: 12px;
  }

  .limit-item {
    padding: 14px 0;
  }

  .test-form {
    padding: 12px;
  }

  .test-form :deep(.el-form-item) {
    display: block;
  }

  .test-form :deep(.el-form-item__label) {
    width: auto !important;
    justify-content: flex-start;
  }

  .test-form :deep(.el-form-item__content) {
    margin-left: 0 !important;
  }

  .test-actions {
    flex-direction: column;
  }

  .test-actions .el-button {
    width: 100%;
    margin-left: 0;
  }

  .quick-key-select {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .quick-key-select .label {
    width: 100%;
  }
}
</style>
