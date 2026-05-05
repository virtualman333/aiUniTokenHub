<template>
  <div class="admin-settings">
    <!-- 头部 -->
    <div class="header">
      <h1>个人设置</h1>
      <p class="subtitle">管理您的管理员账户信息</p>
    </div>

    <el-row :gutter="24">
      <!-- 个人资料 -->
      <el-col :span="12">
        <el-card v-loading="loading">
          <template #header>
            <span class="card-title">个人资料</span>
          </template>
          <el-form :model="profile" label-width="100px">
            <el-form-item label="用户名">
              <el-input v-model="profile.username" />
            </el-form-item>
            <el-form-item label="邮箱">
              <el-input v-model="profile.email" type="email" />
            </el-form-item>
            <el-form-item label="手机号">
              <el-input v-model="profile.phone" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="handleSaveProfile">
                保存修改
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 修改密码 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span class="card-title">修改密码</span>
          </template>
          <el-form :model="passwordForm" label-width="100px">
            <el-form-item label="原密码">
              <el-input v-model="passwordForm.old_password" type="password" show-password />
            </el-form-item>
            <el-form-item label="新密码">
              <el-input v-model="passwordForm.new_password" type="password" show-password />
            </el-form-item>
            <el-form-item label="确认密码">
              <el-input v-model="passwordForm.confirm_password" type="password" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="handleChangePassword">
                修改密码
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useSettings } from '@/views/user/Settings/composables/useSettings'

const {
  loading,
  saving,
  profile,
  passwordForm,
  loadSettings,
  updateProfile,
  changePassword
} = useSettings()

onMounted(() => {
  loadSettings()
})

async function handleSaveProfile() {
  const success = await updateProfile()
  if (success) {
    ElMessage.success('保存成功')
  } else {
    ElMessage.error('保存失败')
  }
}

async function handleChangePassword() {
  try {
    await changePassword()
    ElMessage.success('密码修改成功')
  } catch (e: any) {
    ElMessage.error(e.message || '修改失败')
  }
}
</script>

<style scoped>
.admin-settings {
  padding: 0;
}

.header {
  margin-bottom: 24px;
}

.header h1 {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}

.subtitle {
  color: #6b7280;
  font-size: 14px;
}

.card-title {
  font-weight: 600;
  font-size: 16px;
}
</style>