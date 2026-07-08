<template>
  <div class="tutorial-container">
    <div class="header">
      <h1>快速接入教程</h1>
      <p class="subtitle">学习如何将不同工具接入我们的服务</p>
    </div>

    <el-card class="content-card">
      <el-tabs v-model="activeTab" class="tutorial-tabs">
        <!-- ClaudeCode 教程 -->
        <el-tab-pane label="ClaudeCode 教程" name="claudecode">
          <div class="tutorial-content">
            <p>以下是 Windows、macOS 和 Linux 系统下设置 <code>ANTHROPIC_BASE_URL</code> 和 <code>ANTHROPIC_AUTH_TOKEN</code> 环境变量的详细方法：</p>
            <h3>CC switch</h3>
            <el-image :src="ccSwitch" alt="CC switch" />
            <el-divider />
            <h3>Windows 系统</h3>
            <h4>方法1：配置 settings.json</h4>
            <p>创建 <code>~/.claude/settings.json</code> 文件，内容如下：</p>
            <CodeBlock :code="claudeWindowsSettings" language="json" />
            
            <p>vscode中插件使用，创建文件 <code>~/.claude/config.json</code></p>
            <CodeBlock :code="claudeVscodeConfig" language="json" />

            <h4>方法2：临时设置（仅当前终端有效）</h4>
            <p>在 PowerShell 或 CMD 中执行：</p>
            <CodeBlock :code="claudeWindowsTemp" language="powershell" />

            <h4>方法3：永久设置（全局生效）</h4>
            <p>图形界面：</p>
            <ol>
              <li>右键「此电脑」→「属性」→「高级系统设置」→「环境变量」</li>
              <li>在「用户变量」或「系统变量」中新建：
                <ul>
                  <li>变量名：<code>ANTHROPIC_BASE_URL</code></li>
                  <li>变量值：<code>{{ apiBaseUrl }}</code></li>
                </ul>
              </li>
              <li>同样方法添加 <code>ANTHROPIC_AUTH_TOKEN</code></li>
            </ol>
            <p>PowerShell 永久设置：</p>
            <CodeBlock :code="claudeWindowsPerm" language="powershell" />
            <p class="tip">重启终端后生效。</p>

            <el-divider />

            <h3>macOS 系统</h3>
            <h4>方法1：配置 settings.json</h4>
            <p>创建 <code>~/.claude/settings.json</code> 文件，内容如下：</p>
            <CodeBlock :code="claudeMacSettings" language="json" />

            <p>vscode中插件使用，创建文件 <code>~/.claude/config.json</code></p>
            <CodeBlock :code="claudeVscodeConfig" language="json" />

            <h4>方法2：临时设置（仅当前终端有效）</h4>
            <p>在 终端 中执行：</p>
            <CodeBlock :code="claudeMacTemp" language="bash" />

            <h4>方法3：永久设置</h4>
            <p>编辑 shell 配置文件（根据使用的 shell 选择）：</p>
            <CodeBlock :code="claudeMacPerm" language="bash" />
            <p>立即生效：</p>
            <CodeBlock code="source ~/.bash_profile  # 或 source ~/.zshrc" language="bash" />

            <el-divider />

            <h3>Linux 系统</h3>
            <h4>方法1：配置 settings.json</h4>
            <p>创建 <code>~/.claude/settings.json</code> 文件，内容如下：</p>
            <CodeBlock :code="claudeLinuxSettings" language="json" />

            <h4>方法2：临时设置（仅当前终端有效）</h4>
            <p>在 终端 中执行：</p>
            <CodeBlock :code="claudeLinuxTemp" language="bash" />

            <h4>方法3：永久设置</h4>
            <p>编辑 shell 配置文件（根据使用的 shell 选择）：</p>
            <CodeBlock :code="claudeLinuxPerm" language="bash" />
            <p>立即生效：</p>
            <CodeBlock code="source ~/.bashrc  # 或 source ~/.zshrc" language="bash" />

            <el-divider />

            <h3>通用验证方法</h3>
            <p>在所有系统中，可以通过以下命令验证是否设置成功：</p>
            <CodeBlock :code="claudeVerify" language="bash" />
          </div>
        </el-tab-pane>

        <!-- Codex 教程 -->
        <el-tab-pane label="Codex 教程" name="codex">
          <div class="tutorial-content">
            <h3>1、安装Codex</h3>
            <p>使用 npm 进行安装</p>
            <CodeBlock code="npm install -g @openai/codex" language="bash" />
            
            <h3>2、配置文件</h3>
            <p>编辑文件 <code>~/.codex/config.toml</code></p>
            <CodeBlock :code="codexConfigToml" language="ini" />
            
            <p>编辑文件 <code>~/.codex/auth.json</code></p>
            <CodeBlock :code="codexAuthJson" language="json" />
            
            <!-- <h3>常见问题</h3>
            <h4>报错 <code>wire_api = chat is no longer supported</code> 怎么办？</h4>
            <p><strong>原因：</strong>Codex 新版本使用 Responses API，不支持 <code>wire_api = "chat"</code> 配置。</p>
            <p><strong>解决方案：</strong>请安装旧版codex</p> -->
          </div>
        </el-tab-pane>

        <!-- Gemini 教程 -->
        <el-tab-pane label="Gemini 教程" name="gemini">
          <div class="tutorial-content">
            <h3>1、安装Gemini Cli</h3>
            <p>使用 npm 进行安装</p>
            <CodeBlock code="npm install -g @google/gemini-cli" language="bash" />
            
            <h3>2、配置文件</h3>
            <p>编辑文件 <code>~/.gemini/.env</code></p>
            <CodeBlock :code="geminiEnvConfig" language="ini" />
            
            <p>编辑或创建文件 <code>~/.gemini/settings.json</code></p>
            <CodeBlock :code="geminiSettingsJson" language="json" />
            
            <h3>若出现401</h3>
            <p>输入 <code>/auth</code>，然后填上key</p>
          </div>
        </el-tab-pane>

        <!-- 编程工具接入 -->
        <el-tab-pane label="编程工具接入" name="tools">
          <div class="tutorial-content">
            <p>在支持 Codex 或 OpenAI 兼容接口的编程辅助工具（如 Cursor、Continue、Cline 等）中，您可以轻松接入我们的服务。</p>
            
            <h3>Cursor 接入方法</h3>
            <ol>
              <li>打开 Cursor 设置（<code>Ctrl + Shift + J</code> 或 <code>Cmd + Shift + J</code>，选择 Cursor Settings）。</li>
              <li>导航到 <strong>Models</strong> 标签页。</li>
              <li>在 <strong>OpenAI API Key</strong> 处，输入您的 API Key。</li>
              <li>开启 <strong>Override OpenAI Base URL</strong>，并填入以下地址：
                <CodeBlock :code="apiBaseUrl" language="text" />
              </li>
              <li>如果您希望使用特定模型，可以在 <strong>Model Names</strong> 中手动添加您需要的模型名称（例如 <code>gpt-5.5</code>）。</li>
              <li>保存并关闭设置，您现在可以开始使用 AI 辅助编程了！</li>
            </ol>
            
            <el-divider />
            <h3>Trae 接入方法</h3>
            <ol>
              <li>打开Trae设置 - 模型 - 添加模型</li>
              <el-image :src="traeModel" alt="Trae添加模型" />
              <li>服务商选择openai</li>
              <li>模型选择自定义模型</li>
              <li>模型id输入您需要的模型名称(例如gpt-5.5)</li>
              <li>自定义请求地址填入以下地址：
                <CodeBlock :code="apiBaseUrl + '/chat/completions'" language="text" />
              </li>
            </ol>

            <h3>Continue 接入方法</h3>
            <p>对于 VS Code 或 JetBrains 的 Continue 插件：</p>
            <ol>
              <li>点击 Continue 侧边栏底部的齿轮图标，打开 <code>config.json</code>。</li>
              <li>在 <code>models</code> 数组中添加自定义模型配置：</li>
            </ol>
            <CodeBlock :code="continueConfig" language="json" />
            
            <el-divider />
            <h3>PyCharm\VSCode等大部分主流编辑器 接入方法</h3>
            <ol>
              <li>打开扩展商店</li>
              <li>在商店中搜索kilo code插件</li>
              <el-image :src="kiloCode1" alt="kilo code插件" />
              <el-image :src="kiloCode" alt="kilo code插件" />
              <li>在kilo code中新建配置</li>
              <el-image :src="kiloCode2" alt="kilo code配置" />
            </ol>
            <el-divider />
            <h3>其他兼容工具通用配置</h3>
            <p>对于任何支持自定义 Base URL 的开发工具，通用配置如下：</p>
            <ul>
              <li><strong>API Base URL / Endpoint</strong>: <code>{{ apiBaseUrl }}</code></li>
              <li><strong>API Key / Auth Token</strong>: <code>您的 API Key</code></li>
              <li><strong>Model</strong>: 根据您的需求和模型广场提供的模型列表选择</li>
            </ul>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import CodeBlock from '@/components/CodeBlock.vue'
