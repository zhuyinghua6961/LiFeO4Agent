"""
MultiQueryRetriever 单元测试
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from backend.agents.multi_query_retriever import MultiQueryRetriever, MultiQueryResult


class TestMultiQueryRetriever:
    """MultiQueryRetriever 单元测试类"""
    
    @pytest.fixture
    def mock_vector_repo(self):
        """创建模拟的向量数据库仓储"""
        repo = Mock()
        return repo
    
    @pytest.fixture
    def retriever(self, mock_vector_repo):
        """创建 MultiQueryRetriever 实例"""
        return MultiQueryRetriever(
            vector_repo=mock_vector_repo,
            bge_api_url="http://test-api:8001/v1/embeddings"
        )
    
    def test_init(self, retriever, mock_vector_repo):
        """测试初始化"""
        assert retriever.vector_repo == mock_vector_repo
        assert retriever.bge_api_url == "http://test-api:8001/v1/embeddings"
    
    @patch('backend.agents.multi_query_retriever.requests.post')
    def test_generate_embeddings_batch_success(self, mock_post, retriever):
        """测试批量生成embedding - 成功"""
        # 模拟API响应
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"embedding": [0.1, 0.2, 0.3]},
                {"embedding": [0.4, 0.5, 0.6]}
            ]
        }
        mock_post.return_value = mock_response
        
        queries = ["query1", "query2"]
        embeddings = retriever._generate_embeddings_batch(queries)
        
        assert len(embeddings) == 2
        assert embeddings[0] == [0.1, 0.2, 0.3]
        assert embeddings[1] == [0.4, 0.5, 0.6]
        
        # 验证API调用
        mock_post.assert_called_once_with(
            "http://test-api:8001/v1/embeddings",
            json={"input": queries},
            timeout=30
        )
    
    @patch('backend.agents.multi_query_retriever.requests.post')
    def test_generate_embeddings_batch_empty(self, mock_post, retriever):
        """测试批量生成embedding - 空列表"""
        embeddings = retriever._generate_embeddings_batch([])
        
        assert embeddings == []
        mock_post.assert_not_called()
    
    @patch('backend.agents.multi_query_retriever.requests.post')
    def test_generate_embeddings_batch_failure(self, mock_post, retriever):
        """测试批量生成embedding - 失败"""
        mock_post.side_effect = Exception("API Error")
        
        with pytest.raises(Exception):
            retriever._generate_embeddings_batch(["query1"])
    
    def test_retrieve_single_success(self, retriever, mock_vector_repo):
        """测试单个查询检索 - 成功"""
        # 模拟向量数据库响应
        mock_vector_repo.search.return_value = {
            "success": True,
            "documents": ["doc1", "doc2"],
            "metadatas": [
                {"doi": "10.1021/abc", "title": "Paper 1"},
                {"doi": "10.1021/xyz", "title": "Paper 2"}
            ],
            "distances": [0.2, 0.3],
            "ids": ["id1", "id2"]
        }
        
        query = "test query"
        embedding = [0.1, 0.2, 0.3]
        
        docs = retriever._retrieve_single(query, embedding, top_k=20)
        
        assert len(docs) == 2
        assert docs[0]["text"] == "doc1"
        assert docs[0]["metadata"]["doi"] == "10.1021/abc"
        assert docs[0]["score"] == 0.8  # 1 - 0.2
        assert docs[0]["source_query"] == query
        assert docs[1]["score"] == 0.7  # 1 - 0.3
    
    def test_retrieve_single_failure(self, retriever, mock_vector_repo):
        """测试单个查询检索 - 失败"""
        mock_vector_repo.search.return_value = {
            "success": False,
            "error": "Search failed"
        }
        
        docs = retriever._retrieve_single("query", [0.1, 0.2], top_k=20)
        
        assert docs == []
    
    def test_deduplicate_by_doi_basic(self, retriever):
        """测试DOI去重 - 基本功能"""
        documents = [
            {
                "text": "doc1",
                "metadata": {"doi": "10.1021/abc"},
                "score": 0.8,
                "id": "id1"
            },
            {
                "text": "doc2",
                "metadata": {"doi": "10.1021/abc"},
                "score": 0.7,
                "id": "id2"
            },
            {
                "text": "doc3",
                "metadata": {"doi": "10.1021/xyz"},
                "score": 0.9,
                "id": "id3"
            }
        ]
        
        deduped = retriever.deduplicate_by_doi(documents)
        
        # 应该只保留2个文档（每个DOI一个）
        assert len(deduped) == 2
        
        # 应该保留最高分数的文档
        dois = [doc["metadata"]["doi"] for doc in deduped]
        assert "10.1021/abc" in dois
        assert "10.1021/xyz" in dois
        
        # 对于 10.1021/abc，应该保留分数为0.8的文档
        abc_doc = [doc for doc in deduped if doc["metadata"]["doi"] == "10.1021/abc"][0]
        assert abc_doc["score"] == 0.8
        assert abc_doc["id"] == "id1"
        
        # 结果应该按分数降序排列
        assert deduped[0]["score"] >= deduped[1]["score"]
    
    def test_deduplicate_by_doi_uppercase(self, retriever):
        """测试DOI去重 - 支持大写DOI字段"""
        documents = [
            {
                "text": "doc1",
                "metadata": {"DOI": "10.1021/abc"},
                "score": 0.8,
                "id": "id1"
            },
            {
                "text": "doc2",
                "metadata": {"DOI": "10.1021/abc"},
                "score": 0.7,
                "id": "id2"
            }
        ]
        
        deduped = retriever.deduplicate_by_doi(documents)
        
        assert len(deduped) == 1
        assert deduped[0]["score"] == 0.8
    
    def test_deduplicate_by_doi_no_doi(self, retriever):
        """测试DOI去重 - 没有DOI字段"""
        documents = [
            {
                "text": "doc1",
                "metadata": {},
                "score": 0.8,
                "id": "id1"
            },
            {
                "text": "doc2",
                "metadata": {},
                "score": 0.7,
                "id": "id2"
            }
        ]
        
        deduped = retriever.deduplicate_by_doi(documents)
        
        # 没有DOI时，每个文档都会被分配唯一标识，所以应该保留所有文档
        assert len(deduped) == 2
    
    def test_deduplicate_by_doi_empty(self, retriever):
        """测试DOI去重 - 空列表"""
        deduped = retriever.deduplicate_by_doi([])
        assert deduped == []
    
    @patch('backend.agents.multi_query_retriever.requests.post')
    def test_retrieve_success(self, mock_post, retriever, mock_vector_repo):
        """测试多查询检索 - 成功"""
        # 模拟embedding生成
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"embedding": [0.1, 0.2, 0.3]},
                {"embedding": [0.4, 0.5, 0.6]}
            ]
        }
        mock_post.return_value = mock_response
        
        # 模拟向量数据库响应
        def mock_search(query, query_embedding, n_results):
            if query_embedding == [0.1, 0.2, 0.3]:
                return {
                    "success": True,
                    "documents": ["doc1"],
                    "metadatas": [{"doi": "10.1021/abc"}],
                    "distances": [0.2],
                    "ids": ["id1"]
                }
            else:
                return {
                    "success": True,
                    "documents": ["doc2", "doc3"],
                    "metadatas": [
                        {"doi": "10.1021/xyz"},
                        {"doi": "10.1021/abc"}
                    ],
                    "distances": [0.3, 0.25],
                    "ids": ["id2", "id3"]
                }
        
        mock_vector_repo.search.side_effect = mock_search
        
        queries = ["query1", "query2"]
        result = retriever.retrieve(queries, top_k_per_query=20)
        
        assert isinstance(result, MultiQueryResult)
        assert result.total_before_dedup == 3  # 1 + 2
        assert result.total_after_dedup == 2   # 去重后只有2个DOI
        assert len(result.documents) == 2
        assert result.query_contributions["query1"] == 1
        assert result.query_contributions["query2"] == 2
        assert result.retrieval_time > 0
    
    @patch('backend.agents.multi_query_retriever.requests.post')
    def test_retrieve_empty_queries(self, mock_post, retriever):
        """测试多查询检索 - 空查询列表"""
        result = retriever.retrieve([], top_k_per_query=20)
        
        assert isinstance(result, MultiQueryResult)
        assert result.total_before_dedup == 0
        assert result.total_after_dedup == 0
        assert len(result.documents) == 0
        assert result.query_contributions == {}
        mock_post.assert_not_called()
    
    @patch('backend.agents.multi_query_retriever.requests.post')
    def test_retrieve_embedding_failure(self, mock_post, retriever):
        """测试多查询检索 - embedding生成失败"""
        mock_post.side_effect = Exception("API Error")
        
        result = retriever.retrieve(["query1"], top_k_per_query=20)
        
        assert isinstance(result, MultiQueryResult)
        assert result.total_before_dedup == 0
        assert result.total_after_dedup == 0
        assert len(result.documents) == 0
