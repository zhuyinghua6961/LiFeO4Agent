const API_BASE = '/api/admin'

export const adminApi = {
  async getUsers(page = 1, pageSize = 10) {
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_BASE}/users?page=${page}&page_size=${pageSize}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    return response.json()
  },

  async createUser(username, password) {
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_BASE}/users`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ username, password })
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
  }
}
