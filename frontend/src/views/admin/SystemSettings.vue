<template>
  <div class="system-settings">
    <div class="page-header">
      <h1>系统设置</h1>
      <p class="subtitle">配置系统级别的功能选项</p>
    </div>

    <!-- 邮箱配置卡片 -->
    <div class="config-card" v-loading="loading">
      <!-- 卡片头部 -->
      <div class="card-head">
        <div class="head-left">
          <div class="head-icon">
            <el-icon :size="22"><Message /></el-icon>
          </div>
          <div class="head-meta">
            <div class="head-title">邮箱发送配置</div>
            <div class="head-desc">用于注册验证码、密码重置等场景的邮件发送服务</div>
          </div>
        </div>
        <div class="head-right">
          <div class="status-pill" :class="{ on: form.is_enabled, off: !form.is_enabled }">
            <span class="dot" />
            {{ form.is_enabled ? '已启用' : '未启用' }}
          </div>
          <el-switch v-model="form.is_enabled" size="large" />
        </div>
      </div>

      <!-- 未启用警告 -->
      <transition name="slide-fade">
        <div v-if="!form.is_enabled" class="banner banner-warn">
          <el-icon><Warning /></el-icon>
          <span>邮箱服务当前未启用，注册等需要发送邮件的功能将无法工作</span>
        </div>
      </transition>

      <!-- 表单主体 -->
      <div class="form-body" :class="{ disabled: !form.is_enabled }">
        <!-- Section: 服务器 -->
        <section class="section">
          <header class="section-head">
            <div>
              <div class="section-title">SMTP 服务器</div>
              <div class="section-desc">填写邮件服务商提供的 SMTP 信息</div>
            </div>
            <el-dropdown trigger="click" @command="applyPreset">
              <el-button text class="preset-btn">
                <el-icon><Lightning /></el-icon>
                快速预设
                <el-icon><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    v-for="p in presets"
                    :key="p.code"
                    :command="p.code"
                  >
                    <span class="preset-name">{{ p.name }}</span>
                    <span class="preset-tag">{{ p.smtp_host }}:{{ p.smtp_port }}</span>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </header>

          <div class="grid">
            <!-- SMTP 服务器 -->
            <div class="field col-7">
              <label class="field-label">SMTP 服务器 <span class="req">*</span></label>
              <el-input
                v-model="form.smtp_host"
                placeholder="例如 smtp.qq.com"
                :disabled="!form.is_enabled"
              >
                <template #prefix>
                  <el-icon><Connection /></el-icon>
                </template>
              </el-input>
            </div>

            <!-- 端口（普通输入框） -->
            <div class="field col-2">
              <label class="field-label">端口 <span class="req">*</span></label>
              <el-input
                v-model.number="form.smtp_port"
                placeholder="465"
                maxlength="5"
                :disabled="!form.is_enabled"
              />
              <div class="port-shortcuts">
                <span
                  v-for="p in [25, 465, 587]"
                  :key="p"
                  class="chip"
                  :class="{ active: Number(form.smtp_port) === p }"
                  @click="setPort(p)"
                >
                  {{ p }}
                </span>
              </div>
            </div>

            <!-- 加密方式：segmented -->
            <div class="field col-3">
              <label class="field-label">加密方式</label>
              <div class="segmented" :class="{ disabled: !form.is_enabled }">
                <button
                  v-for="opt in encOptions"
                  :key="opt.value"
                  type="button"
                  class="seg-item"
                  :class="{ active: encryption === opt.value }"
                  :disabled="!form.is_enabled"
                  @click="encryption = opt.value"
                >
                  {{ opt.label }}
                </button>
              </div>
            </div>

            <!-- 用户名 -->
            <div class="field col-6">
              <label class="field-label">SMTP 用户名 <span class="req">*</span></label>
              <el-input
                v-model="form.smtp_user"
                placeholder="通常是你的邮箱地址"
                :disabled="!form.is_enabled"
              >
                <template #prefix>
                  <el-icon><User /></el-icon>
                </template>
              </el-input>
            </div>

            <!-- 密码 -->
            <div class="field col-6">
              <label class="field-label">
                SMTP 密码 / 授权码 <span class="req">*</span>
                <span v-if="form.smtp_password_set" class="badge-set">已设置</span>
              </label>
              <el-input
                v-model="form.smtp_password"
                type="password"
                show-password
                :placeholder="form.smtp_password_set ? '留空则保持不变' : '请输入授权码'"
                autocomplete="new-password"
                :disabled="!form.is_enabled"
              >
                <template #prefix>
                  <el-icon><Lock /></el-icon>
                </template>
              </el-input>
              <div class="hint">
                注意：QQ / 163 等邮箱需填【授权码】，不是登录密码
              </div>
            </div>

            <!-- 发件人邮箱 -->
            <div class="field col-6">
              <label class="field-label">发件人邮箱</label>
              <el-input
                v-model="form.from_email"
                placeholder="留空则使用 SMTP 用户名"
                :disabled="!form.is_enabled"
              >
                <template #prefix>
                  <el-icon><Message /></el-icon>
                </template>
              </el-input>
            </div>

            <!-- 发件人名称 -->
            <div class="field col-6">
              <label class="field-label">发件人名称</label>
              <el-input
                v-model="form.from_name"
                placeholder="如 uniTokenHub"
                :disabled="!form.is_enabled"
              >
                <template #prefix>
                  <el-icon><Postcard /></el-icon>
                </template>
              </el-input>
            </div>
          </div>
        </section>

        <!-- Section: 验证码策略 -->
        <section class="section">
          <header class="section-head">
            <div>
              <div class="section-title">验证码策略</div>
              <div class="section-desc">控制验证码的有效期与频率限制</div>
            </div>
          </header>

          <div class="metric-grid">
            <div class="metric-card">
              <div class="metric-label">
                <el-icon><Timer /></el-icon>
                <span>验证码有效期</span>
              </div>
              <div class="metric-input">
                <el-input
                  v-model.number="form.code_expire_minutes"
                  placeholder="5"
                  :disabled="!form.is_enabled"
                />
                <span class="metric-unit">分钟</span>
              </div>
            </div>

            <div class="metric-card">
              <div class="metric-label">
                <el-icon><Refresh /></el-icon>
                <span>重发间隔</span>
              </div>
              <div class="metric-input">
                <el-input
                  v-model.number="form.code_resend_seconds"
                  placeholder="60"
                  :disabled="!form.is_enabled"
                />
                <span class="metric-unit">秒</span>
              </div>
            </div>

            <div class="metric-card">
              <div class="metric-label">
                <el-icon><Histogram /></el-icon>
                <span>单邮箱日上限</span>
              </div>
              <div class="metric-input">
                <el-input
                  v-model.number="form.daily_limit_per_email"
                  placeholder="10"
                  :disabled="!form.is_enabled"
                />
                <span class="metric-unit">次 / 天</span>
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- 操作栏 -->
      <div class="card-foot">
        <div class="foot-left">
          <span v-if="form.updated_at_text" class="updated">
            上次保存：{{ form.updated_at_text }}
          </span>
        </div>
        <div class="foot-right">
          <el-button
            :disabled="!form.is_enabled"
            @click="openTestDialog"
          >
            <el-icon><Promotion /></el-icon>
            发送测试邮件
          </el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">
            <el-icon><Check /></el-icon>
            保存配置
          </el-button>
        </div>
      </div>
    </div>

    <!-- 测试发送对话框 -->
    <el-dialog
      v-model="testDialogVisible"
      title="发送测试邮件"
      width="440px"
      :close-on-click-modal="false"
    >
      <div class="dialog-body">
        <div class="dialog-tip">
          将使用<strong>已保存的</strong> SMTP 配置发送一封测试邮件
        </div>
        <label class="field-label" style="margin-top: 12px">收件邮箱</label>
        <el-input
          v-model="testEmail"
          placeholder="输入接收测试邮件的邮箱"
          size="large"
        >
          <template #prefix>
            <el-icon><Message /></el-icon>
          </template>
        </el-input>
      </div>
      <template #footer>
        <el-button @click="testDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="testing" @click="handleTest">
          <el-icon><Promotion /></el-icon>
          立即发送
        </el-button>
      </template>
    </el-dialog>

    <!-- 告警配置卡片 -->
    <div class="config-card" v-loading="loading" style="margin-top: 24px;">
      <div class="card-head">
        <div class="head-left">
          <div class="head-icon head-icon-alert">
            <el-icon :size="22"><Bell /></el-icon>
          </div>
          <div class="head-meta">
            <div class="head-title">接口异常告警</div>
            <div class="head-desc">当 API 调用返回非 200 状态码时，自动发送告警邮件通知管理员</div>
          </div>
        </div>
        <div class="head-right">
          <div class="status-pill" :class="{ on: form.alert_enabled, off: !form.alert_enabled }">
            <span class="dot" />
            {{ form.alert_enabled ? '已启用' : '未启用' }}
          </div>
          <el-switch v-model="form.alert_enabled" size="large" />
        </div>
      </div>

      <!-- 告警未启用提示 -->
      <transition name="slide-fade">
        <div v-if="!form.alert_enabled && (!form.is_enabled || !form.alert_emails)" class="banner banner-warn">
          <el-icon><Warning /></el-icon>
          <span>告警功能未开启或未配置收件人，异常时不会发送通知邮件</span>
        </div>
      </transition>

      <div class="form-body" style="padding-bottom: 0;">
        <section class="section">
          <header class="section-head">
            <div>
              <div class="section-title">告警收件人</div>
              <div class="section-desc">配置接收告警邮件的邮箱地址，支持多个</div>
            </div>
          </header>

          <div class="alert-emails-area">
            <label class="field-label">告警邮箱列表 <span class="req">*</span></label>
            <el-input
              v-model="form.alert_emails"
              type="textarea"
              :rows="3"
              placeholder="请输入告警收件邮箱，多个邮箱用英文逗号分隔&#10;例如: admin@example.com, ops@example.com"
              :disabled="!form.is_enabled"
            />
            <div class="hint">多个邮箱使用英文逗号（,）分隔，每个请求周期内同类型告警仅发送一次以避免轰炸</div>

            <!-- 邮件预览标签 -->
            <div v-if="parsedAlertEmails.length" class="email-tags">
              <span
                v-for="(email, idx) in parsedAlertEmails"
                :key="idx"
                class="email-tag"
              >
                {{ email }}
              </span>
              <span class="tag-count">{{ parsedAlertEmails.length }} 个收件人</span>
            </div>
            <div v-else-if="form.alert_emails" class="email-tags">
              <span class="tag-invalid">邮箱格式无效，请检查输入</span>
            </div>
          </div>
        </section>
      </div>

      <div class="card-foot">
        <div class="foot-left"></div>
        <div class="foot-right">
          <el-button
            :disabled="!form.alert_enabled || !form.is_enabled || !form.smtp_password_set"
            @click="openAlertDialog"
          >
            <el-icon><Promotion /></el-icon>
            发送告警测试
          </el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">
            <el-icon><Check /></el-icon>
            保存配置
          </el-button>
        </div>
      </div>
    </div>

    <!-- 告警测试对话框 -->
    <el-dialog
      v-model="alertTestVisible"
      title="发送告警测试邮件"
      width="440px"
      :close-on-click-modal="false"
    >
      <div class="dialog-body">
        <div class="dialog-tip dialog-tip-warn">
          将向<strong>告警配置中的所有收件人</strong>发送一封模拟告警邮件（HTTP 500）
        </div>
        <label class="field-label" style="margin-top: 12px">也可指定单个收件人测试（可选）</label>
        <el-input
          v-model="alertTestEmail"
          placeholder="留空则发送给所有已配置的告警收件人"
          size="large"
        >
          <template #prefix>
            <el-icon><Message /></el-icon>
          </template>
        </el-input>
      </div>
      <template #footer>
        <el-button @click="alertTestVisible = false">取消</el-button>
        <el-button type="warning" :loading="alertTesting" @click="handleAlertTest">
          <el-icon><Promotion /></el-icon>
          发送测试
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Message, Check, Promotion, Warning, Connection,
  User, Lock, Postcard, Timer, Refresh, Histogram,
  Lightning, ArrowDown, Bell,
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import api from '@/stores'

