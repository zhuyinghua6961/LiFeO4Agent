#!/usr/bin/env python3
"""
完整向量数据库构建脚本
从 papers/ 目录的所有 PDF 生成摘要和 embedding，并导入到 ChromaDB
"""
import json
import os
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import requests
import chromadb
from chromadb.config import Settings
import time
from threading import Semaphore

try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    print("❌ PyMuPDF 未安装，请运行: conda install -n agent pymupdf")
    exit(1)

# ==================== 配置 ====================
PAPERS_DIR = Path("/Users/zhuyinghua/Desktop/agent/main/papers")
JSON_DIR = Path("/Users/zhuyinghua/Desktop/agent/main/json")
VECTOR_DB_PATH = "/Users/zhuyinghua/Desktop/agent/main/vector_database"

# BGE Embedding API
BGE_API_URL = "http://hf2d8696.natapp1.cc/v1/embeddings"

# LLM API (阿里百炼)
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DASHSCOPE_MODEL = "deepseek-v3.1"

# 并发配置
MAX_WORKERS = 1  # 完全顺序处理,避免API限流
BATCH_SIZE = 100  # ChromaDB 批量插入大小

# API 限流控制  
API_DELAY = 2.0  # 每个请求之间延迟 2 秒


# ==================== PDF 提取 ====================
def extract_doi_from_pdf(pdf_path: Path) -> str:
    """从 PDF 文件名提取 DOI"""
    filename = pdf_path.stem
    # 文件名格式: Author_Year_Journal_xxx.pdf
    # DOI 在文件名中编码，需要反向解析
    doi = filename.replace('_', '/')
    # 简化: 直接从文件名构造 DOI (实际应该从 PDF 元数据提取)
    return f"10.xxxx/{filename}"  # 占位符


