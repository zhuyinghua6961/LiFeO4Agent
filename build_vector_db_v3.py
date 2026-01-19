#!/usr/bin/env python3
"""
V3.0 向量数据库构建脚本（完整版）
基于 VECTOR_DB_BUILD_SPEC_V3.md 规范

核心特性：
1. 18个完整元数据字段
2. 页内段落定位（chunk_index_in_page, total_chunks_in_page）
3. 文献元数据提取（title, authors, year, journal）
4. 上下文链接（prev_chunk_id, next_chunk_id）
5. 修复DOI映射反转问题

构建时间：约2-3小时（取决于PDF数量和BGE服务性能）
"""
import os
import re
import json
import time
import hashlib
import requests
import fitz  # PyMuPDF
import chromadb
from tqdm import tqdm
from uuid import uuid4
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# 配置区
# ============================================================================
PROJECT_ROOT = os.path.dirname(__file__)
PDF_DIR = os.path.join(PROJECT_ROOT, "papers")
DOI_MAPPING_FILE = os.path.join(PROJECT_ROOT, "doi_to_pdf_mapping.json")
CHROMA_DB_PATH = os.path.join(PROJECT_ROOT, "vector_database_v3")
COLLECTION_NAME = "lfp_papers_v3"
BGE_API_URL = "http://localhost:8001/v1/embeddings"

# 切片参数
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100
BATCH_SIZE = 128

# 构建版本
BUILD_VERSION = "3.0"


# ============================================================================
# 文本切分器
# ============================================================================
class SimpleTextSplitter:
    """递归文本切分器"""
    def __init__(self, chunk_size=600, chunk_overlap=100, separators=None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]
    
    def split_text(self, text: str) -> List[str]:
        """递归切分文本"""
        chunks = []
        text = text.strip()
        
        if len(text) <= self.chunk_size:
            return [text] if text else []
        
        for sep in self.separators:
            if sep == "":
                # 最后手段：按字符数硬切分
                for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
                    chunk = text[i:i + self.chunk_size]
                    if chunk:
                        chunks.append(chunk)
                break
            
            parts = text.split(sep)
            current_chunk = ""
            
            for part in parts:
                test_chunk = current_chunk + sep + part if current_chunk else part
                if len(test_chunk) > self.chunk_size:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = part
                else:
                    current_chunk = test_chunk
            
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            if len(chunks) > 1:
                break
        
        # 合并相邻小块
        merged = []
        for chunk in chunks:
            if not chunk:
                continue
            if merged and len(merged[-1]) + len(chunk) < self.chunk_size:
                merged[-1] += " " + chunk
            else:
                merged.append(chunk)
        
        return merged if merged else [text[:self.chunk_size]]


# ============================================================================
# 工具函数
# ============================================================================
def clean_text(text: str) -> str:
    """清洗文本"""
    # 修复跨行断词
    text = text.replace("-\n", "").replace("\n", " ")
    # 压缩多余空格
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def generate_document_id(filename: str, file_size: int) -> str:
    """生成文档唯一ID"""
    content = f"{filename}_{file_size}"
    return hashlib.sha256(content.encode()).hexdigest()


def get_embeddings(texts: List[str]) -> List[List[float]]:
    """调用 BGE 服务获取向量"""
    if not texts:
        return []
    
    try:
        response = requests.post(
            BGE_API_URL,
            json={"input": texts},
            timeout=120
        )
        response.raise_for_status()
        data = response.json()["data"]
        return [item["embedding"] for item in data]
    except Exception as e:
        logger.error(f"Embedding API 错误: {e}")
        # 错误时返回零向量，避免程序崩溃
        return [[0.0] * 1024 for _ in texts]


def load_doi_mapping() -> Dict[str, str]:
    """
    加载 DOI 映射并反转为 filename -> DOI
    
    原始格式: {"DOI": "filename.pdf"}
    返回格式: {"filename.pdf": "DOI"}
    """
    if os.path.exists(DOI_MAPPING_FILE):
        with open(DOI_MAPPING_FILE, 'r', encoding='utf-8') as f:
            doi_to_file = json.load(f)
        
        # 反转映射：DOI -> filename 变为 filename -> DOI
        file_to_doi = {filename: doi for doi, filename in doi_to_file.items()}
        
        logger.info(f"📋 加载了 {len(file_to_doi)} 个 DOI 映射（已反转）")
        return file_to_doi
    
    logger.warning("⚠️  DOI 映射文件不存在")
    return {}