interface EmailConfigForm {
  is_enabled: boolean
  smtp_host: string
  smtp_port: number | string
  use_ssl: boolean
  use_tls: boolean
  smtp_user: string
  smtp_password: string
  smtp_password_set: boolean
  from_email: string
  from_name: string
  code_expire_minutes: number | string
  code_resend_seconds: number | string
  daily_limit_per_email: number | string
  alert_enabled: boolean
  alert_emails: string
  updated_at_text?: string
}

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const testDialogVisible = ref(false)
const testEmail = ref('')

const form = reactive<EmailConfigForm>({
  is_enabled: false,
  smtp_host: '',
  smtp_port: 465,
  use_ssl: true,
  use_tls: false,
  smtp_user: '',
  smtp_password: '',
  smtp_password_set: false,
  from_email: '',
  from_name: 'uniTokenHub',
  code_expire_minutes: 5,
  code_resend_seconds: 60,
  daily_limit_per_email: 10,
  alert_enabled: false,
  alert_emails: '',
  updated_at_text: '',
})

// 告警相关
const alertTestVisible = ref(false)
const alertTesting = ref(false)
const alertTestEmail = ref('')

const parsedAlertEmails = computed(() => {
  return form.alert_emails
    .split(',')
    .map((s) => s.trim())
    .filter((s) => s && /.+@.+\..+/.test(s))
})

