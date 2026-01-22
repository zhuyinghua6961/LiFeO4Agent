"""
测试ReverseCitationFinder
运行: conda run -n py310 pytest backend/test/test_reverse_citation_finder.py -v
"""
import pytest
from unittest.mock import Mock, patch
from backend.agents.reverse_citation_finder import ReverseCitationFinder


class TestReverseCitationFinder:
    """测试ReverseCitationFinder类"""
    
    @pytest.fixture
    def mock_sentence_collection(self):
        """创建模拟的句子collection"""
        return Mock()
    
    @pytest.fixture
    def mock_paragraph_collection(self):
        """创建模拟的段落collection"""
        return Mock()
    
    @pytest.fixture
    def finder(self, mock_sentence_collection, mock_paragraph_collection):
        """创建ReverseCitationFinder实例"""
        return ReverseCitationFinder(
            sentence_collection=mock_sentence_collection,
            paragraph_collection=mock_paragraph_collection,
            bge_api_url="http://test-api:8001/v1/embeddings"
        )
    
    def test_init(self, mock_sentence_collection, mock_paragraph_collection):
        """测试初始化"""
        finder = ReverseCitationFinder(
            sentence_collection=mock_sentence_collection,
            paragraph_collection=mock_paragraph_collection,
            bge_api_url="http://test-api:8001/v1/embeddings"
        )
        
        assert finder.sentence_collection == mock_sentence_collection
        assert finder.paragraph_collection == mock_paragraph_collection
        assert finder.bge_api_url == "http://test-api:8001/v1/embeddings"
    
    @patch('requests.post')
    def test_generate_embedding(self, mock_post, finder):
        """测试生成embedding"""
        # 模拟API响应
        mock_post.return_value.json.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3]}]
        }
        mock_post.return_value.raise_for_status = Mock()
        
        embedding = finder._generate_embedding("test text")
        
        assert embedding == [0.1, 0.2, 0.3]
        assert mock_post.called
    
    @patch('requests.post')
    def test_generate_embedding_with_cache(self, mock_post, finder):
        """测试embedding缓存"""
        mock_post.return_value.json.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3]}]
        }
        mock_post.return_value.raise_for_status = Mock()
        
        # 第一次调用
        embedding1 = finder._generate_embedding("test text")
        call_count_1 = mock_post.call_count
        
        # 第二次调用（应该使用缓存）
        embedding2 = finder._generate_embedding("test text")
        call_count_2 = mock_post.call_count
        
        assert embedding1 == embedding2
        assert call_count_2 == call_count_1  # 没有额外的API调用
    
    def test_get_page_for_doi(self, finder, mock_paragraph_collection):
        """测试获取页码"""
        # 模拟段落级数据库响应
        mock_paragraph_collection.get.return_value = {
            "metadatas": [{"page": 5, "doi": "10.1016/test"}]
        }
        
        page = finder._get_page_for_doi("10.1016/test")
        
        assert page == 5
        assert mock_paragraph_collection.get.called
    
    def test_get_page_for_doi_with_cache(self, finder, mock_paragraph_collection):
        """测试页码缓存"""
        mock_paragraph_collection.get.return_value = {
            "metadatas": [{"page": 5, "doi": "10.1016/test"}]
        }
        
        # 第一次调用
        page1 = finder._get_page_for_doi("10.1016/test")
        call_count_1 = mock_paragraph_collection.get.call_count
        
        # 第二次调用（应该使用缓存）
        page2 = finder._get_page_for_doi("10.1016/test")
        call_count_2 = mock_paragraph_collection.get.call_count
        
        assert page1 == page2 == 5
        assert call_count_2 == call_count_1  # 没有额外的数据库调用
    
    def test_get_page_for_doi_not_found(self, finder, mock_paragraph_collection):
        """测试DOI不存在时的处理"""
        mock_paragraph_collection.get.return_value = {
            "metadatas": []
        }
        
        page = finder._get_page_for_doi("10.1016/nonexistent")
        
        assert page == 0  # 默认值
    
    @patch('requests.post')
    def test_find_citations_for_doi(
        self, 
        mock_post, 
        finder, 
        mock_sentence_collection,
        mock_paragraph_collection
    ):
        """测试查找引用位置"""
        # 模拟embedding生成
        mock_post.return_value.json.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3]}]
        }
        mock_post.return_value.raise_for_status = Mock()
        
        # 模拟句子级数据库响应
        mock_sentence_collection.query.return_value = {
            "documents": [["This is a test sentence about LiFePO4."]],
            "metadatas": [[{
                "DOI": "10.1016/test",
                "sentence_index": 0,
                "has_number": True,
                "has_unit": False
            }]],
            "distances": [[0.2]]  # 相似度 = 1 - 0.2/2 = 0.9
        }
        
        # 模拟段落级数据库响应
        mock_paragraph_collection.get.return_value = {
            "metadatas": [{"page": 5}]
        }
        
        # 执行查找
        answer_sentences = ["磷酸铁锂的工作电压约为3.4V"]
        citations = finder.find_citations_for_doi(
            doi="10.1016/test",
            answer_sentences=answer_sentences,
            top_k=3
        )
        
        assert len(citations) > 0
        assert citations[0].doi == "10.1016/test"
        assert citations[0].page == 5
        assert citations[0].similarity > 0.8
    
    def test_find_citations_empty_sentences(self, finder):
        """测试空句子列表"""
        citations = finder.find_citations_for_doi(
            doi="10.1016/test",
            answer_sentences=[],
            top_k=3
        )
        
        assert citations == []
    
    def test_clear_cache(self, finder):
        """测试清除缓存"""
        # 添加一些缓存数据
        finder._embedding_cache["test"] = [0.1, 0.2]
        finder._page_cache["10.1016/test"] = 5
        
        # 清除缓存
        finder.clear_cache()
        
        assert len(finder._embedding_cache) == 0
        assert len(finder._page_cache) == 0
    
    def test_get_cache_stats(self, finder):
        """测试获取缓存统计"""
        finder._embedding_cache["test1"] = [0.1]
        finder._embedding_cache["test2"] = [0.2]
        finder._page_cache["doi1"] = 1
        
        stats = finder.get_cache_stats()
        
        assert stats["embedding_cache_size"] == 2
        assert stats["page_cache_size"] == 1
