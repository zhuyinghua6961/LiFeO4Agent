"""
Cypher查询工具
生成和优化Cypher查询
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
import re

logger = logging.getLogger(__name__)


class CypherGenerator:
    """Cypher查询生成器"""
    
    # 属性名映射（中 -> 英）
    PROPERTY_MAP = {
        "振实密度": "tap_density",
        "压实密度": "compaction_density",
        "放电容量": "discharge_capacity",
        "比容量": "discharge_capacity",
        "库伦效率": "coulombic_efficiency",
        "导电率": "conductivity",
        "导电性": "conductivity",
        "粒径": "particle_size",
        "比表面积": "surface_area",
        "循环稳定性": "cycling_stability",
        "碳含量": "carbon_content",
        "合成方法": "synthesis_method",
        "制备方法": "preparation_method",
        "前驱体": "precursor",
        "碳源": "carbon_source",
        "包覆材料": "coating_material"
    }
    
    # 比较操作符映射
    COMPARISON_MAP = {
        ">": ">",
        "<": "<",
        ">=": ">=",
        "<=": "<=",
        "=": "=",
        "==": "=",
        "!=": "<>",
        "不等于": "<>"
    }
    
    def __init__(self):
        """初始化Cypher生成器"""
        pass
    
    def generate_query(
        self,
        property_name: str,
        threshold: float,
        comparison: str = ">",
        limit: int = 100,
        node_type: str = "Material"
    ) -> str:
        """
        生成简单的属性比较查询
        
        Args:
            property_name: 属性名
            threshold: 阈值
            comparison: 比较符
            limit: 结果限制
            
        Returns:
            Cypher查询语句
        """
        en_property = self.PROPERTY_MAP.get(property_name, property_name)
        en_comparison = self.COMPARISON_MAP.get(comparison, comparison)
        
        cypher = f"""
MATCH (m:{node_type})
WHERE m.{en_property} IS NOT NULL 
  AND m.{en_property} {en_comparison} {threshold}
RETURN m.material_name, m.{en_property}
ORDER BY m.{en_property} DESC
LIMIT {limit}
"""
        return cypher.strip()
    
    def generate_material_by_name(self, material_name: str) -> str:
        """
        生成按名称查询材料的Cypher
        
        Args:
            material_name: 材料名称
            
        Returns:
            Cypher查询语句
        """
        return f"""
MATCH (m:Material)
WHERE m.material_name CONTAINS '{material_name}'
RETURN m
LIMIT 1
"""
    
    def generate_material_with_properties(
        self,
        properties: Dict[str, Any],
        min_properties: int = 1
    ) -> str:
        """
        生成多属性筛选查询
        
        Args:
            properties: 属性名到值的映射
            min_properties: 最少匹配属性数
            
        Returns:
            Cypher查询语句
        """
        conditions = []
        for prop, value in properties.items():
            en_prop = self.PROPERTY_MAP.get(prop, prop)
            if isinstance(value, str):
                conditions.append(f"m.{en_prop} CONTAINS '{value}'")
            else:
                conditions.append(f"m.{en_property} = {value}")
        
        where_clause = " OR ".join(conditions[:min_properties])
        if len(conditions) > min_properties:
            where_clause = "(" + where_clause + ") AND (" + " AND ".join(conditions[min_properties:]) + ")"
        
        return f"""
MATCH (m:Material)
WHERE {where_clause}
RETURN m
LIMIT 100
"""
    
    def generate_top_materials(
        self,
        property_name: str,
        limit: int = 10,
        ascending: bool = False
    ) -> str:
        """
        生成查询属性最高/最低材料的Cypher
        
        Args:
            property_name: 属性名
            limit: 结果数量
            ascending: 是否升序
            
        Returns:
            Cypher查询语句
        """
        order = "ASC" if ascending else "DESC"
        en_property = self.PROPERTY_MAP.get(property_name, property_name)
        
        return f"""
MATCH (m:Material)
WHERE m.{en_property} IS NOT NULL
RETURN m.material_name, m.{en_property}
ORDER BY m.{en_property} {order}
LIMIT {limit}
"""
    
    def generate_density_query(
        self,
        density_type: str,
        threshold: float,
        comparison: str = ">"
    ) -> str:
        """
        生成密度查询Cypher
        
        Args:
            density_type: 密度类型 (tap_density, compaction_density)
            threshold: 阈值
            comparison: 比较符
            
        Returns:
            Cypher查询语句
        """
        en_comparison = self.COMPARISON_MAP.get(comparison, comparison)
        
        return f"""
MATCH (m:Material)
WHERE m.{density_type} IS NOT NULL 
  AND m.{density_type} {en_comparison} {threshold}
RETURN m.material_name, m.{density_type}, m.compaction_density
ORDER BY m.{density_type} DESC
"""
    
    def generate_synthesis_method_query(
        self,
        method: str,
        include_details: bool = True
    ) -> str:
        """
        生成按合成方法查询的Cypher
        
        Args:
            method: 合成方法
            include_details: 是否返回详细信息
            
        Returns:
            Cypher查询语句
        """
        if include_details:
            return f"""
MATCH (m:Material)
WHERE m.synthesis_method CONTAINS '{method}'
   OR m.preparation_method CONTAINS '{method}'