// 加密
type Enc = 'ssl' | 'tls' | 'none'
const encryption = ref<Enc>('ssl')
const encOptions: { label: string; value: Enc }[] = [
  { label: 'SSL', value: 'ssl' },
  { label: 'TLS', value: 'tls' },
  { label: '无', value: 'none' },
]

watch(encryption, (val) => {
  form.use_ssl = val === 'ssl'
  form.use_tls = val === 'tls'
})

// 预设
const presets = [
  { code: 'qq', name: 'QQ 邮箱', smtp_host: 'smtp.qq.com', smtp_port: 465, enc: 'ssl' as Enc },
  { code: '163', name: '网易 163', smtp_host: 'smtp.163.com', smtp_port: 465, enc: 'ssl' as Enc },
  { code: '126', name: '网易 126', smtp_host: 'smtp.126.com', smtp_port: 465, enc: 'ssl' as Enc },
  { code: 'aliyun', name: '阿里云企业', smtp_host: 'smtp.qiye.aliyun.com', smtp_port: 465, enc: 'ssl' as Enc },
  { code: 'gmail', name: 'Gmail', smtp_host: 'smtp.gmail.com', smtp_port: 587, enc: 'tls' as Enc },
  { code: 'outlook', name: 'Outlook', smtp_host: 'smtp-mail.outlook.com', smtp_port: 587, enc: 'tls' as Enc },
]

