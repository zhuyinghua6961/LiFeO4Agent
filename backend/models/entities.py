"""
数据实体定义
定义核心领域实体
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class Material:
    """材料实体"""
    material_name: str
    doi: str = ""
    tap_density: Optional[float] = None  # 振实密度 (g/cm³)
    compaction_density: Optional[float] = None  # 压实密度 (g/cm³)
    discharge_capacity: Optional[float] = None  # 放电容量 (mAh/g)
    coulombic_efficiency: Optional[float] = None  # 库伦效率 (%)
    synthesis_method: str = ""  # 合成方法
    preparation_method: str = ""  # 制备方法
    precursor: str = ""  # 前驱体
    carbon_source: str = ""  # 碳源
    carbon_content: Optional[float] = None  # 碳含量 (%)
    coating_material: str = ""  # 包覆材料
    particle_size: Optional[float] = None  # 粒径 (nm)
    surface_area: Optional[float] = None  # 比表面积 (m²/g)
    cycling_stability: Optional[float] = None  # 循环稳定性 (%)
    conductivity: Optional[float] = None  # 导电性 (S/cm)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "material_name": self.material_name,
            "doi": self.doi,
            "tap_density": self.tap_density,
            "compaction_density": self.compaction_density,
            "discharge_capacity": self.discharge_capacity,
            "coulombic_efficiency": self.coulombic_efficiency,
            "synthesis_method": self.synthesis_method,
            "preparation_method": self.preparation_method,
            "precursor": self.precursor,
            "carbon_source": self.carbon_source,
            "carbon_content": self.carbon_content,
            "coating_material": self.coating_material,
            "particle_size": self.particle_size,
            "surface_area": self.surface_area,
            "cycling_stability": self.cycling_stability,
            "conductivity": self.conductivity
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Material':
        """从字典创建"""
        return cls(
            material_name=data.get("material_name", ""),
            doi=data.get("doi", ""),
            tap_density=data.get("tap_density"),
            compaction_density=data.get("compaction_density"),
            discharge_capacity=data.get("discharge_capacity"),
            coulombic_efficiency=data.get("coulombic_efficiency"),
            synthesis_method=data.get("synthesis_method", ""),
            preparation_method=data.get("preparation_method", ""),
            precursor=data.get("precursor", ""),
            carbon_source=data.get("carbon_source", ""),
            carbon_content=data.get("carbon_content"),
            coating_material=data.get("coating_material", ""),
            particle_size=data.get("particle_size"),
            surface_area=data.get("surface_area"),
            cycling_stability=data.get("cycling_stability"),
            conductivity=data.get("conductivity")
        )


@dataclass
class Paper:
    """文献实体"""
    paper_id: str  # 使用文件名作为ID
    title: str
    authors: List[str] = field(default_factory=list)
    journal: str = ""
    year: int = 0
    doi: str = ""
    abstract: str = ""
    summary_embedding: Optional[List[float]] = None  # 摘要嵌入向量
    summary_text: str = ""  # 摘要文本
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "authors": self.authors,
            "journal": self.journal,
            "year": self.year,
            "doi": self.doi,
            "abstract": self.abstract,
            "summary_text": self.summary_text
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Paper':
        """从字典创建"""
        return cls(
            paper_id=data.get("paper_id", ""),
            title=data.get("title", ""),
            authors=data.get("authors", []),
            journal=data.get("journal", ""),
            year=data.get("year", 0),
            doi=data.get("doi", ""),
            abstract=data.get("abstract", ""),
            summary_text=data.get("summary_text", "")
        )


@dataclass
class CommunitySummary:
    """社区摘要实体"""
    community_id: str
    summary_text: str
    paper_ids: List[str] = field(default_factory=list)
    topic_keywords: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "community_id": self.community_id,
            "summary_text": self.summary_text,
            "paper_ids": self.paper_ids,
            "topic_keywords": self.topic_keywords
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommunitySummary':
        """从字典创建"""
        return cls(
            community_id=data.get("community_id", ""),
            summary_text=data.get("summary_text", ""),
            paper_ids=data.get("paper_ids", []),
            topic_keywords=data.get("topic_keywords", [])
        )


@dataclass
class QueryResult:
    """查询结果实体"""
    success: bool
    expert_type: str  # 'neo4j', 'literature', 'community'
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "expert_type": self.expert_type,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata
        }


@dataclass
class RoutingDecision:
    """路由决策实体"""
    primary_expert: str
    confidence: float
    reasoning: str
    secondary_expert: Optional[str] = None
    query_type: Optional[str] = None
    suggested_keywords: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "primary_expert": self.primary_expert,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "secondary_expert": self.secondary_expert,
            "query_type": self.query_type,
            "suggested_keywords": self.suggested_keywords
        }


@dataclass
class SearchResult:
    """搜索结果实体"""
    query: str
    documents: List[Dict[str, Any]] = field(default_factory=list)
    total_count: int = 0
    search_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "query": self.query,
            "documents": self.documents,
            "total_count": self.total_count,
            "search_time_ms": self.search_time_ms
        }