import traeModel from '@/assets/image/doc/trae-model.png'
import kiloCode from '@/assets/image/doc/kilo.png'
import kiloCode1 from '@/assets/image/doc/kilo1.png'
import kiloCode2 from '@/assets/image/doc/kilo2.png'
import ccSwitch from '@/assets/image/doc/cc-switch.png'
const activeTab = ref('claudecode')
const apiBaseUrl = ref(window.location.origin + '/api/proxy/v1')

const claudeWindowsSettings = computed(() => `{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "替换为您的API Key",
    "ANTHROPIC_BASE_URL": "${apiBaseUrl.value}",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1
  },
  "permissions": {
    "allow": [],
    "deny": []
  }
}`)

const claudeVscodeConfig = computed(() => `{
    "primaryApiKey": "uni"
}`)

const claudeWindowsTemp = computed(() => `# PowerShell
$env:ANTHROPIC_BASE_URL="${apiBaseUrl.value}"
$env:ANTHROPIC_AUTH_TOKEN="替换为您的API Key"

# CMD
set ANTHROPIC_BASE_URL=${apiBaseUrl.value}
set ANTHROPIC_AUTH_TOKEN=替换为您的API Key`)

const claudeWindowsPerm = computed(() => `[System.Environment]::SetEnvironmentVariable('ANTHROPIC_BASE_URL', '${apiBaseUrl.value}', 'User')
[System.Environment]::SetEnvironmentVariable('ANTHROPIC_AUTH_TOKEN', '替换为您的API Key', 'User')`)

