#!/usr/bin/env python3
"""
V2.0 向量数据库构建脚本
递归切片 + 页面锚点策略，支持原文高亮和精准跳转

特性:
- 全篇 PDF 处理（非仅前3页）
- 递归语义切片 (600字符，重叠100)
- 元数据绑定 DOI + 页码 + 原文片段
- 支持双栏排版识别
"""
import os
import re
import json
import time
import requests
import fitz  # PyMuPDF
import chromadb
from langchain.text_splitter import RecursiveCharacterTextSplitter
from tqdm import tqdm
from uuid import uuid4
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 配置区 ---
# PDF 文件夹路径
PDF_DIR = "/Users/zhuyinghua/Desktop/agent/main/papers"
# DOI 映射文件路径
DOI_MAPPING_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "doi_to_pdf_mapping.json")
# ChromaDB 持久化路径
CHROMA_DB_PATH = os.path.dirname(__file__)
# 新的集合名称
COLLECTION_NAME = "lfp_papers_v2"
# BGE 服务地址
BGE_API_URL = "http://localhost:8001/v1/embeddings"
# 切片参数
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100
# 批处理大小
BATCH_SIZE = 32


def get_embeddings(texts: list) -> list:
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


def clean_text(text: str) -> str:
    """清洗文本"""
    # 修复跨行断词
    text = text.replace("-\n", "").replace("\n", " ")
    # 压缩多余空格
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def process_single_pdf(filepath: str, filename: str, doi: str) -> list:
    """
    处理单个 PDF 文件
    
    Args:
        filepath: PDF 文件完整路径
        filename: 文件名
        doi: DOI 标识符
        
    Returns:
        切片列表
    """
    chunks = []
    
    try:
        doc = fitz.open(filepath)
        
        for page_index, page in enumerate(doc):
            # 提取文本，sort=True 解决双栏排版问题
            raw_text = page.get_text("text", sort=True)
            clean_text_str = clean_text(raw_text)
            
            # 跳过空白页或内容过少的页面
            if len(clean_text_str) < 50:
                continue
            
            # 递归切分
            text_chunks = text_splitter.split_text(clean_text_str)
            
            for chunk in text_chunks:
                if len(chunk) < 30:  # 跳过太短的碎片
                    continue
                    
                record = {
                    "id": str(uuid4()),
                    "text": chunk,
                    "metadata": {
                        "doi": doi,
                        "filename": filename,
                        "page": page_index + 1,  # PDF 页码从1开始
                        "source_text": chunk[:300] if len(chunk) > 300 else chunk,
                        "type": "content"
                    }
                }
                chunks.append(record)
        
        doc.close()
        
    except Exception as e:
        logger.error(f"处理 PDF 失败 {filename}: {e}")
    
    return chunks


def load_doi_mapping() -> dict:
    """加载 DOI 映射"""
    if os.path.exists(DOI_MAPPING_FILE):
        with open(DOI_MAPPING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def main():
    """主流程"""
    global text_splitter
    
    logger.info("=" * 60)
    logger.info("🚀 V2.0 向量数据库构建程序启动")
    logger.info("=" * 60)
    
    # 1. 检查 PDF 目录
    if not os.path.exists(PDF_DIR):
        logger.error(f"PDF 目录不存在: {PDF_DIR}")
        return
    
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')]
    logger.info(f"📁 找到 {len(pdf_files)} 个 PDF 文件")
    
    if not pdf_files:
        logger.warning("没有找到 PDF 文件")
        return
    
    # 2. 加载 DOI 映射
    file_to_doi = load_doi_mapping()
    logger.info(f"📋 加载了 {len(file_to_doi)} 个 DOI 映射")
    
    # 3. 初始化切分器
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    logger.info("✂️ 初始化递归切分器完成")
    
    # 4. 初始化 ChromaDB
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    
    # 删除旧集合（如果存在）
    try:
        client.delete_collection(COLLECTION_NAME)
        logger.info(f"🗑️ 已删除旧集合: {COLLECTION_NAME}")
    except:
        pass
    
    collection = client.create_collection(name=COLLECTION_NAME)
    logger.info(f"📦 创建新集合: {COLLECTION_NAME}")
    
    # 5. 批量处理
    batch_documents = []
    batch_metadatas = []
    batch_ids = []
    total_chunks = 0
    total_pdfs = 0
    failed_pdfs = []
    
    for filename in tqdm(pdf_files, desc="处理 PDF"):
        filepath = os.path.join(PDF_DIR, filename)
        doi = file_to_doi.get(filename, "unknown_doi")
        
        try:
            pdf_chunks = process_single_pdf(filepath, filename, doi)
            
            if pdf_chunks:
                for item in pdf_chunks:
                    batch_documents.append(item["text"])
                    batch_metadatas.append(item["metadata"])
                    batch_ids.append(item["id"])
                
                total_chunks += len(pdf_chunks)
                total_pdfs += 1
            else:
                failed_pdfs.append(filename)
                
        except Exception as e:
            logger.error(f"处理失败 {filename}: {e}")
            failed_pdfs.append(filename)
            continue
        
        # 批次处理（获取向量并写入数据库）
        if len(batch_documents) >= BATCH_SIZE:
            logger.info(f"   处理批次: {len(batch_documents)} 个切片")
            
            # 获取向量
            embeddings = get_embeddings(batch_documents)
            
            # 写入数据库
            collection.add(
                embeddings=embeddings,
                documents=batch_documents,
                metadatas=batch_metadatas,
                ids=batch_ids
            )
            
            # 清空缓冲区
            batch_documents = []
            batch_metadatas = []
            batch_ids = []
    
    # 处理剩余数据
    if batch_documents:
        logger.info(f"   处理最后批次: {len(batch_documents)} 个切片")
        embeddings = get_embeddings(batch_documents)
        collection.add(
            embeddings=embeddings,
            documents=batch_documents,
            metadatas=batch_metadatas,
            ids=batch_ids
        )
    
    # 6. 统计信息
    final_count = collection.count()
    
    logger.info("=" * 60)
    logger.info("✅ V2.0 向量数据库构建完成!")
    logger.info(f"   处理 PDF: {total_pdfs}/{len(pdf_files)}")
    logger.info(f"   生成切片: {total_chunks}")
    logger.info(f"   数据库总量: {final_count}")
    logger.info(f"   失败文件: {len(failed_pdfs)}")
    if failed_pdfs:
        logger.info(f"   失败列表: {failed_pdfs[:10]}...")
    logger.info("=" * 60)


if __name__ == "__main__":
    text_splitter = None
    main()
