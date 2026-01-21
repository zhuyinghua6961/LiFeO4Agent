<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import { useChatStore } from '../stores/chatStore'
import { api } from '../services/api'
import { formatTime, formatAnswer } from '../utils'
import PdfReader from '../components/PdfReader.vue'

const store = useChatStore()
const pdfReader = ref(null)
const inputMessage = ref('')
const messagesArea = ref(null)

const hasMessages = computed(() => store.currentMessages.length > 0)
const canSend = computed(() => inputMessage.value.trim() && !store.isStreaming)

onMounted(async () => {
  // 从登录状态获取用户信息
  const userStr = localStorage.getItem('user')
  if (!userStr) {
    // 如果没有用户信息，跳转到登录页
    window.location.href = '/login'
    return
  }
  
  try {
    const user = JSON.parse(userStr)
    if (!user.id) {
      window.location.href = '/login'
      return
    }
    
    // 设置用户ID
    store.setUserId(user.id)
  } catch (e) {
    console.error('解析用户信息失败:', e)
    window.location.href = '/login'
    return
  }
  
  await store.loadChats()
  await fetchKbInfo()
  
  if (store.chats.length === 0) {
    await store.createNewChat()
  } else {
    await store.switchChat(store.chats[0].id)
  }
  
  document.addEventListener('click', (e) => {
    const target = e.target
    if (target.classList && target.classList.contains('doi-link')) {
      e.preventDefault()
      const doi = target.getAttribute('data-doi')
      
      // 获取当前消息的位置信息
      const currentMsg = store.currentMessages[store.currentMessages.length - 1]
      const locations = currentMsg.doiLocations?.[doi] || []
      
      if (doi && pdfReader.value) {
        pdfReader.value.openReader(doi, locations)  // 传递位置信息
      }
    }
  })
})

async function fetchKbInfo() {
  try {
    const data = await api.getKbInfo()
    if (data.success) {
      store.setKbInfo({ loading: false, size: data.kb_size })
    }
  } catch (e) {
    store.setKbInfo({ loading: false, size: 0 })
  }
}

function createNewChat() {
  store.createNewChat()
  inputMessage.value = ''
}

function switchChat(chatId) {
  store.switchChat(chatId)
}

function deleteChat(chatId) {
  if (confirm('确定要删除这个对话吗？')) {
    store.deleteChat(chatId)
  }
}

async function sendMessage() {
  if (!canSend.value) {
    if (store.isStreaming) stopStreaming()
    return
  }

  const message = inputMessage.value.trim()
  if (!message) return

  const chat = store.currentChat
  if (!chat) return

  await store.addUserMessage(message)
  inputMessage.value = ''
  scrollToBottom()

  store.addBotMessage({
    role: 'bot',
    content: '',
    queryMode: '',
    expert: '',
    references: [],
    referenceLinks: [],
    steps: []
  })
  scrollToBottom()

  store.setStreaming(true)

  try {
    const chatHistory = store.currentMessages
      .slice(-10)
      .map(m => ({ role: m.role, content: m.content }))

    // 传递 conversationId 到 askStream
    // 注意：userId 从后端 JWT token 中获取，不需要前端传递
    const conversationId = store.currentChat.synced ? parseInt(store.currentChat.id) : null

    console.log('[sendMessage] 发送消息, conversationId:', conversationId, 'synced:', store.currentChat.synced)

    for await (const data of api.askStream(message, chatHistory, conversationId)) {
      if (data.type === 'step') {
        const currentMsg = store.currentMessages[store.currentMessages.length - 1]
        const existingSteps = currentMsg.steps || []
        const stepIndex = existingSteps.findIndex(s => s.step === data.step)
        
        if (stepIndex >= 0) {
          existingSteps[stepIndex] = { step: data.step, message: data.message, status: data.status, data: data.data }
        } else {
          existingSteps.push({ step: data.step, message: data.message, status: data.status, data: data.data })
        }
        store.updateLastBotMessage({ steps: [...existingSteps] })
      } else if (data.type === 'metadata') {
        store.updateLastBotMessage({ 
          expert: data.expert,
          queryMode: data.expert === 'neo4j' ? '知识图谱' : data.expert === 'community' ? '社区分析' : '文献检索'
        })
      } else if (data.type === 'content') {
        store.updateLastBotMessage({ content: store.currentMessages[store.currentMessages.length - 1].content + data.content })
      } else if (data.type === 'done') {
        console.log('[done事件] 收到done事件，references:', data.references)
        const updates = { 
          references: data.references || [], 
          referenceLinks: data.reference_links || [],
          isComplete: true  // 标记消息已完成
        }
        if (data.final_answer) updates.content = data.final_answer
        if (data.doi_locations) updates.doiLocations = data.doi_locations
        if (data.metadata) updates.metadata = data.metadata
        
        console.log('[done事件] 更新内容:', updates)
        store.updateLastBotMessage(updates)
        
        // 强制触发Vue更新
        nextTick(() => {
          console.log('[done事件] 更新后的消息:', store.currentMessages[store.currentMessages.length - 1])
          scrollToBottom()
        })
      } else if (data.type === 'error') {
        store.updateLastBotMessage({ content: '错误: ' + data.error })
      }
      scrollToBottom()
    }
  } catch (e) {
    store.updateLastBotMessage({ content: '错误: ' + e.message })
  }

  store.setStreaming(false)
  scrollToBottom()
}

