<script setup>
import { ref, onMounted } from 'vue'
import { authApi } from '../services/auth'
import { adminApi } from '../services/admin'

const currentUser = ref(null)
const users = ref([])
const loading = ref(false)
const error = ref('')
const success = ref('')
const pagination = ref({ page: 1, pageSize: 10, total: 0 })

const showPasswordModal = ref(false)
const showStatusModal = ref(false)
const showDeleteModal = ref(false)
const showCreateModal = ref(false)
const selectedUser = ref(null)
const newPassword = ref('')
const newUsername = ref('')
const newUserPassword = ref('')

async function fetchCurrentUser() {
  const result = await authApi.getMe()
  if (result.success) currentUser.value = result.data
}

async function fetchUsers() {
  loading.value = true
  error.value = ''
  try {
    const result = await adminApi.getUsers(pagination.value.page, pagination.value.pageSize)
    if (result.success) {
      users.value = result.data
      pagination.value.total = result.pagination.total
    } else {
      error.value = result.error
    }
  } catch (e) {
    error.value = '获取用户列表失败'
  } finally {
    loading.value = false
  }
}

function openPasswordModal(user) {
  selectedUser.value = user
  newPassword.value = ''
  showPasswordModal.value = true
}

async function submitPasswordChange() {
  if (!newPassword.value || newPassword.value.length < 6) {
    error.value = '密码长度不能少于6位'
    return
  }
  const result = await adminApi.changeUserPassword(selectedUser.value.id, newPassword.value)
  if (result.success) {
    success.value = `用户 ${selectedUser.value.username} 的密码已修改`
    showPasswordModal.value = false
    setTimeout(() => success.value = '', 3000)
  } else {
    error.value = result.error
  }
}

function openStatusModal(user) {
  selectedUser.value = user
  showStatusModal.value = true
}

async function submitStatusChange(status) {
  const result = await adminApi.changeUserStatus(selectedUser.value.id, status)
  if (result.success) {
    success.value = `用户 ${selectedUser.value.username} 已${status === 'disabled' ? '停用' : '启用'}`
    showStatusModal.value = false
    await fetchUsers()
    setTimeout(() => success.value = '', 3000)
  } else {
    error.value = result.error
  }
}

function openDeleteModal(user) {
  selectedUser.value = user
  showDeleteModal.value = true
}

