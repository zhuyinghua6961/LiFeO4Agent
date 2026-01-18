// API 服务层 - 封装所有后端请求

const API_BASE = '' // Vite 代理处理（开发环境）或相对路径（生产环境）

export const api = {
  // ==================== 对话管理 API ====================
  
  // 创建新对话
  async createConversation(userId, title = '新对话') {
    const res = await fetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({ user_id: userId, title })
    })
    if (!res.ok) throw new Error('创建对话失败')
    return res.json()
  },

  // 获取对话列表
  async getConversationList(userId, page = 1, pageSize = 20) {
    const res = await fetch(
      `${API_BASE}/api/conversations?user_id=${userId}&page=${page}&page_size=${pageSize}`,
      {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      }
    )
    if (!res.ok) throw new Error('获取对话列表失败')
    return res.json()
  },

  // 获取对话详情
  async getConversationDetail(conversationId, userId) {
    const res = await fetch(
      `${API_BASE}/api/conversations/${conversationId}?user_id=${userId}`,
      {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      }
    )
    if (!res.ok) throw new Error('获取对话详情失败')
    return res.json()
  },

  // 添加消息到对话
  async addMessage(conversationId, userId, message) {
    const res = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/messages`,
      {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ user_id: userId, message })
      }
    )
    if (!res.ok) throw new Error('添加消息失败')
    return res.json()
  },

  // 更新对话标题
  async updateConversationTitle(conversationId, userId, title) {
    const res = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`,
      {
        method: 'PUT',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ user_id: userId, title })
      }
    )
    if (!res.ok) throw new Error('更新标题失败')
    return res.json()
  },

  // 删除对话
  async deleteConversation(conversationId, userId) {
    const res = await fetch(
      `${API_BASE}/api/conversations/${conversationId}?user_id=${userId}`,
      {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      }
    )
    if (!res.ok) throw new Error('删除对话失败')
    return res.status === 204 ? { success: true } : res.json()
  },

  // ==================== 知识库 API ====================
  
  // 获取知识库信息
  async getKbInfo() {
    const res = await fetch(`${API_BASE}/api/kb_info`)
    return res.json()
  },

  // 流式问答（重要：对接重构后的 /api/ask_stream 端点）
  async *askStream(question, chatHistory = [], conversationId = null) {
    const body = {
      question,
      chat_history: chatHistory.slice(-10)
    }
    
    // 如果提供了 conversationId，添加到请求体
    // 注意：userId 从后端 JWT token 中获取，不需要前端传递
    if (conversationId) body.conversation_id = conversationId
    
    const response = await fetch(`${API_BASE}/api/ask_stream`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
      },
      body: JSON.stringify(body)
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.error || '网络错误')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            yield JSON.parse(line.substring(6))
          } catch (e) {
            // 忽略解析错误
          }
        }
      }
    }
  },

  // 普通问答（非流式，已废弃 - 建议使用 askStream）
  async ask(question, chatHistory = []) {
    const res = await fetch(`${API_BASE}/api/ask_stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        chat_history: chatHistory.slice(-10)
      })
    })
    return res.json()
  },

  // 翻译文本
  async translate(texts) {
    const res = await fetch(`${API_BASE}/api/translate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texts })
    })
    return res.json()
  },

  // 查看 PDF
  viewPdf(doi) {
    return `${API_BASE}/api/view_pdf/${encodeURIComponent(doi)}`
  },

  // 总结 PDF
  async summarizePdf(doi) {
    const res = await fetch(`${API_BASE}/api/summarize_pdf/${encodeURIComponent(doi)}`, {
      method: 'POST'
    })
    return res.json()
  }
}