def extract_pdf_text(pdf_path: Path, max_pages: int = 3) -> str:
    """提取 PDF 前几页文本(用于提取摘要和DOI)"""
    try:
        doc = fitz.open(str(pdf_path))
        text_parts = []
        
        # 只提取前3页(通常包含标题、摘要、DOI)
        for page_num in range(min(max_pages, doc.page_count)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                text_parts.append(text)
        
        doc.close()
        full_text = '\n'.join(text_parts)
        return full_text[:5000]  # 限制在5000字符
        
    except Exception as e:
        print(f"  ⚠️ PDF 提取失败 {pdf_path.name}: {e}")
        return ""


def extract_abstract_from_text(text: str) -> str:
    """从文本中提取 Abstract 部分,返回简短摘要"""
    # 尝试提取 Abstract 部分
    patterns = [
        # 英文 Abstract
        r'(?:ABSTRACT|Abstract)\s*[:\n]\s*(.*?)(?:\n\s*\n|\n(?:INTRODUCTION|Introduction|Keywords|KEY\s*WORDS|1\.|©|\d+\.\s+Introduction))',
        # 另一种格式
        r'(?:ABSTRACT|Abstract)\s*[:\n]\s*(.*?)(?=\n[A-Z][a-z]+:|\n\d+\.|\n©)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            abstract = match.group(1).strip()
            # 清理多余空白和换行
            abstract = re.sub(r'\s+', ' ', abstract)
            # 清理可能的页码、引用等
            abstract = re.sub(r'\[\d+\]', '', abstract)
            
            if len(abstract) > 100:  # 确保提取到有效内容
                # 返回前500字符(和原版 JSON 格式一致)
                return abstract[:500].strip()
    
    # 如果没找到 Abstract,返回前300字符作为简短摘要
    clean_text = re.sub(r'\s+', ' ', text)
    return clean_text[:300].strip()


def extract_doi_from_text(text: str) -> str:
    """从文本中提取 DOI"""
    patterns = [
        r'DOI[:\s]+(\d+\.\d+/[^\s\]]+)',
        r'doi[:\s]+(\d+\.\d+/[^\s\]]+)',
        r'https?://doi\.org/(\d+\.\d+/[^\s]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            doi = match.group(1).strip()
            # 清理末尾的标点符号
            doi = re.sub(r'[.,;]$', '', doi)
            return doi
    
    return None


# ==================== LLM 摘要生成 ====================
# 注释掉 LLM 生成,直接使用 PDF 提取的 Abstract
# def generate_summary_with_llm(pdf_text: str, doi: str) -> str:
#     """使用 LLM 生成文献摘要"""
#     pass


# ==================== Embedding 生成 ====================
def generate_embedding(text: str, retry_count=5) -> list:
    """调用 BGE API 生成 embedding (带重试)"""
    
    for attempt in range(retry_count):
        try:
            # 添加延迟避免限流
            time.sleep(API_DELAY)
            
            response = requests.post(
                BGE_API_URL,
                json={
                    "input": [text]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()["data"][0]["embedding"]
            elif response.status_code == 429:
                # 遇到限流,指数退避
                wait_time = (2 ** attempt) * 5  # 5, 10, 20, 40, 80 秒
                print(f"  ⚠️ API 限流 (429), {wait_time}秒后重试 (第{attempt+1}/{retry_count}次)")
                time.sleep(wait_time)
                continue
            else:
                print(f"  ⚠️ Embedding 失败: {response.status_code}")
                if attempt < retry_count - 1:
                    time.sleep(3)
                    continue
                return None
                
        except Exception as e:
            print(f"  ⚠️ Embedding 错误: {e}")
            if attempt < retry_count - 1:
                time.sleep(3)
                continue
            return None
    
    return None


# ==================== 处理单个 PDF ====================
def process_single_pdf(pdf_path: Path) -> dict:
    """处理单个 PDF: 提取文本 -> 生成摘要 -> 生成 embedding"""
    
    # 检查 JSON 是否已存在
    json_filename = pdf_path.stem + "_summary_embedding.json"
    json_path = JSON_DIR / json_filename
    
    if json_path.exists():
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return {
                "status": "exists",
                "data": data[0] if isinstance(data, list) else data,
                "pdf": pdf_path.name
            }
        except Exception as e:
            print(f"  ⚠️ JSON 读取失败 {json_filename}: {e}")
    
    # 提取 PDF 文本
    pdf_text = extract_pdf_text(pdf_path)
    if not pdf_text:
        return {"status": "error", "pdf": pdf_path.name, "error": "PDF文本提取失败"}
    
    # 提取 DOI
    doi = extract_doi_from_text(pdf_text)
    if not doi:
        # 从文件名猜测
        doi = f"unknown/{pdf_path.stem}"
    
    # 提取 Abstract 作为简短摘要(不调用 LLM)
    abstract = extract_abstract_from_text(pdf_text)
    
    # 构造摘要文本(和原版 JSON 格式一致)
    summary = f"[DOI: {doi}] {abstract}"
    
    # 生成 embedding
    embedding = generate_embedding(summary)
    if not embedding:
        return {"status": "error", "pdf": pdf_path.name, "error": "Embedding生成失败"}
    
    # 保存 JSON
    data = {
        "text": summary,
        "embedding": embedding,
        "metadata": {
            "source_file": pdf_path.name,
            "doi": doi
        }
    }
    
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump([data], f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  ⚠️ JSON 保存失败: {e}")
    
    return {
        "status": "success",
        "data": data,
        "pdf": pdf_path.name
    }


# ==================== 主流程 ====================
def main():
    print("=" * 80)
    print("🚀 完整向量数据库构建")
    print("=" * 80)
    
    # 检查目录
    if not PAPERS_DIR.exists():
        print(f"❌ papers 目录不存在: {PAPERS_DIR}")
        return
    
    JSON_DIR.mkdir(exist_ok=True)
    
    # 获取所有 PDF
    pdf_files = sorted(PAPERS_DIR.glob("*.pdf"))
    print(f"📄 找到 {len(pdf_files)} 个 PDF 文件")
    
    if len(pdf_files) == 0:
        print("❌ 没有找到 PDF 文件")
        return
    
    # 检查已有 JSON - 全部忽略,重新生成所有文献
    existing_jsons = set()
    print(f"📦 将重新生成所有文献的向量数据")
    
    # 处理所有 PDF
    pdfs_to_process = pdf_files
    print(f"🔨 需要处理 {len(pdfs_to_process)} 个 PDF")
    
    if len(pdfs_to_process) == 0:
        print("❌ 没有 PDF 需要处理")
        return
    else:
        print(f"\n开始处理 PDF (并发: {MAX_WORKERS})...")
        
        results = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(process_single_pdf, pdf): pdf for pdf in pdfs_to_process}
            
            with tqdm(total=len(pdfs_to_process), desc="处理进度") as pbar:
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    pbar.update(1)
                    
                    if result["status"] == "error":
                        tqdm.write(f"  ❌ {result['pdf']}: {result.get('error', 'Unknown')}")
        
        # 统计
        success_count = sum(1 for r in results if r["status"] == "success")
        exists_count = sum(1 for r in results if r["status"] == "exists")
        error_count = sum(1 for r in results if r["status"] == "error")
        
        print(f"\n处理完成:")
        print(f"  ✅ 新生成: {success_count}")
        print(f"  📦 已存在: {exists_count}")
        print(f"  ❌ 失败: {error_count}")
    
    # 导入到 ChromaDB
    print(f"\n{'='*80}")
    print("📊 导入数据到 ChromaDB")
    print("=" * 80)
    
    # 读取所有 JSON
    json_files = sorted(JSON_DIR.glob("*_summary_embedding.json"))
    print(f"📄 找到 {len(json_files)} 个 JSON 文件")
    
    # 初始化 ChromaDB
    client = chromadb.PersistentClient(
        path=VECTOR_DB_PATH,
        settings=Settings(anonymized_telemetry=False)
    )
    
    # 删除旧集合(使用原版集合名)
    try:
        client.delete_collection("lfp_papers")
        print("🗑️  已删除旧集合: lfp_papers")
    except Exception:
        pass
    
    # 创建新集合(使用原版的集合名)
    collection = client.create_collection(
        name="lfp_papers",
        metadata={"hnsw:space": "cosine"}
    )
    
    # 批量导入
    documents = []
    embeddings = []
    metadatas = []
    ids = []
    total_imported = 0
    
    for i, json_file in enumerate(tqdm(json_files, desc="导入进度")):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            item = data[0] if isinstance(data, list) else data
            text = item.get('text', '')
            embedding = item.get('embedding', [])
            metadata = item.get('metadata', {})
            
            if not text or not embedding:
                continue
            
            doc_id = f"{json_file.stem}_{i}"
            documents.append(text)
            embeddings.append(embedding)
            metadatas.append({
                **metadata,
                'source_file': json_file.name
            })
            ids.append(doc_id)
            
            # 批量插入
            if len(documents) >= BATCH_SIZE:
                collection.add(
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    ids=ids
                )
                total_imported += len(documents)
                documents = []
                embeddings = []
                metadatas = []
                ids = []
                
        except Exception as e:
            tqdm.write(f"  ⚠️ 处理失败 {json_file.name}: {e}")
    
    # 插入剩余数据
    if documents:
        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        total_imported += len(documents)
    
    final_count = collection.count()
    print(f"\n✅ 导入完成!")
    print(f"   最终文档数: {final_count}")
    print(f"   数据库路径: {VECTOR_DB_PATH}")
    
    # ChromaDB PersistentClient 不需要手动关闭
    
    print("\n" + "=" * 80)
    print("🎉 向量数据库构建完成!")
    print("=" * 80)


if __name__ == '__main__':
    main()