function applyPreset(code: string) {
  const p = presets.find((x) => x.code === code)
  if (!p) return
  form.smtp_host = p.smtp_host
  form.smtp_port = p.smtp_port
  encryption.value = p.enc
  ElMessage.success(`已应用预设：${p.name}`)
}

function setPort(p: number) {
  if (!form.is_enabled) return
  form.smtp_port = p
  // 智能切换加密
  if (p === 465) encryption.value = 'ssl'
  else if (p === 587) encryption.value = 'tls'
  else if (p === 25) encryption.value = 'none'
}

function applyConfig(data: any) {
  form.is_enabled = !!data.is_enabled
  form.smtp_host = data.smtp_host || ''
  form.smtp_port = Number(data.smtp_port) || 465
  form.use_ssl = !!data.use_ssl
  form.use_tls = !!data.use_tls
  form.smtp_user = data.smtp_user || ''
  form.smtp_password = ''
  form.smtp_password_set = !!data.smtp_password_set
  form.from_email = data.from_email || ''
  form.from_name = data.from_name || 'uniTokenHub'
  form.code_expire_minutes = Number(data.code_expire_minutes) || 5
  form.code_resend_seconds = Number(data.code_resend_seconds) || 60
  form.daily_limit_per_email = Number(data.daily_limit_per_email) || 10
  form.alert_enabled = !!data.alert_enabled
  form.alert_emails = data.alert_emails || ''
  form.updated_at_text = data.updated_at ? dayjs(data.updated_at).format('YYYY-MM-DD HH:mm:ss') : ''
  encryption.value = form.use_ssl ? 'ssl' : (form.use_tls ? 'tls' : 'none')
}

