# 向量数据库构建规范 V3.0（务实版）

## 文档说明

**版本**: V3.0  
**更新日期**: 2024-01-19  
**设计原则**: 基于实际RAG流程，务实优先，渐进式实施

---

## 1. 核心元数据结构（V3.0）

### 1.1 完整字段定义

```python
metadata = {
    # === 核心标识（3个字段）===
    "document_id": str,              # 文档唯一ID（SHA256）
    "doi": str,                      # DOI标识符
    "filename": str,                 # PDF文件名
    
    # === 层级定位（5个字段）⭐ 高亮功能核心 ===
    "chunk_id": str,                 # 段落UUID
    "chunk_index_global": int,       # 全文序号（从0开始）
    "page": int,                     # 页码（从1开始）
    "chunk_index_in_page": int,      # 页内序号（从0开始）⭐
    "total_chunks_in_page": int,     # 该页总数 ⭐
    
    # === 内容信息（3个字段）===
    "source_text": str,              # 完整段落文本
    "text_hash": str,                # MD5哈希
    "char_count": int,               # 字符数
    
    # === 上下文链接（2个字段）===
    "prev_chunk_id": str | None,    # 前一段落
    "next_chunk_id": str | None,    # 后一段落
    
    # === 文献信息（4个字段）⭐ 引用显示核心 ===
    "title": str,                    # 标题
    "authors": List[str],            # 作者
    "year": int,                     # 年份
    "journal": str,                  # 期刊
    
    # === 构建信息（2个字段）===
    "build_version": "3.0",
    "build_timestamp": str,          # ISO 8601格式
}
```

**总计**: 18个字段  
**存储成本**: ~250 bytes/段落 × 124,348 = ~31 MB

---

## 2. 字段说明

### 2.1 核心标识

#### document_id
- **生成**: `SHA256(filename + file_size)`
- **用途**: 文档去重、版本管理

#### doi
- **格式**: `10.xxxx/xxxxx`
- **来源**: DOI映射文件（需反转）
- **重要**: 必须修复映射，避免`unknown_doi`

#### filename
- **用途**: DOI缺失时的备用标识

### 2.2 层级定位 ⭐ 关键创新

#### chunk_index_in_page
- **范围**: 0 到 total_chunks_in_page - 1
- **用途**: 
  - 计算页内滚动位置
  - 精确定位段落
- **示例**: 如果值为1，total为3，则该段落在页面1/3处

#### total_chunks_in_page
- **用途**: 计算相对位置
- **公式**: `scroll_ratio = (chunk_index_in_page + 0.5) / total_chunks_in_page`

### 2.3 上下文链接

#### prev_chunk_id / next_chunk_id
- **用途**: 实现"查看上下文"功能
- **构建**: 在所有段落处理完后统一建立链接

### 2.4 文献信息 ⭐ 引用显示

#### title, authors, year, journal
- **用途**: 
  - 前端references列表显示
  - 生成引用格式（动态）
- **提取**: 从PDF元数据或第一页文本

---

## 3. 构建流程

### 3.1 整体流程

```
1. 初始化
   ├─ 加载并反转DOI映射
   ├─ 初始化文本切分器
   └─ 连接ChromaDB

2. 文档级处理
   ├─ 提取文献元数据
   ├─ 生成document_id
   └─ 初始化全局计数器

3. 页面级处理
   ├─ 提取页面文本
   ├─ 清洗文本
   ├─ 递归切分段落
   ├─ 统计该页段落数 ⭐
   └─ 初始化页内计数器 ⭐

4. 段落级处理
   ├─ 生成chunk_id
   ├─ 计算位置信息
   ├─ 构建元数据
   └─ 添加到批处理队列

5. 批量写入
   ├─ 调用BGE API
   ├─ 写入ChromaDB
   └─ 清空队列

6. 后处理
   ├─ 建立上下文链接 ⭐
   └─ 生成统计报告
```

### 3.2 关键算法

#### 页内段落计数（核心创新）

