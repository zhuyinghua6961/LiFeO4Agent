#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试向量检索质量
检查检索到的文献是否与问题相关
"""
import chromadb
import requests

# 配置
CHROMA_PATH = "/Users/zhuyinghua/Desktop/agent/main/vector_database"
BGE_API_URL = "http://hf2d8696.natapp1.cc/v1/embeddings"

def generate_embedding(text: str):
    """生成embedding"""
    response = requests.post(BGE_API_URL, json={"input": [text]}, timeout=30)
    return response.json()["data"][0]["embedding"]

def test_search(question: str, top_k: int = 5):
    """测试搜索质量"""
    print("=" * 80)
    print(f"🔍 测试问题: {question}")
    print("=" * 80)
    
    # 连接ChromaDB
    print(f"\n连接向量数据库: {CHROMA_PATH}")
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection("literature")
    print(f"✅ 数据库文档数: {collection.count()}")
    
    # 生成query embedding
    print("\n生成查询向量...")
    query_embedding = generate_embedding(question)
    print(f"✅ 向量维度: {len(query_embedding)}")
    
    # 搜索
    print(f"\n搜索Top {top_k}相关文献...")
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    
    # 分析结果
    documents = results.get('documents', [[]])[0]
    metadatas = results.get('metadatas', [[]])[0]
    distances = results.get('distances', [[]])[0]
    
    print(f"\n📊 检索到 {len(documents)} 篇文献:\n")
    
    for i, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances), 1):
        score = 1 - distance if distance <= 1 else 0
        doi = metadata.get('DOI', metadata.get('doi', 'N/A'))
        
        print(f"[{i}] 相似度: {score:.4f}")
        print(f"    DOI: {doi}")
        print(f"    内容预览: {doc[:200]}...")
        print()
        
        # 检查关键词
        keywords = ["磷酸铁锂", "LiFePO4", "LFP", "锂离子电池", "lithium", "battery"]
        found_keywords = [kw for kw in keywords if kw.lower() in doc.lower()]
        if found_keywords:
            print(f"    ✅ 包含关键词: {', '.join(found_keywords)}")
        else:
            print(f"    ⚠️  未找到相关关键词 - 可能不相关!")
        print("-" * 80)

if __name__ == "__main__":
    # 测试几个问题
    test_questions = [
        "磷酸铁锂的电压是多少",
        "LiFePO4的合成方法",
        "锂离子电池正极材料"
    ]
    
    for question in test_questions:
        test_search(question, top_k=5)
        print("\n\n")