const claudeMacSettings = computed(() => `{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "替换为您的API Key",
    "ANTHROPIC_BASE_URL": "${apiBaseUrl.value}",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1
  },
  "permissions": {
    "allow": [],
    "deny": []
  }
}`)

const claudeMacTemp = computed(() => `export ANTHROPIC_BASE_URL="${apiBaseUrl.value}"
export ANTHROPIC_AUTH_TOKEN="替换为您的API Key"`)

const claudeMacPerm = computed(() => `# 如果是 bash（默认）
echo 'export ANTHROPIC_BASE_URL="${apiBaseUrl.value}"' >> ~/.bash_profile
echo 'export ANTHROPIC_AUTH_TOKEN="替换为您的API Key"' >> ~/.bash_profile

# 如果是 zsh
echo 'export ANTHROPIC_BASE_URL="${apiBaseUrl.value}"' >> ~/.zshrc
echo 'export ANTHROPIC_AUTH_TOKEN="替换为您的API Key"' >> ~/.zshrc`)

const claudeLinuxSettings = computed(() => `{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "替换为您的API Key",
    "ANTHROPIC_BASE_URL": "${apiBaseUrl.value}",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1
  },
  "permissions": {
    "allow": [],
    "deny": []
  }
}`)

const claudeLinuxTemp = computed(() => `export ANTHROPIC_BASE_URL="${apiBaseUrl.value}"
export ANTHROPIC_AUTH_TOKEN="替换为您的API Key"`)