async function loadConfig() {
  loading.value = true
  try {
    const res: any = await api.get('/users/admin/system/email_config/')
    applyConfig(res || {})
  } catch (e: any) {
    ElMessage.error(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function validateBeforeSave(): string | null {
  if (!form.is_enabled) return null
  if (!form.smtp_host) return '请填写 SMTP 服务器'
  const port = Number(form.smtp_port)
  if (!port || port < 1 || port > 65535) return '端口必须在 1-65535 之间'
  if (!form.smtp_user) return '请填写 SMTP 用户名'
  if (!form.smtp_password_set && !form.smtp_password) return '请填写 SMTP 密码 / 授权码'
  return null
}

async function handleSave() {
  const err = validateBeforeSave()
  if (err) {
    ElMessage.warning(err)
    return
  }
  saving.value = true
  try {
    const payload: any = {
      is_enabled: form.is_enabled,
      smtp_host: form.smtp_host,
      smtp_port: Number(form.smtp_port) || 0,
      use_ssl: form.use_ssl,
      use_tls: form.use_tls,
      smtp_user: form.smtp_user,
      from_email: form.from_email,
      from_name: form.from_name,
      code_expire_minutes: Number(form.code_expire_minutes) || 5,
      code_resend_seconds: Number(form.code_resend_seconds) || 60,
      daily_limit_per_email: Number(form.daily_limit_per_email) || 10,
      alert_enabled: form.alert_enabled,
      alert_emails: form.alert_emails,
    }
    if (form.smtp_password) {
      payload.smtp_password = form.smtp_password
    }
    const res: any = await api.put('/users/admin/system/email_config/', payload)
    applyConfig(res || {})
    ElMessage.success('保存成功')
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

function openTestDialog() {
  if (!form.smtp_password_set) {
    ElMessage.warning('请先保存配置后再测试')
    return
  }
  testDialogVisible.value = true
}

async function handleTest() {
  if (!testEmail.value || !/.+@.+\..+/.test(testEmail.value)) {
    ElMessage.warning('请输入有效的收件邮箱')
    return
  }
  testing.value = true
  try {
    await api.post('/users/admin/system/email_config/test/', { to_email: testEmail.value })
    ElMessage.success(`已发送到 ${testEmail.value}`)
    testDialogVisible.value = false
  } catch (e: any) {
    ElMessage.error(e?.message || '发送失败')
  } finally {
    testing.value = false
  }
}

function openAlertDialog() {
  alertTestEmail.value = ''
  alertTestVisible.value = true
}

async function handleAlertTest() {
  alertTesting.value = true
  try {
    const payload: any = {}
    if (alertTestEmail.value && /.+@.+\..+/.test(alertTestEmail.value)) {
      payload.to_email = alertTestEmail.value
    }
    await api.post('/users/admin/system/alert/test/', payload)
    ElMessage.success('告警测试邮件已发送')
    alertTestVisible.value = false
  } catch (e: any) {
    ElMessage.error(e?.message || '发送失败')
  } finally {
    alertTesting.value = false
  }
}

onMounted(loadConfig)
</script>

<style scoped lang="scss">
.system-settings {
  max-width: 1100px;
  margin: 0 auto;
}

/* ========== 页头 ========== */
.page-header {
  margin-bottom: 24px;

  h1 {
    font-size: 24px;
    font-weight: 700;
    color: #0f172a;
    margin: 0 0 6px;
    letter-spacing: -0.01em;
  }

  .subtitle {
    color: #64748b;
    font-size: 14px;
    margin: 0;
  }
}

/* ========== 卡片 ========== */
.config-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: box-shadow 0.2s;

  &:hover {
    box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06);
  }
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 22px 28px;
  background: linear-gradient(180deg, #fafbfc 0%, #ffffff 100%);
  border-bottom: 1px solid #f1f5f9;
}

.head-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.head-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  color: #059669;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.head-meta {
  .head-title {
    font-size: 17px;
    font-weight: 600;
    color: #0f172a;
    margin-bottom: 2px;
  }

  .head-desc {
    font-size: 13px;
    color: #64748b;
  }
}

.head-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }

  &.on {
    background: #ecfdf5;
    color: #047857;

    .dot {
      background: #10b981;
      box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15);
    }
  }

  &.off {
    background: #f1f5f9;
    color: #64748b;

    .dot {
      background: #94a3b8;
    }
  }
}

/* ========== 警告条 ========== */
.banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 28px;
  font-size: 13px;

  &.banner-warn {
    background: #fffbeb;
    color: #b45309;
    border-bottom: 1px solid #fef3c7;
  }
}

/* ========== 表单主体 ========== */
.form-body {
  padding: 8px 28px 24px;
  transition: opacity 0.2s;

  &.disabled {
    opacity: 0.55;
  }
}

