/**
 * 认证API服务
 */
const API_BASE = '/api/auth'

export const authApi = {
  /**
   * 登录
   */
  async login(username, password) {
    const response = await fetch(`${API_BASE}/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username, password })
    })
    return response.json()
  },

  /**
   * 注册
   */
  async register(username, password) {
    const response = await fetch(`${API_BASE}/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username, password })
    })
    return response.json()
  },

  /**
   * 获取当前用户信息
   */
  async getMe() {
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_BASE}/me`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    return response.json()
  },

  /**
   * 修改密码
   */
  async changePassword(oldPassword, newPassword) {
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_BASE}/password`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
    })
    return response.json()
  },

  /**
   * 登出
   */
  async logout() {
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_BASE}/logout`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    return response.json()
  },

  /**
   * 发起密码重置 - 检查安全问题
   */
  async initiatePasswordReset(username) {
    const response = await fetch(`${API_BASE}/forgot-password/initiate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username })
    })
    return response.json()
  },

  /**
   * 验证安全问题并重置密码
   */
  async verifyAndResetPassword(username, answers, newPassword) {
    const response = await fetch(`${API_BASE}/forgot-password/verify`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username, answers, new_password: newPassword })
    })
    return response.json()
  },

  /**
   * 获取当前用户设置的安全问题
   */
  async getSecurityQuestions() {
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_BASE}/security-questions`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    return response.json()
  },

  /**
   * 设置/更新安全问题
   */
  async setSecurityQuestions(questions) {
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_BASE}/security-questions`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ questions })
    })
    return response.json()
  }
}