```python
def process_page(page, page_num, global_counter):
    """处理单个页面"""
    # 1. 提取并清洗文本
    raw_text = page.get_text("text", sort=True)
    clean_text = clean_text_func(raw_text)
    
    # 2. 切分段落
    chunks = text_splitter.split_text(clean_text)
    
    # 3. 统计该页段落数 ⭐
    total_chunks_in_page = len(chunks)
    
    # 4. 处理每个段落
    page_chunks = []
    for chunk_index_in_page, chunk_text in enumerate(chunks):
        metadata = {
            "chunk_id": str(uuid4()),
            "chunk_index_global": global_counter,
            "page": page_num,
            "chunk_index_in_page": chunk_index_in_page,  # ⭐
            "total_chunks_in_page": total_chunks_in_page,  # ⭐
            "source_text": chunk_text,
            "text_hash": hashlib.md5(chunk_text.encode()).hexdigest(),
            "char_count": len(chunk_text),
            # ... 其他字段
        }
        page_chunks.append(metadata)
        global_counter += 1
    
    return page_chunks, global_counter
```

#### 上下文链接构建

```python
def build_context_links(all_chunks):
    """构建段落间的上下文链接"""
    for i, chunk in enumerate(all_chunks):
        chunk["prev_chunk_id"] = all_chunks[i-1]["chunk_id"] if i > 0 else None
        chunk["next_chunk_id"] = all_chunks[i+1]["chunk_id"] if i < len(all_chunks)-1 else None
    return all_chunks
```

#### 文献元数据提取

```python
def extract_paper_metadata(pdf_path, doi):
    """提取文献元数据"""
    doc = fitz.open(pdf_path)
    
    # 1. 尝试从PDF元数据提取
    metadata = doc.metadata
    title = metadata.get("title", "")
    
    # 2. 如果失败，从第一页提取
    if not title:
        first_page = doc[0]
        title = extract_title_from_page(first_page)
    
    # 3. 提取作者、年份、期刊
    authors = extract_authors(doc[0])
    year = extract_year(doc[0])
    journal = extract_journal(doc[0])
    
    return {
        "title": title or "未知标题",
        "authors": authors or ["未知作者"],
        "year": year or 0,
        "journal": journal or "未知期刊"
    }
```

---

## 4. 使用场景

### 4.1 DOI引用插入

```python
# 当前流程
search_result = {
    'documents': [chunk_text, ...],
    'metadatas': [
        {
            'doi': '10.xxxx/xxxx',  # ⭐ 必需
            'source_text': '...',
            ...
        },
        ...
    ],
    'distances': [0.15, 0.23, ...]
}

# DOI插入器使用
doi_inserter.insert_dois(llm_answer, search_result)
# 输出: "答案文本 (doi=10.xxxx/xxxx)"
```

### 4.2 PDF高亮定位

```python
def highlight_chunk(chunk_metadata):
    """在PDF中高亮显示段落"""
    # 1. 跳转到页面
    page_num = chunk_metadata["page"]
    pdf_viewer.goto_page(page_num)
    
    # 2. 计算滚动位置 ⭐
    chunk_index = chunk_metadata["chunk_index_in_page"]
    total_chunks = chunk_metadata["total_chunks_in_page"]
    scroll_ratio = (chunk_index + 0.5) / total_chunks
    
    # 3. 滚动并高亮
    pdf_viewer.scroll_to_ratio(scroll_ratio)
    pdf_viewer.highlight_text(chunk_metadata["source_text"])
```

### 4.3 引用信息显示

```python
def format_reference(chunk_metadata):
    """格式化引用信息"""
    authors = chunk_metadata["authors"]
    year = chunk_metadata["year"]
    title = chunk_metadata["title"]
    journal = chunk_metadata["journal"]
    
    # 生成行内引用
    if len(authors) == 1:
        inline = f"({authors[0].split(',')[0]}, {year})"
    elif len(authors) == 2:
        inline = f"({authors[0].split(',')[0]} & {authors[1].split(',')[0]}, {year})"
    else:
        inline = f"({authors[0].split(',')[0]}等人, {year})"
    
    # 生成完整引用
    full = f"{', '.join(authors)} ({year}). {title}. {journal}."
    
    return {"inline": inline, "full": full}
```

### 4.4 上下文查看

```python
def get_context(chunk_id):
    """获取段落上下文"""
    # 1. 获取当前段落
    chunk = collection.get(ids=[chunk_id])
    metadata = chunk["metadatas"][0]
    
    # 2. 获取前后段落
    prev_id = metadata["prev_chunk_id"]
    next_id = metadata["next_chunk_id"]
    
    context = {"current": chunk}
    if prev_id:
        context["prev"] = collection.get(ids=[prev_id])
    if next_id:
        context["next"] = collection.get(ids=[next_id])
    
    return context
```

---

## 5. 实施计划

### 5.1 短期（本周）

