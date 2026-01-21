"""
QueryExpander 属性测试 (Property-Based Tests)
使用 Hypothesis 进行属性测试
"""
import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock

from backend.agents.query_expander import QueryExpander
from backend.services.llm_service import LLMService


class TestQueryExpanderProperties:
    """QueryExpander 属性测试类"""
    
    @pytest.fixture
    def mock_llm_service(self):
        """创建模拟的LLM服务"""
        mock_service = Mock(spec=LLMService)
        # 模拟LLM返回一个简单的英文翻译
        mock_service.generate.return_value = "translated query"
        return mock_service
    
    @pytest.fixture
    def expander(self, mock_llm_service):
        """创建QueryExpander实例"""
        return QueryExpander(llm_service=mock_llm_service)
    
    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=100, deadline=None)
    def test_property_expansion_preserves_original(self, query):
        """
        **Feature: query-expansion-reranking, Property 1: Query expansion preserves original**
        
        Property: 对于任意查询，扩展后的查询列表应该始终包含原始查询作为第一个元素
        Validates: Requirements 1.4
        """
        # 创建一个不依赖LLM的expander（避免外部依赖）
        expander = QueryExpander(llm_service=None)
        
        # 执行查询扩展
        result = expander.expand(query)
        
        # 验证原始查询在列表中
        assert query.strip() in result.all_queries, \
            f"原始查询 '{query.strip()}' 不在扩展查询列表中: {result.all_queries}"
        
        # 验证原始查询是第一个元素
        assert result.all_queries[0] == query.strip(), \
            f"原始查询 '{query.strip()}' 不是第一个元素，实际第一个是: '{result.all_queries[0]}'"
    
    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=100, deadline=None)
    def test_property_expansion_returns_list(self, query):
        """
        Property: 对于任意查询，扩展应该返回一个非空列表
        """
        expander = QueryExpander(llm_service=None)
        
        result = expander.expand(query)
        
        # 验证返回列表
        assert isinstance(result.all_queries, list), \
            f"扩展结果不是列表: {type(result.all_queries)}"
        
        # 验证列表非空
        assert len(result.all_queries) >= 1, \
            f"扩展查询列表为空"
    
    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=100, deadline=None)
    def test_property_no_duplicates_in_expansion(self, query):
        """
        Property: 对于任意查询，扩展后的查询列表不应包含重复项
        """
        expander = QueryExpander(llm_service=None)
        
        result = expander.expand(query)
        
        # 验证没有重复
        assert len(result.all_queries) == len(set(result.all_queries)), \
            f"扩展查询列表包含重复项: {result.all_queries}"
    
    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=100, deadline=None)
    def test_property_expansion_respects_max_queries(self, query):
        """
        Property: 对于任意查询，扩展后的查询数量不应超过配置的最大值
        """
        from backend.config.settings import settings
        expander = QueryExpander(llm_service=None)
        
        result = expander.expand(query)
        
        # 验证查询数量不超过最大值
        assert len(result.all_queries) <= settings.max_queries, \
            f"扩展查询数量 {len(result.all_queries)} 超过最大值 {settings.max_queries}"
    
    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=100, deadline=None)
    def test_property_expansion_time_non_negative(self, query):
        """
        Property: 对于任意查询，扩展耗时应该是非负数
        """
        expander = QueryExpander(llm_service=None)
        
        result = expander.expand(query)
        
        # 验证耗时非负
        assert result.expansion_time >= 0, \
            f"扩展耗时为负数: {result.expansion_time}"
    
    @given(st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll')), min_size=1, max_size=50))
    @settings(max_examples=50, deadline=None)
    def test_property_english_query_unchanged(self, english_query):
        """
        Property: 对于纯英文查询，翻译应该返回原查询
        """
        expander = QueryExpander(llm_service=None)
        
        result, method = expander.translate_to_english(english_query)
        
        # 纯英文查询应该不需要翻译
        assert result == english_query, \
            f"纯英文查询被修改: '{english_query}' -> '{result}'"
        assert method == "none", \
            f"纯英文查询使用了翻译方法: {method}"
