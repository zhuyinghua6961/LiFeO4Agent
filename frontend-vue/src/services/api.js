// API 服务层 - 封装所有后端请求

const API_BASE = '' // Vite 代理处理（开发环境）或相对路径（生产环境）

export const api = {
  // 获取知识库信息
  async getKbInfo() {
    const res = await fetch(`${API_BASE}/api/kb_info`)
    return res.json()
  },

  // 流式问答（重要：对接重构后的 /api/ask_stream 端点）
  async *askStream(question, chatHistory = []) {
    const response = await fetch(`${API_BASE}/api/ask_stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        chat_history: chatHistory.slice(-10)
        // 注意：重构后的后端不再需要 use_pdf 参数
        // IntegratedAgent 会自动处理路由
      })
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
