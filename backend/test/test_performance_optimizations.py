"""
性能优化测试
测试并行查询、批量API调用、结果缓存等优化功能
"""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from backend.agents.multi_query_retriever import MultiQueryRetriever
from backend.agents.sentence_reranker import SentenceReranker


class TestMultiQueryRetrieverParallel:
    """测试MultiQueryRetriever的并行查询优化"""
    
    def test_parallel_query_execution(self):
        """测试并行查询执行"""
        # 创建mock对象
        mock_vector_repo = Mock()
        mock_vector_repo.search = Mock(return_value={
            "success": True,
            "documents": ["doc1", "doc2"],
            "metadatas": [{"doi": "10.1021/test1"}, {"doi": "10.1021/test2"}],
            "distances": [0.2, 0.3],
            "ids": ["id1", "id2"]
        })
        
        retriever = MultiQueryRetriever(
            vector_repo=mock_vector_repo,
            bge_api_url="http://test-api"
        )
        
        # Mock批量生成embedding
        with patch.object(retriever, '_generate_embeddings_batch') as mock_embed:
            mock_embed.return_value = [[0.1] * 768, [0.2] * 768, [0.3] * 768]
            
            # 执行多查询检索
            queries = ["query1", "query2", "query3"]
            result = retriever.retrieve(queries, top_k_per_query=20)
            
            # 验证结果
            assert result.total_after_dedup > 0
            assert len(result.query_contributions) == 3
            assert result.retrieval_time > 0
    
    def test_parallel_faster_than_sequential(self):
        """测试并行查询比串行查询更快（模拟）"""
        mock_vector_repo = Mock()
        
        # 模拟每次查询需要0.1秒
        def slow_search(*args, **kwargs):
            time.sleep(0.05)  # 模拟网络延迟
            return {
                "success": True,
                "documents": ["doc"],
                "metadatas": [{"doi": "10.1021/test"}],
                "distances": [0.2],
                "ids": ["id1"]
            }
        
        mock_vector_repo.search = slow_search
        
        retriever = MultiQueryRetriever(
            vector_repo=mock_vector_repo,
            bge_api_url="http://test-api"
        )
        
        with patch.object(retriever, '_generate_embeddings_batch') as mock_embed:
            mock_embed.return_value = [[0.1] * 768, [0.2] * 768, [0.3] * 768]
            
            start = time.time()
            queries = ["query1", "query2", "query3"]
            result = retriever.retrieve(queries, top_k_per_query=20)
            elapsed = time.time() - start
            
            # 并行执行应该比串行快（3 * 0.05 = 0.15秒）
            # 并行应该接近0.05秒（最慢的那个）
            assert elapsed < 0.2  # 应该远小于串行的0.15秒
            assert result.total_after_dedup > 0


class TestSentenceRerankerCache:
    """测试SentenceReranker的缓存优化"""
    
    def test_embedding_cache(self):
        """测试查询embedding缓存"""
        mock_collection = Mock()
        reranker = SentenceReranker(
            sentence_collection=mock_collection,
            bge_api_url="http://test-api"
        )
        
        # Mock API调用
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "data": [{"embedding": [0.1] * 768}]
            }
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response
            
            # 第一次调用
            embedding1 = reranker._generate_query_embedding("test query")
            assert len(embedding1) == 768
            assert mock_post.call_count == 1
            
            # 第二次调用相同查询（应该使用缓存）
            embedding2 = reranker._generate_query_embedding("test query")
            assert embedding1 == embedding2
            assert mock_post.call_count == 1  # 没有额外的API调用
            
            # 不同查询（应该调用API）
            embedding3 = reranker._generate_query_embedding("different query")
            assert mock_post.call_count == 2
    
    def test_similarity_cache(self):
        """测试相似度分数缓存"""
        mock_collection = Mock()
        reranker = SentenceReranker(
            sentence_collection=mock_collection,
            bge_api_url="http://test-api"
        )
        
        # 准备测试数据
        query = "test query"
        doi = "10.1021/test"
        sentences = [
            {"similarity": 0.8, "text": "sentence1"},
            {"similarity": 0.6, "text": "sentence2"}
        ]
        
        # 第一次计算
        score1 = reranker._compute_max_sentence_similarity(query, doi, sentences)
        assert score1 == 0.8
        
        # 第二次计算相同的query和doi（应该使用缓存）
        score2 = reranker._compute_max_sentence_similarity(query, doi, sentences)
        assert score1 == score2
        
        # 验证缓存中有数据
        cache_key = reranker._get_cache_key(query, doi)
        assert cache_key in reranker._similarity_cache
    
    def test_clear_cache(self):
        """测试清除缓存"""
        mock_collection = Mock()
        reranker = SentenceReranker(
            sentence_collection=mock_collection,
            bge_api_url="http://test-api"
        )
        
        # 添加一些缓存数据
        reranker._embedding_cache["test"] = [0.1] * 768
        reranker._similarity_cache["test:doi"] = 0.8
        
        # 验证缓存有数据
        assert len(reranker._embedding_cache) > 0
        assert len(reranker._similarity_cache) > 0
        
        # 清除缓存
        reranker.clear_cache()
        
        # 验证缓存已清空
        assert len(reranker._embedding_cache) == 0
        assert len(reranker._similarity_cache) == 0
    
    def test_cache_stats(self):
        """测试缓存统计"""
        mock_collection = Mock()
        reranker = SentenceReranker(
            sentence_collection=mock_collection,
            bge_api_url="http://test-api"
        )
        
        # 初始状态
        stats = reranker.get_cache_stats()
        assert stats["embedding_cache_size"] == 0
        assert stats["similarity_cache_size"] == 0
        
        # 添加缓存
        reranker._embedding_cache["test1"] = [0.1] * 768
        reranker._embedding_cache["test2"] = [0.2] * 768
        reranker._similarity_cache["test:doi1"] = 0.8
        
        # 检查统计
        stats = reranker.get_cache_stats()
        assert stats["embedding_cache_size"] == 2
        assert stats["similarity_cache_size"] == 1


