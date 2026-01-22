"""
反向引用查找器
为给定的DOI找到答案中最相关的句子位置
运行环境: conda run -n py310
"""
import logging
import requests
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from backend.models.citation_location import CitationLocation

logger = logging.getLogger(__name__)


class ReverseCitationFinder:
    """
    反向引用查找器
    
    为参考文献列表中的DOI找到答案中最相关的句子，
    并从数据库中获取准确的页码和段落位置信息。
    """
    
    def __init__(
        self,
        sentence_collection,      # 句子级数据库collection
        paragraph_collection,     # 段落级数据库collection
        bge_api_url: str
    ):
        """
        初始化反向引用查找器
        
        Args:
            sentence_collection: ChromaDB句子级collection (lfp_papers_sentences_v1)
            paragraph_collection: ChromaDB段落级collection (lfp_papers_v3)
            bge_api_url: BGE API地址
        """
        self.sentence_collection = sentence_collection
        self.paragraph_collection = paragraph_collection
        self.bge_api_url = bge_api_url
        
        # 缓存
        self._embedding_cache: Dict[str, List[float]] = {}
        self._page_cache: Dict[str, int] = {}  # DOI -> 页码缓存
        
        logger.info("✅ ReverseCitationFinder 初始化成功")
    
    def _get_query_hash(self, query: str) -> str:
        """生成查询的哈希值（用于缓存）"""
        return hashlib.md5(query.encode('utf-8')).hexdigest()
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        生成文本embedding（带缓存）
        
        Args:
            text: 文本内容
            
        Returns:
            embedding向量
        """
        # 检查缓存
        text_hash = self._get_query_hash(text)
        if text_hash in self._embedding_cache:
            return self._embedding_cache[text_hash]
        
        try:
            response = requests.post(
                self.bge_api_url,
                json={"input": [text]},
                timeout=30
            )
            response.raise_for_status()
            embedding = response.json()["data"][0]["embedding"]
            
            # 缓存结果
            self._embedding_cache[text_hash] = embedding
            
            return embedding
        except Exception as e:
            logger.error(f"❌ 生成embedding失败: {e}")
            raise
    
    def _get_page_for_doi(self, doi: str) -> int:
        """
        从段落级数据库获取DOI的页码
        
        Args:
            doi: 文献DOI
            
        Returns:
            页码（如果找不到返回0）
        """
        # 检查缓存
        if doi in self._page_cache:
            return self._page_cache[doi]
        
        try:
            # 查询段落级数据库
            results = self.paragraph_collection.get(
                where={"doi": doi},
                limit=1,
                include=['metadatas']
            )
            
            if results and results['metadatas']:
                page = results['metadatas'][0].get('page', 0)
                self._page_cache[doi] = page
                return page
            else:
                logger.warning(f"⚠️ 在段落级数据库中未找到DOI: {doi}")
                return 0
                
        except Exception as e:
            logger.error(f"❌ 查询段落级数据库失败 ({doi}): {e}")
            return 0
    
    def find_citations_for_doi(
        self,
        doi: str,
        answer_sentences: List[str],
        top_k: int = 3,
        similarity_threshold: float = 0.3
    ) -> List[CitationLocation]:
        """
        为给定的DOI找到答案中最相关的句子
        
        Args:
            doi: 文献DOI
            answer_sentences: 答案的句子列表
            top_k: 返回的引用位置数量
            similarity_threshold: 相似度阈值
            
        Returns:
            引用位置列表，按相似度降序排列
        """
        if not answer_sentences:
            logger.warning(f"⚠️ 答案句子列表为空")
            return []
        
        logger.info(f"🔍 为DOI查找引用位置: {doi}")
        logger.info(f"   答案句子数: {len(answer_sentences)}")
        
        try:
            # 1. 为每个答案句子生成embedding
            answer_embeddings = []
            for i, sentence in enumerate(answer_sentences):
                if sentence.strip():
                    embedding = self._generate_embedding(sentence)
                    answer_embeddings.append((i, sentence, embedding))
            
            logger.info(f"   生成了 {len(answer_embeddings)} 个embedding")
            
            # 2. 在句子级数据库中查询该DOI的句子
            # 注意：句子级数据库使用大写的"DOI"字段
            all_citations = []
            
            for answer_idx, answer_sentence, answer_embedding in answer_embeddings:
                try:
                    # 查询句子级数据库
                    results = self.sentence_collection.query(
                        query_embeddings=[answer_embedding],
                        n_results=10,  # 多取一些用于筛选
                        where={"DOI": doi},  # 注意大写
                        include=["documents", "metadatas", "distances"]
                    )
                    
                    if not results or not results.get("documents") or not results["documents"][0]:
                        continue
                    
                    # 3. 计算相似度并创建CitationLocation
                    for i in range(len(results["documents"][0])):
                        distance = results["distances"][0][i]
                        similarity = 1 - (distance / 2.0)  # ChromaDB余弦距离转换
                        
                        if similarity >= similarity_threshold:
                            sentence_text = results["documents"][0][i]
                            sentence_metadata = results["metadatas"][0][i]
                            
                            # 从段落级数据库获取页码
                            page = self._get_page_for_doi(doi)
                            
                            # 创建CitationLocation
                            citation = CitationLocation.from_sentence_db(
                                doi=doi,
                                answer_sentence=answer_sentence,
                                answer_sentence_index=answer_idx,
                                sentence_text=sentence_text,
                                sentence_metadata=sentence_metadata,
                                similarity=similarity,
                                page=page
                            )
                            
                            all_citations.append(citation)
                            
                            # 每个答案句子只保留最佳匹配
                            break
                
                except Exception as e:
                    logger.warning(f"⚠️ 查询句子失败 (answer_idx={answer_idx}): {e}")
                    continue
            
            # 4. 按相似度排序，返回top-k
            all_citations.sort(key=lambda x: x.similarity, reverse=True)
            result = all_citations[:top_k]
            
            logger.info(f"✅ 找到 {len(result)} 个引用位置")
            if result:
                logger.info(f"   最高相似度: {result[0].similarity:.3f}")
                logger.info(f"   页码: {result[0].page}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 查找引用位置失败: {e}")
            return []
    
    def clear_cache(self):
        """清除所有缓存"""
        self._embedding_cache.clear()
        self._page_cache.clear()
        logger.info("✅ 缓存已清除")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息
        """
        return {
            "embedding_cache_size": len(self._embedding_cache),
            "page_cache_size": len(self._page_cache)
        }
