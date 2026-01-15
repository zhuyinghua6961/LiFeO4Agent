"""
专家系统测试
"""
import pytest


class TestRouterExpert:
    """路由专家测试类"""
    
    def test_router_expert_exists(self):
        """测试路由专家存在"""
        from backend.agents.experts import RouterExpert
        assert RouterExpert is not None
    
    def test_router_expert_has_experts_dict(self):
        """测试路由专家有专家字典"""
        from backend.agents.experts import RouterExpert
        
        # 检查类属性
        assert hasattr(RouterExpert, 'EXPERTS')
        assert 'neo4j' in RouterExpert.EXPERTS
        assert 'literature' in RouterExpert.EXPERTS
        assert 'community' in RouterExpert.EXPERTS
    
    def test_router_expert_info(self):
        """测试获取专家信息"""
        from backend.agents.experts import RouterExpert
        
        # 测试获取neo4j专家信息
        info = RouterExpert.EXPERTS.get('neo4j', {})
        assert 'name' in info
        assert 'description' in info
        assert 'strengths' in info
        assert 'examples' in info
    
    def test_router_expert_initialization(self):
        """测试路由专家初始化"""
        from backend.agents.experts import RouterExpert
        
        # 不带LLM服务初始化
        router = RouterExpert(llm_service=None)
        assert router is not None
        assert router._llm is None
    
    def test_router_fallback_routing_numeric(self):
        """测试降级路由 - 数值查询"""
        from backend.agents.experts import RouterExpert
        
        router = RouterExpert(llm_service=None)
        
        # 数值查询应该路由到neo4j
        result = router._fallback_routing("振实密度大于2.8的材料")
        assert result == "neo4j"
    
    def test_router_fallback_routing_mechanism(self):
        """测试降级路由 - 机制分析"""
        from backend.agents.experts import RouterExpert
        
        router = RouterExpert(llm_service=None)
        
        # 机制分析应该路由到community
        result = router._fallback_routing("循环稳定性与容量衰减的关系")
        assert result == "community"
    
    def test_router_fallback_routing_default(self):
        """测试降级路由 - 默认"""
        from backend.agents.experts import RouterExpert
        
        router = RouterExpert(llm_service=None)
        
        # 其他查询默认路由到literature
        result = router._fallback_routing("LiFePO4材料的研究")
        assert result == "literature"


class TestQueryExpert:
    """精确查询专家测试类"""
    
    def test_query_expert_exists(self):
        """测试精确查询专家存在"""
        from backend.agents.experts import QueryExpert
        assert QueryExpert is not None
    
    def test_query_expert_can_handle_numeric(self):
        """测试精确查询专家处理数值查询"""
        from backend.agents.experts import QueryExpert
        
        expert = QueryExpert(neo4j_service=None, llm_service=None)
        
        # 数值查询应该被处理
        assert expert.can_handle("振实密度大于2.8") is True
        assert expert.can_handle("容量最高") is True
    
    def test_query_expert_cannot_handle_semantic(self):
        """测试精确查询专家不处理语义查询"""
        from backend.agents.experts import QueryExpert
        
        expert = QueryExpert(neo4j_service=None, llm_service=None)
        
        # 语义查询不应该被处理
        assert expert.can_handle("关于高导电性材料的研究") is False
    
    def test_query_expert_generate_simple_cypher(self):
        """测试生成简单Cypher查询"""
        from backend.agents.experts import QueryExpert
        
        expert = QueryExpert(neo4j_service=None, llm_service=None)
        
        cypher = expert._generate_simple_cypher("振实密度大于2.8")
        
        assert "tap_density" in cypher
        assert "2.8" in cypher


class TestSemanticExpert:
    """语义搜索专家测试类"""
    
    def test_semantic_expert_exists(self):
        """测试语义搜索专家存在"""
        from backend.agents.experts import SemanticExpert
        assert SemanticExpert is not None
    
    def test_semantic_expert_can_handle(self):
        """测试语义搜索专家处理文献查询"""
        from backend.agents.experts import SemanticExpert
        
        expert = SemanticExpert(vector_repo=None, llm_service=None)
        
        # 文献查询应该被处理
        assert expert.can_handle("有哪些关于LiFePO4的研究") is True
        assert expert.can_handle("请帮我查找水热合成的文献") is True
    
    def test_semantic_expert_cannot_handle_numeric(self):
        """测试语义搜索专家不处理数值查询"""
        from backend.agents.experts import SemanticExpert
        
        expert = SemanticExpert(vector_repo=None, llm_service=None)
        
        # 数值查询不应该被处理
        assert expert.can_handle("振实密度大于2.8") is False
    
    def test_semantic_expert_generate_simple_query(self):
        """测试生成简单搜索查询"""
        from backend.agents.experts import SemanticExpert
        
        expert = SemanticExpert(vector_repo=None, llm_service=None)
        
        query = expert._generate_simple_query("有哪些关于高导电性LiFePO4的研究？")
        
        # 应该移除问号
        assert "？" not in query
        assert "?" not in query


class TestExpertsModule:
    """专家模块测试类"""
    
    def test_experts_module_exports(self):
        """测试专家模块导出"""
        from backend.agents import experts
        
        assert hasattr(experts, 'RouterExpert')
        assert hasattr(experts, 'QueryExpert')
        assert hasattr(experts, 'SemanticExpert')
    
    def test_experts_all_list(self):
        """测试__all__列表"""
        from backend.agents.experts import __all__
        
        assert 'RouterExpert' in __all__
        assert 'QueryExpert' in __all__
        assert 'SemanticExpert' in __all__