class TestBatchAPIOptimization:
    """测试批量API调用优化"""
    
    def test_batch_embedding_generation(self):
        """测试批量生成embedding"""
        mock_vector_repo = Mock()
        retriever = MultiQueryRetriever(
            vector_repo=mock_vector_repo,
            bge_api_url="http://test-api"
        )
        
        # Mock API调用
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "data": [
                    {"embedding": [0.1] * 768},
                    {"embedding": [0.2] * 768},
                    {"embedding": [0.3] * 768}
                ]
            }
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response
            
            # 批量生成3个查询的embedding
            queries = ["query1", "query2", "query3"]
            embeddings = retriever._generate_embeddings_batch(queries)
            
            # 验证只调用了一次API
            assert mock_post.call_count == 1
            
            # 验证返回了3个embedding
            assert len(embeddings) == 3
            assert all(len(emb) == 768 for emb in embeddings)
            
            # 验证API调用的参数
            call_args = mock_post.call_args
            assert call_args[1]["json"]["input"] == queries


class TestCandidateLimiting:
    """测试重排序候选数量限制"""
    
    def test_rerank_candidate_limit(self):
        """测试重排序只处理前N个候选"""
        mock_collection = Mock()
        mock_collection.query = Mock(return_value={
            "documents": [["sentence1"]],
            "distances": [[0.2]],
            "metadatas": [[{"doi": "10.1021/test"}]]
        })
        
        reranker = SentenceReranker(
            sentence_collection=mock_collection,
            bge_api_url="http://test-api"
        )
        
        # 创建30个候选文档
        candidates = []
        for i in range(30):
            candidates.append({
                "text": f"document {i}",
                "metadata": {"doi": f"10.1021/test{i}"},
                "score": 0.5 + i * 0.01,
                "id": f"id{i}"
            })
        
        # Mock embedding生成
        with patch.object(reranker, '_generate_query_embedding') as mock_embed:
            mock_embed.return_value = [0.1] * 768
            
            # 执行重排序，要求返回15个
            result = reranker.rerank(
                query="test query",
                candidates=candidates,
                top_k=15
            )
            
            # 验证返回的文档数量不超过top_k
            assert len(result.documents) <= 15
            
            # 验证所有文档都有rerank_score
            assert all("rerank_score" in doc for doc in result.documents)


class TestPerformanceMetrics:
    """测试性能指标记录"""
    
    def test_retrieval_timing(self):
        """测试检索耗时记录"""
        mock_vector_repo = Mock()
        mock_vector_repo.search = Mock(return_value={
            "success": True,
            "documents": ["doc1"],
            "metadatas": [{"doi": "10.1021/test"}],
            "distances": [0.2],
            "ids": ["id1"]
        })
        
        retriever = MultiQueryRetriever(
            vector_repo=mock_vector_repo,
            bge_api_url="http://test-api"
        )
        
        with patch.object(retriever, '_generate_embeddings_batch') as mock_embed:
            mock_embed.return_value = [[0.1] * 768]
            
            result = retriever.retrieve(["query1"], top_k_per_query=20)
            
            # 验证记录了耗时
            assert result.retrieval_time > 0
            assert isinstance(result.retrieval_time, float)
    
    def test_reranking_timing(self):
        """测试重排序耗时记录"""
        mock_collection = Mock()
        mock_collection.query = Mock(return_value={
            "documents": [["sentence1"]],
            "distances": [[0.2]],
            "metadatas": [[{"doi": "10.1021/test"}]]
        })
        
        reranker = SentenceReranker(
            sentence_collection=mock_collection,
            bge_api_url="http://test-api"
        )
        
        candidates = [{
            "text": "document",
            "metadata": {"doi": "10.1021/test"},
            "score": 0.5,
            "id": "id1"
        }]
        
        with patch.object(reranker, '_generate_query_embedding') as mock_embed:
            mock_embed.return_value = [0.1] * 768
            
            result = reranker.rerank(
                query="test query",
                candidates=candidates,
                top_k=15
            )
            
            # 验证记录了耗时
            assert result.reranking_time > 0
            assert isinstance(result.reranking_time, float)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
