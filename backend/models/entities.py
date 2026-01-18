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


@dataclass
class Step:
    """处理步骤实体"""
    step: str  # 步骤ID
    message: str  # 显示消息
    status: str  # 状态: processing/success/error/warning
    data: Optional[Dict[str, Any]] = None  # 额外数据
    error: Optional[str] = None  # 错误信息
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "step": self.step,
            "message": self.message,
            "status": self.status
        }
        if self.data:
            result["data"] = self.data
        if self.error:
            result["error"] = self.error
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Step':
        """从字典创建"""
        return cls(
            step=data.get("step", ""),
            message=data.get("message", ""),
            status=data.get("status", ""),
            data=data.get("data"),
            error=data.get("error")
        )


@dataclass
class Message:
    """消息实体"""
    role: str  # user/assistant
    content: str  # 消息内容
    timestamp: str  # ISO格式时间戳
    query_mode: Optional[str] = None  # 查询模式（仅bot消息）
    expert: Optional[str] = None  # 使用的专家（仅bot消息）
    steps: List[Step] = field(default_factory=list)  # 处理步骤
    references: List[Dict[str, Any]] = field(default_factory=list)  # 参考文献
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp
        }
        if self.query_mode:
            result["queryMode"] = self.query_mode
        if self.expert:
            result["expert"] = self.expert
        if self.steps:
            result["steps"] = [step.to_dict() for step in self.steps]
        if self.references:
            result["references"] = self.references
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """从字典创建"""
        steps_data = data.get("steps", [])
        steps = [Step.from_dict(s) if isinstance(s, dict) else s for s in steps_data]
        
        return cls(
            role=data.get("role", ""),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", ""),
            query_mode=data.get("queryMode"),
            expert=data.get("expert"),
            steps=steps,
            references=data.get("references", [])
        )


@dataclass
class Conversation:
    """对话实体"""
    id: int
    user_id: int
    title: str
    file_path: str
    message_count: int
    created_at: str  # ISO格式时间戳
    updated_at: str  # ISO格式时间戳
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "file_path": self.file_path,
            "message_count": self.message_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        """从字典创建"""
        return cls(
            id=data.get("id", 0),
            user_id=data.get("user_id", 0),
            title=data.get("title", ""),
            file_path=data.get("file_path", ""),
            message_count=data.get("message_count", 0),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", "")
        )
    
    def validate(self) -> List[str]:
        """验证实体数据"""
        errors = []
        if not self.user_id or self.user_id <= 0:
            errors.append("user_id 必须是正整数")
        if not self.title or not self.title.strip():
            errors.append("title 不能为空")
        if self.message_count < 0:
            errors.append("message_count 不能为负数")
        return errors
