#!/usr/bin/env python3
"""
导入 json/ 目录的文献摘要数据到 ChromaDB
"""
import json
import os
from pathlib import Path
import chromadb
from chromadb.config import Settings

# 从环境变量读取配置
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", str(Path(__file__).parent.parent.parent / "vector_database"))


def import_json_data(json_dir: str, collection_name: str = "literature"):
    """
    从 json 目录导入数据到 ChromaDB
    
    Args:
        json_dir: json 文件目录
        collection_name: ChromaDB 集合名称
    """
    print(f"📁 数据源目录: {json_dir}")
    print(f"📁 ChromaDB 路径: {VECTOR_DB_PATH}")
    print(f"📦 集合名称: {collection_name}")
    print("-" * 50)
    
    # 获取所有 json 文件
    json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
    print(f"📄 找到 {len(json_files)} 个 JSON 文件")
    
    if len(json_files) == 0:
        print("❌ 没有找到 JSON 文件")
        return
    
    # 初始化 ChromaDB
    print("\n🔌 连接 ChromaDB...")
    client = chromadb.PersistentClient(
        path=VECTOR_DB_PATH,
        settings=Settings(anonymized_telemetry=False)
    )
    
    # 先删除旧集合（如果存在）
    try:
        client.delete_collection(collection_name)
        print(f"🗑️  已删除旧集合: {collection_name}")
    except Exception:
        pass
    
    # 创建新集合
    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )
    count_before = 0
    
    # 导入数据
    documents = []
    metadatas = []
    embeddings = []
    ids = []
    
    total_items = 0
    batch_size = 50
    
    for i, json_file in enumerate(sorted(json_files)):
        filepath = os.path.join(json_dir, json_file)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 处理数据（可能是列表或单个对象）
            if isinstance(data, list):
                items = data
            else:
                items = [data]
            
            for item in items:
                text = item.get('text', '')
                embedding = item.get('embedding', [])
                metadata = item.get('metadata', {})
                
                if not text or not embedding:
                    continue
                
                # 生成 ID（使用文件名作为基础）
                doc_id = f"{Path(json_file).stem}_{total_items}"
                
                documents.append(text)
                embeddings.append(embedding)
                metadatas.append({
                    **metadata,
                    'source_file': json_file,
                    'imported_at': str(os.path.getmtime(__file__))
                })
                ids.append(doc_id)
                total_items += 1
            
            # 批量导入
            if total_items >= batch_size:
                print(f"  导入进度: {i+1}/{len(json_files)} ({total_items} 条)")
                collection.add(
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    ids=ids
                )
                documents = []
                metadatas = []
                embeddings = []
                ids = []
                
        except Exception as e:
            print(f"  ⚠️ 处理文件 {json_file} 失败: {e}")
            continue
    
    # 导入剩余数据
    if documents:
        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
    
    print("-" * 50)
    count_after = collection.count()
    print(f"✅ 导入完成!")
    print(f"   导入前文档数: {count_before}")
    print(f"   导入后文档数: {count_after}")
    print(f"   新增文档数: {count_after - count_before}")
    
    client.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='导入 JSON 数据到 ChromaDB')
    parser.add_argument('--json_dir', type=str, default='../../../json',
                        help='JSON 文件目录')
    parser.add_argument('--collection', type=str, default='literature',
                        help='ChromaDB 集合名称')
    
    args = parser.parse_args()
    
    # 转换相对路径为绝对路径（从 backend/scripts 开始）
    json_dir = Path(__file__).parent.parent.parent / args.json_dir
    json_dir = json_dir.resolve()
    
    import_json_data(str(json_dir), args.collection)


if __name__ == '__main__':
    main()
