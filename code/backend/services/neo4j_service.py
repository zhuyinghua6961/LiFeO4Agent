"""
Neo4j 服务层
封装 Neo4j 业务逻辑
"""
from typing import Dict, List, Any, Optional
from langchain_community.graphs import Neo4jGraph
import logging

from backend.config.settings import settings
from backend.repositories.neo4j_repository import Neo4jRepository

logger = logging.getLogger(__name__)


class Neo4jService:
    """Neo4j 服务类 - 业务逻辑层"""
    
    def __init__(self):
        """初始化服务"""
        # 使用 LangChain 的 Neo4jGraph（兼容现有代码）
        self._graph = None
        # 使用新的 Repository
        self._repo = Neo4jRepository()
        self._init_graph()
    
    def _init_graph(self):
        """初始化 LangChain Neo4jGraph"""
        try:
            self._graph = Neo4jGraph(
                url=settings.neo4j_url,
                username=settings.neo4j_username,
                password=settings.neo4j_password,
                sanitize=True,
                refresh_schema=False
            )
            logger.info("✅ Neo4jGraph 初始化成功")
        except Exception as e:
            logger.error(f"❌ Neo4jGraph 初始化失败: {e}")
            raise
    
    @property
    def graph(self):
        """获取 LangChain Graph 实例"""
        return self._graph
    
    @property
    def repository(self):
        """获取 Repository 实例"""
        return self._repo
    
    def execute_cypher(self, query: str) -> List[Dict]:
        """执行 Cypher 查询（使用 Repository）"""
        return self._repo.execute_query(query)
    
    def get_material_count(self) -> int:
        """获取材料数量"""
        return self._repo.get_material_count()
    
    def get_node_count(self) -> int:
        """获取节点总数"""
        return self._repo.get_node_count()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self._repo.get_statistics()
        
        # 添加 LangChain Graph 信息
        try:
            schema = self._graph.get_schema
            stats['schema'] = str(schema)[:500]  # 截取部分
        except Exception as e:
            stats['schema_error'] = str(e)
        
        return stats
    
    def query_material(
        self,
        property_name: str,
        threshold: float,
        comparison: str = ">",
        limit: int = 100
    ) -> List[Dict]:
        """
        按属性值查询材料
        
        Args:
            property_name: 属性名（如 tap_density, compaction_density）
            threshold: 阈值
            comparison: 比较符
            limit: 结果限制
            
        Returns:
            材料列表
        """
        return self._repo.get_material_by_property(
            property_name=property_name,
            property_value=threshold,
            operator=comparison,
            limit=limit
        )
    
    def query_by_density(
        self,
        density_type: str,
        threshold: float,
        comparison: str = ">",
        limit: int = 100
    ) -> List[Dict]:
        """
        按密度查询材料
        
        Args:
            density_type: 密度类型 (tap_density, compaction_density)
            threshold: 阈值
            comparison: 比较符
            limit: 结果限制
            
        Returns:
            材料列表
        """
        return self._repo.get_material_by_density(
            density_type=density_type,
            threshold=threshold,
            comparison=comparison,
            limit=limit
        )
    
    def query_by_doi(self, doi: str) -> Optional[Dict]:
        """
        根据 DOI 查询材料
        
        Args:
            doi: 文献 DOI
            
        Returns:
            材料信息或 None
        """
        return self._repo.get_material_by_doi(doi)
    
    def query_by_synthesis_method(
        self, 
        method: str, 
        limit: int = 50
    ) -> List[Dict]:
        """
        按合成方法查询材料
        
        Args:
            method: 合成方法
            limit: 结果限制
            
        Returns:
            材料列表
        """
        return self._repo.get_materials_by_synthesis_method(method, limit)
    
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
            ascending: 是否升序
            
        Returns:
            材料列表
        """
        return self._repo.get_top_materials(property_name, limit, ascending)
    
    def search_materials(self, keyword: str, limit: int = 50) -> List[Dict]:
        """
        关键词搜索材料
        
        Args:
            keyword: 搜索关键词
            limit: 结果限制
            
        Returns:
            材料列表
        """
        return self._repo.search_materials(keyword, limit)
    
    def get_all_properties(self) -> List[str]:
        """获取所有可用属性"""
        return self._repo.get_all_properties()
    
    def close(self):
        """关闭连接"""
        self._repo.close()


# 创建全局实例
_neo4j_service: Optional[Neo4jService] = None


def get_neo4j_service() -> Neo4jService:
    """获取全局 Neo4j Service 实例"""
    global _neo4j_service
    if _neo4j_service is None:
        _neo4j_service = Neo4jService()
    return _neo4j_service
