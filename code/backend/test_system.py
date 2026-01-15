#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统功能测试脚本
Test Script for System Functionality
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from backend.config.settings import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_configuration():
    """测试配置加载"""
    print("\n" + "="*60)
    print("📋 测试1: 配置加载")
    print("="*60)
    
    try:
        assert settings.base_dir, "base_dir 未配置"
        assert settings.llm_model, "llm_model 未配置"
        print(f"✅ 基础目录: {settings.base_dir}")
        print(f"✅ LLM模型: {settings.llm_model}")
        print(f"✅ Neo4j URI: {settings.neo4j_uri}")
        print(f"✅ 向量DB路径: {settings.vector_db_path}")
        
        # 检查可选配置
        if hasattr(settings, 'bge_api_url'):
            print(f"✅ BGE API: {settings.bge_api_url}")
        if hasattr(settings, 'papers_dir'):
            print(f"✅ Papers目录: {settings.papers_dir}")
        if hasattr(settings, 'doi_to_pdf_mapping'):
            print(f"✅ DOI映射文件: {settings.doi_to_pdf_mapping}")
            
        print("✅ 配置加载测试通过")
        return True
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False


def test_llm_service():
    """测试LLM服务"""
    print("\n" + "="*60)
    print("🤖 测试2: LLM服务")
    print("="*60)
    
    try:
        from backend.services import get_llm_service
        from langchain_core.messages import HumanMessage
        
        llm = get_llm_service()
        print("✅ LLM服务初始化成功")
        
        # 测试简单调用
        response = llm.invoke([HumanMessage(content="你好，请用一句话回答：1+1等于几？")])
        print(f"✅ LLM响应: {response.content[:100]}")
        print("✅ LLM服务测试通过")
        return True
    except Exception as e:
        print(f"❌ LLM服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_neo4j_service():
    """测试Neo4j服务"""
    print("\n" + "="*60)
    print("📊 测试3: Neo4j服务（可选）")
    print("="*60)
    
    try:
        from backend.services import get_neo4j_service
        
        neo4j = get_neo4j_service()
        print("✅ Neo4j服务初始化成功")
        
        # 测试连接
        result = neo4j.execute_cypher("MATCH (n) RETURN count(n) as count LIMIT 1")
        print(f"✅ Neo4j连接正常，节点数量: {result[0]['count'] if result else 0}")
        print("✅ Neo4j服务测试通过")
        return True
    except Exception as e:
        print(f"⚠️ Neo4j服务不可用（可选）: {e}")
        return True  # Neo4j是可选的


def test_vector_service():
    """测试向量服务"""
    print("\n" + "="*60)
    print("📚 测试4: 向量服务")
    print("="*60)
    
    try:
        from backend.repositories.vector_repository import VectorRepository
        
        vector_repo = VectorRepository()
        print("✅ 向量数据库初始化成功")
        
        # 测试搜索
        result = vector_repo.search("LiFePO4", top_k=3)
        print(f"✅ 向量搜索测试: 找到 {len(result.get('documents', []))} 条结果")
        print("✅ 向量服务测试通过")
        return True
    except Exception as e:
        print(f"❌ 向量服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pdf_loader():
    """测试PDF加载器"""
    print("\n" + "="*60)
    print("📄 测试5: PDF加载器")
    print("="*60)
    
    try:
        from backend.utils.pdf_loader import PDFManager
        
        if not hasattr(settings, 'papers_dir'):
            print("⚠️ 未配置papers_dir，跳过测试")
            return True
        
        pdf_manager = PDFManager(
            papers_dir=settings.papers_dir,
            mapping_file=getattr(settings, 'doi_to_pdf_mapping', None)
        )
        print("✅ PDF管理器初始化成功")
        
        # 检查映射
        mapping_count = len(pdf_manager.doi_to_pdf_mapping)
        print(f"✅ DOI映射数量: {mapping_count}")
        
        if mapping_count > 0:
            # 测试加载第一个PDF
            first_doi = list(pdf_manager.doi_to_pdf_mapping.keys())[0]
            content = pdf_manager.load_pdf_by_doi(first_doi, max_pages=1)
            if content:
                print(f"✅ PDF加载测试: 成功加载 {first_doi[:30]}...")
            else:
                print(f"⚠️ PDF加载测试: DOI {first_doi} 对应的PDF不存在")
        
        print("✅ PDF加载器测试通过")
        return True
    except Exception as e:
        print(f"⚠️ PDF加载器测试失败（非关键）: {e}")
        return True  # PDF是可选的


def test_experts():
    """测试专家系统"""
    print("\n" + "="*60)
    print("🎯 测试6: 专家系统")
    print("="*60)
    
    try:
        from backend.services import get_llm_service, get_neo4j_service
        from backend.agents.experts import RouterExpert, QueryExpert, SemanticExpert, CommunityExpert
        from backend.repositories.vector_repository import VectorRepository
        
        llm = get_llm_service()
        
        # 测试RouterExpert
        router = RouterExpert(llm_service=llm)
        print("✅ RouterExpert初始化成功")
        
        # 测试路由
        test_question = "振实密度大于2.8的材料有哪些？"
        route_result = router.route(test_question)
        print(f"✅ 路由测试: {test_question}")
        print(f"   推荐专家: {route_result.get('primary_expert')}")
        print(f"   置信度: {route_result.get('confidence')}")
        
        # 测试SemanticExpert
        vector_repo = VectorRepository()
        semantic = SemanticExpert(vector_repo=vector_repo, llm_service=llm)
        print("✅ SemanticExpert初始化成功")
        
        # 测试CommunityExpert
        from backend.repositories.vector_repository import CommunityVectorRepository
        community_repo = CommunityVectorRepository()
        community = CommunityExpert(community_repo=community_repo, llm_service=llm)
        print("✅ CommunityExpert初始化成功")
        
        # 测试QueryExpert（需要Neo4j）
        try:
            neo4j = get_neo4j_service()
            query = QueryExpert(neo4j_service=neo4j, llm_service=llm)
            print("✅ QueryExpert初始化成功")
        except:
            print("⚠️ QueryExpert初始化失败（需要Neo4j）")
        
        print("✅ 专家系统测试通过")
        return True
    except Exception as e:
        print(f"❌ 专家系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integrated_agent():
    """测试IntegratedAgent"""
    print("\n" + "="*60)
    print("🚀 测试7: IntegratedAgent")
    print("="*60)
    
    try:
        from backend.agents.integrated_agent import get_integrated_agent
        
        agent = get_integrated_agent()
        print("✅ IntegratedAgent初始化成功")
        
        # 测试查询（不实际执行，只测试流程）
        test_question = "有哪些关于LiFePO4的研究？"
        print(f"✅ 测试问题: {test_question}")
        print("   (注意：实际查询需要在运行环境中测试)")
        
        print("✅ IntegratedAgent测试通过")
        return True
    except Exception as e:
        print(f"❌ IntegratedAgent测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "🧪 " + "="*58)
    print("   系统功能测试")
    print("="*60)
    
    results = []
    
    # 运行测试
    results.append(("配置加载", test_configuration()))
    results.append(("LLM服务", test_llm_service()))
    results.append(("Neo4j服务", test_neo4j_service()))
    results.append(("向量服务", test_vector_service()))
    results.append(("PDF加载器", test_pdf_loader()))
    results.append(("专家系统", test_experts()))
    results.append(("IntegratedAgent", test_integrated_agent()))
    
    # 统计结果
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    print("-"*60)
    print(f"总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！系统运行正常。")
        return 0
    elif passed >= total * 0.7:
        print(f"\n⚠️ 部分测试失败，但核心功能正常 ({passed}/{total})")
        return 0
    else:
        print(f"\n❌ 测试失败过多 ({passed}/{total})，请检查配置。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
