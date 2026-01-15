"""
数据模型层
定义领域实体和数据传输对象
"""

from .entities import (
    Material,
    Paper,
    CommunitySummary,
    QueryResult,
    RoutingDecision,
    SearchResult
)

from .dtos import (
    QueryType,
    ExpertType,
    QueryRequest,
    QueryResponse,
    RouteRequest,
    RouteResponse,
    MaterialQueryParams,
    MaterialQueryResult,
    SearchParams,
    SearchResponse,
    SynthesisRequest,
    SynthesisResponse,
    HealthResponse,
    ErrorResponse
)

__all__ = [
    # Entities
    'Material',
    'Paper',
    'CommunitySummary',
    'QueryResult',
    'RoutingDecision',
    'SearchResult',
    # DTOs
    'QueryType',
    'ExpertType',
    'QueryRequest',
    'QueryResponse',
    'RouteRequest',
    'RouteResponse',
    'MaterialQueryParams',
    'MaterialQueryResult',
    'SearchParams',
    'SearchResponse',
    'SynthesisRequest',
    'SynthesisResponse',
    'HealthResponse',
    'ErrorResponse',
]
