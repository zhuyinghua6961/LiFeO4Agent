"""
工具测试
"""
import pytest
from pathlib import Path


class TestFormatters:
    """格式化工具测试类"""
    
    def test_number_formatter_float(self):
        """测试数字格式化 - 浮点数"""
        from backend.utils import NumberFormatter
        
        # 正常值 - 根据实际实现检查
        result = NumberFormatter.format_float(3.14159, decimals=2)
        # 检查是否包含 3.14
        assert "3.14" in result
        
        # None值
        result = NumberFormatter.format_float(None)
        assert result == "N/A"
    
    def test_number_formatter_percentage(self):
        """测试数字格式化 - 百分比"""
        from backend.utils import NumberFormatter
        
        # 正常值
        result = NumberFormatter.format_percentage(85.5)
        assert "85.5" in result
        assert "%" in result
        
        # None值
        result = NumberFormatter.format_percentage(None)
        assert result == "N/A"
    
    def test_number_formatter_density(self):
        """测试数字格式化 - 密度"""
        from backend.utils import NumberFormatter
        
        result = NumberFormatter.format_density(2.5)
        assert "2.5" in result
        assert "g/cm³" in result
        
        result = NumberFormatter.format_density(None)
        assert result == "N/A"
    
    def test_number_formatter_capacity(self):
        """测试数字格式化 - 容量"""
        from backend.utils import NumberFormatter
        
        result = NumberFormatter.format_capacity(160.5)
        assert "160.5" in result
        assert "mAh/g" in result
    
    def test_number_formatter_range(self):
        """测试数字格式化 - 范围"""
        from backend.utils import NumberFormatter
        
        # 完整范围
        result = NumberFormatter.format_range(1.0, 5.0, "unit")
        assert "1.0" in result
        assert "5.0" in result
        
        # 只设置上限
        result = NumberFormatter.format_range(None, 5.0, "unit")
        assert "≤" in result
        
        # 只设置下限
        result = NumberFormatter.format_range(1.0, None, "unit")
        assert "≥" in result
        
        # 两者都为None
        result = NumberFormatter.format_range(None, None, "unit")
        assert result == "N/A"


class TestMaterialFormatter:
    """材料格式化测试类"""
    
    def test_format_material(self):
        """测试材料格式化"""
        from backend.utils import MaterialFormatter
        
        data = {
            "material_name": "LiFePO4",
            "tap_density": 2.5,
            "discharge_capacity": 160.0,
            "coulombic_efficiency": 99.0
        }
        
        result = MaterialFormatter.format_material(data)
        
        assert result['name'] == "LiFePO4"
        assert '2.5' in result['tap_density']
        assert '160' in result['discharge_capacity']
    
    def test_format_material_list(self):
        """测试材料列表格式化"""
        from backend.utils import MaterialFormatter
        
        materials = [
            {"material_name": "A", "tap_density": 1.0},
            {"material_name": "B", "tap_density": 2.0}
        ]
        
        results = MaterialFormatter.format_material_list(materials)
        
        assert len(results) == 2
        assert results[0]['name'] == "A"
        assert results[1]['name'] == "B"


class TestJSONFormatter:
    """JSON格式化测试类"""
    
    def test_format_json(self):
        """测试JSON格式化"""
        from backend.utils import JSONFormatter
        
        data = {"key": "value", "number": 123}
        result = JSONFormatter.format_json(data, indent=2)
        
        assert isinstance(result, str)
        assert "key" in result
        assert "value" in result
    
    def test_minify_json(self):
        """测试JSON压缩"""
        from backend.utils import JSONFormatter
        
        data = {"key": "value"}
        result = JSONFormatter.minify_json(data)
        
        assert isinstance(result, str)
        # 压缩后应该没有换行和多余空格
        assert "\n" not in result


class TestTableFormatter:
    """表格格式化测试类"""
    
    def test_format_table(self):
        """测试表格格式化"""
        from backend.utils import TableFormatter
        
        headers = ["Name", "Value"]
        rows = [["A", 1], ["B", 2]]
        
        result = TableFormatter.format_table(headers, rows)
        
        assert isinstance(result, str)
        assert "Name" in result
        assert "A" in result
        assert "B" in result
        # TableFormatter 使用两个空格作为分隔符
        assert "  " in result
    
    def test_format_empty_table(self):
        """测试空表格格式化"""
        from backend.utils import TableFormatter
        
        result = TableFormatter.format_table([], [])
        assert "No data" in result
    
    def test_format_single_row_table(self):
        """测试单行表格格式化"""
        from backend.utils import TableFormatter
        
        headers = ["Name"]
        rows = [["Test"]]
        
        result = TableFormatter.format_table(headers, rows)
        
        assert isinstance(result, str)
        assert "Name" in result
        assert "Test" in result


