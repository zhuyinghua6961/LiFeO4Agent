"""
属性测试：SemanticExpert 回退逻辑
Feature: query-expansion-reranking, Property 8: Fallback preserves functionality
Validates: Requirements 3.5, 6.5
"""
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import Mock, MagicMock, patch
import logging

from backend.agents.experts.semantic_expert import SemanticExpert
from backend.repositories.vector_repository import VectorRepository
from backend.services.llm_service import LLMService

logger = logging.getLogger(__name__)


# 生成器：生成有效的查询字符串
@st.composite
def valid_query(draw):
    """生成有效的查询字符串"""
    # 生成1-100个字符的非空字符串
    query = draw(st.text(min_size=1, max_size=100))
    # 确保不是纯空白
    if query.strip():
        return query.strip()
    return "测试查询"  # 回退到默认查询


class TestFallbackProperties:
    """测试回退逻辑的属性"""
    
    @pytest.fixture
    def mock_vector_repo(self):
        """创建mock的向量仓储"""
        repo = Mock(spec=VectorRepository)
        
        # Mock search方法返回成功结果
        repo.search.return_value = {
            "success": True,
            "documents": ["测试文档1", "测试文档2"],
            "metadatas": [
                {"doi": "10.1021/test1", "title": "Test Paper 1"},
                {"doi": "10.1021/test2", "title": "Test Paper 2"}
            ],
            "distances": [0.2, 0.3],
            "ids": ["id1", "id2"]
        }
        
        # Mock collection
        mock_collection = MagicMock()
        repo._collection = mock_collection
        
        return repo
    
    @pytest.fixture
    def mock_llm_service(self):
        """创建mock的LLM服务"""
        llm = Mock(spec=LLMService)
        
        # Mock generate方法
        llm.generate.return_value = "Test translation"
        
        # Mock invoke方法
        mock_response = Mock()
        mock_response.content = "Test response"
        llm.invoke.return_value = mock_response
        
        return llm
    
    @pytest.fixture
    def semantic_expert_with_mocks(self, mock_vector_repo, mock_llm_service):
        """创建带mock的SemanticExpert实例"""
        with patch('backend.agents.experts.semantic_expert.requests.post') as mock_post:
            # Mock BGE API响应
            mock_response = Mock()
            mock_response.json.return_value = {
                "data": [{"embedding": [0.1] * 1024}]
            }
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response
            
            # Mock句子数据库初始化 - chromadb在_init_sentence_db方法内部导入
            with patch('chromadb.PersistentClient') as mock_chromadb:
                # Mock chromadb client
                mock_client = Mock()
                mock_collection = Mock()
                mock_collection.count.return_value = 1000
                mock_client.get_collection.return_value = mock_collection
                mock_chromadb.return_value = mock_client
                
                expert = SemanticExpert(
                    vector_repo=mock_vector_repo,
                    llm_service=mock_llm_service
                )
                
                # 确保组件未初始化（模拟组件不可用的情况）
                expert._query_expander = None
                expert._multi_query_retriever = None
                expert._sentence_reranker = None
                
                return expert
    
    @given(query=valid_query())
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_fallback_when_expansion_unavailable(
        self,
        query,
        semantic_expert_with_mocks
    ):
        """
        Property 8: 当查询扩展组件不可用时，系统应回退到原始search方法并返回有效结果
        
        For any query, if expansion components are unavailable,
        the system should fall back to the original search method
        and still return valid results.
        """
        expert = semantic_expert_with_mocks
        
        # 确保扩展组件不可用
        assert expert._query_expander is None
        assert expert._multi_query_retriever is None
        
        # Mock BGE API
        with patch('backend.agents.experts.semantic_expert.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "data": [{"embedding": [0.1] * 1024}]
            }
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response
            
            # 调用search_with_expansion（应该回退到search）
            result = expert.search_with_expansion(
                question=query,
                top_k=10,
                enable_expansion=True,
                enable_reranking=True
            )
            
            # 验证：即使组件不可用，仍然返回成功结果
            assert result is not None, "结果不应为None"
            assert isinstance(result, dict), "结果应该是字典"
            assert result.get("success") is True, f"应该返回成功结果，但得到: {result}"
            
            # 验证：返回了文档
            assert "documents" in result, "结果应包含documents字段"
            documents = result["documents"]
            assert isinstance(documents, list), "documents应该是列表"
            assert len(documents) > 0, "应该返回至少一个文档"
            
            # 验证：包含必要的元数据
            assert "expert" in result, "结果应包含expert字段"
            assert result["expert"] == "semantic", "expert应该是semantic"
    
    @given(query=valid_query())
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_fallback_when_expansion_fails(
        self,
        query,
        mock_vector_repo,
        mock_llm_service
    ):
        """
        Property 8: 当查询扩展失败时，系统应回退到原始查询并返回有效结果
        
        For any query, if expansion fails during execution,
        the system should fall back to the original query
        and still return valid results.
        """
        with patch('backend.agents.experts.semantic_expert.requests.post') as mock_post:
            # Mock BGE API响应
            mock_response = Mock()
            mock_response.json.return_value = {
                "data": [{"embedding": [0.1] * 1024}]
            }
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response
            
            # Mock句子数据库
            with patch('chromadb.PersistentClient') as mock_chromadb:
                mock_client = Mock()
                mock_collection = Mock()
                mock_collection.count.return_value = 1000
                mock_client.get_collection.return_value = mock_collection
                mock_chromadb.return_value = mock_client
                
                expert = SemanticExpert(
                    vector_repo=mock_vector_repo,
                    llm_service=mock_llm_service
                )
                
                # Mock query_expander使其抛出异常
                if expert._query_expander:
                    expert._query_expander.expand = Mock(side_effect=Exception("扩展失败"))
                
                # 调用search_with_expansion
                result = expert.search_with_expansion(
                    question=query,
                    top_k=10,
                    enable_expansion=True,
                    enable_reranking=False
                )
                
                # 验证：即使扩展失败，仍然返回成功结果
                assert result is not None, "结果不应为None"
                assert isinstance(result, dict), "结果应该是字典"
                assert result.get("success") is True, f"应该返回成功结果（回退），但得到: {result}"
                
                # 验证：返回了文档
                assert "documents" in result, "结果应包含documents字段"
                documents = result["documents"]
                assert isinstance(documents, list), "documents应该是列表"
                assert len(documents) > 0, "应该返回至少一个文档"
                
                # 验证：expansion_info应该包含错误信息或回退标记
                if "expansion_info" in result:
                    expansion_info = result["expansion_info"]
                    # 如果有expansion_info，应该标记了错误或回退
                    assert "error" in expansion_info or "fallback" in expansion_info, \
                        "expansion_info应该包含错误或回退信息"
    
    @given(query=valid_query())
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_fallback_when_reranking_fails(
        self,
        query,
        mock_vector_repo,
        mock_llm_service
    ):
        """
        Property 8: 当重排序失败时，系统应使用原始排序并返回有效结果
        
        For any query, if reranking fails during execution,
        the system should use the original ranking
        and still return valid results.
        """
        with patch('backend.agents.experts.semantic_expert.requests.post') as mock_post:
            # Mock BGE API响应
            mock_response = Mock()
            mock_response.json.return_value = {
                "data": [{"embedding": [0.1] * 1024}]
            }
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response
            
            # Mock句子数据库
            with patch('chromadb.PersistentClient') as mock_chromadb:
                mock_client = Mock()
                mock_collection = Mock()
                mock_collection.count.return_value = 1000
                mock_client.get_collection.return_value = mock_collection
                mock_chromadb.return_value = mock_client
                
                expert = SemanticExpert(
                    vector_repo=mock_vector_repo,
                    llm_service=mock_llm_service
                )
                
                # Mock sentence_reranker使其抛出异常
                if expert._sentence_reranker:
                    expert._sentence_reranker.rerank = Mock(side_effect=Exception("重排序失败"))
                
                # 调用search_with_expansion
                result = expert.search_with_expansion(
                    question=query,
                    top_k=10,
                    enable_expansion=False,
                    enable_reranking=True
                )
                
                # 验证：即使重排序失败，仍然返回成功结果
                assert result is not None, "结果不应为None"
                assert isinstance(result, dict), "结果应该是字典"
                assert result.get("success") is True, f"应该返回成功结果（回退），但得到: {result}"
                
                # 验证：返回了文档
                assert "documents" in result, "结果应包含documents字段"
                documents = result["documents"]
                assert isinstance(documents, list), "documents应该是列表"
                assert len(documents) > 0, "应该返回至少一个文档"
                
                # 验证：reranking_info应该包含错误信息或回退标记
                if "reranking_info" in result:
                    reranking_info = result["reranking_info"]
                    # 如果有reranking_info，应该标记了错误或回退
                    assert "error" in reranking_info or "fallback" in reranking_info, \
                        "reranking_info应该包含错误或回退信息"
    
    @given(query=valid_query())
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_fallback_preserves_document_structure(
        self,
        query,
        semantic_expert_with_mocks
    ):
        """
        Property 8: 回退时返回的文档结构应该与正常情况一致
        
        For any query, documents returned during fallback
        should have the same structure as normal results.
        """
        expert = semantic_expert_with_mocks
        
        with patch('backend.agents.experts.semantic_expert.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "data": [{"embedding": [0.1] * 1024}]
            }
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response
            
            # 调用search_with_expansion（会回退）
            result = expert.search_with_expansion(
                question=query,
                top_k=10
            )
            
            # 验证文档结构
            if result.get("success") and result.get("documents"):
                documents = result["documents"]
                
                for doc in documents:
                    # 每个文档应该是字典
                    assert isinstance(doc, dict), "每个文档应该是字典"
                    
                    # 应该包含基本字段
                    assert "content" in doc or "text" in doc, \
                        "文档应该包含content或text字段"
                    
                    # 如果有metadata，应该是字典
                    if "metadata" in doc:
                        assert isinstance(doc["metadata"], dict), \
                            "metadata应该是字典"
                    
                    # 如果有score，应该是数字
                    if "score" in doc:
                        assert isinstance(doc["score"], (int, float)), \
                            "score应该是数字"
                        assert 0 <= doc["score"] <= 1, \
                            "score应该在0-1范围内"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
