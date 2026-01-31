"""
测试向量数据库连接
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.repositories.vector_repository import get_vector_repository

def test_connection():
    """测试向量数据库连接"""
    print("=" * 80)
    print("  测试向量数据库连接")
    print("=" * 80)
    
    try:
        # 获取向量库实例
        repo = get_vector_repository()
        
        # 获取文档数量
        count = repo.get_count()
        print(f"\n✅ 连接成功！")
        print(f"📊 文档总数: {count:,}")
        
        # 获取一个样本文档
        result = repo._collection.get(limit=1, include=["documents", "metadatas"])
        if result and result.get("documents"):
            print(f"\n📄 样本文档:")
            print(f"   ID: {result['ids'][0]}")
            print(f"   内容: {result['documents'][0][:100]}...")
            print(f"   元数据: {result['metadatas'][0]}")
        
        print("\n" + "=" * 80)
        print("  测试完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 连接失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_connection()
