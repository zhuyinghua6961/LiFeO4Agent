"""
数据访问层
封装所有数据库操作
"""

from .neo4j_repository import Neo4jRepository, get_neo4j_repository
from .vector_repository import VectorRepository, CommunityVectorRepository, get_vector_repository, get_community_repository

__all__ = [
    'Neo4jRepository',
    'get_neo4j_repository',
    'VectorRepository',
    'CommunityVectorRepository',
    'get_vector_repository',
    'get_community_repository',
]