**目标**: 修复DOI映射，添加核心定位字段

1. ✅ 修复DOI映射
   - 使用 `build_vector_db_v2_fixed.py`
   - 反转映射关系：`filename -> DOI`

2. ✅ 添加页内定位字段
   - `chunk_index_in_page`
   - `total_chunks_in_page`

3. ✅ 提取基本文献元数据
   - title, authors, year, journal

4. ✅ 建立上下文链接
   - prev_chunk_id, next_chunk_id

**预期成果**: 
- DOI引用正常工作
- 为高亮功能准备数据

### 5.2 中期（下周）

**目标**: 实现前端功能

1. 实现PDF高亮
   - 使用 `chunk_index_in_page` 计算滚动位置
   - 使用 `source_text` 进行文本匹配高亮

2. 完善引用显示
   - 显示完整文献信息
   - 支持多种引用格式

3. 实现上下文查看
   - "查看上一段/下一段"按钮
   - 上下文预览面板

**预期成果**:
- 用户可以点击DOI查看原文并高亮
- 引用信息更加完整

### 5.3 长期（下个月）

**目标**: 增强功能（V3.1）

1. 添加精确定位
   - char_start_in_page, char_end_in_page
   - bbox坐标（可选）

2. 添加质量指标
   - text_quality, has_figures, has_equations
   - 支持质量过滤

3. 添加语义标注
   - keywords, entities
   - 支持按材料/方法筛选

**预期成果**:
- 更精确的高亮
- 更智能的搜索过滤

---

## 6. 质量控制

### 6.1 构建前验证

```python
# 1. 检查DOI映射
assert os.path.exists(DOI_MAPPING_FILE)
doi_mapping = load_and_reverse_doi_mapping()
assert len(doi_mapping) > 0
print(f"✅ DOI映射: {len(doi_mapping)} 个")

# 2. 检查PDF目录
pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')]
assert len(pdf_files) > 0
print(f"✅ PDF文件: {len(pdf_files)} 个")

# 3. 检查BGE服务
response = requests.get(BGE_API_URL + "/health")
assert response.status_code == 200
print(f"✅ BGE服务正常")
```

### 6.2 构建后验证

```python
# 1. 数据完整性
total_chunks = collection.count()
print(f"总段落数: {total_chunks}")

# 2. DOI有效性
sample = collection.get(limit=100)
valid_dois = sum(1 for m in sample["metadatas"] if m["doi"].startswith("10."))
print(f"有效DOI比例: {valid_dois}/100")

# 3. 页内序号检查
for meta in sample["metadatas"][:10]:
    assert 0 <= meta["chunk_index_in_page"] < meta["total_chunks_in_page"]
print(f"✅ 页内序号验证通过")
```

---

## 7. 常见问题

**Q: 为什么chunk_index_in_page从0开始？**  
A: 符合编程习惯，便于数组索引。显示给用户时可以+1。

**Q: 跨页段落如何处理？**  
A: 归属到主要页面（文本占比更多的页面）。

**Q: 如何处理DOI提取失败的文献？**  
A: 使用filename作为备用标识，但需要尽快修复DOI映射。

**Q: 文献元数据提取失败怎么办？**  
A: 使用默认值（"未知标题"等），不影响核心功能。

**Q: V3.0和V3.1的主要区别？**  
A: V3.0包含核心功能所需的18个字段，V3.1添加增强功能的额外字段。

---

## 8. 附录

### 8.1 存储成本对比

| 版本 | 字段数 | 单段落大小 | 总大小（124K段落） |
|------|--------|------------|-------------------|
| V2.0 | 5 | ~100 bytes | ~12 MB |
| V3.0 | 18 | ~250 bytes | ~31 MB |
| V3.1 | 28 | ~400 bytes | ~50 MB |

### 8.2 功能支持对比

| 功能 | V2.0 | V3.0 | V3.1 |
|------|------|------|------|
| DOI引用 | ❌ | ✅ | ✅ |
| PDF高亮 | ❌ | ✅ | ✅✅ |
| 引用显示 | ❌ | ✅ | ✅ |
| 上下文查看 | ❌ | ✅ | ✅ |
| 精确高亮 | ❌ | ❌ | ✅ |
| 质量过滤 | ❌ | ❌ | ✅ |
| 语义搜索 | ❌ | ❌ | ✅ |

---

**文档版本**: V3.0  
**最后更新**: 2024-01-19  
**维护者**: LiFeO4Agent Team
