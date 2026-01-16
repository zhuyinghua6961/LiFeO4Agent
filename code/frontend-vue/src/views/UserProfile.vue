<script setup>
import { ref, onMounted } from 'vue'
import { authApi } from '../services/auth'

const currentUser = ref(null)
const loading = ref(false)
const error = ref('')
const success = ref('')

// 修改密码表单
const showPasswordForm = ref(false)
const oldPassword = ref('')
const newPassword = ref('')

async function fetchCurrentUser() {
  loading.value = true
  try {
    const result = await authApi.getMe()
    if (result.success) {
      currentUser.value = result.data
    } else {
      error.value = result.error
    }
  } catch (e) {
    error.value = '获取用户信息失败'
  } finally {
    loading.value = false
  }
}

async function submitPasswordChange() {
  error.value = ''
  success.value = ''
  
  if (!oldPassword.value || !newPassword.value) {
    error.value = '请填写所有字段'
    return
  }
  
  if (newPassword.value.length < 8) {
    error.value = '新密码长度不能少于8位'
    return
  }
  
  if (!/[a-zA-Z]/.test(newPassword.value)) {
    error.value = '新密码必须包含字母'
    return
  }
  
  if (!/[0-9]/.test(newPassword.value)) {
    error.value = '新密码必须包含数字'
    return
  }
  
  if (!/[!@#$%^&*()_+\-=\[\]{};\'\\:"|<,./>?]/.test(newPassword.value)) {
    error.value = '新密码必须包含英文符号'
    return
  }
  
  const result = await authApi.changePassword(oldPassword.value, newPassword.value)
  
  if (result.success) {
    success.value = '密码修改成功'
    showPasswordForm.value = false
    oldPassword.value = ''
    newPassword.value = ''
    setTimeout(() => success.value = '', 3000)
  } else {
    error.value = result.error
  }
}

async function logout() {
  await authApi.logout()
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  window.location.href = '/login'
}

onMounted(fetchCurrentUser)
</script>

<template>
  <div class="profile-container">
    <header class="profile-header">
      <div class="header-left">
        <a href="/" class="back-link">← 返回对话</a>
        <h1>个人中心</h1>
      </div>
      <button class="logout-btn" @click="logout">退出登录</button>
    </header>

    <main class="profile-main">
      <div v-if="loading" class="loading">加载中...</div>
      
      <template v-else-if="currentUser">
        <!-- 用户信息卡片 -->
        <div class="info-card">
          <h2>基本信息</h2>
          <div class="info-row">
            <span class="label">用户名</span>
            <span class="value">{{ currentUser.username }}</span>
          </div>
          <div class="info-row">
            <span class="label">角色</span>
            <span class="value role-badge" :class="currentUser.role">
              {{ currentUser.role === 'admin' ? '管理员' : '普通用户' }}
            </span>
          </div>
          <div class="info-row">
            <span class="label">状态</span>
            <span class="value status-badge" :class="currentUser.status">
              {{ currentUser.status === 'active' ? '正常' : '已停用' }}
            </span>
          </div>
          <div class="info-row">
            <span class="label">创建时间</span>
            <span class="value">{{ currentUser.created_at }}</span>
          </div>
        </div>

        <!-- 修改密码 -->
        <div class="action-card">
          <h2>修改密码</h2>
          
          <div v-if="success" class="alert alert-success">{{ success }}</div>
          <div v-if="error" class="alert alert-error">{{ error }}</div>
          
          <div v-if="!showPasswordForm">
            <button class="action-btn" @click="showPasswordForm = true">
              修改密码
            </button>
          </div>
          
          <div v-else class="password-form">
            <div class="form-group">
              <label>旧密码</label>
              <input type="password" v-model="oldPassword" placeholder="请输入旧密码">
            </div>
            <div class="form-group">
              <label>新密码</label>
              <input type="password" v-model="newPassword" placeholder="请输入新密码（8位以上，包含字母、数字、符号）">
            </div>
            <div class="form-actions">
              <button class="btn-secondary" @click="showPasswordForm = false">取消</button>
              <button class="btn-primary" @click="submitPasswordChange">确认修改</button>
            </div>
          </div>
        </div>
      </template>
    </main>
  </div>
</template>

<style scoped>
.profile-container {
  min-height: 100vh;
  background: #f3f4f6;
}

.profile-header {
  background: white;
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.back-link {
  color: #667eea;
  text-decoration: none;
  font-size: 14px;
}

.back-link:hover {
  text-decoration: underline;
}

.header-left h1 {
  font-size: 20px;
  color: #1f2937;
  margin: 0;
}

.logout-btn {
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.profile-main {
  padding: 24px;
  max-width: 600px;
  margin: 0 auto;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #6b7280;
}

.info-card, .action-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.info-card h2, .action-card h2 {
  font-size: 16px;
  color: #1f2937;
  margin: 0 0 16px 0;
  padding-bottom: 12px;
  border-bottom: 1px solid #e5e7eb;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f3f4f6;
}

.info-row:last-child {
  border-bottom: none;
}

.label {
  color: #6b7280;
  font-size: 14px;
}

.value {
  color: #1f2937;
  font-size: 14px;
  font-weight: 500;
}

.role-badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
}

.role-badge.admin {
  background: #dbeafe;
  color: #1d4ed8;
}

.role-badge.user {
  background: #dcfce7;
  color: #166534;
}

.status-badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
}

.status-badge.active {
  background: #dcfce7;
  color: #166534;
}

.status-badge.disabled {
  background: #fee2e2;
  color: #dc2626;
}

.action-btn {
  width: 100%;
  padding: 12px;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #374151;
}

.action-btn:hover {
  background: #e5e7eb;
}

.password-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 14px;
  color: #374151;
}

.form-group input {
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 8px;
}

.btn-primary, .btn-secondary {
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  border: none;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
}

.alert {
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.alert-success {
  background: #dcfce7;
  color: #166534;
}

.alert-error {
  background: #fef2f2;
  color: #dc2626;
}
</style>
