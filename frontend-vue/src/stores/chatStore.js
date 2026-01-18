import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '../services/api'

export const useChatStore = defineStore('chat', () => {
  // 状态
  const chats = ref([])
  const currentChatId = ref(null)
  const isStreaming = ref(false)
  const kbInfo = ref({ loading: true, size: 0 })
  const userId = ref(null)
  const syncStatus = ref('synced') // synced/syncing/failed

  // 计算属性
  const currentChat = computed(() => 
    chats.value.find(c => c.id === currentChatId.value)
  )

  const currentMessages = computed(() => 
    currentChat.value?.messages || []
  )

  // ==================== 用户管理 ====================
  
  function setUserId(id) {
    userId.value = id
    localStorage.setItem('lfp_user_id', id)
  }

  function getUserId() {
    if (!userId.value) {
      const saved = localStorage.getItem('lfp_user_id')
      if (saved) {
        userId.value = parseInt(saved)
      }
    }
    return userId.value
  }

  // ==================== 对话加载（服务器优先）====================
  
  async function loadChats() {
    const uid = getUserId()
    
    if (uid) {
      // 尝试从服务器加载
      try {
        syncStatus.value = 'syncing'
        const response = await api.getConversationList(uid)
        
        if (response.conversations) {
          // 转换服务器数据格式为前端格式
          chats.value = response.conversations.map(conv => ({
            id: conv.id.toString(),
            title: conv.title,
            messages: [], // 消息按需加载
            createdAt: conv.created_at,
            updatedAt: conv.updated_at,
            messageCount: conv.message_count,
            synced: true
          }))
          
          // 同步到 localStorage
          saveChats()
          syncStatus.value = 'synced'
          return
        }
      } catch (e) {
        console.error('从服务器加载对话失败:', e)
        syncStatus.value = 'failed'
      }
    }
    
    // 降级到 localStorage
    const saved = localStorage.getItem('lfp_chats')
    if (saved) {
      try {
        chats.value = JSON.parse(saved)
      } catch (e) {
        chats.value = []
      }
    }
  }

  // ==================== 对话管理 ====================
  
  function saveChats() {
    localStorage.setItem('lfp_chats', JSON.stringify(chats.value))
  }

  async function createNewChat() {
    // 总是先在本地创建对话，不立即同步到服务器
    // 只有当用户第一次发送消息时才会创建服务器对话
    const chat = {
      id: Date.now().toString(),
      title: '新对话',
      messages: [],
      createdAt: new Date(),
      synced: false  // 标记为未同步
    }
    chats.value.unshift(chat)
    currentChatId.value = chat.id
    saveChats()
    return chat
  }

  async function switchChat(chatId) {
    currentChatId.value = chatId
    const chat = chats.value.find(c => c.id === chatId)
    
    console.log('[switchChat] 切换到对话:', chatId, 'synced:', chat?.synced, 'messageCount:', chat?.messageCount)
    
    // 如果是服务器同步的对话，总是从服务器加载最新消息
    if (chat && chat.synced) {
      const uid = getUserId()
      if (uid) {
        try {
          console.log('[switchChat] 从服务器加载对话详情...')
          const response = await api.getConversationDetail(parseInt(chat.id), uid)
          console.log('[switchChat] 服务器返回:', response)
          console.log('[switchChat] 消息数量:', response.messages?.length)
          
          if (response.messages) {
            // 使用 Vue 3 的响应式方式更新数组
            chat.messages = [...response.messages]
            chat.messageCount = response.messages.length
            saveChats()
            console.log('[switchChat] 消息已更新到 chat.messages, 当前消息数:', chat.messages.length)
          }
        } catch (e) {
          console.error('[switchChat] 加载对话详情失败:', e)
          // 如果加载失败，尝试使用本地缓存的消息
          if (!chat.messages || chat.messages.length === 0) {
            chat.messages = []
          }
        }
      }
    }
  }

  async function deleteChat(chatId) {
    const chat = chats.value.find(c => c.id === chatId)
    const uid = getUserId()
    
    if (chat && chat.synced && uid) {
      // 服务器删除
      try {
        await api.deleteConversation(parseInt(chat.id), uid)
      } catch (e) {
        console.error('删除对话失败:', e)
      }
    }
    
    // 本地删除
    const index = chats.value.findIndex(c => c.id === chatId)
    if (index > -1) {
      chats.value.splice(index, 1)
      if (chatId === currentChatId.value) {
        currentChatId.value = chats.value[0]?.id || null
      }
      saveChats()
    }
  }

  function clearAllChats() {
    chats.value = []
    currentChatId.value = null
    saveChats()
  }

  // ==================== 消息管理 ====================
  
  async function addUserMessage(content) {
    if (!currentChat.value) return
    
    const uid = getUserId()
    
    // 如果是第一次发送消息且对话未同步，先在服务器创建对话
    if (!currentChat.value.synced && currentChat.value.messages.length === 0 && uid) {
      try {
        syncStatus.value = 'syncing'
        const title = content.substring(0, 30) + (content.length > 30 ? '...' : '')
        const response = await api.createConversation(uid, title)
        
        // 更新本地对话信息
        currentChat.value.id = response.conversation_id.toString()
        currentChat.value.title = response.title || title
        currentChat.value.createdAt = response.created_at
        currentChat.value.updatedAt = response.updated_at
        currentChat.value.synced = true
        
        console.log('[addUserMessage] 首次发送消息，创建服务器对话:', currentChat.value.id)
        syncStatus.value = 'synced'
      } catch (e) {
        console.error('创建服务器对话失败:', e)
        syncStatus.value = 'failed'
        // 即使创建失败，也继续添加消息到本地
      }
    }
    
    const message = {
      role: 'user',
      content,
      timestamp: new Date()
    }
    
    currentChat.value.messages.push(message)
    
    // 自动生成标题（如果还没有自定义标题）
    if (currentChat.value.messages.length === 1 && currentChat.value.title === '新对话') {
      currentChat.value.title = content.substring(0, 30) + (content.length > 30 ? '...' : '')
    }
    
    saveChats()
    
    // 同步到服务器（如果对话已经同步）
    if (uid && currentChat.value.synced) {
      try {
        await api.addMessage(parseInt(currentChat.value.id), uid, message)
      } catch (e) {
        console.error('同步用户消息失败:', e)
        currentChat.value.synced = false
      }
    }
  }

  async function addBotMessage(message) {
    if (!currentChat.value) return
    
    const botMessage = {
      role: 'bot',
      ...message,
      timestamp: new Date()
    }
    
    currentChat.value.messages.push(botMessage)
    saveChats()
    
    // 注意：不在这里同步到服务器，因为消息可能还不完整
    // 等流式响应完成后，由 ask_stream 接口自动保存完整消息
  }

  function updateLastBotMessage(updates) {
    if (!currentChat.value || currentChat.value.messages.length === 0) return
    const last = currentChat.value.messages[currentChat.value.messages.length - 1]
    if (last.role === 'bot') {
      Object.assign(last, updates)
      saveChats()
      // 注意：不在这里同步，由后端 ask_stream 统一处理
    }
  }
  
  // 新增：同步完整的 bot 消息到服务器（在流式响应完成后调用）
  async function syncLastBotMessage() {
    if (!currentChat.value || currentChat.value.messages.length === 0) return
    const last = currentChat.value.messages[currentChat.value.messages.length - 1]
    
    if (last.role === 'bot' && last.content) {
      const uid = getUserId()
      if (uid && currentChat.value.synced) {
        try {
          await api.addMessage(parseInt(currentChat.value.id), uid, last)
        } catch (e) {
          console.error('同步AI消息失败:', e)
          currentChat.value.synced = false
        }
      }
    }
  }
  function updateLastBotMessage(updates) {
    if (!currentChat.value || currentChat.value.messages.length === 0) return
    const last = currentChat.value.messages[currentChat.value.messages.length - 1]
    if (last.role === 'bot') {
      Object.assign(last, updates)
      saveChats()
      // 注意：不在这里同步，由后端 ask_stream 统一处理
    }
  }

  // ==================== 其他 ====================
  
  function setStreaming(value) {
    isStreaming.value = value
  }

  function setKbInfo(info) {
    kbInfo.value = info
  }

  return {
    chats,
    currentChatId,
    currentChat,
    currentMessages,
    isStreaming,
    kbInfo,
    userId,
    syncStatus,
    setUserId,
    getUserId,
    loadChats,
    saveChats,
    createNewChat,
    switchChat,
    deleteChat,
    clearAllChats,
    addUserMessage,
    addBotMessage,
    updateLastBotMessage,
    syncLastBotMessage,
    setStreaming,
    setKbInfo
  }
})
