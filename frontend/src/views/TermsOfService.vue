<template>
  <div class="terms-page">
    <!-- 导航栏 -->
    <nav class="navbar">
      <div class="navbar-container">
        <div class="navbar-brand">
          <img :src="logoSrc" alt="uniTokenHub" class="logo" />
          <span class="brand-name">uniTokenHub</span>
        </div>
        <div class="navbar-links">
          <a href="/#features" class="nav-link">{{ t('home.nav.features') }}</a>
          <a href="/#pricing" class="nav-link">{{ t('home.nav.pricing') }}</a>
          <a href="/#docs" class="nav-link">{{ t('home.nav.docs') }}</a>
        </div>
        <div class="navbar-actions">
          <button class="btn btn-outline" @click="$router.push('/login')">{{ t('auth.login') }}</button>
          <button class="btn btn-primary" @click="$router.push('/register')">{{ t('auth.register') }}</button>
        </div>
      </div>
    </nav>
    
    <div class="terms-container">
      <div class="terms-content">
        <h1>{{ t('terms.title') }}</h1>
        <p class="last-updated">{{ t('terms.lastUpdated') }}: 2024年1月1日</p>
        
        <section>
          <h2>{{ t('terms.intro.title') }}</h2>
          <p>{{ t('terms.intro.desc') }}</p>
        </section>
        
        <section>
          <h2>{{ t('terms.account.title') }}</h2>
          <ul>
            <li>{{ t('terms.account.item1') }}</li>
            <li>{{ t('terms.account.item2') }}</li>
            <li>{{ t('terms.account.item3') }}</li>
            <li>{{ t('terms.account.item4') }}</li>
            <li>{{ t('terms.account.item5') }}</li>
          </ul>
        </section>
        
        <section>
          <h2>{{ t('terms.service.title') }}</h2>
          <ul>
            <li>{{ t('terms.service.item1') }}</li>
            <li>{{ t('terms.service.item2') }}</li>
            <li>{{ t('terms.service.item3') }}</li>
            <li>{{ t('terms.service.item4') }}</li>
          </ul>
        </section>
        
        <section>
          <h2>{{ t('terms.usage.title') }}</h2>
          <ul>
            <li>{{ t('terms.usage.item1') }}</li>
            <li>{{ t('terms.usage.item2') }}</li>
            <li>{{ t('terms.usage.item3') }}</li>
            <li>{{ t('terms.usage.item4') }}</li>
            <li>{{ t('terms.usage.item5') }}</li>
          </ul>
        </section>
        
        <section>
          <h2>{{ t('terms.payment.title') }}</h2>
          <ul>
            <li>{{ t('terms.payment.item1') }}</li>
            <li>{{ t('terms.payment.item2') }}</li>
            <li>{{ t('terms.payment.item3') }}</li>
            <li>{{ t('terms.payment.item4') }}</li>
          </ul>
        </section>
        
        <section>
          <h2>{{ t('terms.intellectual.title') }}</h2>
          <ul>
            <li>{{ t('terms.intellectual.item1') }}</li>
            <li>{{ t('terms.intellectual.item2') }}</li>
            <li>{{ t('terms.intellectual.item3') }}</li>
          </ul>
        </section>
        
        <section>
          <h2>{{ t('terms.termination.title') }}</h2>
          <p>{{ t('terms.termination.desc') }}</p>
        </section>
        
        <section>
          <h2>{{ t('terms.disclaimer.title') }}</h2>
          <p>{{ t('terms.disclaimer.desc') }}</p>
        </section>
        
        <section>
          <h2>{{ t('terms.changes.title') }}</h2>
          <p>{{ t('terms.changes.desc') }}</p>
        </section>
        
        <section>
          <h2>{{ t('terms.contact.title') }}</h2>
          <p>{{ t('terms.contact.desc') }}</p>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from '@/composables/useI18n'
import logoSrc from '@/assets/image/logo.png'

const { t } = useI18n()
</script>

<style scoped>
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.navbar-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 12px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.navbar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.navbar-brand .logo {
  width: 32px;
  height: 32px;
  border-radius: 8px;
}

.brand-name {
  font-size: 18px;
  font-weight: 700;
  color: #1a1a2e;
}

.navbar-links {
  display: flex;
  gap: 28px;
}

.nav-link {
  text-decoration: none;
  color: #606266;
  font-weight: 500;
  transition: color 0.3s;
  
  &:hover {
    color: #409eff;
  }
}

.navbar-actions {
  display: flex;
  gap: 10px;
}

.btn {
  padding: 7px 18px;
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

.terms-page {
  min-height: 100vh;
  background: #f5f7fa;
}

.terms-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 100px 24px 60px;
}

.terms-content {
  background: #fff;
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.terms-content h1 {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0 0 8px;
}

.last-updated {
  font-size: 14px;
  color: #909399;
  margin: 0 0 32px;
}

.terms-content section {
  margin-bottom: 32px;
}

.terms-content h2 {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0 0 16px;
}

.terms-content p {
  font-size: 15px;
  color: #606266;
  line-height: 1.8;
  margin: 0;
}

.terms-content ul {
  margin: 0;
  padding-left: 20px;
}

.terms-content li {
  font-size: 15px;
  color: #606266;
  line-height: 1.8;
  margin-bottom: 8px;
}
</style>