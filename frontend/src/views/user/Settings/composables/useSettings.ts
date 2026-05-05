/**
 * 设置 Composable
 */
import { ref, reactive } from 'vue'
import api from '@/stores'

export function useSettings() {
  const loading = ref(false)
  const saving = ref(false)

  const profile = reactive({
    username: '',
    email: '',
    phone: ''
  })

  const passwordForm = reactive({
    old_password: '',
    new_password: '',
    confirm_password: ''
  })

  /**
   * 加载用户设置
   */
  async function loadSettings() {
    loading.value = true
    try {
      const res = await api.get('/users/auth/me/')
      profile.username = res.username || ''
      profile.email = res.email || ''
      profile.phone = res.phone || ''
    } catch (e) {
      console.error('加载设置失败:', e)
    } finally {
      loading.value = false
    }
  }

  /**
   * 更新个人资料
   */
  async function updateProfile() {
    saving.value = true
    try {
      await api.patch('/users/auth/me/', profile)
      return true
    } catch (e) {
      console.error('更新失败:', e)
      return false
    } finally {
      saving.value = false
    }
  }

  /**
   * 修改密码
   */
  async function changePassword() {
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      throw new Error('两次输入的密码不一致')
    }
    
    saving.value = true
    try {
      await api.post('/users/auth/change-password/', {
        old_password: passwordForm.old_password,
        new_password: passwordForm.new_password
      })
      // 清空表单
      passwordForm.old_password = ''
      passwordForm.new_password = ''
      passwordForm.confirm_password = ''
      return true
    } catch (e) {
      console.error('修改密码失败:', e)
      throw e
    } finally {
      saving.value = false
    }
  }

  return {
    loading,
    saving,
    profile,
    passwordForm,
    loadSettings,
    updateProfile,
    changePassword
  }
}
