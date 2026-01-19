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
    
    def __init__(self, collection_name: str = "lfp_papers_v3"):
        """
        初始化向量数据库
        
        Args:
            collection_name: 集合名称（默认使用段落级别的 v3 版本）
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
        语义搜索（支持段落级别检索和 DOI 去重）
        
        Args:
            query: 搜索查询文本（如果提供query_embedding则忽略）
            query_embedding: 查询的embedding向量（1024维）
            n_results: 返回结果数量
            where_filter: 过滤条件
            
        Returns:
            搜索结果（包含 documents, metadatas, distances）
            注意：段落级别数据库会自动按 DOI 去重，返回每篇文献的最相关段落
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
            
            # 查询更多结果用于去重（段落级别数据库需要）
            fetch_count = n_results * 3  # 获取3倍数量用于去重
            
            result = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=fetch_count,
                where=where_filter
            )
            
            # 提取结果
            documents = result.get("documents", [[]])[0]
            metadatas = result.get("metadatas", [[]])[0]
            distances = result.get("distances", [[]])[0]
            ids = result.get("ids", [[]])[0]
            
            # 按 DOI 去重（保留每个 DOI 的最相关段落）
            seen_dois = set()
            deduped_docs = []
            deduped_metas = []
            deduped_dists = []
            deduped_ids = []
            
            for i in range(len(documents)):
                meta = metadatas[i]
                doi = meta.get('doi', 'unknown')
                
                # 如果所有文档都是 unknown_doi，则不进行DOI去重
                # 否则跳过 unknown_doi 文档
                if doi == 'unknown_doi':
                    # 检查是否所有文档都是 unknown_doi
                    all_unknown = all(m.get('doi') == 'unknown_doi' for m in metadatas)
                    if not all_unknown:
                        continue  # 只有在有其他有效DOI时才跳过
                
                # 去重：每个 DOI 只保留第一个（最相关的）段落
                # 但如果DOI是 unknown_doi，则不去重（因为无法区分）
                if doi == 'unknown_doi' or doi not in seen_dois:
                    if doi != 'unknown_doi':
                        seen_dois.add(doi)
                    deduped_docs.append(documents[i])
                    deduped_metas.append(meta)
                    deduped_dists.append(distances[i])
                    deduped_ids.append(ids[i])
                    
                    # 达到目标数量就停止
                    if len(deduped_docs) >= n_results:
                        break
            
            return {
                "success": True,
                "documents": deduped_docs,
                "metadatas": deduped_metas,
                "distances": deduped_dists,
                "ids": deduped_ids
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
        根据 DOI 获取文档（段落级别数据库会返回所有相关段落）
        
        Args:
            doi: 文献 DOI
            
        Returns:
            文档信息列表或 None（v2 版本返回多个段落）
        """
        try:
            result = self._collection.get(
                where={"doi": doi},
                limit=100  # 限制返回段落数量
            )
            
            if result and result.get("ids"):
                # 返回所有段落
                return {
                    "ids": result["ids"],
                    "documents": result["documents"],
                    "metadatas": result["metadatas"],
                    "count": len(result["ids"])
                }
            return None
            
        except Exception as e:
            logger.error(f"获取 DOI 文档失败: {e}")
            return None
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        根据 chunk_id 获取单个段落
        
        Args:
            chunk_id: 段落ID
            
        Returns:
            段落信息或 None
        """
        try:
            if not chunk_id:
                return None
            
            result = self._collection.get(
                ids=[chunk_id],
                include=["documents", "metadatas"]
            )
            
            if result and result.get("ids"):
                return {
                    "id": result["ids"][0],
                    "document": result["documents"][0],
                    "metadata": result["metadatas"][0]
                }
            return None
            
        except Exception as e:
            logger.error(f"获取段落失败 ({chunk_id}): {e}")
            return None
    
    def get_chunk_with_context(
        self, 
        chunk_id: str, 
        window: int = 2
    ) -> Dict[str, Any]:
        """
        获取段落及其上下文（V3新功能）
        
        Args:
            chunk_id: 段落ID
            window: 上下文窗口大小（前后各window个段落）
            
        Returns:
            包含主段落和上下文的完整信息
        """
        try:
            # 获取主段落
            main_chunk = self.get_chunk_by_id(chunk_id)
            if not main_chunk:
                return {
                    "success": False,
                    "error": f"段落不存在: {chunk_id}"
                }
            
            metadata = main_chunk["metadata"]
            
            # 收集上下文段落
            context_chunks = []
            
            # 向前获取
            current_id = chunk_id
            for i in range(window):
                prev_id = metadata.get("prev_chunk_id") if i == 0 else context_chunks[0]["metadata"].get("prev_chunk_id")
                if prev_id:
                    prev_chunk = self.get_chunk_by_id(prev_id)
                    if prev_chunk:
                        context_chunks.insert(0, prev_chunk)
                        metadata = prev_chunk["metadata"]
                    else:
                        break
                else:
                    break
            
            # 添加主段落
            main_index = len(context_chunks)
            context_chunks.append(main_chunk)
            
            # 向后获取
            metadata = main_chunk["metadata"]
            for i in range(window):
                next_id = metadata.get("next_chunk_id") if i == 0 else context_chunks[-1]["metadata"].get("next_chunk_id")
                if next_id:
                    next_chunk = self.get_chunk_by_id(next_id)
                    if next_chunk:
                        context_chunks.append(next_chunk)
                        metadata = next_chunk["metadata"]
                    else:
                        break
                else:
                    break
            
            # 组合完整文本
            full_text = " ".join([chunk["document"] for chunk in context_chunks])
            
            # 构建上下文信息
            main_meta = main_chunk["metadata"]
            context_info = {
                "success": True,
                "main_chunk_id": chunk_id,
                "full_text": full_text,
                "main_text": main_chunk["document"],
                "context_chunks": len(context_chunks),
                "main_chunk_index": main_index,
                "metadata": main_meta,
                "context_range": {
                    "start_page": context_chunks[0]["metadata"].get("page"),
                    "end_page": context_chunks[-1]["metadata"].get("page"),
                    "start_chunk_global": context_chunks[0]["metadata"].get("chunk_index_global"),
                    "end_chunk_global": context_chunks[-1]["metadata"].get("chunk_index_global"),
                }
            }
            
            return context_info
            
        except Exception as e:
            logger.error(f"获取上下文失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
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
        获取所有文档的元数据（兼容新旧元数据格式）
        
        Args:
            limit: 限制数量
            
        Returns:
            元数据列表（自动兼容 source_file 和 filename 字段）
        """
        try:
            result = self._collection.get(limit=limit)
            metadatas = result.get("metadatas", [])
            
            # 标准化元数据字段（兼容新旧格式）
            normalized = []
            for meta in metadatas:
                # 统一使用 filename 字段
                if 'source_file' in meta and 'filename' not in meta:
                    meta['filename'] = meta['source_file']
                elif 'filename' in meta and 'source_file' not in meta:
                    meta['source_file'] = meta['filename']
                normalized.append(meta)
            
            return normalized
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
