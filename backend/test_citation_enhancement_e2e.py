"""
端到端测试：引用位置增强功能
运行环境: cd backend && conda run -n py310 python test_citation_enhancement_e2e.py
"""
import sys
import os

# 添加backend目录到Python路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from agents.experts.semantic_expert import SemanticExpert
from repositories.vector_repository import VectorRepository
from services.llm_service import LLMService


def test_citation_enhancement():
    """测试引用位置增强功能"""
    print("="*80)
    print("🧪 引用位置增强功能 - 端到端测试")
    print("="*80)
    
    # 初始化组件
    print("\n📦 初始化组件...")
    vector_repo = VectorRepository()
    llm_service = LLMService()
    semantic_expert = SemanticExpert(vector_repo=vector_repo, llm_service=llm_service)
    
    # 测试问题
    question = "磷酸铁锂的电压是多少"
    print(f"\n❓ 测试问题: {question}")
    
    # 执行查询
    print("\n🔍 执行查询...")
    result = semantic_expert.query_with_details(question, top_k=20, load_pdf=False)
    
    # 检查结果
    print("\n📊 检查结果...")
    
    answer = result.get('answer', '')
    doi_locations = result.get('doi_locations', {})
    pdf_info = result.get('pdf_info', {})
    
    print(f"\n✅ 答案长度: {len(answer)} 字符")
    print(f"✅ 找到的文献数: {pdf_info.get('documents_found', 0)}")
    print(f"✅ DOI位置映射数: {len(doi_locations)}")
    
    # 显示doi_locations详情
    if doi_locations:
        print(f"\n📍 引用位置详情:")
        for doi, locations in doi_locations.items():
            print(f"\n  DOI: {doi}")
            print(f"  引用位置数: {len(locations)}")
            for i, loc in enumerate(locations[:2], 1):  # 只显示前2个
                print(f"\n    [{i}] 页码: {loc.get('page')}, 段落: {loc.get('chunk_index_in_page')}")
                print(f"        相似度: {loc.get('similarity'):.3f}")
                print(f"        置信度: {loc.get('confidence')}")
                print(f"        答案句子: {loc.get('answer_sentence', '')[:50]}...")
                print(f"        原文片段: {loc.get('source_text', '')[:50]}...")
                if loc.get('has_number'):
                    print(f"        📊 含数值")
                if loc.get('has_unit'):
                    print(f"        📏 含单位")
    else:
        print("\n⚠️  警告: 没有找到引用位置")
    
    # 验证覆盖率
    print(f"\n📈 覆盖率分析:")
    documents_found = pdf_info.get('documents_found', 0)
    if documents_found > 0:
        # 提取前5个DOI作为参考文献列表
        search_result = semantic_expert.search(question, top_k=20, with_scores=True)
        if search_result.get('success'):
            reference_dois = []
            for doc in search_result['documents'][:5]:
                meta = doc.get('metadata', {})
                doi = meta.get('doi') or meta.get('DOI')
                if doi and doi != 'N/A':
                    reference_dois.append(doi)
            
            print(f"  参考文献列表: {len(reference_dois)} 个DOI")
            print(f"  有引用位置的DOI: {len(doi_locations)} 个")
            
            covered = len(doi_locations)
            total = len(reference_dois)
            coverage = (covered / total * 100) if total > 0 else 0
            print(f"  覆盖率: {coverage:.1f}%")
            
            # 检查哪些DOI没有引用位置
            missing_dois = set(reference_dois) - set(doi_locations.keys())
            if missing_dois:
                print(f"\n  ⚠️  未覆盖的DOI:")
                for doi in missing_dois:
                    print(f"    - {doi}")
            else:
                print(f"\n  ✅ 所有参考文献DOI都有引用位置！")
    
    print("\n" + "="*80)
    print("✅ 测试完成")
    print("="*80)


if __name__ == "__main__":
    test_citation_enhancement()
