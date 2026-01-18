"""
Neo4j 数据访问层
封装所有 Neo4j 数据库操作
"""
from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase
import logging

from backend.config.settings import settings

logger = logging.getLogger(__name__)


class Neo4jRepository:
    """Neo4j 数据库访问类"""
    
    def __init__(self):
        """初始化 Neo4j 连接"""
        self._driver = None
        self._init_driver()
    
    def _init_driver(self):
        """初始化 Neo4j 驱动"""
        try:
            self._driver = GraphDatabase.driver(
                settings.neo4j_url,
                auth=(settings.neo4j_username, settings.neo4j_password)
            )
            # 验证连接
            self._driver.verify_connectivity()
            logger.info("✅ Neo4j 连接成功")
        except Exception as e:
            logger.error(f"❌ Neo4j 连接失败: {e}")
            raise
    
    def close(self):
        """关闭连接"""
        if self._driver:
            self._driver.close()
    
    def execute_query(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """
        执行 Cypher 查询
        
        Args:
            query: Cypher 查询语句
            parameters: 查询参数
            
        Returns:
            查询结果列表
        """
        with self._driver.session() as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]
    
    def get_node_count(self) -> int:
        """获取节点总数"""
        query = "MATCH (n) RETURN count(n) as count"
        result = self.execute_query(query)
        return result[0]['count'] if result else 0
    
    def get_material_by_density(
        self, 
        density_type: str, 
        threshold: float, 
        comparison: str = ">",
        limit: int = 100
    ) -> List[Dict]:
        """
        按密度筛选材料
        
        Args:
            density_type: _density, compaction_density密度类型 (tap)
            threshold: 阈值
            comparison: 比较符 (>, <, >=, <=)
            limit: 结果限制
            
        Returns:
            材料列表
        """
        query = f"""
        MATCH (m:Material)
        WHERE m.{density_type} IS NOT NULL 
        AND m.{density_type} {comparison} $threshold
        RETURN m
        ORDER BY m.{density_type} DESC
        LIMIT $limit
        """
        result = self.execute_query(query, {"threshold": threshold, "limit": limit})
        return [record['m'] for record in result]
    
    def get_material_by_property(
        self, 
        property_name: str, 
        property_value: Any,
        operator: str = "=",
        limit: int = 100
    ) -> List[Dict]:
        """
        按属性筛选材料
        
        Args:
            property_name: 属性名
            property_value: 属性值
            operator: 操作符
            limit: 结果限制
            
        Returns:
            材料列表
        """
        query = f"""
        MATCH (m:Material)
        WHERE m.{property_name} {operator} $value
        RETURN m
        LIMIT $limit
        """
        result = self.execute_query(query, {"value": property_value, "limit": limit})
        return [record['m'] for record in result]
    
    def get_all_properties(self) -> List[str]:
        """获取所有材料属性的键"""
        query = """
        MATCH (m:Material)
        UNWIND keys(m) as key
        RETURN DISTINCT key
        ORDER BY key
        """
        result = self.execute_query(query)
        return [record['key'] for record in result]
    
    def get_material_count(self) -> int:
        """获取材料节点总数"""
        query = "MATCH (m:Material) RETURN count(m) as count"
        result = self.execute_query(query)
        return result[0]['count'] if result else 0
    
    def get_material_by_doi(self, doi: str) -> Optional[Dict]:
        """
        根据 DOI 查找材料
        
        Args:
            doi: 文献 DOI
            
        Returns:
            材料节点或 None
        """
        query = """
        MATCH (m:Material)
        WHERE m.material_name CONTAINS $doi
        RETURN m
        LIMIT 1
        """
        result = self.execute_query(query, {"doi": doi})
        return result[0]['m'] if result else None
    
    def get_materials_by_synthesis_method(self, method: str, limit: int = 50) -> List[Dict]:
        """
        按合成方法筛选材料
        
        Args:
            method: 合成方法名称
            limit: 结果限制
            
        Returns:
            材料列表
        """
        query = """
        MATCH (m:Material)
        WHERE m.synthesis_method CONTAINS $method 
           OR m.preparation_method CONTAINS $method
        RETURN m
        LIMIT $limit
        """
        result = self.execute_query(query, {"method": method, "limit": limit})
        return [record['m'] for record in result]
    
    def get_top_materials(
        self, 
        property_name: str, 
        limit: int = 10,
        ascending: bool = False
    ) -> List[Dict]:
        """
        获取属性值最高/最低的材料
        
        Args:
            property_name: 属性名
            limit: 结果数量
            ascending: 是否升序（False=降序，取最高）
            
        Returns:
            材料列表
        """
        order = "ASC" if ascending else "DESC"
        query = f"""
        MATCH (m:Material)
        WHERE m.{property_name} IS NOT NULL
        RETURN m
        ORDER BY m.{property_name} {order}
        LIMIT $limit
        """
        result = self.execute_query(query, {"limit": limit})
        return [record['m'] for record in result]
    
    def search_materials(self, keyword: str, limit: int = 50) -> List[Dict]:
        """
        关键词搜索材料
        
        Args:
            keyword: 搜索关键词
            limit: 结果限制
            
        Returns:
            材料列表
        """
        query = """
        MATCH (m:Material)
        WHERE m.material_name CONTAINS $keyword
           OR m.synthesis_method CONTAINS $keyword
           OR m.precursor CONTAINS $keyword
        RETURN m
        LIMIT $limit
        """
        result = self.execute_query(query, {"keyword": keyword, "limit": limit})
        return [record['m'] for record in result]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        stats = {}
        
        # 节点统计
        stats['total_nodes'] = self.get_node_count()
        stats['material_count'] = self.get_material_count()
        
        # 属性统计
        properties = self.get_all_properties()
        stats['available_properties'] = properties
        
        return stats
    
    def get_schema(self) -> Dict[str, Any]:
        """获取数据库 Schema 信息"""
        query = """
        CALL db.schema.visualization()
        """
        try:
            result = self.execute_query(query)
            return {
                "success": True,
                "schema": result
            }
        except Exception as e:
            logger.warning(f"获取 Schema 失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# 创建全局实例
_neo4j_repo: Optional[Neo4jRepository] = None


def get_neo4j_repository() -> Neo4jRepository:
    """获取全局 Neo4j Repository 实例"""
    global _neo4j_repo
    if _neo4j_repo is None:
        _neo4j_repo = Neo4jRepository()
    return _neo4j_repo
