<template>
  <div class="home-page">
    <!-- 导航栏 -->
    <nav class="navbar">
      <div class="navbar-container">
        <div class="navbar-brand">
          <img :src="logoSrc" alt="uniTokenHub" class="logo" />
          <span class="brand-name">uniTokenHub</span>
        </div>
        <div class="navbar-links">
          <a href="#features" class="nav-link">{{ t('home.nav.features') }}</a>
          <a href="#pricing" class="nav-link">{{ t('home.nav.pricing') }}</a>
          <a href="#docs" class="nav-link">{{ t('home.nav.docs') }}</a>
        </div>
        <div class="navbar-actions">
          <button class="btn btn-outline" @click="$router.push('/login')">{{ t('auth.login') }}</button>
          <button class="btn btn-primary" @click="$router.push('/register')">{{ t('auth.register') }}</button>
        </div>
      </div>
    </nav>

    <!-- Hero 区域 -->
    <section class="hero">
      <div class="hero-container">
        <div class="hero-content">
          <h1 class="hero-title">{{ t('home.hero.title') }}</h1>
          <p class="hero-subtitle">{{ t('home.hero.subtitle') }}</p>
          <div class="hero-actions">
            <button class="btn btn-primary btn-large" @click="$router.push('/register')">
              {{ t('home.hero.getStarted') }}
            </button>
            <button class="btn btn-outline btn-large" @click="scrollToDocs">
              {{ t('home.hero.viewDocs') }}
            </button>
          </div>
          <div class="hero-stats">
            <div class="stat-item">
              <div class="stat-value">100K+</div>
              <div class="stat-label">{{ t('home.hero.stats.requests') }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">99.9%</div>
              <div class="stat-label">{{ t('home.hero.stats.uptime') }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">50ms</div>
              <div class="stat-label">{{ t('home.hero.stats.latency') }}</div>
            </div>
          </div>
        </div>
        <div class="hero-code">
          <div class="code-header">
            <span class="code-lang">bash</span>
            <button class="copy-btn" @click="copyCode">
              <el-icon><CopyDocument /></el-icon>
              <span>{{ copied ? 'Copied!' : 'Copy' }}</span>
            </button>
          </div>
          <pre class="code-block"><code class="language-bash">curl -X POST https://api.unitokenhub.com/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello"}]
  }'</code></pre>
        </div>
      </div>
    </section>

    <!-- 功能特性 -->
    <section id="features" class="features">
      <div class="features-container">
        <div class="section-header">
          <h2>{{ t('home.features.title') }}</h2>
          <p>{{ t('home.features.subtitle') }}</p>
        </div>
        <div class="features-grid">
          <div class="feature-card">
            <div class="feature-icon">
              <el-icon><Link /></el-icon>
            </div>
            <h3>{{ t('home.features.multiChannel.title') }}</h3>
            <p>{{ t('home.features.multiChannel.desc') }}</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">
              <el-icon><TrendCharts /></el-icon>
            </div>
            <h3>{{ t('home.features.loadBalance.title') }}</h3>
            <p>{{ t('home.features.loadBalance.desc') }}</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">
              <el-icon><Wallet /></el-icon>
            </div>
            <h3>{{ t('home.features.transparent.title') }}</h3>
            <p>{{ t('home.features.transparent.desc') }}</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">
              <el-icon><Lock /></el-icon>
            </div>
            <h3>{{ t('home.features.security.title') }}</h3>
            <p>{{ t('home.features.security.desc') }}</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">
              <el-icon><Histogram /></el-icon>
            </div>
            <h3>{{ t('home.features.analytics.title') }}</h3>
            <p>{{ t('home.features.analytics.desc') }}</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">
              <el-icon><Setting /></el-icon>
            </div>
            <h3>{{ t('home.features.customize.title') }}</h3>
            <p>{{ t('home.features.customize.desc') }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 定价方案 -->
    <section id="pricing" class="pricing">
      <div class="pricing-container">
        <div class="section-header">
          <h2>{{ t('home.pricing.title') }}</h2>
          <p>{{ t('home.pricing.subtitle') }}</p>
        </div>
        <div class="pricing-grid">
          <div class="pricing-card">
            <div class="pricing-header">
              <h3>{{ t('home.pricing.free.title') }}</h3>
              <div class="pricing-price">
                <span class="currency">¥</span>
                <span class="amount">0</span>
                <span class="period">/月</span>
              </div>
            </div>
            <ul class="pricing-features">
              <li>{{ t('home.pricing.free.feature1') }}</li>
              <li>{{ t('home.pricing.free.feature2') }}</li>
              <li>{{ t('home.pricing.free.feature3') }}</li>
              <li class="disabled">{{ t('home.pricing.free.feature4') }}</li>
              <li class="disabled">{{ t('home.pricing.free.feature5') }}</li>
            </ul>
            <button class="btn btn-outline" @click="$router.push('/register')">{{ t('home.pricing.start') }}</button>
          </div>
          <div class="pricing-card popular">
            <div class="popular-badge">{{ t('home.pricing.popular') }}</div>
            <div class="pricing-header">
              <h3>{{ t('home.pricing.pro.title') }}</h3>
              <div class="pricing-price">
                <span class="currency">¥</span>
                <span class="amount">99</span>
                <span class="period">/月</span>
              </div>
            </div>
            <ul class="pricing-features">
              <li>{{ t('home.pricing.pro.feature1') }}</li>
              <li>{{ t('home.pricing.pro.feature2') }}</li>
              <li>{{ t('home.pricing.pro.feature3') }}</li>
              <li>{{ t('home.pricing.pro.feature4') }}</li>
              <li class="disabled">{{ t('home.pricing.pro.feature5') }}</li>
            </ul>
            <button class="btn btn-primary" @click="$router.push('/register')">{{ t('home.pricing.start') }}</button>
          </div>
          <div class="pricing-card">
            <div class="pricing-header">
              <h3>{{ t('home.pricing.enterprise.title') }}</h3>
              <div class="pricing-price">
                <span class="currency">¥</span>
                <span class="amount">定制</span>
              </div>
            </div>
            <ul class="pricing-features">
              <li>{{ t('home.pricing.enterprise.feature1') }}</li>
              <li>{{ t('home.pricing.enterprise.feature2') }}</li>
              <li>{{ t('home.pricing.enterprise.feature3') }}</li>
              <li>{{ t('home.pricing.enterprise.feature4') }}</li>
              <li>{{ t('home.pricing.enterprise.feature5') }}</li>
            </ul>
            <button class="btn btn-outline" @click="$router.push('/app/tickets')">{{ t('home.pricing.contact') }}</button>
          </div>
        </div>
      </div>
    </section>

    <!-- 文档入口 -->
    <section id="docs" class="docs-section">
      <div class="docs-container">
        <div class="docs-content">
          <h2>{{ t('home.docs.title') }}</h2>
          <p>{{ t('home.docs.subtitle') }}</p>
          <button class="btn btn-primary" @click="$router.push('/app/api-doc')">{{ t('home.docs.getStarted') }}</button>
        </div>
      </div>
    </section>

    <!-- 页脚 -->
    <footer class="footer">
      <div class="footer-container">
        <div class="footer-links">
          <div class="footer-column">
            <h4>{{ t('home.footer.product') }}</h4>
            <a href="#features">{{ t('home.footer.features') }}</a>
            <a href="#pricing">{{ t('home.footer.pricing') }}</a>
            <a href="#docs">{{ t('home.footer.docs') }}</a>
          </div>
          <div class="footer-column">
            <h4>{{ t('home.footer.company') }}</h4>
            <a href="#">{{ t('home.footer.about') }}</a>
            <a href="#">{{ t('home.footer.contact') }}</a>
            <a href="#">{{ t('home.footer.blog') }}</a>
          </div>
          <div class="footer-column">
            <h4>{{ t('home.footer.legal') }}</h4>
            <a href="/privacy-policy">{{ t('home.footer.privacy') }}</a>
            <a href="/terms-of-service">{{ t('home.footer.terms') }}</a>
            <a href="#">{{ t('home.footer.cookies') }}</a>
          </div>
        </div>
        <div class="footer-bottom">
          <p>&copy; 2026 uniTokenHub. {{ t('home.footer.allRights') }}</p>
        </div>
      </div>
    </footer>
    
    <!-- Cookie 同意弹窗 -->
    <CookieConsent />
  </div>
</template>

<script setup>
import { useI18n } from '@/composables/useI18n'
import { Link, TrendCharts, Wallet, Lock, Histogram, Setting, CopyDocument } from '@element-plus/icons-vue'
import logoSrc from '@/assets/image/logo.png'
import CookieConsent from '@/components/CookieConsent.vue'

const { t } = useI18n()
import { ref } from 'vue'

const copied = ref(false)

const copyCode = async () => {
  const code = `curl -X POST https://api.unitokenhub.com/v1/chat/completions \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello"}]
  }'`
  await navigator.clipboard.writeText(code)
  copied.value = true
  setTimeout(() => {
    copied.value = false
  }, 2000)
}

const scrollToDocs = () => {
  const docsSection = document.getElementById('docs')
  if (docsSection) {
    docsSection.scrollIntoView({ behavior: 'smooth' })
  }
}
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
}

/* 导航栏 */
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
  padding: 16px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.navbar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo {
  width: 36px;
  height: 36px;
  border-radius: 8px;
}

.brand-name {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
}

.navbar-links {
  display: flex;
  gap: 32px;
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
  gap: 12px;
}

.btn {
  padding: 8px 20px;
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

.btn-large {
  padding: 12px 32px;
  font-size: 16px;
}

/* Hero 区域 */
.hero {
  padding: 120px 24px 80px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.hero-container {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 48px;
  align-items: center;
}

.hero-content {
  color: #fff;
}

.hero-title {
  font-size: 48px;
  font-weight: 700;
  margin: 0 0 16px;
  line-height: 1.2;
}

.hero-subtitle {
  font-size: 18px;
  opacity: 0.9;
  margin: 0 0 32px;
  line-height: 1.6;
}

.hero-actions {
  display: flex;
  gap: 16px;
  margin-bottom: 48px;
}

.hero-stats {
  display: flex;
  gap: 48px;
}

.stat-item {
  text-align: left;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
}

.stat-label {
  font-size: 14px;
  opacity: 0.8;
}

.hero-code {
  background: rgba(0, 0, 0, 0.25);
  border-radius: 16px;
  overflow: hidden;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.code-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: rgba(0, 0, 0, 0.2);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.code-lang {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  font-weight: 500;
}

.copy-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: 6px;
  padding: 6px 12px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background: rgba(255, 255, 255, 0.15);
    color: #fff;
  }
  
  .el-icon {
    font-size: 14px;
  }
}

.code-block {
  margin: 0;
  padding: 16px 24px;
  overflow-x: auto;
}

.code-block code {
  font-family: 'Fira Code', 'Monaco', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.7;
  color: #fff;
  opacity: 0.95;
  white-space: pre;
}

/* 功能特性 */
.features {
  padding: 80px 24px;
  background: #fff;
}

.section-header {
  text-align: center;
  margin-bottom: 48px;
}

.section-header h2 {
  font-size: 36px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0 0 16px;
}

.section-header p {
  font-size: 16px;
  color: #606266;
  margin: 0;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.feature-card {
  background: #f5f7fa;
  border-radius: 16px;
  padding: 32px;
  transition: all 0.3s;
  
  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  }
}

.feature-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  
  .el-icon {
    font-size: 24px;
    color: #fff;
  }
}

.feature-card h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0 0 8px;
}

