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
          <code>{{ apiBaseUrl }}/v1</code>
          <el-button size="small" text @click="copyText(apiBaseUrl + '/v1')">复制</el-button>
        </el-descriptions-item>
        <el-descriptions-item label="认证方式">Bearer Token (API Key)</el-descriptions-item>
        <el-descriptions-item label="模型列表">
          <el-tag size="small" v-for="model in models" :key="model.code" style="margin-right: 4px;">
            {{ model.code }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="协议">OpenAI Compatible</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 认证说明 -->
    <el-card class="info-card">
      <template #header>
        <div class="card-header">
          <span>认证说明</span>
        </div>
      </template>
      <p>所有 API 请求都需要在 Header 中携带您的 API Key：</p>
      <pre class="code-block">Authorization: Bearer YOUR_API_KEY</pre>
      <p class="tip">请在 <router-link to="/my-keys">我的密钥</router-link> 页面获取您的 API Key</p>
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
              <pre class="code-block">curl {{ apiBaseUrl }}/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"</pre>
            </el-tab-pane>
            <el-tab-pane label="Python">
              <pre class="code-block">import openai

client = openai.OpenAI(
    api_key="YOUR_API_KEY",
    base_url="{{ apiBaseUrl }}/v1"
)

# 获取模型列表
models = client.models.list()
for model in models.data:
    print(model.id)</pre>
            </el-tab-pane>
            <el-tab-pane label="JavaScript">
              <pre class="code-block">const client = new OpenAI({
  apiKey: 'YOUR_API_KEY',
  baseURL: '{{ apiBaseUrl }}/v1'
});

const models = await client.models.list();
console.log(models.data);</pre>
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
              <pre class="code-block">curl {{ apiBaseUrl }}/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "system", "content": "你是我的助手"},
      {"role": "user", "content": "你好"}
    ],
    "stream": false
  }'</pre>
            </el-tab-pane>
            <el-tab-pane label="Python">
              <pre class="code-block">from openai import OpenAI

client = OpenAI(
    api_key="YOUR_API_KEY",
    base_url="{{ apiBaseUrl }}/v1"
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
        print(chunk.choices[0].delta.content, end="")</pre>
            </el-tab-pane>
            <el-tab-pane label="JavaScript">
              <pre class="code-block">import OpenAI from 'openai';

const client = new OpenAI({
  apiKey: 'YOUR_API_KEY',
  baseURL: '{{ apiBaseUrl }}/v1'
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
}</pre>
            </el-tab-pane>
          </el-tabs>
        </div>

        <div class="response-example">
          <h4>响应示例</h4>
          <pre class="code-block">{{ chatResponseExample }}</pre>
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
              <pre class="code-block">curl {{ apiBaseUrl }}/v1/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo-instruct",
    "prompt": "The capital of France is",
    "max_tokens": 50
  }'</pre>
            </el-tab-pane>
            <el-tab-pane label="Python">
              <pre class="code-block">completion = client.completions.create(
    model="gpt-3.5-turbo-instruct",
    prompt="The capital of France is",
    max_tokens=50
)
print(completion.choices[0].text)</pre>
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
              <pre class="code-block">curl {{ apiBaseUrl }}/v1/embeddings \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "text-embedding-ada-002",
    "input": "The food was delicious and the service"
  }'</pre>
            </el-tab-pane>
            <el-tab-pane label="Python">
              <pre class="code-block">embedding = client.embeddings.create(
    model="text-embedding-ada-002",
    input="The food was delicious and the service"
)
print(embedding.data[0].embedding)</pre>
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Timer, Document, Coin } from '@element-plus/icons-vue'

const apiBaseUrl = ref(window.location.origin + '/api')

const models = ref([
  { code: 'gpt-4', name: 'GPT-4' },
  { code: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo' },
  { code: 'claude-3-opus', name: 'Claude 3 Opus' },
  { code: 'claude-3-sonnet', name: 'Claude 3 Sonnet' },
])

const chatParams = ref([
  { name: 'model', type: 'string', required: true, description: '模型标识符', default: '-' },
  { name: 'messages', type: 'array', required: true, description: '消息列表 [{role, content}]', default: '-' },
  { name: 'temperature', type: 'float', required: false, description: '采样温度 (0-2)', default: '1.0' },
  { name: 'max_tokens', type: 'integer', required: false, description: '最大生成 tokens', default: '模型上限' },
  { name: 'stream', type: 'boolean', required: false, description: '是否使用流式输出', default: 'false' },
  { name: 'top_p', type: 'float', required: false, description: '核采样概率', default: '1.0' },
  { name: 'frequency_penalty', type: 'float', required: false, description: '频率惩罚 (-2~2)', default: '0' },
  { name: 'presence_penalty', type: 'float', required: false, description: '存在惩罚 (-2~2)', default: '0' },
])

const chatResponseExample = ref(`{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1677858242,
  "model": "gpt-3.5-turbo",
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

const errorCodes = ref([
  { code: '401', message: 'Invalid API Key', solution: '检查 API Key 是否正确' },
  { code: '403', message: 'Forbidden', solution: '账户权限不足或已禁用' },
  { code: '429', message: 'Rate limit exceeded', solution: '降低请求频率或升级套餐' },
  { code: '500', message: 'Internal server error', solution: '服务端错误，稍后重试' },
  { code: '503', message: 'Service unavailable', solution: '服务暂时不可用' },
  { code: 'insufficient_quota', message: '账户余额不足', solution: '请前往账单中心充值' },
])

function copyText(text) {
  navigator.clipboard.writeText(text)
  ElMessage.success('已复制到剪贴板')
}
</script>

<style scoped>
.api-doc {
  max-width: 1000px;
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
}

.endpoint-section {
  padding: 16px 0;
}

.endpoint-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
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

.code-block {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
  margin: 0;
}

.tip {
  color: #666;
  font-size: 14px;
  margin-top: 12px;
}

.tip a {
  color: #409eff;
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
</style>
