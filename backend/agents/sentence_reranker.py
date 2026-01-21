"""
句子级重排序器
负责使用句子数据库重新排序候选文献
"""
import logging
import requests
import time
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from functools import lru_cache

logger = logging.getLogger(__name__)


@dataclass
class RerankingResult:
    """重排序结果"""
    documents: List[Dict]                      # 重排序后的文档列表
    similarity_scores: Dict[str, float]        # 每个DOI的相似度
    reranking_time: float                      # 重排序耗时（秒）
    top_3_changes: List[tuple[str, int, int]]  # top-3的排名变化 (doi, old_rank, new_rank)


class SentenceReranker:
    """句子级重排序器类"""
    
    def __init__(
        self, 
        sentence_collection,
        bge_api_url: str
    ):
        """
        初始化重排序器
        
        Args:
            sentence_collection: ChromaDB句子级collection实例
            bge_api_url: BGE API地址
        """
        self.sentence_collection = sentence_collection
        self.bge_api_url = bge_api_url
        
        # 初始化缓存字典（用于缓存查询embedding和相似度分数）
        self._embedding_cache: Dict[str, List[float]] = {}
        self._similarity_cache: Dict[str, float] = {}
        
        logger.info("✅ SentenceReranker 初始化成功")
    
    def _get_query_hash(self, query: str) -> str:
        """
        生成查询的哈希值（用于缓存）
        
        Args:
            query: 查询文本
            
        Returns:
            查询的MD5哈希值
        """
        return hashlib.md5(query.encode('utf-8')).hexdigest()
    
    def _get_cache_key(self, query: str, doi: str) -> str:
        """
        生成缓存键
        
        Args:
            query: 查询文本
            doi: 文献DOI
            
        Returns:
            缓存键
        """
        query_hash = self._get_query_hash(query)
        return f"{query_hash}:{doi}"
    
    def _generate_query_embedding(self, query: str) -> List[float]:
        """
        生成查询embedding（带缓存）
        
        Args:
            query: 查询文本
            
        Returns:
            查询embedding向量
            
        Raises:
            Exception: 如果API调用失败
        """
        # 检查缓存
        query_hash = self._get_query_hash(query)
        if query_hash in self._embedding_cache:
            logger.info(f"✅ 使用缓存的查询embedding")
            return self._embedding_cache[query_hash]
        
        try:
            response = requests.post(
                self.bge_api_url,
                json={"input": [query]},
                timeout=30
            )
            response.raise_for_status()
            embedding = response.json()["data"][0]["embedding"]
            
            # 缓存结果
            self._embedding_cache[query_hash] = embedding
            logger.info(f"✅ 生成并缓存查询embedding")
            
            return embedding
        except Exception as e:
            logger.error(f"❌ 生成查询embedding失败: {e}")
            raise
    
    def _clean_doi(self, doi: str) -> str:
        """
        清理DOI，去掉常见的后缀
        
        Args:
            doi: 原始DOI
            
        Returns:
            清理后的DOI
        """
        if not doi:
            return doi
        
        # 去掉常见后缀
        suffixes = ["abstract", "full", "pdf", "epdf", "html"]
        doi_lower = doi.lower()
        
        for suffix in suffixes:
            if doi_lower.endswith(suffix):
                # 去掉后缀
                doi = doi[:-len(suffix)]
                logger.debug(f"清理DOI: 去掉后缀 '{suffix}' -> {doi}")
                break
        
        return doi.strip()
    
    def _batch_query_sentences(
        self, 
        query_embedding: List[float],
        dois: List[str],
        n_results_per_doi: int = 50
    ) -> Dict[str, List[Dict]]:
        """
        批量查询句子数据库（优化版）
        
        Args:
            query_embedding: 查询embedding
            dois: DOI列表
            n_results_per_doi: 每个DOI返回的句子数量
            
        Returns:
            DOI到句子列表的映射
        """
        doi_to_sentences = {}
        
        # 批量查询优化：对于多个DOI，可以考虑并行查询
        # 但由于ChromaDB的限制，这里仍然串行查询，但添加了更好的错误处理
        
        for doi in dois:
            try:
                # 在句子数据库中查询该DOI的所有句子
                # 注意：句子数据库中DOI字段是大写的"DOI"
                results = self.sentence_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results_per_doi,
                    where={"DOI": doi}
                )
                
                # 提取句子和相似度
                sentences = []
                if results and results.get("documents"):
                    documents = results["documents"][0]
                    distances = results["distances"][0]
                    metadatas = results["metadatas"][0]
                    
                    # 添加调试日志
                    if len(documents) > 0:
                        logger.debug(f"✅ DOI {doi}: 找到 {len(documents)} 个句子")
                    else:
                        logger.warning(f"⚠️ DOI {doi}: 查询成功但没有返回句子")
                    
                    for i in range(len(documents)):
                        # ChromaDB使用余弦距离，范围[0,2]
                        # 转换为相似度：similarity = 1 - (distance / 2)
                        # 这样相似度范围是[0,1]，其中1表示完全相同，0表示完全不同
                        distance = distances[i]
                        similarity = 1 - (distance / 2.0)
                        
                        sentences.append({
                            "text": documents[i],
                            "distance": distance,
                            "similarity": similarity,
                            "metadata": metadatas[i]
                        })
                else:
                    logger.warning(f"⚠️ DOI {doi}: 查询返回空结果")
                
                doi_to_sentences[doi] = sentences
                
            except Exception as e:
                logger.warning(f"⚠️ 查询DOI句子失败 ({doi}): {e}")
                doi_to_sentences[doi] = []
        
        return doi_to_sentences
    
    def clear_cache(self):
        """清除所有缓存"""
        self._embedding_cache.clear()
        self._similarity_cache.clear()
        logger.info("✅ 缓存已清除")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息
        """
        return {
            "embedding_cache_size": len(self._embedding_cache),
            "similarity_cache_size": len(self._similarity_cache)
        }
    
    def _compute_max_sentence_similarity(
        self,
        query: str,
        doi: str,
        doi_sentences: List[Dict]
    ) -> float:
        """
        计算DOI的最高句子相似度（带缓存）
        
        Args:
            query: 查询文本
            doi: 文献DOI
            doi_sentences: 该DOI的句子列表
            
        Returns:
            最高句子相似度
        """
        # 检查缓存
        cache_key = self._get_cache_key(query, doi)
        if cache_key in self._similarity_cache:
            logger.debug(f"✅ 使用缓存的相似度分数: {doi}")
            return self._similarity_cache[cache_key]
        
        if not doi_sentences:
            logger.warning(f"⚠️ DOI {doi} 没有句子数据")
            return 0.0
        
        # 找到最高相似度
        max_similarity = max(s["similarity"] for s in doi_sentences)
        
        # 缓存结果
        self._similarity_cache[cache_key] = max_similarity
        
        return max_similarity
    
    def rerank(
        self,
        query: str,
        candidates: List[Dict],
        top_k: int = 15
    ) -> RerankingResult:
        """
        重新排序候选文献
        
        Args:
            query: 原始查询
            candidates: 候选文献列表
            top_k: 返回的文献数量
            
        Returns:
            重排序结果
        """
        start_time = time.time()
        
        if not candidates:
            logger.warning("⚠️ 候选文献列表为空")
            return RerankingResult(
                documents=[],
                similarity_scores={},
                reranking_time=0.0,
                top_3_changes=[]
            )
        
        logger.info(f"🔄 开始重排序: {len(candidates)} 个候选文献")
        
        # 记录原始排名（用于对比）
        original_ranking = {}
        for i, doc in enumerate(candidates):
            metadata = doc.get("metadata", {})
            doi = metadata.get("doi") or metadata.get("DOI", f"no_doi_{i}")
            # 清理DOI
            if doi and not doi.startswith("no_doi_"):
                doi = self._clean_doi(doi)
            original_ranking[doi] = i
        
        try:
            # 1. 生成查询embedding
            query_embedding = self._generate_query_embedding(query)
            
            # 2. 提取所有候选DOI并清理
            dois = []
            for doc in candidates:
                metadata = doc.get("metadata", {})
                doi = metadata.get("doi") or metadata.get("DOI")
                if doi:
                    # 清理DOI（去掉abstract等后缀）
                    clean_doi = self._clean_doi(doi)
                    dois.append(clean_doi)
            
            if not dois:
                logger.warning("⚠️ 候选文献中没有有效的DOI")
                # 为候选文献添加rerank_score（使用原始分数）
                for doc in candidates:
                    doc["rerank_score"] = doc.get("score", 0.0)
                return RerankingResult(
                    documents=candidates[:top_k],
                    similarity_scores={},
                    reranking_time=time.time() - start_time,
                    top_3_changes=[]
                )
            
            # 3. 批量查询句子数据库
            doi_to_sentences = self._batch_query_sentences(
                query_embedding,
                dois,
                n_results_per_doi=50
            )
            
            # 4. 计算每个DOI的最高句子相似度
            similarity_scores = {}
            cache_hits = 0
            cache_misses = 0
            
            for doi, sentences in doi_to_sentences.items():
                cache_key = self._get_cache_key(query, doi)
                if cache_key in self._similarity_cache:
                    cache_hits += 1
                else:
                    cache_misses += 1
                
                max_sim = self._compute_max_sentence_similarity(query, doi, sentences)
                similarity_scores[doi] = max_sim
            
            logger.info(f"📊 缓存统计: 命中={cache_hits}, 未命中={cache_misses}")
            
            # 5. 为每个候选文献添加重排序分数
            for doc in candidates:
                metadata = doc.get("metadata", {})
                doi = metadata.get("doi") or metadata.get("DOI")
                if doi:
                    # 清理DOI后再查找相似度
                    clean_doi = self._clean_doi(doi)
                    if clean_doi in similarity_scores:
                        doc["rerank_score"] = similarity_scores[clean_doi]
                    else:
                        # 如果没有句子数据，使用原始分数
                        doc["rerank_score"] = doc.get("score", 0.0)
                else:
                    # 如果没有句子数据，使用原始分数
                    doc["rerank_score"] = doc.get("score", 0.0)
            
            # 6. 按重排序分数降序排列
            reranked_docs = sorted(
                candidates,
                key=lambda x: x.get("rerank_score", 0.0),
                reverse=True
            )
            
            # 7. 计算top-3的排名变化
            top_3_changes = []
            for i in range(min(3, len(reranked_docs))):
                doc = reranked_docs[i]
                metadata = doc.get("metadata", {})
                doi = metadata.get("doi") or metadata.get("DOI", f"no_doi_{i}")
                # 清理DOI
                if doi and not doi.startswith("no_doi_"):
                    doi = self._clean_doi(doi)
                old_rank = original_ranking.get(doi, -1)
                new_rank = i
                top_3_changes.append((doi, old_rank, new_rank))
            
            # 8. 返回top-k结果
            final_docs = reranked_docs[:top_k]
            
            reranking_time = time.time() - start_time
            
            logger.info(f"✅ 重排序完成:")
            logger.info(f"   - 候选数量: {len(candidates)}")
            logger.info(f"   - 返回数量: {len(final_docs)}")
            logger.info(f"   - 耗时: {reranking_time:.2f}s")
            logger.info(f"   - Top-3变化: {top_3_changes}")
            
            return RerankingResult(
                documents=final_docs,
                similarity_scores=similarity_scores,
                reranking_time=reranking_time,
                top_3_changes=top_3_changes
            )
            
        except Exception as e:
            logger.error(f"❌ 重排序失败: {e}")
            # 失败时返回原始排序，添加rerank_score
            for doc in candidates:
                doc["rerank_score"] = doc.get("score", 0.0)
            return RerankingResult(
                documents=candidates[:top_k],
                similarity_scores={},
                reranking_time=time.time() - start_time,
                top_3_changes=[]
            )
