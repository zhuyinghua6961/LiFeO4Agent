# 批量清洗 Markdown 文件

## 概述

`batch_clean_markdown.py` 是一个批处理脚本，用于批量清洗 Marker 输出的 Markdown 文件。它使用增强版的 `MarkdownCleaner` 进行深度清洗，解决以下问题：

- ✅ 硬换行合并（"LiFePO4\ncathode" → "LiFePO4 cathode"）
- ✅ 引用噪音去除（"possible. 1-3 Li-ion" → "possible. Li-ion"）
- ✅ OCR 错误修复（"Lilean" → "Li-lean"）
- ✅ 图注和页眉页脚删除
- ✅ HTML 标签清理

## 使用方法

### 基本用法

```bash
# 批量清洗所有 Marker 输出的 Markdown 文件
conda run -n agent python qwen2.5B/batch_clean_markdown.py
```

### 自定义参数

```bash
# 指定输入输出目录
conda run -n agent python qwen2.5B/batch_clean_markdown.py \
    --input-dir marker_service/outputs \
    --output-dir qwen2.5B/output/cleaned

# 指定文件匹配模式
conda run -n agent python qwen2.5B/batch_clean_markdown.py \
    --pattern "*.md"
```

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--input-dir` | `marker_service/outputs` | Marker 输出目录 |
| `--output-dir` | `qwen2.5B/output/cleaned` | 清洗后文件保存目录 |
| `--pattern` | `*.md` | 文件匹配模式 |

## 输出

### 文件命名

清洗后的文件会添加 `_cleaned` 后缀：
- 输入：`paper.md`
- 输出：`paper_cleaned.md`

### 统计报告

脚本会在处理完成后显示统计报告：

```
================================================================================
📊 批量清洗完成！
================================================================================
✅ 成功: 100 个文件
❌ 失败: 0 个文件
📝 总共删除引用: 1234 个
🔗 总共合并硬换行: 567 处
🔧 总共修复 OCR 错误: 89 处
================================================================================

💾 清洗后的文件保存在: /path/to/qwen2.5B/output/cleaned
```

## 清洗效果示例

### 原始文本（Marker 输出）

```markdown
... the as-fabricated Li-lean anode allows the cell to match with LiFePO4
cathode with excellent cyclic stability. 1-3 Li-ion batteries ...
```

### 清洗后文本

```markdown
... the as-fabricated Li-lean anode allows the cell to match with LiFePO4 cathode with excellent cyclic stability. Li-ion batteries ...
```

## 注意事项

1. **环境要求**：必须在 `agent` conda 环境下运行
2. **输入文件**：确保 Marker 已经处理完 PDF 文件
3. **输出目录**：会自动创建，无需手动创建
4. **文件覆盖**：如果输出文件已存在，会被覆盖

## 集成到重建流程

批量清洗是向量数据库重建流程的第一步：

```bash
# 步骤 1: 批量清洗 Markdown
conda run -n agent python qwen2.5B/batch_clean_markdown.py

# 步骤 2: 重建 Chunk 数据库
conda run -n agent python rebuild_vector_db/rebuild_chunks.py \
    --input-dir qwen2.5B/output/cleaned \
    --output-db ./chroma_chunks_v2

# 步骤 3: 重建句子数据库
conda run -n agent python rebuild_vector_db/rebuild_sentences.py \
    --input-dir qwen2.5B/output/cleaned \
    --output-db ./chroma_sentences_v2
```

## 故障排除

### 问题：找不到 .md 文件

**解决方案**：检查输入目录是否正确，确保 Marker 已经处理完 PDF 文件。

### 问题：导入错误

**解决方案**：确保在 `agent` conda 环境下运行：
```bash
conda activate agent
python qwen2.5B/batch_clean_markdown.py
```

### 问题：处理失败

**解决方案**：查看错误信息，单个文件失败不会影响其他文件的处理。
