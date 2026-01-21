"""
MultiQueryRetriever 属性测试（Property-Based Testing）
使用 Hypothesis 进行属性测试
"""
import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock
from backend.agents.multi_query_retriever import MultiQueryRetriever


# 定义文档策略
def document_strategy():
    """生成文档的策略"""
    return st.fixed_dictionaries({
        "text": st.text(min_size=1, max_size=100),
        "metadata": st.fixed_dictionaries({
            "doi": st.one_of(
                st.none(),
                st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='./'))
            )
        }),
        "score": st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        "id": st.text(min_size=1, max_size=20)
    })


class TestMultiQueryRetrieverProperties:
    """MultiQueryRetriever 属性测试类"""
    
    def _create_retriever(self):
        """创建 MultiQueryRetriever 实例"""
        mock_repo = Mock()
        return MultiQueryRetriever(
            vector_repo=mock_repo,
            bge_api_url="http://test-api:8001/v1/embeddings"
        )
    
    @given(st.lists(document_strategy(), min_size=0, max_size=50))
    @settings(max_examples=100, deadline=None)
    def test_deduplication_idempotent(self, documents):
        """
        **Feature: query-expansion-reranking, Property 2: Deduplication is idempotent**
        **Validates: Requirements 1.4**
        
        Property: 对任意文档列表，去重操作应该是幂等的
        即：deduplicate(deduplicate(docs)) == deduplicate(docs)
        """
        retriever = self._create_retriever()
        
        # 第一次去重
        deduped_once = retriever.deduplicate_by_doi(documents)
        
        # 第二次去重
        deduped_twice = retriever.deduplicate_by_doi(deduped_once)
        
        # 验证幂等性：两次去重的结果应该相同
        assert len(deduped_once) == len(deduped_twice)
        
        # 验证文档内容相同（按DOI比较）
        dois_once = [doc["metadata"].get("doi") or doc["id"] for doc in deduped_once]
        dois_twice = [doc["metadata"].get("doi") or doc["id"] for doc in deduped_twice]
        assert dois_once == dois_twice
        
        # 验证分数相同
        scores_once = [doc["score"] for doc in deduped_once]
        scores_twice = [doc["score"] for doc in deduped_twice]
        assert scores_once == scores_twice
    
    @given(st.lists(document_strategy(), min_size=0, max_size=50))
    @settings(max_examples=100, deadline=None)
    def test_deduplication_preserves_best_score(self, documents):
        """
        Property: 去重应该保留每个DOI的最高分数文档
        （仅对有DOI的文档进行验证）
        """
        retriever = self._create_retriever()
        
        if not documents:
            return
        
        deduped = retriever.deduplicate_by_doi(documents)
        
        # 构建原始文档的DOI到最高分数的映射（仅包含有DOI的文档）
        doi_to_max_score = {}
        for doc in documents:
            doi = doc["metadata"].get("doi") or doc["metadata"].get("DOI")
            if doi:  # 只考虑有DOI的文档
                if doi not in doi_to_max_score or doc["score"] > doi_to_max_score[doi]:
                    doi_to_max_score[doi] = doc["score"]
        
        # 验证去重后有DOI的文档都是最高分数
        for doc in deduped:
            doi = doc["metadata"].get("doi") or doc["metadata"].get("DOI")
            if doi:  # 只验证有DOI的文档
                assert doc["score"] == doi_to_max_score[doi]
    
    @given(st.lists(document_strategy(), min_size=0, max_size=50))
    @settings(max_examples=100, deadline=None)
    def test_deduplication_reduces_or_maintains_count(self, documents):
        """
        Property: 去重后的文档数量应该小于或等于原始数量
        """
        retriever = self._create_retriever()
        
        deduped = retriever.deduplicate_by_doi(documents)
        assert len(deduped) <= len(documents)
    
    @given(st.lists(document_strategy(), min_size=0, max_size=50))
    @settings(max_examples=100, deadline=None)
    def test_deduplication_sorted_by_score(self, documents):
        """
        Property: 去重后的文档应该按分数降序排列
        """
        retriever = self._create_retriever()
        
        deduped = retriever.deduplicate_by_doi(documents)
        
        # 验证排序
        for i in range(len(deduped) - 1):
            assert deduped[i]["score"] >= deduped[i + 1]["score"]
    
    @given(st.lists(document_strategy(), min_size=0, max_size=50))
    @settings(max_examples=100, deadline=None)
    def test_doi_extraction_completeness(self, documents):
        """
        **Feature: query-expansion-reranking, Property 10: DOI extraction completeness**
        **Validates: Requirements 1.4**
        
        Property: 对任意文档列表，如果文档有DOI字段（'doi' 或 'DOI'），
        它应该被提取到候选DOI池中
        """
        retriever = self._create_retriever()
        
        if not documents:
            return
        
        # 收集所有有效的DOI
        expected_dois = set()
        for doc in documents:
            doi = doc["metadata"].get("doi") or doc["metadata"].get("DOI")
            if doi:
                expected_dois.add(doi)
        
        # 去重后获取DOI
        deduped = retriever.deduplicate_by_doi(documents)
        actual_dois = set()
        for doc in deduped:
            doi = doc["metadata"].get("doi") or doc["metadata"].get("DOI")
            if doi:
                actual_dois.add(doi)
        
        # 验证：所有有效的DOI都应该在去重后的结果中
        assert expected_dois == actual_dois