# ============================================================================
# 文献元数据提取
# ============================================================================
def extract_title_from_page(page) -> str:
    """从页面提取标题（通常是第一页最大字号的文本）"""
    try:
        blocks = page.get_text("dict")["blocks"]
        title_candidates = []
        
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        size = span["size"]
                        if text and len(text) > 10 and size > 12:
                            title_candidates.append((text, size))
        
        # 按字号排序，取最大的
        if title_candidates:
            title_candidates.sort(key=lambda x: x[1], reverse=True)
            return title_candidates[0][0]
    except:
        pass
    
    return ""


def extract_authors_from_text(text: str) -> List[str]:
    """从文本中提取作者（简单规则）"""
    # 查找常见作者模式
    patterns = [
        r'([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # John Smith
        r'([A-Z]\.\s*[A-Z]\.\s*[A-Z][a-z]+)',  # J. K. Smith
    ]
    
    authors = []
    for pattern in patterns:
        matches = re.findall(pattern, text[:1000])  # 只搜索前1000字符
        authors.extend(matches[:5])  # 最多5个作者
        if authors:
            break
    
    return authors[:5] if authors else []


def extract_year_from_text(text: str) -> int:
    """从文本中提取年份"""
    # 查找4位数年份（1900-2099）
    matches = re.findall(r'\b(19\d{2}|20\d{2})\b', text[:2000])
    if matches:
        # 返回最常见的年份
        from collections import Counter
        year_counts = Counter(matches)
        return int(year_counts.most_common(1)[0][0])
    return 0


def extract_journal_from_text(text: str) -> str:
    """从文本中提取期刊名（简单规则）"""
    # 查找常见期刊关键词
    journal_keywords = [
        r'Journal of ([A-Z][a-z\s]+)',
        r'([A-Z][a-z\s]+) Journal',
        r'Proceedings of ([A-Z][a-z\s]+)',
    ]
    
    for pattern in journal_keywords:
        match = re.search(pattern, text[:2000])
        if match:
            return match.group(0)
    
    return ""


def extract_paper_metadata(pdf_path: str, doi: str) -> Dict[str, any]:
    """
    提取文献元数据
    
    Returns:
        {
            "title": str,
            "authors": List[str],
            "year": int,
            "journal": str
        }
    """
    try:
        doc = fitz.open(pdf_path)
        
        # 1. 尝试从PDF元数据提取
        metadata = doc.metadata
        title = metadata.get("title", "").strip()
        
        # 2. 从第一页提取
        first_page = doc[0]
        first_page_text = first_page.get_text()
        
        # 标题
        if not title or len(title) < 10:
            title = extract_title_from_page(first_page)
        
        # 作者
        authors = extract_authors_from_text(first_page_text)
        
        # 年份
        year = extract_year_from_text(first_page_text)
        
        # 期刊
        journal = extract_journal_from_text(first_page_text)
        
        doc.close()
        
        return {
            "title": title if title else "未知标题",
            "authors": authors if authors else ["未知作者"],
            "year": year if year else 0,
            "journal": journal if journal else "未知期刊"
        }
        
    except Exception as e:
        logger.warning(f"提取元数据失败: {e}")
        return {
            "title": "未知标题",
            "authors": ["未知作者"],
            "year": 0,
            "journal": "未知期刊"
        }


