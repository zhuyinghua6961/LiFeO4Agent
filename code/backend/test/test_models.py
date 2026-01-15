"""
模型测试
"""
import pytest
from datetime import datetime


class TestMaterialEntity:
    """材料实体测试类"""
    
    def test_material_creation(self):
        """测试材料实体创建"""
        from backend.models import Material
        
        material = Material(
            material_name="LiFePO4",
            tap_density=2.5,
            discharge_capacity=160.0
        )
        
        assert material.material_name == "LiFePO4"
        assert material.tap_density == 2.5
        assert material.discharge_capacity == 160.0
    
    def test_material_to_dict(self):
        """测试材料实体转换为字典"""
        from backend.models import Material
        
        material = Material(
            material_name="LiFePO4",
            tap_density=2.5
        )
        data = material.to_dict()
        
        assert isinstance(data, dict)
        assert data['material_name'] == "LiFePO4"
        assert data['tap_density'] == 2.5
    
    def test_material_from_dict(self):
        """测试从字典创建材料实体"""
        from backend.models import Material
        
        data = {
            "material_name": "NMC",
            "tap_density": 3.0,
            "discharge_capacity": 200.0
        }
        material = Material.from_dict(data)
        
        assert material.material_name == "NMC"
        assert material.tap_density == 3.0
    
    def test_material_optional_fields(self):
        """测试材料实体的可选字段"""
        from backend.models import Material
        
        material = Material(material_name="Test")
        assert material.doi == ""
        assert material.tap_density is None
        assert material.synthesis_method == ""


class TestPaperEntity:
    """文献实体测试类"""
    
    def test_paper_creation(self):
        """测试文献实体创建"""
        from backend.models import Paper
        
        paper = Paper(
            paper_id="test_001",
            title="Test Paper",
            authors=["Author1", "Author2"],
            year=2024
        )
        
        assert paper.paper_id == "test_001"
        assert paper.title == "Test Paper"
        assert len(paper.authors) == 2
        assert paper.year == 2024
    
    def test_paper_to_dict(self):
        """测试文献实体转换为字典"""
        from backend.models import Paper
        
        paper = Paper(
            paper_id="test_001",
            title="Test Paper"
        )
        data = paper.to_dict()
        
        assert isinstance(data, dict)
        assert data['paper_id'] == "test_001"
        assert data['title'] == "Test Paper"
    
    def test_paper_from_dict(self):
        """测试从字典创建文献实体"""
        from backend.models import Paper
        
        data = {
            "paper_id": "test_002",
            "title": "Another Paper",
            "year": 2023
        }
        paper = Paper.from_dict(data)
        
        assert paper.paper_id == "test_002"


class TestDTOs:
    """数据传输对象测试类"""
    
    def test_query_request_validation(self):
        """测试查询请求验证"""
        from backend.models import QueryRequest
        
        # 有效请求
        req = QueryRequest(question="测试问题", top_k=10)
        errors = req.validate()
        assert len(errors) == 0
        
        # 无效请求（空问题）
        req = QueryRequest(question="", top_k=10)
        errors = req.validate()
        assert "问题不能为空" in errors[0]
    
    def test_query_request_invalid_topk(self):
        """测试查询请求top_k验证"""
        from backend.models import QueryRequest
        
        req = QueryRequest(question="测试", top_k=0)
        errors = req.validate()
        assert len(errors) > 0
    
    def test_route_request_validation(self):
        """测试路由请求验证"""
        from backend.models import RouteRequest
        
        # 有效请求
        req = RouteRequest(question="测试问题")
        errors = req.validate()
        assert len(errors) == 0
        
        # 无效请求
        req = RouteRequest(question="")
        errors = req.validate()
        assert len(errors) > 0
    
    def test_search_params_validation(self):
        """测试搜索参数验证"""
        from backend.models import SearchParams
        
        # 有效参数
        params = SearchParams(query="测试", top_k=10)
        errors = params.validate()
        assert len(errors) == 0
        
        # 无效参数
        params = SearchParams(query="", top_k=0)
        errors = params.validate()
        assert len(errors) > 0
    
    def test_material_query_params_validation(self):
        """测试材料查询参数验证"""
        from backend.models import MaterialQueryParams
        
        # 有效参数
        params = MaterialQueryParams(
            property_name="tap_density",
            threshold=2.5,
            comparison=">"
        )
        errors = params.validate()
        assert len(errors) == 0
        
        # 无效比较符
        params = MaterialQueryParams(
            property_name="tap_density",
            threshold=2.5,
            comparison="invalid"
        )
        errors = params.validate()
        assert len(errors) > 0
    
    def test_synthesis_request_validation(self):
        """测试综合查询请求验证"""
        from backend.models import SynthesisRequest
        
        # 有效请求
        req = SynthesisRequest(question="测试问题")
        errors = req.validate()
        assert len(errors) == 0
        
        # 无效模式
        req = SynthesisRequest(question="测试问题", synthesis_mode="invalid")
        errors = req.validate()
        assert len(errors) > 0


class TestEnums:
    """枚举测试类"""
    
    def test_query_type_enum(self):
        """测试查询类型枚举"""
        from backend.models import QueryType
        
        assert QueryType.NUMERIC.value == "numeric"
        assert QueryType.SEMANTIC.value == "semantic"
        assert QueryType.ANALYSIS.value == "analysis"
        assert QueryType.MIXED.value == "mixed"
    
    def test_expert_type_enum(self):
        """测试专家类型枚举"""
        from backend.models import ExpertType
        
        assert ExpertType.NEO4J.value == "neo4j"
        assert ExpertType.LITERATURE.value == "literature"
        assert ExpertType.COMMUNITY.value == "community"