.feature-card p {
  font-size: 14px;
  color: #606266;
  margin: 0;
  line-height: 1.6;
}

/* 定价方案 */
.pricing {
  padding: 80px 24px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
}

.pricing-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  max-width: 1000px;
  margin: 0 auto;
}

.pricing-card {
  background: #fff;
  border-radius: 16px;
  padding: 32px;
  position: relative;
  border: 2px solid transparent;
  transition: all 0.3s;
  
  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  }
  
  &.popular {
    border-color: #667eea;
    transform: scale(1.02);
  }
}

.popular-badge {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  padding: 4px 16px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.pricing-header {
  text-align: center;
  margin-bottom: 24px;
}

.pricing-header h3 {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0 0 16px;
}

.pricing-price {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 4px;
}

.currency {
  font-size: 24px;
  font-weight: 600;
  color: #606266;
}

.amount {
  font-size: 48px;
  font-weight: 700;
  color: #1a1a2e;
}

.period {
  font-size: 16px;
  color: #909399;
}

.pricing-features {
  list-style: none;
  padding: 0;
  margin: 0 0 24px;
}

.pricing-features li {
  padding: 12px 0;
  border-bottom: 1px solid #e4e7ed;
  font-size: 14px;
  color: #606266;
  display: flex;
  align-items: center;
  gap: 8px;
  
  &::before {
    content: '✓';
    color: #67c23a;
    font-weight: bold;
  }
  
  &.disabled {
    color: #909399;
    
    &::before {
      content: '✗';
      color: #909399;
    }
  }
  
  &:last-child {
    border-bottom: none;
  }
}

.pricing-card .btn {
  width: 100%;
  padding: 12px;
}

/* 文档入口 */
.docs-section {
  padding: 80px 24px;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}

.docs-container {
  max-width: 800px;
  margin: 0 auto;
  text-align: center;
}

.docs-content h2 {
  font-size: 32px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 16px;
}

.docs-content p {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.8);
  margin: 0 0 32px;
}

/* 页脚 */
.footer {
  padding: 60px 24px 24px;
  background: #141414;
}

.footer-container {
  max-width: 1200px;
  margin: 0 auto;
}

.footer-links {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 32px;
  margin-bottom: 32px;
}

.footer-column h4 {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  margin: 0 0 16px;
}

.footer-column a {
  display: block;
  color: #909399;
  text-decoration: none;
  font-size: 14px;
  margin-bottom: 8px;
  transition: color 0.3s;
  
  &:hover {
    color: #fff;
  }
}

.footer-bottom {
  border-top: 1px solid #252525;
  padding-top: 24px;
  text-align: center;
}

.footer-bottom p {
  color: #606266;
  font-size: 14px;
  margin: 0;
}

/* 响应式 */
@media (max-width: 768px) {
  .hero-container {
    grid-template-columns: 1fr;
    text-align: center;
  }
  
  .hero-title {
    font-size: 32px;
  }
  
  .hero-stats {
    justify-content: center;
  }
  
  .features-grid {
    grid-template-columns: 1fr;
  }
  
  .pricing-grid {
    grid-template-columns: 1fr;
  }
  
  .navbar-links {
    display: none;
  }
  
  .footer-links {
    grid-template-columns: 1fr;
  }
}
</style>
