// 工具函数

import { marked } from 'marked'

// 格式化时间
export function formatTime(date) {
  const d = new Date(date)
  const now = new Date()
  const diff = now - d
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
  return d.toLocaleDateString()
}

// 格式化答案 - Markdown 渲染
export function formatAnswer(text, referenceSnippets = []) {
  if (!text) return ''
  
  // 预处理 LaTeX 和 DOI
  text = cleanLaTeX(text)
  text = linkifyDOI(text, referenceSnippets)
  
  // 使用 marked 渲染 Markdown
  try {
    return marked.parse(text, { breaks: true, gfm: true, tables: true })
  } catch (e) {
    return text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  }
}

// 清理 LaTeX 公式
function cleanLaTeX(text) {
  text = text.replace(/\\\[[\s\S]*?\\\]/g, m => cleanLaTeXCommands(m.replace(/\\\[|\]/g, '')))
  text = text.replace(/\$\$[\s\S]*?\$\$/g, m => cleanLaTeXCommands(m.replace(/\$\$/g, '')))
  text = text.replace(/\\\([\s\S]*?\\\)/g, m => cleanLaTeXCommands(m.replace(/\\\(|\\\)/g, '')))
  text = text.replace(/\$[^$]+\$/g, m => cleanLaTeXCommands(m.replace(/\$/g, '')))
  return text
}

// 清理 LaTeX 命令
function cleanLaTeXCommands(text) {
  const subs = {'0':'₀','1':'₁','2':'₂','3':'₃','4':'₄','5':'₅','6':'₆','7':'₇','8':'₈','9':'₉'}
  const sups = {'0':'⁰','1':'¹','2':'²','3':'³','4':'⁴','5':'⁵','6':'⁶','7':'⁷','8':'⁸','9':'⁹'}
  
  text = text.replace(/_(\d+)/g, m => m.slice(1).split('').map(c => subs[c] || c).join(''))
  text = text.replace(/\^(\d+)/g, m => m.slice(1).split('').map(c => sups[c] || c).join(''))
  text = text.replace(/\\rightarrow/g, '→').replace(/\\leftarrow/g, '←')
  text = text.replace(/\\Rightarrow/g, '⇐').replace(/\\Leftarrow/g, '⇒')
  text = text.replace(/\\[a-zA-Z]+\{([^}]+)\}/g, '$1')
  text = text.replace(/\\[a-zA-Z]+/g, '')
  return text.trim()
}

// DOI 转为可点击链接
function linkifyDOI(text, referenceLinks = []) {
  // 处理新格式: （doi:10.xxx）· 查看原文
  text = text.replace(/（doi:([^\s）]+)）\s*·\s*查看原文/g, (match, doi) => {
    const safeDoi = doi.replace(/"/g, '')
    return `(<a href="#" class="doi-link" data-doi="${safeDoi}" onclick="window.openPdfFromDoi('${safeDoi}'); return false;">doi=${safeDoi}</a> · <a href="#" class="view-original-link" data-doi="${safeDoi}" onclick="window.openPdfFromDoi('${safeDoi}'); return false;">查看原文</a>)`
  })
  
  // 处理旧格式: (doi=10.xxx)
  text = text.replace(/\(doi=([^\s\)]+)\)/gi, (match, doi) => {
    const safeDoi = doi.replace(/"/g, '')
    return `(<a href="#" class="doi-link" data-doi="${safeDoi}" onclick="window.openPdfFromDoi('${safeDoi}'); return false;">doi=${safeDoi}</a>)`
  })
  
  // 新增: 识别表格和文本中的纯DOI文本 (10.xxxx/xxxxx)
  // 避免在HTML标签和已经处理过的链接中重复处理
  text = text.replace(/(?<!href="|data-doi="|doi=)\b(10\.\d{4,}[\w\.\/-]+[\w\/-])(?!")/g, (match, doi) => {
    // 检查是否在HTML标签中
    const beforeMatch = text.substring(0, text.indexOf(match))
    const lastTagStart = beforeMatch.lastIndexOf('<')
    const lastTagEnd = beforeMatch.lastIndexOf('>')
    
    // 如果在HTML标签内部,不处理
    if (lastTagStart > lastTagEnd) {
      return match
    }
    
    const safeDoi = doi.replace(/"/g, '')
    return `<a href="#" class="doi-link" data-doi="${safeDoi}" onclick="window.openPdfFromDoi('${safeDoi}'); return false;">${doi}</a>`
  })
  
  return text
}

// HTML 转义
export function escapeHtml(text) {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}
