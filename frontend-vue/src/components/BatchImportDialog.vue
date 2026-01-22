<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  show: Boolean
})

const emit = defineEmits(['close', 'import-success'])

const selectedFile = ref(null)
const isDragging = ref(false)
const uploading = ref(false)
const error = ref('')

const fileInput = ref(null)

// 文件信息
const fileInfo = computed(() => {
  if (!selectedFile.value) return null
  return {
    name: selectedFile.value.name,
    size: formatFileSize(selectedFile.value.size),
    type: selectedFile.value.name.split('.').pop().toLowerCase()
  }
})

// 格式化文件大小
function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

// 验证文件
function validateFile(file) {
  error.value = ''
  
  // 检查文件类型
  const ext = file.name.split('.').pop().toLowerCase()
  if (!['xlsx', 'csv'].includes(ext)) {
    error.value = '只支持 .xlsx 和 .csv 格式的文件'
    return false
  }
  
  // 检查文件大小（5MB）
  const maxSize = 5 * 1024 * 1024
  if (file.size > maxSize) {
    error.value = '文件大小不能超过 5MB'
    return false
  }
  
  return true
}

// 文件选择
function handleFileSelect(event) {
  const file = event.target.files[0]
  if (file && validateFile(file)) {
    selectedFile.value = file
  }
}

// 点击选择文件
function triggerFileSelect() {
  fileInput.value.click()
}

// 拖拽事件
function handleDragOver(event) {
  event.preventDefault()
  isDragging.value = true
}

function handleDragLeave() {
  isDragging.value = false
}

function handleDrop(event) {
  event.preventDefault()
  isDragging.value = false
  
  const file = event.dataTransfer.files[0]
  if (file && validateFile(file)) {
    selectedFile.value = file
  }
}

// 下载模板
async function downloadTemplate(format) {
  try {
    const token = localStorage.getItem('token')
    const response = await fetch(`/api/admin/users/import-template?format=${format}`, {
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
  } catch (err) {
    error.value = err.message || '下载模板失败'
  }
}

// 开始导入
async function startImport() {
  if (!selectedFile.value) {
    error.value = '请先选择文件'
    return
  }
  
  uploading.value = true
  error.value = ''
  
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    
    const token = localStorage.getItem('token')
    const response = await fetch('/api/admin/users/batch-import', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    })
    
    const result = await response.json()
    
    if (result.success) {
      emit('import-success', result.data)
      close()
    } else {
      error.value = result.error || '导入失败'
    }
  } catch (err) {
    error.value = err.message || '导入失败，请稍后重试'
  } finally {
    uploading.value = false
  }
}

// 关闭对话框
function close() {
  selectedFile.value = null
  error.value = ''
  emit('close')
}
</script>

