<script setup>
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import { useChatStore } from './stores/chatStore'
import { api } from './services/api'
import { formatTime, formatAnswer, escapeHtml } from './utils'
import PdfReader from './components/PdfReader.vue'

// Store
const store = useChatStore()

// PDF Reader
const pdfReader = ref(null)

// Refs
const inputMessage = ref('')
const messagesArea = ref(null)
const inputTextarea = ref(null)

// Computed
const hasMessages = computed(() => store.currentMessages.length > 0)
const canSend = computed(() => inputMessage.value.trim() && !store.isStreaming)
const kbInfoText = computed(() => {
  const info = store.kbInfo
  if (info.loading) return '加载中...'
  return `知识库: ${info.size} 条`
})

// Lifecycle
onMounted(async () => {
  store.loadChats()
  await fetchKbInfo()
  if (store.chats.length === 0) {
    store.createNewChat()
  } else {
    store.switchChat(store.chats[0].id)
  }
})

// Methods
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

function clearAllChats() {
  if (store.chats.length > 0 && confirm(`确定要清空所有 ${store.chats.length} 个对话吗？`)) {
    store.clearAllChats()
    store.createNewChat()
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

  // 添加用户消息
  store.addUserMessage(message)
  inputMessage.value = ''
  scrollToBottom()

  // 创建空的 bot 消息
  store.addBotMessage({
    role: 'bot',
    content: '',
    queryMode: '',
    expert: '',
    confidence: 0,
    reasoning: '',
    references: [],
    referenceLinks: []
  })
  scrollToBottom()

  store.setStreaming(true)

  try {
    const chatHistory = store.currentMessages
      .slice(-10)
      .map(m => ({ role: m.role, content: m.content }))

    for await (const data of api.askStream(message, chatHistory)) {
      if (data.type === 'start') {
        // 开始查询
        console.log('🚀 开始生成答案')
      } else if (data.type === 'thinking') {
        // 思考过程 - 可以在加载动画中显示
        console.log('💭', data.content)
      } else if (data.type === 'metadata') {
        // 专家路由信息
        store.updateLastBotMessage({ 
          expert: data.expert,
          confidence: data.confidence,
          reasoning: data.reasoning,
          queryMode: data.expert === 'neo4j' ? '知识图谱' : data.expert === 'community' ? '社区分析' : '文献检索'
        })
      } else if (data.type === 'content') {
        // 流式内容
        store.updateLastBotMessage({ content: store.currentMessages[store.currentMessages.length - 1].content + data.content })
      } else if (data.type === 'done') {
        // 完成 - 使用 final_answer 或保留流式内容
        const updates = {
          references: data.references || [],
          referenceLinks: data.reference_links || []
        }
        if (data.final_answer) {
          updates.content = data.final_answer
        }
        store.updateLastBotMessage(updates)
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

// Auto-resize textarea
function autoResize(e) {
  e.target.style.height = 'auto'
  e.target.style.height = e.target.scrollHeight + 'px'
}



// 打开 PDF 预览（根据路径）
window.openPdfFromPath = (element) => {
  const pdfPath = element.dataset.pdf
  const doi = element.dataset.doi
  
  if (doi) {
    // 优先使用 DOI
    if (pdfReader.value) {
      pdfReader.value.openReader(doi)
    }
  } else if (pdfPath) {
    // 提取 DOI
    const filename = pdfPath.split('/').pop()
    const extractedDoi = filename.replace('.pdf', '').replace(/_/g, '/')
    
    // 打开 PDF 阅读器
    if (pdfReader.value) {
      pdfReader.value.openReader(extractedDoi)
    }
  } else {
    alert('PDF 文件路径不存在')
  }
}

// 直接使用 DOI 打开 PDF
window.openPdfFromDoi = (doi) => {
  if (doi && pdfReader.value) {
    pdfReader.value.openReader(doi)
  } else {
    alert('DOI 不存在')
  }
}
</script>

<template>
  <div class="app-container">
    <!-- 左侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="sidebar-title-bar">
          <div class="sidebar-title">对话历史</div>
          <button class="clear-all-btn" @click="clearAllChats">清空</button>
        </div>
        <button class="new-chat-btn" @click="createNewChat">新建对话</button>
      </div>

      <!-- 系统说明 -->
      <div class="system-info-section">
        <div class="info-title">💡 系统说明</div>
        <div class="info-content">
          <p>• 基于预加载的 <strong>6,254 篇</strong> 磷酸铁锂文献</p>
          <p>• 支持知识图谱、文献检索、社区分析</p>
          <p>• 自动识别 DOI 并加载原文</p>
        </div>
      </div>

      <!-- 对话历史列表 -->
      <div class="chat-history">
        <div v-if="store.chats.length === 0" class="empty-history" style="padding:20px;text-align:center;color:#9ca3af;">
          暂无对话
        </div>
        <div 
          v-for="chat in store.chats" 
          :key="chat.id"
          class="history-item"
          :class="{ active: chat.id === store.currentChatId }"
          @click="switchChat(chat.id)"
        >
          <div>
            <div class="history-title">{{ chat.title }}</div>
            <div class="history-time">{{ formatTime(chat.createdAt) }}</div>
          </div>
          <button class="history-delete" @click.stop="deleteChat(chat.id)">🗑️</button>
        </div>
      </div>
    </aside>

    <!-- 主聊天区 -->
    <main class="main-chat">
      <!-- 头部 -->
      <header class="chat-header">
        <div class="ai-icon">✨</div>
        <div class="header-title">
          <h1>磷酸铁锂知识图谱 AI</h1>
          <div class="kb-info">{{ kbInfoText }}</div>
        </div>
      </header>

      <!-- 消息区域 -->
      <div class="messages-area" ref="messagesArea">
        <template v-if="!hasMessages">
          <div class="empty-state">
            <div class="empty-icon">🔋</div>
            <div class="empty-title">你好！我是磷酸铁锂材料专家</div>
            <div>请提出您的问题</div>
          </div>
        </template>
        
        <template v-else>
          <div 
            v-for="(msg, index) in store.currentMessages" 
            :key="index"
            class="message"
            :class="'message-' + msg.role"
          >
            <template v-if="msg.role === 'user'">
              <div class="message-content">{{ msg.content }}</div>
            </template>
            
            <template v-else-if="msg.role === 'bot'">
              <div class="bot-avatar">✨</div>
              <div class="message-content">
                <div v-if="msg.queryMode" class="query-mode-badge">{{ msg.queryMode }}</div>
                <div v-if="msg.content" v-html="formatAnswer(msg.content, msg.referenceLinks)"></div>
                <div v-else class="loading-animation">
                  <div class="loading-spinner">
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                  </div>
                  <span>思考中...</span>
                </div>
              </div>
            </template>
            
            <template v-else-if="msg.type === 'system'">
              <div style="text-align:center;color:#6b7280;font-size:13px;margin:15px 0;">
                {{ msg.content }}
              </div>
            </template>
          </div>
        </template>
      </div>

      <!-- 输入区域 -->
      <div class="input-area">
        <div class="input-wrapper">
          <textarea
            v-model="inputMessage"
            placeholder="问我任何关于磷酸铁锂的问题..."
            rows="1"
            ref="inputTextarea"
            @keydown.enter.prevent="sendMessage"
            @input="autoResize($event)"
          ></textarea>
          <button 
            class="send-btn" 
            :disabled="!canSend"
            @click="sendMessage"
          >
            {{ store.isStreaming ? '⏹' : '➤' }}
          </button>
        </div>
      </div>
    </main>

    <!-- PDF 阅读器组件 -->
    <PdfReader ref="pdfReader" />
  </div>
</template>