function stopStreaming() {
  store.setStreaming(false)
  store.updateLastBotMessage({ 
    content: (store.currentMessages[store.currentMessages.length - 1]?.content || '') + '\n\n[对话已中断]' 
  })
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesArea.value) {
      messagesArea.value.scrollTop = messagesArea.value.scrollHeight
    }
  })
}

function autoResize(e) {
  e.target.style.height = 'auto'
  e.target.style.height = e.target.scrollHeight + 'px'
}
</script>

<template>
  <div class="app-container">
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="sidebar-title">对话历史</div>
        <button class="new-chat-btn" @click="createNewChat">新建对话</button>
      </div>
      <div class="system-info-section">
        <div class="info-title">💡 系统说明</div>
        <div class="info-content">
          <p>• 基于预加载的 <strong>6,254 篇</strong> 磷酸铁锂文献</p>
          <p>• 支持知识图谱、文献检索、社区分析</p>
        </div>
      </div>
      <div class="chat-history">
        <div v-if="store.chats.length === 0" class="empty-history">暂无对话</div>
        <div 
          v-for="chat in store.chats" 
          :key="chat.id"
          class="history-item"
          :class="{ active: chat.id === store.currentChatId }"
          @click="switchChat(chat.id)"
        >
          <div class="history-title">
            {{ chat.title }}
            <span v-if="chat.synced === false" class="sync-icon sync-failed" title="同步失败">⚠️</span>
            <span v-else-if="store.syncStatus === 'syncing'" class="sync-icon sync-syncing" title="同步中">🔄</span>
            <span v-else-if="chat.synced" class="sync-icon sync-synced" title="已同步">☁️</span>
          </div>
          <div class="history-time">{{ formatTime(chat.createdAt) }}</div>
        </div>
      </div>
    </aside>

    <main class="main-chat">
      <header class="chat-header">
        <div class="header-left">
          <div class="ai-icon">✨</div>
          <div class="header-title">
            <h1>磷酸铁锂知识图谱 AI</h1>
            <div class="kb-info">知识库: {{ store.kbInfo.size }} 条</div>
          </div>
        </div>
        <div class="header-right">
          <a href="/profile" class="nav-link">个人中心</a>
          <a href="/admin" class="nav-link admin-only">管理后台</a>
        </div>
      </header>

      <div class="messages-area" ref="messagesArea">
        <template v-if="!hasMessages">
          <div class="empty-state">
            <div class="empty-icon">🔋</div>
            <div class="empty-title">你好！我是磷酸铁锂材料专家</div>
            <div>请提出您的问题</div>
          </div>
        </template>
        <template v-else>
          <div v-for="(msg, index) in store.currentMessages" :key="index" class="message" :class="'message-' + msg.role">
            <template v-if="msg.role === 'user'">
              <div class="message-content">{{ msg.content }}</div>
            </template>
            <template v-else-if="msg.role === 'bot' || msg.role === 'assistant'">
              <div class="bot-avatar">✨</div>
              <div class="message-content">
                <div v-if="msg.queryMode" class="query-mode-badge">{{ msg.queryMode }}</div>
                <div v-if="msg.steps && msg.steps.length > 0" class="processing-steps">
                  <div v-for="(step, idx) in msg.steps" :key="idx" class="step-item" :class="'step-' + step.status">
                    <span class="step-icon">{{ step.status === 'processing' ? '⏳' : step.status === 'success' ? '✅' : '❌' }}</span>
                    <span class="step-message">{{ step.message }}</span>
                    <span v-if="step.data && step.data.count" class="step-badge">{{ step.data.count }}</span>
                  </div>
                </div>
                <div v-if="msg.content" v-html="formatAnswer(msg.content, msg.referenceLinks)"></div>
                <div v-else class="loading-animation"><span>思考中...</span></div>
                <div v-if="msg.references && msg.references.length > 0" class="references-section">
                  <div class="references-title">📚 参考文献</div>
                  <div class="references-list">
                    <div v-for="(ref, idx) in msg.references" :key="idx" class="reference-item" @click="ref.doi && pdfReader.openReader(ref.doi)">
                      <div class="reference-index">[{{ idx + 1 }}]</div>
                      <div class="reference-content">
                        <div class="reference-title">{{ ref.title || '未提供标题' }}</div>
                        <div class="reference-meta" v-if="ref.doi">DOI: <span class="doi-link">{{ ref.doi }}</span></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </template>
      </div>

      <div class="input-area">
        <div class="input-wrapper">
          <textarea v-model="inputMessage" placeholder="问我任何关于磷酸铁锂的问题..." rows="1" @keydown.enter.prevent="sendMessage" @input="autoResize($event)"></textarea>
          <button class="send-btn" :disabled="!canSend" @click="sendMessage">{{ store.isStreaming ? '⏹' : '➤' }}</button>
        </div>
      </div>
    </main>

    <PdfReader ref="pdfReader" />
  </div>