# ============================================================================
# PDF处理
# ============================================================================
def process_single_pdf(
    filepath: str,
    filename: str,
    doi: str,
    text_splitter: SimpleTextSplitter
) -> List[Dict]:
    """
    处理单个 PDF 文件（V3.0完整版，带OOM保护）
    
    Returns:
        切片列表，每个切片包含完整的V3.0元数据
    """
    chunks = []
    doc = None
    
    try:
        # 获取文件大小
        file_size = os.path.getsize(filepath)
        
        # 生成document_id
        document_id = generate_document_id(filename, file_size)
        
        # 提取文献元数据
        paper_meta = extract_paper_metadata(filepath, doi)
        
        # 打开PDF
        doc = fitz.open(filepath)
        
        # OOM保护：限制最大页数（避免超大PDF）
        max_pages = min(len(doc), 500)  # 最多处理500页
        if len(doc) > max_pages:
            logger.warning(f"   ⚠️  {filename} 有 {len(doc)} 页，只处理前 {max_pages} 页")
        
        # 全局计数器
        global_counter = 0
        all_chunks_data = []  # 存储所有段落数据，用于后续建立链接
        
        # 逐页处理
        for page_index in range(max_pages):
            page = doc[page_index]
            page_num = page_index + 1
            
            # 提取文本
            raw_text = page.get_text("text", sort=True)
            clean_text_str = clean_text(raw_text)
            
            # 跳过空白页
            if len(clean_text_str) < 50:
                continue
            
            # 切分段落
            page_chunks = text_splitter.split_text(clean_text_str)
            
            # 统计该页段落数 ⭐ 核心创新
            total_chunks_in_page = len(page_chunks)
            
            # 处理每个段落
            for chunk_index_in_page, chunk_text in enumerate(page_chunks):
                if len(chunk_text) < 30:  # 跳过太短的碎片
                    continue
                
                # 生成chunk_id
                chunk_id = str(uuid4())
                
                # 构建完整的V3.0元数据
                chunk_data = {
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "metadata": {
                        # === 核心标识 ===
                        "document_id": document_id,
                        "doi": doi,
                        "filename": filename,
                        
                        # === 层级定位 ⭐ ===
                        "chunk_id": chunk_id,
                        "chunk_index_global": global_counter,
                        "page": page_num,
                        "chunk_index_in_page": chunk_index_in_page,  # ⭐ 关键字段
                        "total_chunks_in_page": total_chunks_in_page,  # ⭐ 关键字段
                        
                        # === 内容信息 ===
                        "source_text": chunk_text,
                        "text_hash": hashlib.md5(chunk_text.encode()).hexdigest(),
                        "char_count": len(chunk_text),
                        
                        # === 上下文链接（稍后填充）===
                        "prev_chunk_id": "",
                        "next_chunk_id": "",
                        
                        # === 文献信息 ⭐ ===
                        "title": paper_meta["title"] or "Unknown",
                        "authors": ", ".join(paper_meta["authors"]) if isinstance(paper_meta["authors"], list) else (paper_meta["authors"] or "Unknown"),
                        "year": paper_meta["year"] or 0,
                        "journal": paper_meta["journal"] or "Unknown",
                        
                        # === 构建信息 ===
                        "build_version": BUILD_VERSION,
                        "build_timestamp": datetime.now().isoformat(),
                    }
                }
                
                all_chunks_data.append(chunk_data)
                global_counter += 1
            
            # OOM保护：每处理50页清理一次内存
            if page_index % 50 == 0 and page_index > 0:
                import gc
                gc.collect()
        
        # 关闭文档
        if doc:
            doc.close()
            doc = None
        
        # 建立上下文链接 ⭐
        for i, chunk_data in enumerate(all_chunks_data):
            if i > 0:
                chunk_data["metadata"]["prev_chunk_id"] = all_chunks_data[i-1]["chunk_id"]
            if i < len(all_chunks_data) - 1:
                chunk_data["metadata"]["next_chunk_id"] = all_chunks_data[i+1]["chunk_id"]
        
        # 返回结果（OOM保护：不保留中间变量）
        result = all_chunks_data
        all_chunks_data = None  # 释放引用
        return result
        
    except Exception as e:
        logger.error(f"处理 PDF 失败 {filename}: {e}")
        # OOM保护：异常时确保释放资源
        if doc:
            try:
                doc.close()
            except:
                pass
        import gc
        gc.collect()
        return []