const claudeLinuxPerm = computed(() => `# 如果是 bash
echo 'export ANTHROPIC_BASE_URL="${apiBaseUrl.value}"' >> ~/.bashrc
echo 'export ANTHROPIC_AUTH_TOKEN="替换为您的API Key"' >> ~/.bashrc

# 如果是 zsh
echo 'export ANTHROPIC_BASE_URL="${apiBaseUrl.value}"' >> ~/.zshrc
echo 'export ANTHROPIC_AUTH_TOKEN="替换为您的API Key"' >> ~/.zshrc`)

const claudeVerify = computed(() => `# macOS/Linux
echo $ANTHROPIC_BASE_URL
echo $ANTHROPIC_AUTH_TOKEN

# Windows PowerShell
echo $env:ANTHROPIC_BASE_URL
echo $env:ANTHROPIC_AUTH_TOKEN

# Windows CMD
echo %ANTHROPIC_BASE_URL%
echo %ANTHROPIC_AUTH_TOKEN%`)

const continueConfig = computed(() => `{
  "models": [
    {
      "title": "My Custom Model",
      "provider": "openai",
      "model": "gpt-4o",
      "apiKey": "替换为您的API Key",
      "apiBase": "${apiBaseUrl.value}"
    }
  ]
}`)

const codexConfigToml = computed(() => `model_provider = "uni"
# 可配置模型广场中的模型
model = "gpt-5.5"  # 优先使用GPT模型, 其他模型可能会报错
# 可配置high medium low
model_reasoning_effort = "high"
disable_response_storage = true

# unicode配置
[model_providers.uni]
name = "uni"
base_url = "${apiBaseUrl.value}"
wire_api = "responses"
requires_openai_auth = true`)

const codexAuthJson = computed(() => `{
  "OPENAI_API_KEY": "替换为您的API Key"
}`)

const geminiEnvConfig = computed(() => `GOOGLE_GEMINI_BASE_URL="${apiBaseUrl.value}"
GEMINI_API_KEY=你的APIKey
GEMINI_MODEL=gemini-3-pro-preview`)

const geminiSettingsJson = computed(() => `{
  "ide": {
    "enabled": true
  },
  "security": {
    "auth": {
      "selectedType": "你的api-key"
    }
  }
}`)

</script>

<style scoped>
.tutorial-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: var(--space-6);
  animation: fadeIn 0.5s ease-out;
}

.header {
  text-align: center;
  margin-bottom: var(--space-8);
}

.header h1 {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin-bottom: var(--space-3);
  letter-spacing: -0.025em;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.subtitle {
  color: var(--text-secondary);
  font-size: var(--text-base);
  font-weight: var(--font-normal);
}

.content-card {
  min-height: 500px;
  border-radius: var(--radius-xl);
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.tutorial-tabs {
  padding: 0 var(--space-4);
}

.tutorial-content {
  padding: var(--space-4) 0;
  line-height: var(--leading-relaxed);
  color: var(--text-primary);
}

.tutorial-content h3 {
  font-size: var(--text-xl);
  margin: var(--space-6) 0 var(--space-4);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-light);
  color: var(--text-primary);
  font-weight: var(--font-semibold);
}

.tutorial-content h4 {
  font-size: var(--text-base);
  margin: var(--space-4) 0 var(--space-3);
  color: var(--text-secondary);
  font-weight: var(--font-medium);
}

.tutorial-content p {
  margin-bottom: var(--space-3);
  color: var(--text-secondary);
}

.tutorial-content ul, .tutorial-content ol {
  margin-bottom: var(--space-4);
  padding-left: var(--space-6);
}

.tutorial-content li {
  margin-bottom: var(--space-2);
  color: var(--text-secondary);
}

.tutorial-content code {
  background-color: var(--neutral-100);
  padding: 2px 6px;
  border-radius: var(--radius-xs);
  color: var(--error-600);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  border: 1px solid var(--neutral-200);
}

.tip {
  color: var(--text-tertiary);
  font-size: var(--text-sm);
  margin-top: var(--space-3);
  font-style: italic;
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .tutorial-container {
    padding: var(--space-4);
  }
  
  .header h1 {
    font-size: var(--text-2xl);
  }
  
  .content-card {
    min-height: auto;
  }
  
  .tutorial-tabs {
    padding: 0 var(--space-2);
  }
}
</style>
