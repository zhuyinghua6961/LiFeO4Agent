"""
向量数据库访问层
封装 ChromaDB 操作
"""
from typing import Dict, List, Any, Optional
import logging

from backend.config.settings import settings

logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    logger.warning("ChromaDB 未安装")


class VectorRepository:
    """ChromaDB 向量数据库访问类"""
    
    def __init__(self, collection_name: str = "lfp_papers"):
        """
        初始化向量数据库
        
        Args:
            collection_name: 集合名称
        """
        if not CHROMA_AVAILABLE:
            raise ImportError("ChromaDB 未安装，请先安装: pip install chromadb")
        
        self._client = None
        self._collection = None
        self._collection_name = collection_name
        self._init_client()
    
    def _init_client(self):
        """初始化 ChromaDB 客户端"""
        try:
            self._client = chromadb.PersistentClient(
                path=settings.vector_db_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # 获取集合（不使用embedding function，因为数据已经包含预计算的embedding）
            self._collection = self._client.get_collection(
                name=self._collection_name
            )
            
            logger.info(f"✅ ChromaDB 连接成功，集合: {self._collection_name}")
            logger.info(f"   文档数量: {self._collection.count()}")
            
        except Exception as e:
            logger.error(f"❌ ChromaDB 连接失败: {e}")
            raise
    
    def search(
        self, 
        query: str = None,
        query_embedding: List[float] = None,
        n_results: int = 10,
        where_filter: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        语义搜索
        
        Args:
            query: 搜索查询文本（如果提供query_embedding则忽略）
            query_embedding: 查询的embedding向量（1024维）
            n_results: 返回结果数量
            where_filter: 过滤条件
            
        Returns:
            搜索结果（包含 documents, metadatas, distances）
        """
        try:
            # 如果没有提供embedding，返回错误
            if query_embedding is None:
                return {
                    "success": False,
                    "error": "需要提供 query_embedding 参数（1024维向量）",
                    "documents": [],
                    "metadatas": [],
                    "distances": [],
                    "ids": []
                }
            
            result = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter
            )
            
            return {
                "success": True,
                "documents": result.get("documents", [[]])[0],
                "metadatas": result.get("metadatas", [[]])[0],
                "distances": result.get("distances", [[]])[0],
                "ids": result.get("ids", [[]])[0]
            }
            
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "documents": [],
                "metadatas": [],
                "distances": [],
                "ids": []
            }
    
    def search_with_filter(
        self,
        query: str,
        n_results: int = 10,
        property_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        带属性过滤的搜索
        
        Args:
            query: 搜索查询
            n_results: 返回数量
            property_filter: 属性过滤条件
            
        Returns:
            搜索结果
        """
        # 构建 ChromaDB where 过滤条件
        where_filter = None
        if property_filter:
            where_filter = {}
            for key, value in property_filter.items():
                where_filter[key] = {"$eq": value}
        
        return self.search(query, n_results, where_filter)
    
    def get_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        根据 DOI 获取文档
        
        Args:
            doi: 文献 DOI
            
        Returns:
            文档信息或 None
        """
        try:
            result = self._collection.get(
                where={"doi": doi}
            )
            
            if result and result.get("ids"):
                return {
                    "id": result["ids"][0],
                    "document": result["documents"][0],
                    "metadata": result["metadatas"][0]
                }
            return None
            
        except Exception as e:
            logger.error(f"获取 DOI 文档失败: {e}")
            return None
    
    def get_count(self) -> int:
        """获取文档总数"""
        try:
            return self._collection.count()
        except Exception as e:
            logger.error(f"获取文档数量失败: {e}")
            return 0
    
    def get_all_documents(self, limit: int = 10000) -> List[Dict]:
        """
        获取所有文档（用于关键词匹配降级方案）
        
        Args:
            limit: 限制数量
            
        Returns:
            文档列表，每项包含 text 和 metadata
        """
        try:
            result = self._collection.get(limit=limit, include=["documents", "metadatas"])
            docs = []
            for i, doc in enumerate(result.get("documents", [])):
                docs.append({
                    "text": doc,
                    "metadata": result.get("metadatas", [{}])[i]
                })
            return docs
        except Exception as e:
            logger.error(f"获取所有文档失败: {e}")
            return []
    
    def get_all_metadata(self, limit: int = 1000) -> List[Dict]:
        """
        获取所有文档的元数据
        
        Args:
            limit: 限制数量
            
        Returns:
            元数据列表
        """
        try:
            result = self._collection.get(limit=limit)
            return result.get("metadatas", [])
        except Exception as e:
            logger.error(f"获取元数据失败: {e}")
            return []
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict],
        ids: List[str]
    ) -> bool:
        """
        添加文档
        
        Args:
            documents: 文档内容列表
            metadatas: 元数据列表
            ids: ID 列表
            
        Returns:
            是否成功
        """
        try:
            self._collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"✅ 添加 {len(documents)} 个文档")
            return True
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            return False
    
    def delete_by_doi(self, doi: str) -> bool:
        """
        根据 DOI 删除文档
        
        Args:
            doi: 文献 DOI
            
        Returns:
            是否成功
        """
        try:
            self._collection.delete(
                where={"doi": doi}
            )
            logger.info(f"✅ 删除 DOI 为 {doi} 的文档")
            return True
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False
    
    def close(self):
        """关闭连接"""
        if self._client:
            self._client.close()


class CommunityVectorRepository:
    """社区摘要向量数据库访问类"""
    
    def __init__(self, collection_name: str = "communities"):
        """初始化社区向量数据库"""
        if not CHROMA_AVAILABLE:
            raise ImportError("ChromaDB 未安装")
        
        self._client = None
        self._collection = None
        self._collection_name = collection_name
        self._init_client()
    
    def _init_client(self):
        """初始化 ChromaDB 客户端"""
        try:
            self._client = chromadb.PersistentClient(
                path=settings.community_vector_db_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info(f"✅ 社区向量库连接成功，集合: {self._collection_name}")
            logger.info(f"   文档数量: {self._collection.count()}")
            
        except Exception as e:
            logger.error(f"❌ 社区向量库连接失败: {e}")
            raise
    
    def search(
        self, 
        query: str, 
        n_results: int = 10
    ) -> Dict[str, Any]:
        """搜索社区摘要"""
        try:
            result = self._collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            return {
                "success": True,
                "documents": result.get("documents", [[]])[0],
                "metadatas": result.get("metadatas", [[]])[0],
                "distances": result.get("distances", [[]])[0],
                "ids": result.get("ids", [[]])[0]
            }
            
        except Exception as e:
            logger.error(f"社区摘要搜索失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "documents": [],
                "metadatas": [],
                "distances": []
            }
    
    def get_count(self) -> int:
        """获取文档总数"""
        try:
            return self._collection.count()
        except Exception as e:
            logger.error(f"获取文档数量失败: {e}")
            return 0
    
    def close(self):
        """关闭连接"""
        if self._client:
            self._client.close()


# 创建全局实例
_vector_repo: Optional[VectorRepository] = None
_community_repo: Optional[CommunityVectorRepository] = None


def get_vector_repository() -> VectorRepository:
    """获取全局 Vector Repository 实例"""
    global _vector_repo
    if _vector_repo is None:
        _vector_repo = VectorRepository()
    return _vector_repo


def get_community_repository() -> CommunityVectorRepository:
    """获取全局 Community Repository 实例"""
    global _community_repo
    if _community_repo is None:
        _community_repo = CommunityVectorRepository()
    return _community_repo
