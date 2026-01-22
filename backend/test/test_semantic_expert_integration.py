"""
测试SemanticExpert与EnhancedDOIInserter的集成
运行环境: conda run -n py310 pytest backend/test/test_semantic_expert_integration.py
"""
import pytest
from unittest.mock import Mock, MagicMock, patch


def test_extract_reference_dois():
    """测试提取参考文献DOI列表"""
    from backend.agents.experts.semantic_expert import SemanticExpert
    from backend.repositories.vector_repository import VectorRepository
    
    # 创建mock对象
    vector_repo = Mock(spec=VectorRepository)
    expert = SemanticExpert(vector_repo=vector_repo, llm_service=None)
    
    # 测试数据
    documents = [
        {"metadata": {"doi": "10.1016/j.jpowsour.2022.001"}},
        {"metadata": {"DOI": "10.1016/j.jpowsour.2022.002"}},
        {"metadata": {"doi": "10.1016/j.jpowsour.2022.003"}},
        {"metadata": {"doi": "N/A"}},  # 应该被过滤
        {"metadata": {"doi": "10.1016/j.jpowsour.2022.004"}},
        {"metadata": {"doi": "10.1016/j.jpowsour.2022.005"}},
        {"metadata": {"doi": "10.1016/j.jpowsour.2022.006"}},
    ]
    
    # 提取top-5
    reference_dois = expert._extract_reference_dois(documents, top_k=5)
    
    assert len(reference_dois) == 5
    assert "10.1016/j.jpowsour.2022.001" in reference_dois
    assert "10.1016/j.jpowsour.2022.002" in reference_dois
    assert "10.1016/j.jpowsour.2022.003" in reference_dois
    assert "10.1016/j.jpowsour.2022.004" in reference_dois
    assert "10.1016/j.jpowsour.2022.005" in reference_dois
    assert "N/A" not in reference_dois


def test_extract_reference_dois_with_duplicates():
    """测试提取参考文献DOI列表（有重复）"""
    from backend.agents.experts.semantic_expert import SemanticExpert
    from backend.repositories.vector_repository import VectorRepository
    
    vector_repo = Mock(spec=VectorRepository)
    expert = SemanticExpert(vector_repo=vector_repo, llm_service=None)
    
    # 测试数据（有重复DOI）
    documents = [
        {"metadata": {"doi": "10.1016/j.jpowsour.2022.001"}},
        {"metadata": {"doi": "10.1016/j.jpowsour.2022.001"}},  # 重复
        {"metadata": {"doi": "10.1016/j.jpowsour.2022.002"}},
        {"metadata": {"doi": "10.1016/j.jpowsour.2022.003"}},
        {"metadata": {"doi": "10.1016/j.jpowsour.2022.004"}},
        {"metadata": {"doi": "10.1016/j.jpowsour.2022.005"}},
    ]
    
    reference_dois = expert._extract_reference_dois(documents, top_k=5)
    
    # 应该去重
    assert len(reference_dois) == 5
    assert reference_dois.count("10.1016/j.jpowsour.2022.001") == 1


def test_extract_reference_dois_insufficient():
    """测试提取参考文献DOI列表（文档不足）"""
    from backend.agents.experts.semantic_expert import SemanticExpert
    from backend.repositories.vector_repository import VectorRepository
    
    vector_repo = Mock(spec=VectorRepository)
    expert = SemanticExpert(vector_repo=vector_repo, llm_service=None)
    
    # 只有2个有效DOI
    documents = [
        {"metadata": {"doi": "10.1016/j.jpowsour.2022.001"}},
        {"metadata": {"doi": "10.1016/j.jpowsour.2022.002"}},
        {"metadata": {"doi": "N/A"}},
    ]
    
    reference_dois = expert._extract_reference_dois(documents, top_k=5)
    
    # 应该只返回2个
    assert len(reference_dois) == 2


