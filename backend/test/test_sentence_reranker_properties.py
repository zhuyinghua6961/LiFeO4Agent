"""
SentenceReranker 属性测试
使用 Hypothesis 进行基于属性的测试
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, patch
from backend.agents.sentence_reranker import SentenceReranker, RerankingResult


# 定义策略：生成候选文档
@st.composite
def candidate_document(draw):
    """生成单个候选文档"""
    doi = draw(st.one_of(
        st.just(None),  # 可能没有DOI
        st.text(min_size=10, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'P')))
    ))
    
    return {
        "text": draw(st.text(min_size=10, max_size=200)),
        "metadata": {
            "doi": doi,
            "title": draw(st.text(min_size=5, max_size=50))
        },
        "score": draw(st.floats(min_value=0.0, max_value=1.0)),
        "distance": draw(st.floats(min_value=0.0, max_value=1.0))
    }


@st.composite
def candidate_list(draw, min_size=1, max_size=50):
    """生成候选文档列表"""
    return draw(st.lists(
        candidate_document(),
        min_size=min_size,
        max_size=max_size
    ))


class TestSentenceRerankerProperties:
    """SentenceReranker 属性测试类"""
    
    def _create_mock_reranker(self):
        """创建模拟的reranker"""
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "documents": [[]],
            "distances": [[]],
            "metadatas": [[]]
        }
        
        reranker = SentenceReranker(
            sentence_collection=mock_collection,
            bge_api_url="http://test-api:8001/v1/embeddings"
        )
        return reranker
    
    @given(candidates=candidate_list(min_size=1, max_size=30))
    @settings(max_examples=100, deadline=None)
    @patch('requests.post')
    def test_property_reranking_preserves_all_candidates(self, mock_post, candidates):
        """
        **Feature: query-expansion-reranking, Property 3: Reranking preserves all candidates**
        **Validates: Requirements 2.4**
        
        Property: For any candidate list, reranking should return the same number of 
        documents (or fewer if top_k is specified), but never more.
        """
        # 过滤掉空文本的候选
        candidates = [c for c in candidates if c.get("text", "").strip()]
        assume(len(candidates) > 0)
        
        # 创建mock reranker
        mock_reranker = self._create_mock_reranker()
        
        # 模拟embedding生成
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1] * 1024}]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # 模拟句子查询
        def mock_query(*args, **kwargs):
            return {
                "documents": [["Sentence"]],
                "distances": [[0.2]],
                "metadatas": [[{"doi": "test"}]]
            }
        
        mock_reranker.sentence_collection.query.side_effect = mock_query
        
        # 测试不同的top_k值
        for top_k in [5, 10, len(candidates), len(candidates) + 10]:
            result = mock_reranker.rerank("test query", candidates, top_k=top_k)
            
            # 验证：返回的文档数量不应超过候选数量和top_k的最小值
            expected_max = min(len(candidates), top_k)
            assert len(result.documents) <= expected_max, \
                f"Reranking returned {len(result.documents)} documents, " \
                f"but should return at most {expected_max}"
            
            # 验证：返回的文档数量不应超过原始候选数量
            assert len(result.documents) <= len(candidates), \
                f"Reranking returned more documents ({len(result.documents)}) " \
                f"than candidates ({len(candidates)})"
    
    @given(
        candidates=candidate_list(min_size=1, max_size=30),
        top_k=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=100, deadline=None)
    @patch('requests.post')
    def test_property_reranking_respects_top_k(self, mock_post, candidates, top_k):
        """
        Property: Reranking should never return more than top_k documents.
        """
        # 过滤掉空文本的候选
        candidates = [c for c in candidates if c.get("text", "").strip()]
        assume(len(candidates) > 0)
        
        # 创建mock reranker
        mock_reranker = self._create_mock_reranker()
        
        # 模拟embedding生成
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1] * 1024}]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # 模拟句子查询
        mock_reranker.sentence_collection.query.return_value = {
            "documents": [["Sentence"]],
            "distances": [[0.2]],
            "metadatas": [[{"doi": "test"}]]
        }
        
        result = mock_reranker.rerank("test query", candidates, top_k=top_k)
        
        # 验证：返回的文档数量不应超过top_k
        assert len(result.documents) <= top_k, \
            f"Reranking returned {len(result.documents)} documents, " \
            f"but top_k was {top_k}"
    
    @given(candidates=candidate_list(min_size=1, max_size=30))
    @settings(max_examples=100, deadline=None)
    @patch('requests.post')
    def test_property_reranking_returns_valid_result(self, mock_post, candidates):
        """
        Property: Reranking should always return a valid RerankingResult object.
        """
        # 过滤掉空文本的候选
        candidates = [c for c in candidates if c.get("text", "").strip()]
        assume(len(candidates) > 0)
        
        # 创建mock reranker
        mock_reranker = self._create_mock_reranker()
        
        # 模拟embedding生成
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1] * 1024}]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # 模拟句子查询
        mock_reranker.sentence_collection.query.return_value = {
            "documents": [["Sentence"]],
            "distances": [[0.2]],
            "metadatas": [[{"doi": "test"}]]
        }
        
        result = mock_reranker.rerank("test query", candidates, top_k=10)
        
        # 验证：返回的是RerankingResult对象
        assert isinstance(result, RerankingResult)
        
        # 验证：必需字段存在
        assert hasattr(result, 'documents')
        assert hasattr(result, 'similarity_scores')
        assert hasattr(result, 'reranking_time')
        assert hasattr(result, 'top_3_changes')
        
        # 验证：字段类型正确
        assert isinstance(result.documents, list)
        assert isinstance(result.similarity_scores, dict)
        assert isinstance(result.reranking_time, float)
        assert isinstance(result.top_3_changes, list)
    
    @given(candidates=candidate_list(min_size=0, max_size=30))
    @settings(max_examples=50, deadline=None)
    def test_property_reranking_handles_empty_candidates(self, candidates):
        """
        Property: Reranking should handle empty candidate lists gracefully.
        """
        # 创建mock reranker
        mock_reranker = self._create_mock_reranker()
        
        result = mock_reranker.rerank("test query", candidates, top_k=10)
        
        # 验证：空候选列表应该返回空结果
        if len(candidates) == 0:
            assert len(result.documents) == 0
            assert result.similarity_scores == {}
        
        # 验证：总是返回有效的RerankingResult
        assert isinstance(result, RerankingResult)
    
    @given(
        candidates=candidate_list(min_size=1, max_size=30),
        query=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=50, deadline=None)
    @patch('requests.post')
    def test_property_reranking_preserves_document_structure(self, mock_post, candidates, query):
        """
        Property: Reranking should preserve the structure of candidate documents.
        """
        # 过滤掉空文本的候选
        candidates = [c for c in candidates if c.get("text", "").strip()]
        assume(len(candidates) > 0)
        
        # 创建mock reranker
        mock_reranker = self._create_mock_reranker()
        
        # 模拟embedding生成
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1] * 1024}]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # 模拟句子查询
        mock_reranker.sentence_collection.query.return_value = {
            "documents": [["Sentence"]],
            "distances": [[0.2]],
            "metadatas": [[{"doi": "test"}]]
        }
        
        result = mock_reranker.rerank(query, candidates, top_k=10)
        
        # 验证：返回的文档应该保持原有字段
        for doc in result.documents:
            assert "text" in doc
            assert "metadata" in doc
            # rerank_score 应该被添加
            assert "rerank_score" in doc


    @given(
        candidates=candidate_list(min_size=1, max_size=30),
        query=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=100, deadline=None)
    @patch('requests.post')
    def test_property_sentence_similarity_is_bounded(self, mock_post, candidates, query):
        """
        **Feature: query-expansion-reranking, Property 4: Sentence similarity is bounded**
        **Validates: Requirements 2.3**
        
        Property: For any query and sentence, the computed similarity score should be 
        in the range [0, 1].
        """
        # 过滤掉空文本的候选
        candidates = [c for c in candidates if c.get("text", "").strip()]
        assume(len(candidates) > 0)
        
        # 确保至少有一个候选有DOI
        for i, c in enumerate(candidates):
            if not c.get("metadata", {}).get("doi"):
                c["metadata"]["doi"] = f"10.1021/test{i}"
        
        # 创建mock reranker
        mock_reranker = self._create_mock_reranker()
        
        # 模拟embedding生成
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1] * 1024}]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # 模拟句子查询，返回随机相似度
        import random
        def mock_query(*args, **kwargs):
            # 生成随机距离（0到1之间）
            distance = random.random()
            return {
                "documents": [["Sentence"]],
                "distances": [[distance]],
                "metadatas": [[{"doi": "test"}]]
            }
        
        mock_reranker.sentence_collection.query.side_effect = mock_query
        
        result = mock_reranker.rerank(query, candidates, top_k=10)
        
        # 验证：所有相似度分数应该在[0, 1]范围内
        for doi, similarity in result.similarity_scores.items():
            assert 0.0 <= similarity <= 1.0, \
                f"Similarity score {similarity} for DOI {doi} is out of bounds [0, 1]"
        
        # 验证：所有文档的rerank_score应该在[0, 1]范围内
        for doc in result.documents:
            rerank_score = doc.get("rerank_score", 0.0)
            assert 0.0 <= rerank_score <= 1.0, \
                f"Rerank score {rerank_score} is out of bounds [0, 1]"


    @given(
        candidates=candidate_list(min_size=3, max_size=30),
        query=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=100, deadline=None)
    @patch('requests.post')
    def test_property_reranking_improves_relevance_ordering(self, mock_post, candidates, query):
        """
        **Feature: query-expansion-reranking, Property 7: Reranking improves relevance ordering**
        **Validates: Requirements 2.4**
        
        Property: For any candidate list, the top-k documents after reranking should have 
        higher average sentence-level similarity than before reranking.
        """
        # 过滤掉空文本的候选
        candidates = [c for c in candidates if c.get("text", "").strip()]
        assume(len(candidates) >= 3)
        
        # 确保所有候选都有DOI和不同的原始分数
        for i, c in enumerate(candidates):
            if not c.get("metadata", {}).get("doi"):
                c["metadata"]["doi"] = f"10.1021/test{i}"
            # 设置递减的原始分数
            c["score"] = 1.0 - (i * 0.01)
        
        # 创建mock reranker
        mock_reranker = self._create_mock_reranker()
        
        # 模拟embedding生成
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1] * 1024}]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # 模拟句子查询，为不同的DOI返回不同的相似度
        # 让后面的DOI有更高的句子相似度（模拟重排序改进）
        doi_to_similarity = {}
        for i, c in enumerate(candidates):
            doi = c["metadata"]["doi"]
            # 反转相似度：后面的DOI有更高的句子相似度
            doi_to_similarity[doi] = 0.5 + (i * 0.01)
        
        def mock_query(*args, **kwargs):
            doi = kwargs.get("where", {}).get("doi")
            similarity = doi_to_similarity.get(doi, 0.5)
            distance = 1.0 - similarity
            return {
                "documents": [["Sentence"]],
                "distances": [[distance]],
                "metadatas": [[{"doi": doi}]]
            }
        
        mock_reranker.sentence_collection.query.side_effect = mock_query
        
        # 计算重排序前top-3的平均相似度（使用原始分数）
        top_k = min(3, len(candidates))
        original_top_k = candidates[:top_k]
        original_avg_similarity = sum(
            doi_to_similarity.get(c["metadata"]["doi"], 0.0) 
            for c in original_top_k
        ) / top_k
        
        # 执行重排序
        result = mock_reranker.rerank(query, candidates, top_k=top_k)
        
        # 计算重排序后top-k的平均相似度
        reranked_avg_similarity = sum(
            result.similarity_scores.get(doc["metadata"]["doi"], 0.0)
            for doc in result.documents
        ) / len(result.documents)
        
        # 验证：重排序后的平均相似度应该 >= 原始平均相似度
        # 使用小的容差来处理浮点数比较
        assert reranked_avg_similarity >= original_avg_similarity - 0.001, \
            f"Reranking did not improve relevance: " \
            f"original avg={original_avg_similarity:.4f}, " \
            f"reranked avg={reranked_avg_similarity:.4f}"