.section {
  padding: 20px 0;
  border-bottom: 1px dashed #f1f5f9;

  &:last-child {
    border-bottom: 0;
  }
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.section-desc {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 2px;
}

.preset-btn {
  color: #059669 !important;
  font-weight: 500;

  &:hover {
    background: #ecfdf5 !important;
  }
}

.preset-name {
  font-weight: 500;
  margin-right: 12px;
}

.preset-tag {
  font-family: ui-monospace, monospace;
  font-size: 11px;
  color: #94a3b8;
}

/* ========== 字段网格 ========== */
.grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 16px 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;

  &.col-2 { grid-column: span 2; }
  &.col-3 { grid-column: span 3; }
  &.col-4 { grid-column: span 4; }
  &.col-6 { grid-column: span 6; }
  &.col-7 { grid-column: span 7; }
  &.col-12 { grid-column: span 12; }
}

.field-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #334155;

  .req {
    color: #ef4444;
    margin-left: -2px;
  }
}

.badge-set {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 4px;
  background: #ecfdf5;
  color: #047857;
  font-size: 11px;
  font-weight: 500;
  margin-left: 4px;
}

.hint {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.5;
  margin-top: 2px;
}

/* ========== 端口快捷 ========== */
.port-shortcuts {
  display: flex;
  gap: 6px;
  margin-top: 4px;
}

.chip {
  padding: 2px 10px;
  border-radius: 6px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  font-size: 12px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s;
  font-family: ui-monospace, monospace;

  &:hover {
    border-color: #10b981;
    color: #059669;
  }

  &.active {
    background: #ecfdf5;
    border-color: #10b981;
    color: #047857;
    font-weight: 600;
  }
}

/* ========== 加密方式分段 ========== */
.segmented {
  display: inline-flex;
  background: #f1f5f9;
  border-radius: 8px;
  padding: 3px;
  width: 100%;

  &.disabled .seg-item {
    cursor: not-allowed;
    opacity: 0.5;
  }
}

.seg-item {
  flex: 1;
  border: 0;
  background: transparent;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 13px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s;
  font-weight: 500;

  &:hover:not(:disabled):not(.active) {
    color: #334155;
  }

  &.active {
    background: #fff;
    color: #059669;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  }

  &:disabled {
    cursor: not-allowed;
  }
}

/* ========== 验证码策略 ========== */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.metric-card {
  background: #fafbfc;
  border: 1px solid #f1f5f9;
  border-radius: 10px;
  padding: 14px 16px;
  transition: all 0.15s;

  &:hover {
    border-color: #d1fae5;
    background: #fff;
  }
}

.metric-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #475569;
  margin-bottom: 10px;
  font-weight: 500;

  .el-icon {
    color: #10b981;
  }
}

.metric-input {
  display: flex;
  align-items: center;
  gap: 8px;

  :deep(.el-input__wrapper) {
    background: #fff;
  }
}

.metric-unit {
  font-size: 12px;
  color: #94a3b8;
  flex-shrink: 0;
}

/* ========== 操作栏 ========== */
.card-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 28px;
  background: #fafbfc;
  border-top: 1px solid #f1f5f9;
}

.foot-left .updated {
  font-size: 12px;
  color: #94a3b8;
}

.foot-right {
  display: flex;
  gap: 8px;
}

/* ========== 对话框 ========== */
.dialog-body {
  padding: 0 4px;
}

.dialog-tip {
  font-size: 13px;
  color: #64748b;
  background: #f8fafc;
  padding: 10px 14px;
  border-radius: 8px;
  border-left: 3px solid #10b981;
  line-height: 1.6;

  strong {
    color: #047857;
  }
}

.dialog-tip-warn {
  border-left-color: #f59e0b;
  strong {
    color: #d97706;
  }
}

/* ========== 告警配置 ========== */
.head-icon-alert {
  background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
  color: #ea580c;
}

.alert-emails-area {
  .email-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 10px;
  }

  .email-tag {
    display: inline-flex;
    align-items: center;
    padding: 3px 10px;
    background: #ecfdf5;
    color: #047857;
    border-radius: 6px;
    font-size: 12px;
    font-family: ui-monospace, monospace;
  }

  .tag-count {
    font-size: 12px;
    color: #94a3b8;
    align-self: center;
    margin-left: 4px;
  }

  .tag-invalid {
    font-size: 12px;
    color: #ef4444;
  }
}

/* ========== 过渡 ========== */
.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.25s ease;
}
.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

/* 响应式 */
@media (max-width: 900px) {
  .grid {
    grid-template-columns: repeat(6, 1fr);

    .field.col-2,
    .field.col-3,
    .field.col-7 {
      grid-column: span 6;
    }

    .field.col-6 {
      grid-column: span 6;
    }
  }

  .metric-grid {
    grid-template-columns: 1fr;
  }
}
</style>
