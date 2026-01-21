"""
QueryExpander 单元测试
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch

from backend.agents.query_expander import QueryExpander, QueryExpansionResult
from backend.services.llm_service import LLMService


class TestQueryExpander:
    """QueryExpander 单元测试类"""
    
    @pytest.fixture
    def mock_llm_service(self):
        """创建模拟的LLM服务"""
        mock_service = Mock(spec=LLMService)
        return mock_service
    
    @pytest.fixture
    def expander(self, mock_llm_service):
        """创建QueryExpander实例"""
        return QueryExpander(llm_service=mock_llm_service)
    
    @pytest.fixture
    def expander_no_llm(self):
        """创建没有LLM的QueryExpander实例"""
        return QueryExpander(llm_service=None)
    
    def test_init_loads_term_mapping(self, expander):
        """测试初始化时加载术语映射表"""
        assert isinstance(expander.term_mapping, dict)
        assert len(expander.term_mapping) > 0
        # 验证一些已知术语
        assert "磷酸铁锂" in expander.term_mapping
        assert expander.term_mapping["磷酸铁锂"] == "LiFePO4"
    
    def test_init_loads_synonyms(self, expander):
        """测试初始化时加载同义词库"""
        assert isinstance(expander.synonyms, dict)
        assert len(expander.synonyms) > 0
        # 验证一些已知同义词
        assert "压实密度" in expander.synonyms
        assert isinstance(expander.synonyms["压实密度"], list)
    
    def test_contains_chinese(self, expander):
        """测试中文检测"""
        assert expander._contains_chinese("磷酸铁锂") is True
        assert expander._contains_chinese("LiFePO4") is False
        assert expander._contains_chinese("磷酸铁锂 LiFePO4") is True
        assert expander._contains_chinese("") is False
    
    def test_translate_to_english_no_chinese(self, expander):
        """测试翻译纯英文查询"""
        query = "LiFePO4 compaction density"
        result, method = expander.translate_to_english(query)
        assert result == query
        assert method == "none"
    
    def test_translate_to_english_with_llm(self, expander, mock_llm_service):
        """测试使用LLM翻译"""
        query = "磷酸铁锂的压实密度"
        mock_llm_service.generate.return_value = "compaction density of LiFePO4"
        
        result, method = expander.translate_to_english(query)
        
        assert result == "compaction density of LiFePO4"
        assert method == "llm"
        mock_llm_service.generate.assert_called_once()
    
    def test_translate_to_english_llm_fallback(self, expander, mock_llm_service):
        """测试LLM失败时回退到规则翻译"""
        query = "磷酸铁锂的压实密度"
        mock_llm_service.generate.side_effect = Exception("LLM error")
        
        result, method = expander.translate_to_english(query)
        
        # 应该使用规则翻译
        assert method == "rule"
        assert "LiFePO4" in result
        assert "compaction density" in result
    
    def test_translate_with_rules(self, expander):
        """测试规则翻译"""
        query = "磷酸铁锂的压实密度"
        result = expander._translate_with_rules(query)
        
        # 验证术语被替换
        assert "LiFePO4" in result
        assert "compaction density" in result
    
    def test_translate_with_rules_no_llm(self, expander_no_llm):
        """测试没有LLM时的翻译"""
        query = "磷酸铁锂的导电率"
        result, method = expander_no_llm.translate_to_english(query)
        
        assert method == "rule"
        assert "LiFePO4" in result
        assert "conductivity" in result
    
    def test_generate_synonyms(self, expander):
        """测试同义词生成"""
        query = "磷酸铁锂的压实密度"
        result = expander.generate_synonyms(query)
        
        # 应该替换为同义词
        assert result != query
        # 验证同义词被使用
        synonyms = expander.synonyms.get("压实密度", [])
        if synonyms:
            assert synonyms[0] in result
    
    def test_generate_synonyms_no_match(self, expander):
        """测试没有匹配同义词的情况"""
        query = "unknown term"
        result = expander.generate_synonyms(query)
        
        # 没有匹配时应返回原查询
        assert result == query
    
    def test_expand_basic(self, expander, mock_llm_service):
        """测试基本查询扩展"""
        query = "磷酸铁锂的压实密度"
        mock_llm_service.generate.return_value = "compaction density of LiFePO4"
        
        result = expander.expand(query)
        
        # 验证结果类型
        assert isinstance(result, QueryExpansionResult)
        
        # 验证原始查询
        assert result.original_query == query
        
        # 验证查询列表
        assert len(result.all_queries) >= 1
        assert result.all_queries[0] == query  # 第一个应该是原始查询
        
        # 验证英文查询
        assert result.english_query != query
        
        # 验证同义词查询
        assert result.synonym_query != query
        
        # 验证耗时
        assert result.expansion_time >= 0
        
        # 验证翻译方法
        assert result.translation_method in ["llm", "rule", "none"]
    
    def test_expand_preserves_original(self, expander, mock_llm_service):
        """测试扩展后保留原始查询"""
        query = "测试查询"
        mock_llm_service.generate.return_value = "test query"
        
        result = expander.expand(query)
        
        # 原始查询应该在列表中
        assert query in result.all_queries
        # 原始查询应该是第一个
        assert result.all_queries[0] == query
    
    def test_expand_deduplication(self, expander_no_llm):
        """测试查询去重"""
        # 使用一个没有同义词的查询
        query = "LiFePO4 test"
        
        result = expander_no_llm.expand(query)
        
        # 验证没有重复
        assert len(result.all_queries) == len(set(result.all_queries))
    
    def test_expand_max_queries_limit(self, expander, mock_llm_service):
        """测试查询数量限制"""
        query = "磷酸铁锂的压实密度"
        mock_llm_service.generate.return_value = "compaction density of LiFePO4"
        
        result = expander.expand(query)
        
        # 验证查询数量不超过配置的最大值
        from backend.config.settings import settings
        assert len(result.all_queries) <= settings.max_queries
    
    def test_expand_english_query(self, expander):
        """测试扩展英文查询"""
        query = "LiFePO4 compaction density"
        
        result = expander.expand(query)
        
        # 英文查询应该保持不变
        assert result.original_query == query
        assert result.english_query == query
        assert result.translation_method == "none"
    
    def test_expand_with_whitespace(self, expander, mock_llm_service):
        """测试带空格的查询"""
        query = "  磷酸铁锂  "
        mock_llm_service.generate.return_value = "LiFePO4"
        
        result = expander.expand(query)
        
        # 应该去除空格
        assert result.original_query == query.strip()
