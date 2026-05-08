<template>
  <Transition name="fade">
    <div v-if="showConsent" class="cookie-consent-overlay" @click.self="handleReject">
      <div class="cookie-consent-modal">
        <div class="cookie-icon">
          <el-icon><Cookie /></el-icon>
        </div>
        <h3>{{ t('cookie.title') }}</h3>
        <p>{{ t('cookie.description') }}</p>
        <div class="cookie-links">
          <router-link to="/privacy-policy" target="_blank">{{ t('cookie.privacy') }}</router-link>
          <span class="divider">|</span>
          <router-link to="/terms-of-service" target="_blank">{{ t('cookie.terms') }}</router-link>
        </div>
        <div class="cookie-actions">
          <button class="btn btn-outline" @click="handleReject">{{ t('cookie.reject') }}</button>
          <button class="btn btn-primary" @click="handleAccept">{{ t('cookie.accept') }}</button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Cookie } from '@element-plus/icons-vue'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const showConsent = ref(false)

const checkConsent = () => {
  const consent = localStorage.getItem('cookieConsent')
  if (!consent) {
    showConsent.value = true
  }
}

const handleAccept = () => {
  localStorage.setItem('cookieConsent', 'accepted')
  showConsent.value = false
}

const handleReject = () => {
  localStorage.setItem('cookieConsent', 'rejected')
  showConsent.value = false
}

onMounted(() => {
  checkConsent()
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.cookie-consent-overlay {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  padding: 24px;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(10px);
}

.cookie-consent-modal {
  max-width: 500px;
  margin: 0 auto;
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  text-align: center;
}

.cookie-icon {
  width: 56px;
  height: 56px;
  margin: 0 auto 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  
  .el-icon {
    font-size: 28px;
    color: #fff;
  }
}

.cookie-consent-modal h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0 0 12px;
}

.cookie-consent-modal p {
  font-size: 14px;
  color: #606266;
  margin: 0 0 16px;
  line-height: 1.6;
}

.cookie-links {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 20px;
  
  a {
    font-size: 13px;
    color: #667eea;
    text-decoration: none;
    
    &:hover {
      text-decoration: underline;
    }
  }
  
  .divider {
    color: #dcdfe6;
  }
}

.cookie-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn {
  padding: 10px 24px;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
  border: none;
  font-size: 14px;
}

.btn-outline {
  background: transparent;
  border: 1px solid #dcdfe6;
  color: #606266;
  
  &:hover {
    border-color: #409eff;
    color: #409eff;
  }
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  }
}
</style>