@patch('backend.agents.enhanced_doi_inserter.EnhancedDOIInserter')
def test_insert_dois_with_enhanced_inserter(mock_inserter_class):
    """测试使用EnhancedDOIInserter插入DOI"""
    from backend.agents.experts.semantic_expert import SemanticExpert
    from backend.repositories.vector_repository import VectorRepository
    from backend.models.citation_location import CitationLocation
    
    # 创建mock对象
    vector_repo = Mock(spec=VectorRepository)
    vector_repo._collection = Mock()  # 模拟段落级数据库
    
    expert = SemanticExpert(vector_repo=vector_repo, llm_service=None)
    expert._sentence_collection = Mock()  # 模拟句子级数据库
    expert._bge_api_url = "http://localhost:8000/embeddings"
    
    # 模拟EnhancedDOIInserter的返回值
    mock_inserter = Mock()
    mock_inserter_class.return_value = mock_inserter
    
    mock_citation = CitationLocation(
        doi="10.1016/j.jpowsour.2022.001",
        answer_sentence="测试句子",
        answer_sentence_index=0,
        source_text="原文",
        page=1,
        similarity=0.8
    )
    
    mock_inserter.insert_dois_with_full_coverage.return_value = (
        "测试答案 (doi=10.1016/j.jpowsour.2022.001)",
        {"10.1016/j.jpowsour.2022.001": [mock_citation]}
    )
    
    # 测试数据
    answer = "测试答案"
    documents = [{"metadata": {"doi": "10.1016/j.jpowsour.2022.001"}}]
    reference_dois = ["10.1016/j.jpowsour.2022.001"]
    
    # 调用方法
    answer_with_dois, doi_locations = expert._insert_dois_with_enhanced_inserter(
        answer=answer,
        documents=documents,
        reference_dois=reference_dois
    )
    
    # 验证
    assert "(doi=10.1016/j.jpowsour.2022.001)" in answer_with_dois
    assert "10.1016/j.jpowsour.2022.001" in doi_locations
    assert len(doi_locations["10.1016/j.jpowsour.2022.001"]) == 1
    
    # 验证EnhancedDOIInserter被正确调用
    mock_inserter_class.assert_called_once()
    mock_inserter.insert_dois_with_full_coverage.assert_called_once_with(
        answer=answer,
        documents=documents,
        reference_dois=reference_dois,
        similarity_threshold=0.3
    )


def test_insert_dois_by_embedding_with_reference_dois():
    """测试_insert_dois_by_embedding方法接受reference_dois参数"""
    from backend.agents.experts.semantic_expert import SemanticExpert
    from backend.repositories.vector_repository import VectorRepository
    
    vector_repo = Mock(spec=VectorRepository)
    vector_repo._collection = Mock()
    
    expert = SemanticExpert(vector_repo=vector_repo, llm_service=None)
    expert._sentence_collection = Mock()
    expert._bge_api_url = "http://localhost:8000/embeddings"
    
    # Mock _insert_dois_with_enhanced_inserter
    with patch.object(expert, '_insert_dois_with_enhanced_inserter') as mock_method:
        mock_method.return_value = ("答案", {})
        
        answer = "测试答案"
        documents = [{"metadata": {"doi": "10.1016/j.jpowsour.2022.001"}}]
        reference_dois = ["10.1016/j.jpowsour.2022.001"]
        
        # 调用方法
        result = expert._insert_dois_by_embedding(
            answer=answer,
            documents=documents,
            reference_dois=reference_dois
        )
        
        # 验证调用了增强的插入器
        mock_method.assert_called_once()


def test_insert_dois_by_embedding_auto_extract_reference_dois():
    """测试_insert_dois_by_embedding自动提取参考文献DOI"""
    from backend.agents.experts.semantic_expert import SemanticExpert
    from backend.repositories.vector_repository import VectorRepository
    
    vector_repo = Mock(spec=VectorRepository)
    vector_repo._collection = Mock()
    
    expert = SemanticExpert(vector_repo=vector_repo, llm_service=None)
    expert._sentence_collection = Mock()
    expert._bge_api_url = "http://localhost:8000/embeddings"
    
    # Mock方法
    with patch.object(expert, '_extract_reference_dois') as mock_extract:
        with patch.object(expert, '_insert_dois_with_enhanced_inserter') as mock_insert:
            mock_extract.return_value = ["doi1", "doi2"]
            mock_insert.return_value = ("答案", {})
            
            answer = "测试答案"
            documents = [{"metadata": {"doi": "doi1"}}, {"metadata": {"doi": "doi2"}}]
            
            # 不提供reference_dois参数
            result = expert._insert_dois_by_embedding(
                answer=answer,
                documents=documents
            )
            
            # 验证自动提取了参考文献DOI
            mock_extract.assert_called_once_with(documents, top_k=5)
            mock_insert.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
