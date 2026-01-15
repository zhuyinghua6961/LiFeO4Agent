<template>
  <div v-if="isOpen" class="pdf-reader-modal">
    <div class="pdf-reader-overlay" @click="closeReader"></div>
    <div class="pdf-reader-container">
      <!-- 头部 -->
      <div class="pdf-reader-header">
        <div>
          <h2>📄 原文阅读器（增强版）</h2>
          <p class="doi-text">DOI: {{ currentDoi }}</p>
        </div>
        <div class="header-actions">
          <button class="pdf-action-btn" @click="toggleTranslationPanel" title="显示/隐藏翻译面板">
            🌐 翻译面板
          </button>
          <button class="pdf-close-btn" @click="closeReader">✕</button>
        </div>
      </div>

      <!-- PDF查看区 -->
      <div class="pdf-viewer-layout">
        <!-- 左侧PDF -->
        <div class="pdf-viewer-left">
          <div class="pdf-canvas-wrapper" @mouseup="handleTextSelection">
            <!-- PDF错误提示 -->
            <div v-if="pdfError" class="pdf-error-container">
              <div class="pdf-error-content">
                <div class="error-icon">⚠️</div>
                <h3>{{ pdfError.message }}</h3>
                <p class="error-doi">DOI: {{ pdfError.doi }}</p>
                <div class="error-actions">
                  <a 
                    :href="`https://doi.org/${pdfError.doi}`" 
                    target="_blank" 
                    class="online-view-btn"
                  >
                    🌐 在线查看文献
                  </a>
                  <button @click="closeReader" class="close-error-btn">关闭</button>
                </div>
              </div>
            </div>
            
            <!-- PDF iframe -->
            <iframe 
              v-else-if="pdfUrl"
              :src="pdfUrl" 
              class="pdf-iframe"
              frameborder="0"
            ></iframe>
            
            <!-- 加载中 -->
            <div v-else class="pdf-loading">
              <div class="loading-spinner"></div>
              <p>加载PDF中...</p>
            </div>
          </div>
        </div>

        <!-- 右侧翻译面板 -->
        <div v-show="showTranslationPanel" class="translation-panel">
          <div class="translation-panel-header">
            <h3>🌐 翻译助手</h3>
            <p>选中文本后点击翻译按钮</p>
          </div>

          <div class="translation-panel-content">
            <!-- 欢迎页 -->
            <div v-if="translations.length === 0" class="translation-welcome">
              <div class="welcome-icon">📖</div>
              <p class="welcome-title">欢迎使用翻译助手</p>
              <p class="welcome-desc">在PDF中选中文本，然后点击"翻译选中文本"按钮</p>
            </div>

            <!-- 翻译历史 -->
            <div v-for="(item, index) in translations" :key="index" class="translation-item">
              <div class="translation-item-header">
                <span class="translation-time">{{ item.time }}</span>
              </div>
              <div class="translation-item-content">
                <div class="translation-source">
                  <div class="lang-label">🇬🇧 英文</div>
                  <div class="text-content">{{ item.source }}</div>
                </div>
                <div class="translation-target">
                  <div class="lang-label">🇨🇳 中文</div>
                  <div class="text-content" :class="{ loading: item.loading }">
                    {{ item.loading ? '翻译中...' : item.translation }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 翻译按钮 -->
          <div class="translation-actions">
            <button 
              class="translate-btn" 
              :disabled="!selectedText || isTranslating"
              @click="translateSelected"
            >
              {{ isTranslating ? '⏳ 翻译中...' : '🌐 翻译选中文本' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { api } from '../services/api'

// Props & Emits
const emit = defineEmits(['close'])

// State
const isOpen = ref(false)
const currentDoi = ref('')
const pdfUrl = ref('')
const pdfError = ref(null)
const showTranslationPanel = ref(true)
const selectedText = ref('')
const translations = ref([])
const isTranslating = ref(false)

// Methods
function openReader(doi) {
  currentDoi.value = doi
  pdfUrl.value = `/api/pdf/${doi.replace(/\//g, '_')}.pdf`
  pdfError.value = null
  isOpen.value = true
  translations.value = []
  selectedText.value = ''
  
  // 检测PDF是否存在
  fetch(pdfUrl.value, { method: 'HEAD' })
    .then(response => {
      if (!response.ok) {
        pdfError.value = {
          message: '本地PDF文件不存在',
          doi: currentDoi.value
        }
        pdfUrl.value = ''
      }
    })
    .catch(() => {
      pdfError.value = {
        message: '本地PDF文件不存在',
        doi: currentDoi.value
      }
      pdfUrl.value = ''
    })
}

function closeReader() {
  isOpen.value = false
  currentDoi.value = ''
  pdfUrl.value = ''
  pdfError.value = null
  emit('close')
}

function toggleTranslationPanel() {
  showTranslationPanel.value = !showTranslationPanel.value
}

function handleTextSelection() {
  setTimeout(() => {
    const selection = window.getSelection()
    const text = selection?.toString().trim()
    if (text && text.length > 0) {
      selectedText.value = text
    }
  }, 100)
}

async function translateSelected() {
  if (!selectedText.value || isTranslating.value) return

  isTranslating.value = true

  // 添加翻译项
  const item = {
    time: new Date().toLocaleTimeString(),
    source: selectedText.value,
    translation: '',
    loading: true
  }
  translations.value.unshift(item)

  try {
    const result = await api.translate([selectedText.value])
    if (result.success && result.translations.length > 0) {
      item.translation = result.translations[0]
    } else {
      item.translation = '翻译失败'
    }
  } catch (error) {
    console.error('翻译错误:', error)
    item.translation = '翻译失败: ' + error.message
  } finally {
    item.loading = false
    isTranslating.value = false
  }
}

// Expose methods
defineExpose({
  openReader,
  closeReader
})
</script>

<style scoped>
.pdf-reader-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pdf-reader-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
}

.pdf-reader-container {
  position: relative;
  width: 95vw;
  height: 95vh;
  background: white;
  border-radius: 16px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(50px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.pdf-reader-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 30px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.pdf-reader-header h2 {
  margin: 0;
  font-size: 20px;
}

.doi-text {
  font-size: 13px;
  opacity: 0.9;
  margin: 5px 0 0 0;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.pdf-action-btn {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.pdf-action-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
}

.pdf-close-btn {
  padding: 8px 16px;
  background: rgba(239, 68, 68, 0.9);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 18px;
  font-weight: bold;
  transition: all 0.2s;
}

.pdf-close-btn:hover {
  background: rgba(220, 38, 38, 1);
}

.pdf-viewer-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.pdf-viewer-left {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f3f4f6;
}

.pdf-canvas-wrapper {
  flex: 1;
  position: relative;
  overflow: auto;
}

.pdf-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.pdf-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #6b7280;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e5e7eb;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.translation-panel {
  width: 400px;
  display: flex;
  flex-direction: column;
  background: white;
  border-left: 1px solid #e5e7eb;
}

.translation-panel-header {
  padding: 20px;
  border-bottom: 1px solid #e5e7eb;
  background: #f9fafb;
}

.translation-panel-header h3 {
  margin: 0 0 8px 0;
  font-size: 16px;
  color: #374151;
}

.translation-panel-header p {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
}

.translation-panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.translation-welcome {
  text-align: center;
  padding: 60px 20px;
  color: #9ca3af;
}

.welcome-icon {
  font-size: 64px;
  margin-bottom: 20px;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.welcome-title {
  font-size: 18px;
  font-weight: 600;
  color: #6b7280;
  margin: 0 0 10px 0;
}

.welcome-desc {
  font-size: 14px;
  margin: 0;
}

.translation-item {
  margin-bottom: 20px;
  padding: 15px;
  background: #f9fafb;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  animation: slideInRight 0.4s ease-out;
}

@keyframes slideInRight {
  from {
    opacity: 0;
    transform: translateX(20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.translation-item-header {
  font-size: 12px;
  color: #9ca3af;
  margin-bottom: 12px;
}

.translation-item-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.translation-source,
.translation-target {
  padding: 12px;
  background: white;
  border-radius: 8px;
}

.lang-label {
  font-size: 12px;
  font-weight: 600;
  color: #667eea;
  margin-bottom: 8px;
}

.translation-target .lang-label {
  color: #10b981;
}

/* PDF错误提示样式 */
.pdf-error-container {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f9fafb;
}

.pdf-error-content {
  text-align: center;
  padding: 40px;
  max-width: 500px;
}

.error-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.pdf-error-content h3 {
  font-size: 20px;
  color: #374151;
  margin: 0 0 12px 0;
}

.error-doi {
  font-size: 14px;
  color: #6b7280;
  margin: 0 0 24px 0;
  font-family: monospace;
  background: white;
  padding: 8px 12px;
  border-radius: 6px;
  display: inline-block;
}

.error-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.online-view-btn,
.close-error-btn {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.online-view-btn {
  background: #667eea;
  color: white;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.online-view-btn:hover {
  background: #5568d3;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.close-error-btn {
  background: #e5e7eb;
  color: #374151;
}

.close-error-btn:hover {
  background: #d1d5db;
}

.text-content {
  font-size: 14px;
  line-height: 1.6;
  color: #374151;
  word-wrap: break-word;
}

.text-content.loading {
  color: #9ca3af;
  font-style: italic;
}

.translation-actions {
  padding: 20px;
  border-top: 1px solid #e5e7eb;
  background: #f9fafb;
}

.translate-btn {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.translate-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
}

.translate-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
