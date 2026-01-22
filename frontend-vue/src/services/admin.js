const API_BASE = '/api/admin'

export const adminApi = {
  async getUsers(page = 1, pageSize = 10) {
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_BASE}/users?page=${page}&page_size=${pageSize}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    return response.json()
  },

  async createUser(username, password, userType = 'common') {
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_BASE}/users`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ username, password, user_type: userType })
    })
    return response.json()
  },

  async changeUserPassword(userId, newPassword) {
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_BASE}/users/${userId}/password`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ new_password: newPassword })
    })
    return response.json()
  },

  async changeUserStatus(userId, status) {
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_BASE}/users/${userId}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ status })
    })
    return response.json()
  },

  async deleteUser(userId) {
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_BASE}/users/${userId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    })
    return response.json()
  },

  async getUserPassword(userId) {
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_BASE}/users/${userId}/password`, {
      method: 'GET',
      headers: { 'Authorization': `Bearer ${token}` }
    })
    return response.json()
  },

  async batchImportUsers(file) {
    const token = localStorage.getItem('token')
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await fetch(`${API_BASE}/users/batch-import`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    })
    return response.json()
  },

  async downloadImportTemplate(format = 'xlsx') {
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_BASE}/users/import-template?format=${format}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    
    if (!response.ok) {
      throw new Error('下载模板失败')
    }
    
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `user_import_template.${format}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  }
}