class TestResponseFormatter:
    """响应格式化测试类"""
    
    def test_success_response(self):
        """测试成功响应格式化"""
        from backend.utils import ResponseFormatter
        
        result = ResponseFormatter.success(data={"key": "value"})
        
        assert result['success'] is True
        assert result['data']['key'] == "value"
        assert 'timestamp' in result
    
    def test_error_response(self):
        """测试错误响应格式化"""
        from backend.utils import ResponseFormatter
        
        result = ResponseFormatter.error(message="测试错误", code="TEST_ERROR")
        
        assert result['success'] is False
        assert result['error']['message'] == "测试错误"
        assert result['error']['code'] == "TEST_ERROR"
    
    def test_paginated_response(self):
        """测试分页响应格式化"""
        from backend.utils import ResponseFormatter
        
        result = ResponseFormatter.paginated(
            data=[1, 2, 3],
            page=1,
            page_size=10,
            total=100
        )
        
        assert result['success'] is True
        assert len(result['data']) == 3
        assert result['pagination']['page'] == 1
        assert result['pagination']['total'] == 100
        assert result['pagination']['total_pages'] == 10


class TestHelperFunctions:
    """辅助函数测试类"""
    
    def test_truncate_text(self):
        """测试文本截断"""
        from backend.utils import truncate_text
        
        # 正常截断
        result = truncate_text("这是一个很长的文本", max_length=5, suffix="...")
        assert len(result) <= 8  # 5 + 3
        assert result.endswith("...")
        
        # 不需要截断
        result = truncate_text("短文本", max_length=100)
        assert result == "短文本"
    
    def test_format_duration(self):
        """测试时长格式化"""
        from backend.utils import format_duration
        
        # 微秒
        result = format_duration(0.0005)
        assert "μs" in result
        
        # 毫秒
        result = format_duration(0.5)
        assert "ms" in result
        
        # 秒
        result = format_duration(30.0)
        assert "s" in result
        
        # 分钟
        result = format_duration(120.5)
        assert "m" in result


class TestCypherUtils:
    """Cypher工具测试类"""
    
    def test_cypher_generator_exists(self):
        """测试Cypher生成器存在"""
        from backend.utils import CypherGenerator
        assert CypherGenerator is not None
    
    def test_cypher_generator_property_map(self):
        """测试属性名映射"""
        from backend.utils import CypherGenerator
        
        gen = CypherGenerator()
        
        # 检查属性映射
        assert "振实密度" in gen.PROPERTY_MAP
        assert gen.PROPERTY_MAP["振实密度"] == "tap_density"
    
    def test_cypher_generator_comparison_map(self):
        """测试比较符映射"""
        from backend.utils import CypherGenerator
        
        gen = CypherGenerator()
        
        assert gen.COMPARISON_MAP[">"] == ">"
        assert gen.COMPARISON_MAP[">="] == ">="
    
    def test_generate_simple_query(self):
        """测试生成简单查询"""
        from backend.utils import CypherGenerator
        
        gen = CypherGenerator()
        cypher = gen.generate_query(
            property_name="tap_density",
            threshold=2.5,
            comparison=">",
            limit=10
        )
        
        assert "MATCH" in cypher
        assert "tap_density" in cypher
        assert "2.5" in cypher
        assert "LIMIT 10" in cypher
    
    def test_generate_top_materials(self):
        """测试生成Top材料查询"""
        from backend.utils import CypherGenerator
        
        gen = CypherGenerator()
        cypher = gen.generate_top_materials(
            property_name="tap_density",
            limit=5
        )
        
        assert "MATCH" in cypher
        assert "ORDER BY" in cypher
        assert "LIMIT 5" in cypher
    
    def test_cypher_validator(self):
        """测试Cypher验证器"""
        from backend.utils import CypherValidator
        
        # 有效查询
        valid, errors = CypherValidator.validate(
            "MATCH (m:Material) RETURN m LIMIT 10"
        )
        assert valid or len(errors) == 0
        
        # 清理查询
        sanitized = CypherValidator.sanitize(
            "MATCH (m:Material) // comment\nRETURN m"
        )
        assert "//" not in sanitized
