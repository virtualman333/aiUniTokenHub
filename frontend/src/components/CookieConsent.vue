<template>
  <Transition name="slide-up">
    <div v-if="showConsent" class="cookie-banner">
      <div class="cookie-container">
        <div class="cookie-icon-wrapper">
          <el-icon :size="24"><Sugar /></el-icon>
        </div>
        <div class="cookie-content">
          <p class="cookie-text">
            {{ t('cookie.description') }}
            <router-link to="/privacy-policy" target="_blank" class="cookie-link">{{ t('cookie.privacy') }}</router-link>
            <span class="cookie-separator">·</span>
            <router-link to="/terms-of-service" target="_blank" class="cookie-link">{{ t('cookie.terms') }}</router-link>
          </p>
        </div>
        <div class="cookie-actions">
          <button class="btn-reject" @click="handleReject">{{ t('cookie.reject') }}</button>
          <button class="btn-accept" @click="handleAccept">{{ t('cookie.accept') }}</button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Sugar } from '@element-plus/icons-vue'
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
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}

.cookie-banner {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  padding: 16px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 -4px 30px rgba(0, 0, 0, 0.08);
}

.cookie-container {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 0;
}

.cookie-icon-wrapper {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.cookie-content {
  flex: 1;
  min-width: 0;
}

.cookie-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #4a5568;
}

.cookie-link {
  color: #667eea;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s;
  
  &:hover {
    color: #5568d3;
    text-decoration: underline;
  }
}

.cookie-separator {
  margin: 0 6px;
  color: #cbd5e0;
}

.cookie-actions {
  flex-shrink: 0;
  display: flex;
  gap: 8px;
  align-items: center;
}

.btn-reject,
.btn-accept {
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
  white-space: nowrap;
}

.btn-reject {
  background: transparent;
  color: #718096;
  
  &:hover {
    background: #f7fafc;
    color: #2d3748;
  }
}

.btn-accept {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
  
  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  }
  
  &:active {
    transform: translateY(0);
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .cookie-container {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .cookie-icon-wrapper {
    display: none;
  }
  
  .cookie-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>