"""
多查询检索器
负责执行多个查询并合并结果
"""
import logging
import requests
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.repositories.vector_repository import VectorRepository
from backend.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class MultiQueryResult:
    """多查询检索结果"""
    documents: List[Dict]                # 合并后的文档列表
    query_contributions: Dict[str, int]  # 每个查询的贡献度
    total_before_dedup: int              # 去重前的总数
    total_after_dedup: int               # 去重后的总数
    retrieval_time: float                # 检索耗时（秒）


class MultiQueryRetriever:
    """多查询检索器类"""
    
    def __init__(self, vector_repo: VectorRepository, bge_api_url: str):
        """
        初始化多查询检索器
        
        Args:
            vector_repo: 向量数据库仓储实例
            bge_api_url: BGE API地址
        """
        self.vector_repo = vector_repo
        self.bge_api_url = bge_api_url
        logger.info("✅ MultiQueryRetriever 初始化成功")
    
    def _generate_embeddings_batch(self, queries: List[str]) -> List[List[float]]:
        """
        批量生成查询embedding
        
        Args:
            queries: 查询列表
            
        Returns:
            embedding列表
            
        Raises:
            Exception: 如果API调用失败
        """
        if not queries:
            return []
        
        try:
            logger.info(f"🔢 正在为 {len(queries)} 个查询生成embedding...")
            response = requests.post(
                self.bge_api_url,
                json={"input": queries},
                timeout=30
            )
            response.raise_for_status()
            embeddings = [item["embedding"] for item in response.json()["data"]]
            logger.info(f"✅ 成功生成 {len(embeddings)} 个embedding")
            return embeddings
        except Exception as e:
            logger.error(f"❌ 批量生成embedding失败: {e}")
            raise
    
    def _retrieve_single(
        self, 
        query: str, 
        query_embedding: List[float], 
        top_k: int = 20
    ) -> List[Dict]:
        """
        单个查询检索
        
        Args:
            query: 查询文本
            query_embedding: 查询embedding
            top_k: 返回结果数量
            
        Returns:
            检索结果列表
        """
        try:
            result = self.vector_repo.search(
                query=query,
                query_embedding=query_embedding,
                n_results=top_k
            )
            
            if not result.get("success"):
                logger.warning(f"⚠️ 查询失败: {query}")
                return []
            
            # 构建文档列表
            documents = []
            for i in range(len(result.get("documents", []))):
                doc = {
                    "text": result["documents"][i],
                    "metadata": result["metadatas"][i],
                    "distance": result["distances"][i],
                    "id": result["ids"][i],
                    "score": 1 - result["distances"][i],  # 转换为相似度分数
                    "source_query": query  # 记录来源查询
                }
                documents.append(doc)
            
            logger.info(f"✅ 查询 '{query}' 返回 {len(documents)} 个结果")
            return documents
            
        except Exception as e:
            logger.error(f"❌ 单个查询检索失败 ({query}): {e}")
            return []
    
    def deduplicate_by_doi(self, documents: List[Dict]) -> List[Dict]:
        """
        按DOI去重，保留每个DOI的最高相似度文档
        
        Args:
            documents: 文档列表
            
        Returns:
            去重后的文档列表
        """
        if not documents:
            return []
        
        # 使用字典存储每个DOI的最佳文档
        doi_to_best_doc: Dict[str, Dict] = {}
        
        for doc in documents:
            # 提取DOI（支持 'doi' 和 'DOI' 两种字段名）
            metadata = doc.get("metadata", {})
            doi = metadata.get("doi") or metadata.get("DOI")
            
            if not doi:
                # 如果没有DOI，为每个文档生成唯一标识
                # 使用 Python 的 id() 函数获取对象的唯一标识
                doi = f"no_doi_{id(doc)}"
            
            # 如果是第一次遇到这个DOI，或者当前文档的分数更高
            if doi not in doi_to_best_doc or doc["score"] > doi_to_best_doc[doi]["score"]:
                doi_to_best_doc[doi] = doc
        
        # 转换为列表并按分数排序
        deduped_docs = list(doi_to_best_doc.values())
        deduped_docs.sort(key=lambda x: x["score"], reverse=True)
        
        logger.info(f"✅ 去重完成: {len(documents)} -> {len(deduped_docs)} 个文档")
        return deduped_docs
    
    def retrieve(
        self, 
        queries: List[str], 
        top_k_per_query: int = 20
    ) -> MultiQueryResult:
        """
        执行多查询检索（使用并行查询优化）
        
        Args:
            queries: 查询列表
            top_k_per_query: 每个查询返回的结果数
            
        Returns:
            多查询检索结果
        """
        start_time = time.time()
        
        if not queries:
            logger.warning("⚠️ 查询列表为空")
            return MultiQueryResult(
                documents=[],
                query_contributions={},
                total_before_dedup=0,
                total_after_dedup=0,
                retrieval_time=0.0
            )
        
        logger.info(f"🔍 开始多查询检索: {len(queries)} 个查询")
        
        # 1. 批量生成embedding
        try:
            embeddings = self._generate_embeddings_batch(queries)
        except Exception as e:
            logger.error(f"❌ 批量生成embedding失败: {e}")
            return MultiQueryResult(
                documents=[],
                query_contributions={},
                total_before_dedup=0,
                total_after_dedup=0,
                retrieval_time=time.time() - start_time
            )
        
        # 2. 并行执行多个查询（性能优化）
        all_documents = []
        query_contributions = {}
        
        # 使用线程池并行执行查询
        max_workers = min(len(queries), 3)  # 最多3个并行线程
        logger.info(f"🚀 使用 {max_workers} 个并行线程执行查询")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有查询任务
            future_to_query = {
                executor.submit(self._retrieve_single, query, embedding, top_k_per_query): query
                for query, embedding in zip(queries, embeddings)
            }
            
            # 收集结果
            for future in as_completed(future_to_query):
                query = future_to_query[future]
                try:
                    docs = future.result()
                    all_documents.extend(docs)
                    query_contributions[query] = len(docs)
                except Exception as e:
                    logger.error(f"❌ 查询失败 ({query}): {e}")
                    query_contributions[query] = 0
        
        total_before_dedup = len(all_documents)
        
        # 3. 去重
        deduped_documents = self.deduplicate_by_doi(all_documents)
        total_after_dedup = len(deduped_documents)
        
        retrieval_time = time.time() - start_time
        
        logger.info(f"✅ 多查询检索完成:")
        logger.info(f"   - 查询数量: {len(queries)}")
        logger.info(f"   - 并行线程: {max_workers}")
        logger.info(f"   - 去重前: {total_before_dedup} 个文档")
        logger.info(f"   - 去重后: {total_after_dedup} 个文档")
        logger.info(f"   - 耗时: {retrieval_time:.2f}s")
        logger.info(f"   - 各查询贡献: {query_contributions}")
        
        return MultiQueryResult(
            documents=deduped_documents,
            query_contributions=query_contributions,
            total_before_dedup=total_before_dedup,
            total_after_dedup=total_after_dedup,
            retrieval_time=retrieval_time
        )
