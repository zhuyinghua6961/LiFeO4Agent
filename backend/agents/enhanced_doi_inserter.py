"""
增强的DOI插入器
确保参考文献列表中的所有DOI都有引用位置
运行环境: conda run -n py310
"""
import logging
import requests
from typing import List, Dict, Any, Tuple, Optional

from backend.models.citation_location import CitationLocation
from backend.agents.reverse_citation_finder import ReverseCitationFinder

logger = logging.getLogger(__name__)


class EnhancedDOIInserter:
    """
    增强的DOI插入器
    
    结合两种策略确保完整覆盖：
    1. 步骤1：为答案中的每个句子找最相关的DOI（原有逻辑）
    2. 步骤2：为参考文献列表中的每个DOI找最相关的答案句子（新增）
    
    最终合并两种方式的引用位置，确保参考文献列表中的所有DOI都有引用位置。
    """
    
    def __init__(
        self,
        sentence_collection,      # 句子级数据库collection
        paragraph_collection,     # 段落级数据库collection
        bge_api_url: str
    ):
        """
        初始化增强的DOI插入器
        
        Args:
            sentence_collection: ChromaDB句子级collection
            paragraph_collection: ChromaDB段落级collection
            bge_api_url: BGE API地址
        """
        self.sentence_collection = sentence_collection
        self.paragraph_collection = paragraph_collection
        self.bge_api_url = bge_api_url
        
        # 初始化反向查找器
        self.reverse_finder = ReverseCitationFinder(
            sentence_collection=sentence_collection,
            paragraph_collection=paragraph_collection,
            bge_api_url=bge_api_url
        )
        
        logger.info("✅ EnhancedDOIInserter 初始化成功")
    
    def insert_dois_with_full_coverage(
        self,
        answer: str,
        documents: List[Dict],
        reference_dois: List[str],
        similarity_threshold: float = 0.3
    ) -> Tuple[str, Dict[str, List[CitationLocation]]]:
        """
        插入DOI并确保参考文献列表中的所有DOI都有引用位置
        
        Args:
            answer: LLM生成的纯净答案
            documents: 一级检索结果（段落级）
            reference_dois: 参考文献列表中的DOI（top-5）
            similarity_threshold: 相似度阈值
            
        Returns:
            - answer_with_dois: 插入DOI后的答案
            - doi_locations: DOI到引用位置列表的映射
        """
        if not answer or not answer.strip():
            logger.warning("⚠️ 答案为空，无法插入DOI")
            return answer, {}
        
        logger.info("\n" + "="*80)
        logger.info("🎯 开始增强的DOI插入")
        logger.info(f"   答案长度: {len(answer)} 字符")
        logger.info(f"   参考文献数: {len(reference_dois)}")
        logger.info(f"   相似度阈值: {similarity_threshold}")
        logger.info("="*80)
        
        # 拆分答案为句子
        answer_sentences = self._split_sentences(answer)
        logger.info(f"📝 拆分为 {len(answer_sentences)} 个句子")
        
        if not answer_sentences:
            logger.warning("⚠️ 答案拆分失败")
            return answer, {}
        
        # ========== 步骤1：为答案句子找DOI（原有逻辑）==========
        logger.info("\n" + "="*80)
        logger.info("📌 [步骤1] 为答案句子找最相关的DOI")
        logger.info("="*80)
        
        step1_locations = self._find_dois_for_sentences(
            answer_sentences=answer_sentences,
            documents=documents,
            similarity_threshold=similarity_threshold
        )
        
        step1_doi_count = len(step1_locations)
        logger.info(f"✅ 步骤1完成: 找到 {step1_doi_count} 个DOI的引用位置")
        
        # ========== 步骤2：为参考文献DOI找答案句子（新增）==========
        logger.info("\n" + "="*80)
        logger.info("📌 [步骤2] 为参考文献DOI找最相关的答案句子")
        logger.info("="*80)
        
        step2_locations = self._find_sentences_for_dois(
            reference_dois=reference_dois,
            answer_sentences=answer_sentences,
            similarity_threshold=similarity_threshold
        )
        
        step2_doi_count = len(step2_locations)
        logger.info(f"✅ 步骤2完成: 找到 {step2_doi_count} 个DOI的引用位置")
        
        # ========== 步骤3：合并引用位置 ==========
        logger.info("\n" + "="*80)
        logger.info("🔄 [步骤3] 合并引用位置")
        logger.info("="*80)
        
        merged_locations = self._merge_locations(step1_locations, step2_locations)
        
        logger.info(f"✅ 合并完成: 共 {len(merged_locations)} 个DOI有引用位置")
        
        # 检查覆盖率
        covered_dois = set(merged_locations.keys())
        missing_dois = set(reference_dois) - covered_dois
        coverage_rate = len(covered_dois) / len(reference_dois) * 100 if reference_dois else 0
        
        logger.info(f"📊 覆盖率统计:")
        logger.info(f"   参考文献总数: {len(reference_dois)}")
        logger.info(f"   已覆盖: {len(covered_dois)} ({coverage_rate:.1f}%)")
        logger.info(f"   未覆盖: {len(missing_dois)}")
        
        if missing_dois:
            logger.warning(f"⚠️ 以下DOI未找到引用位置:")
            for doi in missing_dois:
                logger.warning(f"   - {doi}")
        
        # ========== 步骤4：插入DOI到答案 ==========
        logger.info("\n" + "="*80)
        logger.info("✍️ [步骤4] 插入DOI到答案")
        logger.info("="*80)
        
        answer_with_dois = self._insert_dois_to_answer(
            answer_sentences=answer_sentences,
            doi_locations=merged_locations
        )
        
        logger.info(f"✅ DOI插入完成")
        logger.info("="*80)
        
        return answer_with_dois, merged_locations
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        拆分文本为句子列表
        
        Args:
            text: 文本内容
            
        Returns:
            句子列表
        """
        sentences = []
        current = ""
        
        for char in text:
            current += char
            # 中文句号、问号、感叹号
            if char in ['。', '？', '！', '\n']:
                if current.strip():
                    sentences.append(current)
                current = ""
        
        # 添加最后一个句子
        if current.strip():
            sentences.append(current)
        
        return sentences
    
    def _find_dois_for_sentences(
        self,
        answer_sentences: List[str],
        documents: List[Dict],
        similarity_threshold: float
    ) -> Dict[str, List[CitationLocation]]:
        """
        步骤1：为答案中的每个句子找最相关的DOI
        
        这是原有的DOI插入逻辑：
        - 为每个答案句子生成embedding
        - 在句子级数据库中查询最相关的文献句子
        - 提取DOI并记录引用位置
        
        Args:
            answer_sentences: 答案句子列表
            documents: 一级检索结果
            similarity_threshold: 相似度阈值
            
        Returns:
            DOI到引用位置列表的映射
        """
        doi_locations = {}
        
        # 提取候选DOI池（从一级检索结果）
        candidate_dois = self._extract_candidate_dois(documents)
        logger.info(f"   候选DOI池: {len(candidate_dois)} 个")
        
        if not candidate_dois:
            logger.warning("⚠️ 没有候选DOI")
            return doi_locations
        
        # 批量生成答案句子的embedding
        try:
            valid_sentences = [(i, s) for i, s in enumerate(answer_sentences) if s.strip()]
            sentence_texts = [s for _, s in valid_sentences]
            
            logger.info(f"   正在为 {len(sentence_texts)} 个句子生成embedding...")
            response = requests.post(
                self.bge_api_url,
                json={"input": sentence_texts},
                timeout=60
            )
            response.raise_for_status()
            embeddings = [item["embedding"] for item in response.json()["data"]]
            logger.info(f"   ✅ 成功生成 {len(embeddings)} 个embedding")
            
        except Exception as e:
            logger.error(f"❌ 生成embedding失败: {e}")
            return doi_locations
        
        # 为每个句子查找最相关的DOI
        matched_count = 0
        for (sent_idx, sentence), embedding in zip(valid_sentences, embeddings):
            # 跳过特殊行
            sent_strip = sentence.strip()
            if not sent_strip or sent_strip.startswith('#') or '|' in sent_strip:
                continue
            
            try:
                # 在句子级数据库中查询
                results = self.sentence_collection.query(
                    query_embeddings=[embedding],
                    n_results=50,
                    include=["documents", "metadatas", "distances"]
                )
                
                # 找到最佳匹配（只考虑候选DOI池）
                best_match = None
                best_similarity = 0.0
                
                if results and results["metadatas"] and results["metadatas"][0]:
                    for i, meta in enumerate(results["metadatas"][0]):
                        doi = meta.get('DOI') or meta.get('doi')
                        
                        if doi and doi in candidate_dois:
                            distance = results["distances"][0][i]
                            similarity = 1 - (distance / 2.0)
                            
                            if similarity > best_similarity:
                                best_similarity = similarity
                                best_match = {
                                    'doi': doi,
                                    'content': results["documents"][0][i],
                                    'metadata': meta,
                                    'similarity': similarity
                                }
                
                # 如果找到匹配且超过阈值
                if best_match and best_similarity >= similarity_threshold:
                    doi = best_match['doi']
                    
                    # 获取页码（从段落级数据库）
                    page = self._get_page_for_doi(doi)
                    
                    # 创建CitationLocation
                    citation = CitationLocation.from_sentence_db(
                        doi=doi,
                        answer_sentence=sent_strip,
                        answer_sentence_index=sent_idx,
                        sentence_text=best_match['content'],
                        sentence_metadata=best_match['metadata'],
                        similarity=best_similarity,
                        page=page
                    )
                    
                    # 添加到结果
                    if doi not in doi_locations:
                        doi_locations[doi] = []
                    doi_locations[doi].append(citation)
                    
                    matched_count += 1
                    logger.debug(f"   ✅ 句子{sent_idx}: {doi} (相似度={best_similarity:.3f})")
                    
            except Exception as e:
                logger.error(f"❌ 查询句子失败 (idx={sent_idx}): {e}")
                continue
        
        logger.info(f"   匹配成功: {matched_count}/{len(valid_sentences)} 个句子")
        
        return doi_locations
    
    def _find_sentences_for_dois(
        self,
        reference_dois: List[str],
        answer_sentences: List[str],
        similarity_threshold: float
    ) -> Dict[str, List[CitationLocation]]:
        """
        步骤2：为参考文献列表中的每个DOI找最相关的答案句子
        
        这是新增的反向查找逻辑：
        - 对于每个参考文献DOI
        - 使用ReverseCitationFinder找到答案中最相关的句子
        - 记录引用位置
        
        Args:
            reference_dois: 参考文献DOI列表
            answer_sentences: 答案句子列表
            similarity_threshold: 相似度阈值
            
        Returns:
            DOI到引用位置列表的映射
        """
        doi_locations = {}
        
        logger.info(f"   正在为 {len(reference_dois)} 个参考文献DOI查找引用位置...")
        
        for doi in reference_dois:
            try:
                # 使用反向查找器
                citations = self.reverse_finder.find_citations_for_doi(
                    doi=doi,
                    answer_sentences=answer_sentences,
                    top_k=3,  # 每个DOI最多3个引用位置
                    similarity_threshold=similarity_threshold
                )
                
                if citations:
                    doi_locations[doi] = citations
                    logger.debug(f"   ✅ {doi}: 找到 {len(citations)} 个引用位置")
                else:
                    logger.debug(f"   ⚠️ {doi}: 未找到引用位置")
                    
            except Exception as e:
                logger.error(f"❌ 反向查找失败 ({doi}): {e}")
                continue
        
        logger.info(f"   反向查找完成: {len(doi_locations)}/{len(reference_dois)} 个DOI有引用位置")
        
        return doi_locations
    
    def _merge_locations(
        self,
        step1_locations: Dict[str, List[CitationLocation]],
        step2_locations: Dict[str, List[CitationLocation]]
    ) -> Dict[str, List[CitationLocation]]:
        """
        合并两种方式的引用位置
        
        合并策略：
        1. 对于每个DOI，合并两种方式找到的引用位置
        2. 去重：相同答案句子索引的位置只保留相似度最高的
        3. 排序：按相似度降序排列
        
        Args:
            step1_locations: 步骤1的结果
            step2_locations: 步骤2的结果
            
        Returns:
            合并后的引用位置映射
        """
        merged = {}
        
        # 收集所有DOI
        all_dois = set(step1_locations.keys()) | set(step2_locations.keys())
        
        for doi in all_dois:
            locations = []
            
            # 添加步骤1的位置
            if doi in step1_locations:
                locations.extend(step1_locations[doi])
            
            # 添加步骤2的位置
            if doi in step2_locations:
                locations.extend(step2_locations[doi])
            
            # 去重：相同答案句子索引只保留相似度最高的
            deduped = {}
            for loc in locations:
                sent_idx = loc.answer_sentence_index
                if sent_idx not in deduped or loc.similarity > deduped[sent_idx].similarity:
                    deduped[sent_idx] = loc
            
            # 排序：按相似度降序
            sorted_locations = sorted(deduped.values(), key=lambda x: x.similarity, reverse=True)
            
            # 限制每个DOI最多5个引用位置
            merged[doi] = sorted_locations[:5]
            
            logger.debug(f"   {doi}: 合并 {len(locations)} → 去重 {len(deduped)} → 保留 {len(merged[doi])}")
        
        return merged
    
    def _insert_dois_to_answer(
        self,
        answer_sentences: List[str],
        doi_locations: Dict[str, List[CitationLocation]]
    ) -> str:
        """
        将DOI插入到答案中
        
        策略：
        - 为每个答案句子找到对应的DOI（如果有）
        - 在句子末尾插入 (doi=XXX)
        - 如果一个句子有多个DOI，只插入相似度最高的
        
        Args:
            answer_sentences: 答案句子列表
            doi_locations: DOI到引用位置列表的映射
            
        Returns:
            插入DOI后的答案
        """
        # 构建句子索引到DOI的映射
        sentence_to_doi = {}
        
        for doi, locations in doi_locations.items():
            for loc in locations:
                sent_idx = loc.answer_sentence_index
                if sent_idx not in sentence_to_doi or loc.similarity > sentence_to_doi[sent_idx][1]:
                    sentence_to_doi[sent_idx] = (doi, loc.similarity)
        
        # 插入DOI
        answer_with_dois = ""
        inserted_count = 0
        
        for i, sentence in enumerate(answer_sentences):
            sent_strip = sentence.strip()
            
            # 跳过空行和特殊行
            if not sent_strip or sent_strip.startswith('#') or '|' in sent_strip:
                answer_with_dois += sentence
                continue
            
            # 如果这个句子有对应的DOI
            if i in sentence_to_doi:
                doi, similarity = sentence_to_doi[i]
                # 在句子末尾插入DOI（去除原有的换行符，统一添加）
                answer_with_dois += f"{sent_strip} (doi={doi})\n"
                inserted_count += 1
                logger.debug(f"   插入DOI: 句子{i} → {doi} (相似度={similarity:.3f})")
            else:
                answer_with_dois += sentence
        
        logger.info(f"   插入了 {inserted_count} 个DOI引用")
        
        return answer_with_dois
    
    def _extract_candidate_dois(self, documents: List[Dict]) -> set:
        """
        从一级检索结果中提取候选DOI池
        
        Args:
            documents: 一级检索返回的文档列表
            
        Returns:
            候选DOI集合
        """
        candidate_dois = set()
        
        for doc in documents:
            meta = doc.get('metadata', {})
            doi = meta.get('doi') or meta.get('DOI')
            
            if doi and doi != 'N/A' and 'unknown' not in doi.lower():
                candidate_dois.add(doi)
        
        return candidate_dois
    
    def _get_page_for_doi(self, doi: str) -> int:
        """
        从段落级数据库获取DOI的页码
        
        Args:
            doi: 文献DOI
            
        Returns:
            页码（如果找不到返回0）
        """
        try:
            results = self.paragraph_collection.get(
                where={"doi": doi},
                limit=1,
                include=['metadatas']
            )
            
            if results and results['metadatas']:
                return results['metadatas'][0].get('page', 0)
            else:
                return 0
                
        except Exception as e:
            logger.error(f"❌ 查询段落级数据库失败 ({doi}): {e}")
            return 0
