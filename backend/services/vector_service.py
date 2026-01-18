"""
向量数据库服务
封装向量数据库操作
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
import time

from backend.repositories.vector_repository import VectorRepository, CommunityVectorRepository
from backend.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class VectorService:
    """向量数据库服务"""
    
    def __init__(
        self,
        vector_repo: Optional[VectorRepository] = None,
        community_repo: Optional[CommunityVectorRepository] = None,
        llm_service: Optional[LLMService] = None
    ):
        """
        初始化向量服务
        
        Args:
            vector_repo: 文献向量仓储
            community_repo: 社区向量仓储
            llm_service: LLM服务
        """
        self._vector_repo = vector_repo
        self._community_repo = community_repo
        self._llm = llm_service
        
        logger.info("🔢 向量服务初始化完成")
    
    def search_literature(
        self,
        query: str,
        top_k: int = 10,
        filter_metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        搜索文献
        
        Args:
            query: 搜索查询
            top_k: 返回数量
            filter_metadata: 元数据过滤
            
        Returns:
            搜索结果
        """
        if self._vector_repo is None:
            return {
                "success": False,
                "error": "向量数据库未初始化",
                "documents": []
            }
        
        try:
            start_time = time.time()
            
            results = self._vector_repo.search(
                query=query,
                top_k=top_k,
                with_scores=True,
                filter_metadata=filter_metadata
            )
            
            search_time = (time.time() - start_time) * 1000
            
            # 格式化结果
            documents = []
            for doc, score in results:
                doc_data = {
                    "id": doc.id if hasattr(doc, 'id') else str(doc),
                    "content": doc.page_content if hasattr(doc, 'page_content') else str(doc),
                    "score": score
                }
                if hasattr(doc, 'metadata') and doc.metadata:
                    doc_data["metadata"] = doc.metadata
                documents.append(doc_data)
            
            return {
                "success": True,
                "query": query,
                "documents": documents,
                "total_count": len(documents),
                "search_time_ms": search_time
            }
            
        except Exception as e:
            logger.error(f"文献搜索失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "documents": []
            }
    
    def search_community(
        self,
        query: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        搜索社区摘要
        
        Args:
            query: 搜索查询
            top_k: 返回数量
            
        Returns:
            搜索结果
        """
        if self._community_repo is None:
            return {
                "success": False,
                "error": "社区向量数据库未初始化",
                "communities": []
            }
        
        try:
            start_time = time.time()
            
            results = self._community_repo.search(
                query=query,
                top_k=top_k,
                with_scores=True
            )
            
            search_time = (time.time() - start_time) * 1000
            
            # 格式化结果
            communities = []
            for doc, score in results:
                doc_data = {
                    "id": doc.id if hasattr(doc, 'id') else str(doc),
                    "content": doc.page_content if hasattr(doc, 'page_content') else str(doc),
                    "score": score
                }
                if hasattr(doc, 'metadata') and doc.metadata:
                    doc_data["metadata"] = doc.metadata
                communities.append(doc_data)
            
            return {
                "success": True,
                "query": query,
                "communities": communities,
                "total_count": len(communities),
                "search_time_ms": search_time
            }
            
        except Exception as e:
            logger.error(f"社区搜索失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "communities": []
            }
    
    def find_similar(
        self,
        document_text: str,
        top_k: int = 5,
        collection: str = "literature"
    ) -> Dict[str, Any]:
        """
        查找相似文档
        
        Args:
            document_text: 文档内容
            top_k: 返回数量
            collection: 集合名称
            
        Returns:
            相似文档列表
        """
        if collection == "community":
            repo = self._community_repo
        else:
            repo = self._vector_repo
        
        if repo is None:
            return {
                "success": False,
                "error": "向量数据库未初始化",
                "documents": []
            }
        
        try:
            results = repo.find_similar(
                document_text=document_text,
                top_k=top_k
            )
            
            documents = []
            for doc in results:
                doc_data = {
                    "content": doc.page_content if hasattr(doc, 'page_content') else str(doc),
                }
                if hasattr(doc, 'metadata') and doc.metadata:
                    doc_data["metadata"] = doc.metadata
                documents.append(doc_data)
            
            return {
                "success": True,
                "documents": documents,
                "total_count": len(documents)
            }
            
        except Exception as e:
            logger.error(f"查找相似文档失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "documents": []
            }
    
    def aggregate_knowledge(
        self,
        query: str,
        literature_k: int = 10,
        community_k: int = 5
    ) -> Dict[str, Any]:
        """
        聚合知识（文献+社区摘要）
        
        Args:
            query: 查询
            literature_k: 文献数量
            community_k: 社区数量
            
        Returns:
            聚合结果
        """
        literature_result = self.search_literature(query, top_k=literature_k)
        community_result = self.search_community(query, top_k=community_k)
        
        return {
            "success": True,
            "query": query,
            "literature": literature_result.get("documents", []),
            "communities": community_result.get("communities", []),
            "total_literature": literature_result.get("total_count", 0),
            "total_communities": community_result.get("total_count", 0)
        }
    
    def get_collection_stats(self, collection: str = "literature") -> Dict[str, Any]:
        """
        获取集合统计信息
        
        Args:
            collection: 集合名称
            
        Returns:
            统计信息
        """
        if collection == "community":
            repo = self._community_repo
        else:
            repo = self._vector_repo
        
        if repo is None:
            return {
                "success": False,
                "error": "向量数据库未初始化",
                "count": 0
            }
        
        try:
            count = repo.count()
            return {
                "success": True,
                "collection": collection,
                "count": count
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "count": 0
            }
    
    def health_check(self) -> Dict[str, bool]:
        """
        健康检查
        
        Returns:
            服务状态
        """
        return {
            "vector_repo": self._vector_repo is not None,
            "community_repo": self._community_repo is not None,
            "llm_service": self._llm is not None
        }


# 全局实例（懒加载）
_vector_service_instance: Optional[VectorService] = None


def get_vector_service(
    vector_repo: Optional[VectorRepository] = None,
    community_repo: Optional[CommunityVectorRepository] = None,
    llm_service: Optional[LLMService] = None
) -> VectorService:
    """
    获取向量服务全局实例
    
    Args:
        vector_repo: 文献向量仓储
        community_repo: 社区向量仓储
        llm_service: LLM服务
        
    Returns:
        VectorService实例
    """
    global _vector_service_instance
    
    if _vector_service_instance is None:
        _vector_service_instance = VectorService(
            vector_repo=vector_repo,
            community_repo=community_repo,
            llm_service=llm_service
        )
    
    return _vector_service_instance


def reset_vector_service():
    """重置向量服务实例（用于测试）"""
    global _vector_service_instance
    _vector_service_instance = None