# ============================================================================
# 主流程
# ============================================================================
def main():
    """主流程"""
    logger.info("=" * 80)
    logger.info("🚀 V3.0 向量数据库构建程序启动")
    logger.info("   基于 VECTOR_DB_BUILD_SPEC_V3.md 规范")
    logger.info("=" * 80)
    
    # ========== 1. 构建前验证 ==========
    logger.info("\n📋 [步骤1] 构建前验证")
    
    # 检查 PDF 目录
    if not os.path.exists(PDF_DIR):
        logger.error(f"❌ PDF 目录不存在: {PDF_DIR}")
        return
    
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')]
    logger.info(f"✅ PDF文件: {len(pdf_files)} 个")
    
    if not pdf_files:
        logger.warning("⚠️  没有找到 PDF 文件")
        return
    
    # 加载 DOI 映射
    file_to_doi = load_doi_mapping()
    valid_dois = sum(1 for doi in file_to_doi.values() if doi.startswith("10."))
    logger.info(f"✅ DOI映射: {len(file_to_doi)} 个（有效: {valid_dois}）")
    
    # 检查 BGE 服务
    try:
        response = requests.get(BGE_API_URL.replace("/v1/embeddings", "/health"), timeout=5)
        logger.info(f"✅ BGE服务正常")
    except:
        logger.warning(f"⚠️  BGE服务可能未启动: {BGE_API_URL}")
    
    # ========== 2. 初始化 ==========
    logger.info("\n🔧 [步骤2] 初始化")
    
    # 初始化切分器
    text_splitter = SimpleTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    logger.info(f"✅ 文本切分器: chunk_size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}")
    
    # 初始化 ChromaDB
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    
    # 删除旧集合
    try:
        client.delete_collection(COLLECTION_NAME)
        logger.info(f"🗑️  已删除旧集合: {COLLECTION_NAME}")
    except:
        pass
    
    collection = client.create_collection(name=COLLECTION_NAME)
    logger.info(f"✅ 创建新集合: {COLLECTION_NAME}")
    
    # ========== 3. 批量处理 ==========
    logger.info(f"\n📄 [步骤3] 处理PDF文件（共 {len(pdf_files)} 个）")
    
    batch_documents = []
    batch_metadatas = []
    batch_ids = []
    
    total_chunks = 0
    total_pdfs = 0
    failed_pdfs = []
    
    stats = {
        "valid_doi": 0,
        "unknown_doi": 0,
        "with_title": 0,
        "with_authors": 0,
        "with_year": 0,
    }
    
    start_time = time.time()
    
    for idx, filename in enumerate(tqdm(pdf_files, desc="处理PDF"), 1):
        filepath = os.path.join(PDF_DIR, filename)
        doi = file_to_doi.get(filename, "unknown_doi")
        
        # 统计DOI
        if doi.startswith("10."):
            stats["valid_doi"] += 1
        else:
            stats["unknown_doi"] += 1
        
        try:
            # 处理PDF
            pdf_chunks = process_single_pdf(filepath, filename, doi, text_splitter)
            
            if pdf_chunks:
                # 统计元数据质量
                first_meta = pdf_chunks[0]["metadata"]
                if first_meta["title"] != "未知标题":
                    stats["with_title"] += 1
                if first_meta["authors"] != ["未知作者"]:
                    stats["with_authors"] += 1
                if first_meta["year"] > 0:
                    stats["with_year"] += 1
                
                # 添加到批次
                for chunk_data in pdf_chunks:
                    batch_documents.append(chunk_data["text"])
                    batch_metadatas.append(chunk_data["metadata"])
                    batch_ids.append(chunk_data["chunk_id"])
                
                total_chunks += len(pdf_chunks)
                total_pdfs += 1
            else:
                failed_pdfs.append(filename)
                
        except Exception as e:
            logger.error(f"❌ 处理失败 {filename}: {e}")
            failed_pdfs.append(filename)
            continue
        
        # 批次写入（OOM保护：立即写入并清空缓冲区）
        if len(batch_documents) >= BATCH_SIZE:
            logger.info(f"   💾 写入批次: {len(batch_documents)} 个段落")
            
            # 获取向量
            embeddings = get_embeddings(batch_documents)
            
            # 写入数据库
            collection.add(
                embeddings=embeddings,
                documents=batch_documents,
                metadatas=batch_metadatas,
                ids=batch_ids
            )
            
            # 立即清空缓冲区（OOM保护）⭐
            batch_documents.clear()
            batch_metadatas.clear()
            batch_ids.clear()
            embeddings = None  # 释放embedding内存
            
            # 强制垃圾回收（可选，但有助于释放内存）
            import gc
            gc.collect()
        
        # 每处理100个PDF显示进度
        if idx % 100 == 0:
            elapsed = time.time() - start_time
            avg_time = elapsed / idx
            remaining = (len(pdf_files) - idx) * avg_time
            logger.info(f"   进度: {idx}/{len(pdf_files)}, "
                       f"已用时: {elapsed/60:.1f}分钟, "
                       f"预计剩余: {remaining/60:.1f}分钟")
    
    # 处理剩余数据
    if batch_documents:
        logger.info(f"   💾 写入最后批次: {len(batch_documents)} 个段落")
        embeddings = get_embeddings(batch_documents)
        collection.add(
            embeddings=embeddings,
            documents=batch_documents,
            metadatas=batch_metadatas,
            ids=batch_ids
        )
        
        # 清空缓冲区
        batch_documents.clear()
        batch_metadatas.clear()
        batch_ids.clear()
        embeddings = None
        
        import gc
        gc.collect()
    
    # ========== 4. 构建后验证 ==========
    logger.info("\n🔍 [步骤4] 构建后验证")
    
    final_count = collection.count()
    logger.info(f"✅ 数据库总段落数: {final_count}")
    
    # 抽样验证
    sample = collection.get(limit=100)
    sample_metas = sample["metadatas"]
    
    # 验证DOI
    valid_doi_count = sum(1 for m in sample_metas if m["doi"].startswith("10."))
    logger.info(f"✅ 有效DOI比例: {valid_doi_count}/100")
    
    # 验证页内序号
    try:
        for meta in sample_metas[:10]:
            assert 0 <= meta["chunk_index_in_page"] < meta["total_chunks_in_page"]
        logger.info(f"✅ 页内序号验证通过")
    except AssertionError:
        logger.warning(f"⚠️  页内序号验证失败")
    
    # 验证上下文链接
    linked_count = sum(1 for m in sample_metas if m.get("prev_chunk_id") or m.get("next_chunk_id"))
    logger.info(f"✅ 上下文链接: {linked_count}/100 个段落有链接")
    
    # ========== 5. 统计报告 ==========
    total_time = time.time() - start_time
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ V3.0 向量数据库构建完成!")
    logger.info("=" * 80)
    logger.info(f"📊 处理统计:")
    logger.info(f"   - 处理PDF: {total_pdfs}/{len(pdf_files)}")
    logger.info(f"   - 失败PDF: {len(failed_pdfs)}")
    logger.info(f"   - 生成段落: {total_chunks}")
    logger.info(f"   - 数据库总量: {final_count}")
    logger.info(f"")
    logger.info(f"📋 DOI统计:")
    logger.info(f"   - 有效DOI: {stats['valid_doi']}")
    logger.info(f"   - 未知DOI: {stats['unknown_doi']}")
    logger.info(f"")
    logger.info(f"📚 元数据质量:")
    logger.info(f"   - 有标题: {stats['with_title']}/{total_pdfs}")
    logger.info(f"   - 有作者: {stats['with_authors']}/{total_pdfs}")
    logger.info(f"   - 有年份: {stats['with_year']}/{total_pdfs}")
    logger.info(f"")
    logger.info(f"⏱️  耗时: {total_time/60:.1f} 分钟")
    logger.info(f"💾 存储路径: {CHROMA_DB_PATH}")
    logger.info(f"📦 集合名称: {COLLECTION_NAME}")
    logger.info("=" * 80)
    
    if failed_pdfs:
        logger.info(f"\n⚠️  失败文件列表（前10个）:")
        for f in failed_pdfs[:10]:
            logger.info(f"   - {f}")


if __name__ == "__main__":
    main()
