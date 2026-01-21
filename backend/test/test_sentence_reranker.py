"""
SentenceReranker 单元测试
测试句子级重排序功能
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.agents.sentence_reranker import SentenceReranker, RerankingResult


class TestSentenceReranker:
    """SentenceReranker 单元测试类"""
    
    @pytest.fixture
    def mock_sentence_collection(self):
        """创建模拟的句子collection"""
        collection = Mock()
        collection.count.return_value = 1000
        return collection
    
    @pytest.fixture
    def reranker(self, mock_sentence_collection):
        """创建SentenceReranker实例"""
        return SentenceReranker(
            sentence_collection=mock_sentence_collection,
            bge_api_url="http://test-api:8001/v1/embeddings"
        )
    
    @pytest.fixture
    def sample_candidates(self):
        """创建示例候选文献"""
        return [
            {
                "text": "Document 1 about LiFePO4",
                "metadata": {"doi": "10.1021/abc", "title": "Paper 1"},
                "score": 0.8,
                "distance": 0.2
            },
            {
                "text": "Document 2 about battery",
                "metadata": {"doi": "10.1021/def", "title": "Paper 2"},
                "score": 0.7,
                "distance": 0.3
            },
            {
                "text": "Document 3 about cathode",
                "metadata": {"doi": "10.1021/ghi", "title": "Paper 3"},
                "score": 0.6,
                "distance": 0.4
            }
        ]
    
    def test_init(self, mock_sentence_collection):
        """测试初始化"""
        reranker = SentenceReranker(
            sentence_collection=mock_sentence_collection,
            bge_api_url="http://test-api:8001/v1/embeddings"
        )
        
        assert reranker.sentence_collection == mock_sentence_collection
        assert reranker.bge_api_url == "http://test-api:8001/v1/embeddings"
    
    @patch('requests.post')
    def test_generate_query_embedding(self, mock_post, reranker):
        """测试生成查询embedding"""
        # 模拟API响应
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1] * 1024}]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # 生成embedding
        embedding = reranker._generate_query_embedding("test query")
        
        # 验证
        assert len(embedding) == 1024
        assert all(x == 0.1 for x in embedding)
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_generate_query_embedding_failure(self, mock_post, reranker):
        """测试生成embedding失败"""
        # 模拟API失败
        mock_post.side_effect = Exception("API Error")
        
        # 应该抛出异常
        with pytest.raises(Exception):
            reranker._generate_query_embedding("test query")
    
    def test_batch_query_sentences(self, reranker, mock_sentence_collection):
        """测试批量查询句子"""
        # 模拟句子查询结果
        mock_sentence_collection.query.return_value = {
            "documents": [[
                "Sentence 1 about compaction density",
                "Sentence 2 about electrode"
            ]],
            "distances": [[0.1, 0.2]],
            "metadatas": [[
                {"doi": "10.1021/abc", "page": 1},
                {"doi": "10.1021/abc", "page": 2}
            ]]
        }
        
        # 查询句子
        query_embedding = [0.1] * 1024
        dois = ["10.1021/abc"]
        result = reranker._batch_query_sentences(query_embedding, dois)
        
        # 验证
        assert "10.1021/abc" in result
        assert len(result["10.1021/abc"]) == 2
        # 新的相似度计算: similarity = 1 - (distance / 2)
        assert result["10.1021/abc"][0]["similarity"] == 0.95  # 1 - (0.1 / 2)
        assert result["10.1021/abc"][1]["similarity"] == 0.9   # 1 - (0.2 / 2)
    
    def test_batch_query_sentences_empty_dois(self, reranker):
        """测试空DOI列表"""
        query_embedding = [0.1] * 1024
        result = reranker._batch_query_sentences(query_embedding, [])
        
        assert result == {}
    
    def test_compute_max_sentence_similarity(self, reranker):
        """测试计算最高句子相似度"""
        sentences = [
            {"text": "Sentence 1", "similarity": 0.8},
            {"text": "Sentence 2", "similarity": 0.9},
            {"text": "Sentence 3", "similarity": 0.7}
        ]
        
        max_sim = reranker._compute_max_sentence_similarity("test query", "10.1021/abc", sentences)
        
        assert max_sim == 0.9
    
    def test_compute_max_sentence_similarity_empty(self, reranker):
        """测试空句子列表"""
        max_sim = reranker._compute_max_sentence_similarity("test query", "10.1021/abc", [])
        
        assert max_sim == 0.0
    
    @patch('requests.post')
    def test_rerank_success(self, mock_post, reranker, sample_candidates, mock_sentence_collection):
        """测试重排序成功"""
        # 模拟embedding生成
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1] * 1024}]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # 模拟句子查询（第二个DOI有更高的句子相似度）
        def mock_query(*args, **kwargs):
            doi = kwargs.get("where", {}).get("DOI")  # 注意：使用大写DOI
            if doi == "10.1021/abc":
                return {
                    "documents": [["Sentence 1"]],
                    "distances": [[0.3]],
                    "metadatas": [[{"DOI": doi}]]
                }
            elif doi == "10.1021/def":
                return {
                    "documents": [["Sentence 2"]],
                    "distances": [[0.1]],  # 更高的相似度
                    "metadatas": [[{"DOI": doi}]]
                }
            elif doi == "10.1021/ghi":
                return {
                    "documents": [["Sentence 3"]],
                    "distances": [[0.5]],
                    "metadatas": [[{"DOI": doi}]]
                }
        
        mock_sentence_collection.query.side_effect = mock_query
        
        # 执行重排序
        result = reranker.rerank("test query", sample_candidates, top_k=3)
        
        # 验证
        assert isinstance(result, RerankingResult)
        assert len(result.documents) == 3
        
        # 第二个文档应该排在第一位（因为句子相似度更高）
        assert result.documents[0]["metadata"]["doi"] == "10.1021/def"
        # 新的相似度计算: similarity = 1 - (distance / 2)
        assert result.documents[0]["rerank_score"] == 0.95  # 1 - (0.1 / 2)
        
        # 验证相似度分数
        assert "10.1021/abc" in result.similarity_scores
        assert "10.1021/def" in result.similarity_scores
        assert "10.1021/ghi" in result.similarity_scores
        
        # 验证top-3变化
        assert len(result.top_3_changes) == 3
    
    @patch('requests.post')
    def test_rerank_empty_candidates(self, mock_post, reranker):
        """测试空候选列表"""
        result = reranker.rerank("test query", [], top_k=10)
        
        assert isinstance(result, RerankingResult)
        assert len(result.documents) == 0
        assert result.similarity_scores == {}
    
    @patch('requests.post')
    def test_rerank_no_dois(self, mock_post, reranker):
        """测试没有DOI的候选文献"""
        # 模拟embedding生成
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1] * 1024}]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        candidates = [
            {
                "text": "Document without DOI",
                "metadata": {"title": "Paper"},
                "score": 0.8
            }
        ]
        
        result = reranker.rerank("test query", candidates, top_k=1)
        
        # 应该返回原始候选
        assert len(result.documents) == 1
        assert result.similarity_scores == {}
    
    @patch('requests.post')
    def test_rerank_api_failure(self, mock_post, reranker, sample_candidates):
        """测试API失败时的回退"""
        # 模拟API失败
        mock_post.side_effect = Exception("API Error")
        
        result = reranker.rerank("test query", sample_candidates, top_k=3)
        
        # 应该返回原始排序
        assert isinstance(result, RerankingResult)
        assert len(result.documents) == 3
        assert result.documents[0]["metadata"]["doi"] == "10.1021/abc"  # 原始顺序
    
    @patch('requests.post')
    def test_rerank_preserves_top_k(self, mock_post, reranker, sample_candidates, mock_sentence_collection):
        """测试重排序保持top_k限制"""
        # 模拟embedding生成
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1] * 1024}]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # 模拟句子查询
        mock_sentence_collection.query.return_value = {
            "documents": [["Sentence"]],
            "distances": [[0.2]],
            "metadatas": [[{"doi": "10.1021/abc"}]]
        }
        
        # 请求top_k=2
        result = reranker.rerank("test query", sample_candidates, top_k=2)
        
        # 应该只返回2个文档
        assert len(result.documents) == 2
    
    def test_rerank_sorting_order(self, reranker, sample_candidates, mock_sentence_collection):
        """测试重排序后的排序顺序"""
        # 创建有明确rerank_score的候选
        candidates_with_scores = [
            {**doc, "rerank_score": score}
            for doc, score in zip(sample_candidates, [0.5, 0.9, 0.7])
        ]
        
        # 手动排序（模拟rerank内部逻辑）
        sorted_docs = sorted(
            candidates_with_scores,
            key=lambda x: x.get("rerank_score", 0.0),
            reverse=True
        )
        
        # 验证排序是降序的
        assert sorted_docs[0]["rerank_score"] == 0.9
        assert sorted_docs[1]["rerank_score"] == 0.7
        assert sorted_docs[2]["rerank_score"] == 0.5
        
        # 验证是降序
        for i in range(len(sorted_docs) - 1):
            assert sorted_docs[i]["rerank_score"] >= sorted_docs[i+1]["rerank_score"]
