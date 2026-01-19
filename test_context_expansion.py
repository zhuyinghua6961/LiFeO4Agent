#!/usr/bin/env python3
"""测试V3上下文扩展功能"""
import sys
sys.path.insert(0, 'backend')

from repositories.vector_repository import get_vector_repository

print("=" * 80)
print("🔍 测试V3上下文扩展功能")
print("=" * 80)

repo = get_vector_repository()

# 获取一个样本段落
print("\n📋 获取样本段落...")
sample = repo._collection.get(limit=1, include=["metadatas"])
chunk_id = sample["ids"][0]
metadata = sample["metadatas"][0]

print(f"✅ 样本段落ID: {chunk_id}")
print(f"   DOI: {metadata.get('doi')}")
print(f"   页码: {metadata.get('page')}")
print(f"   页内序号: {metadata.get('chunk_index_in_page')}/{metadata.get('total_chunks_in_page')}")
print(f"   前向链接: {'有' if metadata.get('prev_chunk_id') else '无'}")
print(f"   后向链接: {'有' if metadata.get('next_chunk_id') else '无'}")

# 测试上下文扩展
print(f"\n🔗 测试上下文扩展（前后各2段）...")
context_result = repo.get_chunk_with_context(chunk_id, window=2)

if context_result.get('success'):
    print(f"✅ 上下文扩展成功！")
    print(f"   总段落数: {context_result['context_chunks']}")
    print(f"   主段落位置: 第{context_result['main_chunk_index']+1}个")
    print(f"   页面范围: 第{context_result['context_range']['start_page']}-{context_result['context_range']['end_page']}页")
    print(f"   段落范围: 全局索引{context_result['context_range']['start_chunk_global']}-{context_result['context_range']['end_chunk_global']}")
    print(f"\n📝 内容长度对比:")
    print(f"   主段落: {len(context_result['main_text'])} 字符")
    print(f"   完整上下文: {len(context_result['full_text'])} 字符")
    print(f"   扩展倍数: {len(context_result['full_text']) / len(context_result['main_text']):.1f}x")
    
    print(f"\n📄 主段落内容预览:")
    print(f"   {context_result['main_text'][:200]}...")
    
    print(f"\n📄 完整上下文预览:")
    print(f"   {context_result['full_text'][:300]}...")
else:
    print(f"❌ 上下文扩展失败: {context_result.get('error')}")

print("\n" + "=" * 80)
print("✅ 测试完成")
print("=" * 80)
