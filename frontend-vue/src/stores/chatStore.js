import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useChatStore = defineStore('chat', () => {
  // 状态
  const chats = ref([])
  const currentChatId = ref(null)
  const isStreaming = ref(false)
  const kbInfo = ref({ loading: true, size: 0 })

  // 计算属性
  const currentChat = computed(() => 
    chats.value.find(c => c.id === currentChatId.value)
  )

  const currentMessages = computed(() => 
    currentChat.value?.messages || []
  )

  // Actions
  function loadChats() {
    const saved = localStorage.getItem('lfp_chats')
    if (saved) {
      try {
        chats.value = JSON.parse(saved)
      } catch (e) {
        chats.value = []
      }
    }
  }

  function saveChats() {
    localStorage.setItem('lfp_chats', JSON.stringify(chats.value))
  }

  function createNewChat() {
    const chat = {
      id: Date.now().toString(),
      title: '新对话',
      messages: [],
      createdAt: new Date()
    }
    chats.value.unshift(chat)
    currentChatId.value = chat.id
    saveChats()
    return chat
  }

  function switchChat(chatId) {
    currentChatId.value = chatId
  }

  function deleteChat(chatId) {
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

  function addUserMessage(content) {
    if (!currentChat.value) return
    currentChat.value.messages.push({
      role: 'user',
      content,
      timestamp: new Date()
    })
    if (currentChat.value.messages.length === 1) {
      currentChat.value.title = content.substring(0, 30) + (content.length > 30 ? '...' : '')
    }
    saveChats()
  }

  function addBotMessage(message) {
    if (!currentChat.value) return
    currentChat.value.messages.push({
      role: 'bot',
      ...message,
      timestamp: new Date()
    })
    saveChats()
  }

  function updateLastBotMessage(updates) {
    if (!currentChat.value || currentChat.value.messages.length === 0) return
    const last = currentChat.value.messages[currentChat.value.messages.length - 1]
    if (last.role === 'bot') {
      Object.assign(last, updates)
      saveChats()
    }
  }

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
    loadChats,
    saveChats,
    createNewChat,
    switchChat,
    deleteChat,
    clearAllChats,
    addUserMessage,
    addBotMessage,
    updateLastBotMessage,
    setStreaming,
    setKbInfo
  }
})