</template>

<style scoped>
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-right {
  margin-left: auto;
  display: flex;
  gap: 12px;
}

.nav-link {
  color: #667eea;
  text-decoration: none;
  font-size: 14px;
  padding: 8px 16px;
  border: 1px solid #667eea;
  border-radius: 6px;
  transition: all 0.2s;
}

.nav-link:hover {
  background: #667eea;
  color: white;
}

.admin-only {
  display: none;
}

.app-container {
  display: flex;
  min-height: 100vh;
  background: #f8fafc;
}

.sidebar {
  width: 280px;
  background: white;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #e2e8f0;
}

.sidebar-title {
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 12px;
}

.new-chat-btn {
  width: 100%;
  padding: 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

.system-info-section {
  padding: 16px 20px;
  background: #f1f5f9;
}

.info-title {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 8px;
}

.info-content {
  font-size: 12px;
  color: #475569;
}

.chat-history {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.history-item {
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 8px;
  transition: background 0.2s;
}

.history-item:hover {
  background: #f1f5f9;
}

.history-item.active {
  background: #e0e7ff;
}

.history-title {
  font-size: 14px;
  color: #1e293b;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sync-icon {
  font-size: 12px;
  margin-left: 4px;
}

.sync-syncing {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.history-time {
  font-size: 12px;
  color: #94a3b8;
}

.empty-history {
  text-align: center;
  color: #94a3b8;
  padding: 20px;
}

.main-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chat-header {
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid #e2e8f0;
}

.ai-icon {
  font-size: 32px;
}

.header-title h1 {
  font-size: 18px;
  color: #1e293b;
  margin: 0;
}

.kb-info {
  font-size: 13px;
  color: #64748b;
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: #64748b;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-title {
  font-size: 20px;
  color: #1e293b;
  margin-bottom: 8px;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.message-user {
  justify-content: flex-end;
}

.message-bot {
  justify-content: flex-start;
}

.message-content {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
}

.message-user .message-content {
  background: #667eea;
  color: white;
}

.message-bot .message-content {
  background: white;
  border: 1px solid #e2e8f0;
}

.bot-avatar {
  font-size: 24px;
}

.query-mode-badge {
  display: inline-block;
  padding: 4px 10px;
  background: #dbeafe;
  color: #1d4ed8;
  border-radius: 4px;
  font-size: 12px;
  margin-bottom: 8px;
}

.processing-steps {
  margin-bottom: 12px;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  font-size: 13px;
}

.step-badge {
  background: #dcfce7;
  color: #166534;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  margin-left: 8px;
}

.loading-animation {
  color: #64748b;
  font-size: 14px;
}

.references-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e2e8f0;
}

.references-title {
  font-size: 13px;
  color: #475569;
  margin-bottom: 8px;
}

.reference-item {
  display: flex;
  gap: 8px;
  padding: 8px;
  background: #f8fafc;
  border-radius: 6px;
  margin-bottom: 6px;
  cursor: pointer;
}

.reference-item:hover {
  background: #f1f5f9;
}

.reference-index {
  color: #667eea;
  font-size: 12px;
}

.reference-title {
  font-size: 13px;
  color: #1e293b;
}

.reference-meta {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
}

.doi-link {
  color: #667eea;
  text-decoration: none;
}

.input-area {
  padding: 16px 24px;
  background: white;
  border-top: 1px solid #e2e8f0;
}

.input-wrapper {
  display: flex;
  gap: 12px;
  background: #f8fafc;
  border-radius: 12px;
  padding: 8px;
  border: 1px solid #e2e8f0;
}

.input-wrapper textarea {
  flex: 1;
  border: none;
  background: transparent;
  padding: 8px;
  font-size: 14px;
  resize: none;
  outline: none;
}

.send-btn {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