async function submitDelete() {
  const result = await adminApi.deleteUser(selectedUser.value.id)
  if (result.success) {
    success.value = `用户 ${selectedUser.value.username} 已删除`
    showDeleteModal.value = false
    await fetchUsers()
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

function changePage(page) {
  pagination.value.page = page
  fetchUsers()
}

function openCreateModal() {
  newUsername.value = ''
  newUserPassword.value = ''
  error.value = ''
  showCreateModal.value = true
}

async function submitCreateUser() {
  error.value = ''
  
  if (!newUsername.value || !newUserPassword.value) {
    error.value = '用户名和密码不能为空'
    return
  }
  
  if (newUsername.value.length < 3 || newUsername.value.length > 50) {
    error.value = '用户名长度必须在3-50之间'
    return
  }
  
  if (newUserPassword.value.length < 6) {
    error.value = '密码长度不能少于6位'
    return
  }
  
  if (newUsername.value.toLowerCase().startsWith('admin')) {
    error.value = '不能创建以 admin 为前缀的用户名'
    return
  }
  
  const result = await adminApi.createUser(newUsername.value, newUserPassword.value)
  
  if (result.success) {
    success.value = `用户 ${newUsername.value} 创建成功`
    showCreateModal.value = false
    await fetchUsers()
    setTimeout(() => success.value = '', 3000)
  } else {
    error.value = result.error
  }
}

onMounted(async () => {
  await fetchCurrentUser()
  await fetchUsers()
})
</script>

<template>
  <div class="admin-container">
    <header class="admin-header">
      <div class="header-left">
        <h1>管理员后台</h1>
        <span class="user-info" v-if="currentUser">管理员: {{ currentUser.username }}</span>
      </div>
      <button class="logout-btn" @click="logout">退出登录</button>
    </header>

    <main class="admin-main">
      <div v-if="success" class="alert alert-success">{{ success }}</div>
      <div v-if="error" class="alert alert-error">{{ error }}</div>

      <div class="user-section">
        <div class="section-header">
          <h2>用户管理</h2>
          <button class="add-user-btn" @click="openCreateModal">添加用户</button>
        </div>

        <div v-if="loading" class="loading">加载中...</div>

        <table v-else class="user-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>用户名</th>
              <th>角色</th>
              <th>状态</th>
              <th>创建时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td>{{ user.id }}</td>
              <td>{{ user.username }}</td>
              <td><span class="role-badge" :class="user.role">{{ user.role === 'admin' ? '管理员' : '用户' }}</span></td>
              <td><span class="status-badge" :class="user.status">{{ user.status === 'active' ? '正常' : '停用' }}</span></td>
              <td>{{ user.created_at }}</td>
              <td class="actions">
                <button class="action-btn" @click="openPasswordModal(user)">修改密码</button>
                <button class="action-btn" :class="user.status === 'active' ? 'btn-danger' : 'btn-success'" @click="openStatusModal(user)">
                  {{ user.status === 'active' ? '停用' : '启用' }}
                </button>
                <button class="action-btn btn-danger" @click="openDeleteModal(user)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="pagination.total > pagination.pageSize" class="pagination">
          <button :disabled="pagination.page === 1" @click="changePage(pagination.page - 1)">上一页</button>
          <span>第 {{ pagination.page }} 页 / 共 {{ Math.ceil(pagination.total / pagination.pageSize) }} 页</span>
          <button :disabled="pagination.page * pagination.pageSize >= pagination.total" @click="changePage(pagination.page + 1)">下一页</button>
        </div>
      </div>
    </main>

    <!-- Modals -->
    <div v-if="showPasswordModal" class="modal-overlay" @click.self="showPasswordModal = false">
      <div class="modal">
        <h3>修改密码 - {{ selectedUser?.username }}</h3>
        <div class="modal-body">
          <div class="form-group">
            <label>新密码</label>
            <input type="password" v-model="newPassword" placeholder="请输入新密码（至少6位）">
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showPasswordModal = false">取消</button>
          <button class="btn-primary" @click="submitPasswordChange">确认修改</button>
        </div>
      </div>
    </div>

    <div v-if="showStatusModal" class="modal-overlay" @click.self="showStatusModal = false">
      <div class="modal">
        <h3>{{ selectedUser?.status === 'active' ? '停用' : '启用' }}用户 - {{ selectedUser?.username }}</h3>
        <div class="modal-body"><p>确定要{{ selectedUser?.status === 'active' ? '停用' : '启用' }}该用户吗？</p></div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showStatusModal = false">取消</button>
          <button class="btn-danger" @click="submitStatusChange(selectedUser?.status === 'active' ? 'disabled' : 'active')">确认</button>
        </div>
      </div>
    </div>

    <div v-if="showDeleteModal" class="modal-overlay" @click.self="showDeleteModal = false">
      <div class="modal">
        <h3>删除用户 - {{ selectedUser?.username }}</h3>
        <div class="modal-body"><p class="warning">确定要删除该用户吗？此操作不可恢复！</p></div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showDeleteModal = false">取消</button>
          <button class="btn-danger" @click="submitDelete">确认删除</button>
        </div>
      </div>
    </div>

    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal">
        <h3>添加新用户</h3>
        <div class="modal-body">
          <div class="form-group">
            <label>用户名</label>
            <input type="text" v-model="newUsername" placeholder="请输入用户名（3-50字符）">
          </div>
          <div class="form-group">
            <label>密码</label>
            <input type="password" v-model="newUserPassword" placeholder="请输入密码（至少6位）">
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showCreateModal = false">取消</button>
          <button class="btn-primary" @click="submitCreateUser">确认添加</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-container { min-height: 100vh; background: #f3f4f6; }
.admin-header { background: white; padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.header-left { display: flex; align-items: center; gap: 20px; }
.header-left h1 { font-size: 20px; color: #1f2937; margin: 0; }
.user-info { color: #6b7280; font-size: 14px; }
.logout-btn { background: #f3f4f6; border: 1px solid #d1d5db; padding: 8px 16px; border-radius: 6px; cursor: pointer; }
.admin-main { padding: 24px; max-width: 1200px; margin: 0 auto; }
.alert { padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; }
.alert-success { background: #dcfce7; color: #166534; }
.alert-error { background: #fef2f2; color: #dc2626; }
.user-section { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.section-header h2 { font-size: 18px; color: #1f2937; margin: 0; }
.add-user-btn { background: #667eea; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 14px; }
.add-user-btn:hover { background: #5a67d8; }
.user-count { color: #6b7280; font-size: 14px; }
.loading { text-align: center; padding: 40px; color: #6b7280; }
.user-table { width: 100%; border-collapse: collapse; }
.user-table th, .user-table td { padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }
.user-table th { background: #f9fafb; font-weight: 500; color: #374151; font-size: 14px; }
.user-table td { color: #1f2937; font-size: 14px; }
.role-badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; }
.role-badge.admin { background: #dbeafe; color: #1d4ed8; }
.role-badge.user { background: #dcfce7; color: #166534; }
.status-badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; }
.status-badge.active { background: #dcfce7; color: #166534; }
.status-badge.disabled { background: #fee2e2; color: #dc2626; }
.actions { display: flex; gap: 8px; }
.action-btn { padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; border: 1px solid #d1d5db; background: white; }
.action-btn:hover { background: #f9fafb; }
.action-btn.btn-success { background: #dcfce7; border-color: #86efac; color: #166534; }
.action-btn.btn-danger { background: #fee2e2; border-color: #fca5a5; color: #dc2626; }
.pagination { display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 20px; }
.pagination button { padding: 8px 16px; border: 1px solid #d1d5db; background: white; border-radius: 6px; cursor: pointer; }
.pagination button:disabled { opacity: 0.5; cursor: not-allowed; }
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; }
.modal { background: white; border-radius: 12px; padding: 24px; width: 100%; max-width: 400px; }
.modal h3 { font-size: 18px; color: #1f2937; margin: 0 0 16px 0; }
.modal-body { margin-bottom: 24px; }
.modal-body .form-group { display: flex; flex-direction: column; gap: 8px; }
.modal-body .form-group label { font-size: 14px; color: #374151; }
.modal-body .form-group input { padding: 10px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; }
.modal-body .warning { color: #dc2626; font-size: 14px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 12px; }
.btn-primary, .btn-secondary, .btn-danger { padding: 10px 20px; border-radius: 6px; font-size: 14px; cursor: pointer; border: none; }
.btn-primary { background: #667eea; color: white; }
.btn-secondary { background: #f3f4f6; color: #374151; border: 1px solid #d1d5db; }
.btn-danger { background: #dc2626; color: white; }
</style>