<template>
  <div v-if="show" class="modal-overlay" @click.self="close">
    <div class="modal">
      <div class="modal-header">
        <h3>批量导入用户</h3>
        <button class="close-btn" @click="close">×</button>
      </div>

      <div class="modal-body">
        <!-- 错误提示 -->
        <div v-if="error" class="alert alert-error">{{ error }}</div>

        <!-- 模板下载 -->
        <div class="template-section">
          <p class="section-title">第一步：下载导入模板</p>
          <div class="template-buttons">
            <button class="template-btn" @click="downloadTemplate('xlsx')">
              <span class="icon">📊</span>
              下载 Excel 模板
            </button>
            <button class="template-btn" @click="downloadTemplate('csv')">
              <span class="icon">📄</span>
              下载 CSV 模板
            </button>
          </div>
          <p class="hint">模板包含示例数据，请按照格式填写用户信息</p>
        </div>

        <!-- 文件上传 -->
        <div class="upload-section">
          <p class="section-title">第二步：上传填写好的文件</p>
          
          <div 
            class="upload-area" 
            :class="{ 'dragging': isDragging, 'has-file': selectedFile }"
            @dragover="handleDragOver"
            @dragleave="handleDragLeave"
            @drop="handleDrop"
            @click="triggerFileSelect"
          >
            <input 
              ref="fileInput" 
              type="file" 
              accept=".xlsx,.csv" 
              @change="handleFileSelect"
              style="display: none"
            >
            
            <div v-if="!selectedFile" class="upload-placeholder">
              <span class="upload-icon">📁</span>
              <p class="upload-text">点击选择文件或拖拽文件到此处</p>
              <p class="upload-hint">支持 .xlsx 和 .csv 格式，最大 5MB</p>
            </div>
            
            <div v-else class="file-info-display">
              <span class="file-icon">📄</span>
              <div class="file-details">
                <p class="file-name">{{ fileInfo.name }}</p>
                <p class="file-meta">{{ fileInfo.size }} · {{ fileInfo.type.toUpperCase() }}</p>
              </div>
              <button class="remove-file-btn" @click.stop="selectedFile = null">×</button>
            </div>
          </div>
        </div>

        <!-- 导入说明 -->
        <div class="info-section">
          <p class="info-title">📌 导入说明：</p>
          <ul class="info-list">
            <li>文件必须包含三列：username（用户名）、password（密码）、user_type（用户身份）</li>
            <li>用户身份只能是 <code>super</code>（超级用户）或 <code>common</code>（普通用户）</li>
            <li>用户名长度 3-50 字符，不能以 admin 开头</li>
            <li>密码长度不少于 6 位</li>
            <li>单次最多导入 1000 条记录</li>
          </ul>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn-secondary" @click="close" :disabled="uploading">取消</button>
        <button 
          class="btn-primary" 
          @click="startImport" 
          :disabled="!selectedFile || uploading"
        >
          <span v-if="uploading">导入中...</span>
          <span v-else>开始导入</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 12px;
  width: 100%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h3 {
  font-size: 18px;
  color: #1f2937;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 28px;
  color: #9ca3af;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
}

.close-btn:hover {
  background: #f3f4f6;
  color: #374151;
}

.modal-body {
  padding: 24px;
}

.alert {
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.alert-error {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}

.template-section,
.upload-section,
.info-section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin: 0 0 12px 0;
}

.template-buttons {
  display: flex;
  gap: 12px;
}

.template-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #374151;
  transition: all 0.2s;
}

.template-btn:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
}

.template-btn .icon {
  font-size: 18px;
}

.hint {
  font-size: 12px;
  color: #6b7280;
  margin: 8px 0 0 0;
}

.upload-area {
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: #fafafa;
}

.upload-area:hover {
  border-color: #667eea;
  background: #f9fafb;
}

.upload-area.dragging {
  border-color: #667eea;
  background: #eef2ff;
}

.upload-area.has-file {
  padding: 16px;
  background: #f9fafb;
  border-style: solid;
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-icon {
  font-size: 48px;
}

.upload-text {
  font-size: 14px;
  color: #374151;
  margin: 0;
}

.upload-hint {
  font-size: 12px;
  color: #6b7280;
  margin: 0;
}

.file-info-display {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-icon {
  font-size: 32px;
}

.file-details {
  flex: 1;
  text-align: left;
}

.file-name {
  font-size: 14px;
  color: #1f2937;
  margin: 0 0 4px 0;
  font-weight: 500;
}

.file-meta {
  font-size: 12px;
  color: #6b7280;
  margin: 0;
}

.remove-file-btn {
  background: #fee2e2;
  border: none;
  color: #dc2626;
  font-size: 20px;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.remove-file-btn:hover {
  background: #fecaca;
}

.info-section {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 16px;
}

.info-title {
  font-size: 13px;
  font-weight: 500;
  color: #1e40af;
  margin: 0 0 8px 0;
}

.info-list {
  margin: 0;
  padding-left: 20px;
  font-size: 12px;
  color: #1e40af;
  line-height: 1.6;
}

.info-list code {
  background: #dbeafe;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 11px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #e5e7eb;
}

.btn-primary,
.btn-secondary {
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #5a67d8;
}

.btn-primary:disabled {
  background: #d1d5db;
  cursor: not-allowed;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
}

.btn-secondary:hover:not(:disabled) {
  background: #e5e7eb;
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
