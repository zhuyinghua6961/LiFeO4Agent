"""
数据传输对象 (DTOs)
API层与业务层之间的数据交换格式
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class QueryType(str, Enum):
    """查询类型枚举"""
    NUMERIC = "numeric"
    SEMANTIC = "semantic"
    ANALYSIS = "analysis"
    MIXED = "mixed"


class ExpertType(str, Enum):
    """专家类型枚举"""
    NEO4J = "neo4j"
    LITERATURE = "literature"
    COMMUNITY = "community"


@dataclass
class QueryRequest:
    """查询请求 DTO"""
    question: str
    top_k: int = 10
    include_scores: bool = False
    filter_metadata: Optional[Dict] = None
    
    def validate(self) -> List[str]:
        """验证请求数据"""
        errors = []
        if not self.question or not self.question.strip():
            errors.append("问题不能为空")
        if self.top_k < 1 or self.top_k > 100:
            errors.append("top_k 必须在 1-100 之间")
        return errors


@dataclass
class QueryResponse:
    """查询响应 DTO"""
    success: bool
    answer: str
    expert_type: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "answer": self.answer,
            "expert_type": self.expert_type,
            "sources": self.sources,
            "metadata": self.metadata,
            "error": self.error
        }


@dataclass
class RouteRequest:
    """路由请求 DTO"""
    question: str
    
    def validate(self) -> List[str]:
        """验证请求数据"""
        errors = []
        if not self.question or not self.question.strip():
            errors.append("问题不能为空")
        return errors


@dataclass
class RouteResponse:
    """路由响应 DTO"""
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
class MaterialQueryParams:
    """材料查询参数 DTO"""
    property_name: str
    threshold: float
    comparison: str = ">"
    limit: int = 100
    material_type: Optional[str] = None
    
    def validate(self) -> List[str]:
        """验证请求数据"""
        errors = []
        valid_comparisons = [">", "<", ">=", "<=", "=", "!="]
        if self.comparison not in valid_comparisons:
            errors.append(f"comparison 必须是: {valid_comparisons}")
        if self.limit < 1 or self.limit > 1000:
            errors.append("limit 必须在 1-1000 之间")
        return errors


@dataclass
class MaterialQueryResult:
    """材料查询结果 DTO"""
    materials: List[Dict[str, Any]]
    total_count: int
    query: str
    execution_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "materials": self.materials,
            "total_count": self.total_count,
            "query": self.query,
            "execution_time_ms": self.execution_time_ms
        }


@dataclass
class SearchParams:
    """搜索参数 DTO"""
    query: str
    top_k: int = 10
    with_scores: bool = False
    filter_metadata: Optional[Dict] = None
    
    def validate(self) -> List[str]:
        """验证请求数据"""
        errors = []
        if not self.query or not self.query.strip():
            errors.append("查询不能为空")
        if self.top_k < 1 or self.top_k > 100:
            errors.append("top_k 必须在 1-100 之间")
        return errors


@dataclass
class SearchResponse:
    """搜索响应 DTO"""
    success: bool
    query: str
    documents: List[Dict[str, Any]]
    total_count: int
    search_time_ms: float = 0.0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "query": self.query,
            "documents": self.documents,
            "total_count": self.total_count,
            "search_time_ms": self.search_time_ms,
            "error": self.error
        }


@dataclass
class SynthesisRequest:
    """综合查询请求 DTO"""
    question: str
    max_sources: int = 10
    synthesis_mode: str = "detailed"  # "brief" | "detailed" | "technical"
    
    def validate(self) -> List[str]:
        """验证请求数据"""
        errors = []
        if not self.question or not self.question.strip():
            errors.append("问题不能为空")
        if self.synthesis_mode not in ["brief", "detailed", "technical"]:
            errors.append("synthesis_mode 必须是: brief, detailed, technical")
        return errors


@dataclass
class SynthesisResponse:
    """综合查询响应 DTO"""
    success: bool
    synthesized_answer: str
    sources: List[Dict[str, Any]]
    expert_used: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "synthesized_answer": self.synthesized_answer,
            "sources": self.sources,
            "expert_used": self.expert_used,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "error": self.error
        }


@dataclass
class HealthResponse:
    """健康检查响应 DTO"""
    status: str
    services: Dict[str, bool]
    version: str = "1.0.0"
    timestamp: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "status": self.status,
            "services": self.services,
            "version": self.version,
            "timestamp": self.timestamp
        }


@dataclass
class ErrorResponse:
    """错误响应 DTO"""
    error: str
    code: str
    details: Optional[Dict] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error": self.error,
            "code": self.code,
            "details": self.details
        }