RETURN m.material_name, m.synthesis_method, m.preparation_method, 
       m.tap_density, m.discharge_capacity
LIMIT 50
"""
        else:
            return f"""
MATCH (m:Material)
WHERE m.synthesis_method CONTAINS '{method}'
RETURN m.material_name
LIMIT 50
"""
    
    def generate_paper_query(self, paper_doi: str) -> str:
        """
        生成按DOI查询文献的Cypher
        
        Args:
            paper_doi: 文献DOI
            
        Returns:
            Cypher查询语句
        """
        return f"""
MATCH (p:Paper)-[:DESCRIBES]->(m:Material)
WHERE p.doi = '{paper_doi}'
RETURN p, m
"""
    
    def generate_relationship_query(
        self,
        relationship_type: str,
        direction: str = "outgoing"
    ) -> str:
        """
        生成关系查询Cypher
        
        Args:
            relationship_type: 关系类型
            direction: 方向 (outgoing/incoming)
            
        Returns:
            Cypher查询语句
        """
        arrow = "-->" if direction == "outgoing" else "<--"
        return f"""
MATCH (m:Material)-[r:{relationship_type}]->(n)
RETURN m.material_name, r, n
LIMIT 50
"""


class CypherOptimizer:
    """Cypher查询优化器"""
    
    @staticmethod
    def optimize_query(cypher: str) -> str:
        """
        优化Cypher查询
        
        Args:
            cypher: 原始Cypher
            
        Returns:
            优化后的Cypher
        """
        # 移除多余的空白字符
        lines = [line.strip() for line in cypher.split('\n') if line.strip()]
        optimized = '\n'.join(lines)
        
        # 确保使用索引（如果存在）
        # 这里可以添加更多的优化规则
        
        return optimized
    
    @staticmethod
    def add_explain(cypher: str) -> str:
        """
        添加EXPLAIN前缀
        
        Args:
            cypher: 原始Cypher
            
        Returns:
            带EXPLAIN的Cypher
        """
        return f"EXPLAIN {cypher}"
    
    @staticmethod
    def add_profile(cypher: str) -> str:
        """
        添加PROFILE前缀（用于性能分析）
        
        Args:
            cypher: 原始Cypher
            
        Returns:
            带PROFILE的Cypher
        """
        return f"PROFILE {cypher}"


class CypherValidator:
    """Cypher查询验证器"""
    
    # 允许的关键词
    ALLOWED_KEYWORDS = [
        "MATCH", "WHERE", "RETURN", "LIMIT", "SKIP", "ORDER", "BY",
        "CREATE", "MERGE", "SET", "DELETE", "REMOVE", "WITH",
        "OPTIONAL", "UNWIND", "FOREACH", "UNION", "AS"
    ]
    
    # 允许的节点类型
    ALLOWED_NODES = ["Material", "Paper", "Community", "Summary"]
    
    # 允许的关系类型
    ALLOWED_RELATIONSHIPS = ["DESCRIBES", "RELATED_TO", "CITES"]
    
    @classmethod
    def validate(cls, cypher: str) -> Tuple[bool, List[str]]:
        """
        验证Cypher查询安全性
        
        Args:
            cypher: Cypher查询
            
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        
        # 检查是否包含危险关键词
        dangerous_keywords = ["DETACH DELETE", "DROP", "CREATE INDEX", "DROP INDEX"]
        for keyword in dangerous_keywords:
            if keyword in cypher.upper():
                errors.append(f"不允许的关键词: {keyword}")
        
        # 检查节点类型
        for node in cls.ALLOWED_NODES:
            pattern = rf"\({node}:"
            if re.search(pattern, cypher) is None:
                # 检查是否有任何节点类型
                if re.search(r"\([a-zA-Z]+:", cypher):
                    for match in re.finditer(r"\(([a-zA-Z]+):", cypher):
                        node_type = match.group(1)
                        if node_type not in cls.ALLOWED_NODES and node_type.lower() != "m":
                            errors.append(f"不允许的节点类型: {node_type}")
        
        return len(errors) == 0, errors
    
    @classmethod
    def sanitize(cls, cypher: str) -> str:
        """
        清理Cypher查询
        
        Args:
            cypher: 原始Cypher
            
        Returns:
            清理后的Cypher
        """
        # 移除注释
        cypher = re.sub(r"//.*", "", cypher)
        
        # 移除多余空白
        cypher = re.sub(r"\s+", " ", cypher)
        
        return cypher.strip()


def build_material_properties_dict(material_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    从材料数据构建属性字典
    
    Args:
        material_data: 材料原始数据
        
    Returns:
        标准化的属性字典
    """
    property_map = {
        "振实密度": "tap_density",
        "压实密度": "compaction_density",
        "放电容量": "discharge_capacity",
        "库伦效率": "coulombic_efficiency",
        "导电率": "conductivity",
        "粒径": "particle_size",
        "比表面积": "surface_area",
        "循环稳定性": "cycling_stability",
        "碳含量": "carbon_content"
    }
    
    result = {}
    for cn_name, en_name in property_map.items():
        if cn_name in material_data:
            result[en_name] = material_data[cn_name]
        elif en_name in material_data:
            result[en_name] = material_data[en_name]
    
    return result
