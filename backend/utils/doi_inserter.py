"""
DOI插入工具 - 程序化将DOI插入到答案中
避免LLM编造DOI，确保所有DOI来自检索结果
"""
import re
import logging
from typing import Dict, List, Any, Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # 设置为DEBUG级别以查看详细日志


def validate_doi(doi: str) -> Optional[str]:
    """
    验证并清理DOI格式
    
    Args:
        doi: 原始DOI字符串
        
    Returns:
        清理后的DOI或None（无效）
    """
    if not doi:
        return None
    
    doi = doi.strip()
    
    # 移除可能混入的URL部分
    url_patterns = [r'www\.', r'http://', r'https://', r'\.com', r'\.org', r'\.net']
    for pattern in url_patterns:
        match = re.search(pattern, doi, re.IGNORECASE)
        if match:
            doi = doi[:match.start()].strip()
            break
    
    # 移除末尾标点
    doi = re.sub(r'[.,;:]+$', '', doi)
    
    # 验证基本格式：10.xxxx/xxxxx
    if not re.match(r'^10\.\d+/[A-Za-z0-9._\-/]{2,}$', doi):
        return None
    
    return doi


class ProgrammaticDOIInserter:
    """程序化DOI插入器 - 基于相似度匹配自动插入DOI"""
    
    def __init__(
        self,
        similarity_threshold: float = 0.22,  # 降低阈值到0.22,基于实际测试优化
        seq_weight: float = 0.4,  # 降低文本权重,LLM会重组表达
        vector_weight: float = 0.6,  # 提高向量权重,更可靠的语义相似度
        max_compare_chars: int = 1000
    ):
        """
        初始化DOI插入器
        
        Args:
            similarity_threshold: 相似度阈值，超过此值才插入DOI（默认0.30）
            seq_weight: 文本序列相似度权重
            vector_weight: 向量相似度权重
            max_compare_chars: 最大比较字符数
        """
        self.similarity_threshold = similarity_threshold
        self.seq_weight = seq_weight
        self.vector_weight = vector_weight
        self.max_compare_chars = max_compare_chars
        
        logger.info(f"   DOI插入器初始化: 阈值={similarity_threshold}, 文本权重={seq_weight}, 向量权重={vector_weight}")
    
    def insert_dois(
        self,
        answer: str,
        search_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        将DOI程序化插入到答案中，并返回位置信息
        
        工作原理：
        1. 将答案拆分为句子
        2. 对每个句子，计算与检索文档的相似度
        3. 如果相似度超过阈值，插入对应文档的DOI
        4. 记录每个DOI的位置信息（页码、段落号等）
        
        Args:
            answer: LLM生成的纯净答案（不含DOI）
            search_results: 检索结果，包含documents, metadatas, distances
            
        Returns:
            {
                'answer': 插入DOI后的答案,
                'doi_locations': 每个DOI的位置信息
            }
        """
        if not answer or not search_results:
            return {
                'answer': answer,
                'doi_locations': {}
            }
        
        # 提取检索结果中的候选文档
        candidate_docs = self._extract_candidate_docs(search_results)
        
        if not candidate_docs:
            logger.info("   ⚠️ 无可用的带DOI文档，跳过DOI插入")
            return {
                'answer': answer,
                'doi_locations': {}
            }
        
        # 将答案拆分为句子
        sentences = self._split_sentences(answer)
        
        # 对每个句子匹配最佳DOI
        output_sentences = []
        inserted_dois = set()
        matched_count = 0
        total_sentences = 0
        doi_locations = {}  # 记录每个DOI的位置信息
        
        for sent in sentences:
            # 检查是否是换行符、空行、标题行、表格行
            sent_strip = sent.strip()
            
            # 空行、换行符直接保留
            if sent == '\n' or not sent_strip:
                output_sentences.append(sent)
                continue
            
            # 标题行和表格行直接保留（不插入DOI）
            if sent_strip.startswith('#') or '|' in sent_strip:
                output_sentences.append(sent)
                continue
            
            # 已包含DOI的句子直接保留
            if self._has_doi(sent_strip):
                output_sentences.append(sent)
                continue
            
            # 检测并移除句首的列表序号 (如 "1. ", "2) ", "a. ", "* ")
            list_marker_match = re.match(r'^(\s*)([0-9]+[.)]\s*|[a-zA-Z][.)]\s*|[*\-+]\s+)', sent_strip)
            if list_marker_match:
                prefix = list_marker_match.group(0)
                sent_content = sent_strip[len(prefix):]
            else:
                prefix = ""
                sent_content = sent_strip
            
            total_sentences += 1
            
            # 使用去除序号后的内容进行匹配
            best_doc, best_score = self._find_best_match(sent_content if sent_content else sent_strip, candidate_docs)
            
            # 调试日志
            if total_sentences <= 5:  # 只记录前5个句子的详细信息
                logger.debug(f"   句子 {total_sentences}: {sent_content[:50] if sent_content else sent_strip[:50]}...")
                logger.debug(f"   最佳匹配DOI: {best_doc['doi'] if best_doc else 'None'}")
                logger.debug(f"   相似度分数: {best_score:.3f} (阈值: {self.similarity_threshold})")
            
            # 如果相似度超过阈值，插入DOI（在内容后，序号保持原位）
            if best_doc and best_score >= self.similarity_threshold:
                doi = best_doc['doi']
                inserted_dois.add(doi)
                matched_count += 1
                
                # 记录位置信息
                metadata = best_doc.get('metadata', {})
                if doi not in doi_locations:
                    doi_locations[doi] = []
                
                doi_locations[doi].append({
                    'sentence': sent_content if sent_content else sent_strip,
                    'page': metadata.get('page', 0),
                    'chunk_index_in_page': metadata.get('chunk_index_in_page', 0),
                    'total_chunks_in_page': metadata.get('total_chunks_in_page', 1),
                    'similarity': best_score,
                    'source_preview': best_doc['text'][:300],
                    'confidence': 'high' if best_score >= 0.4 else 'medium' if best_score >= 0.3 else 'low'
                })
                
                # DOI插入到内容末尾，保留序号前缀和换行符
                if prefix:
                    output_sent = prefix + sent_content.rstrip() + f" (doi={doi})\n"
                else:
                    output_sent = sent_strip.rstrip() + f" (doi={doi})\n"
                output_sentences.append(output_sent)
                logger.debug(f"   ✅ 插入DOI: {doi} (相似度: {best_score:.3f})")
            else:
                # 保留原始句子（包含换行）
                output_sentences.append(sent)
        
        result = "".join(output_sentences)
        
        logger.info(f"   ✅ 程序化DOI插入完成: 分析了 {total_sentences} 个句子，匹配 {matched_count} 个，插入了 {len(inserted_dois)} 个不同的DOI")
        if inserted_dois:
            logger.info(f"   插入的DOI: {', '.join(sorted(inserted_dois))}")
        else:
            logger.warning(f"   ⚠️ 没有插入任何DOI - 可能原因：")
            logger.warning(f"      1. 答案句子与检索文档相似度都低于阈值 {self.similarity_threshold}")
            logger.warning(f"      2. 阈值设置过高，建议降低到 0.3-0.35")
            logger.warning(f"      3. 答案内容与检索结果不匹配")
        
        # 记录位置信息统计
        if doi_locations:
            logger.info(f"   📍 位置信息统计:")
            for doi, locations in doi_locations.items():
                pages = set(loc['page'] for loc in locations)
                logger.info(f"      {doi}: {len(locations)}个引用，分布在第{sorted(pages)}页")
        
        return {
            'answer': result,
            'doi_locations': doi_locations
        }
    
    def _extract_candidate_docs(self, search_results: Dict[str, Any]) -> List[Dict]:
        """从检索结果中提取候选文档（带DOI和元数据）"""
        metadatas = search_results.get('metadatas', []) or []
        documents = search_results.get('documents', []) or []
        distances = search_results.get('distances', []) or []
        
        candidates = []
        
        for i, (meta, doc) in enumerate(zip(metadatas, documents)):
            if not meta or not doc:
                continue
            
            # 提取DOI
            doi_raw = meta.get('DOI') or meta.get('doi') or ''
            doi_raw = doi_raw.strip()
            
            if not doi_raw or not doi_raw.startswith('10.'):
                continue
            
            # 验证DOI
            doi_clean = validate_doi(doi_raw)
            if not doi_clean:
                continue
            
            # 计算向量相似度 (1 - distance)
            try:
                dist = distances[i] if i < len(distances) else 1.0
                vector_sim = max(0.0, 1.0 - float(dist))
            except:
                vector_sim = 0.0
            
            candidates.append({
                'doi': doi_clean,
                'text': doc,
                'vector_sim': vector_sim,
                'metadata': meta  # 保留完整的元数据
            })
        
        logger.info(f"   提取到 {len(candidates)} 个候选文档（带DOI）")
        return candidates
    
    def _split_sentences(self, text: str) -> List[str]:
        """将文本拆分为句子，保留标点符号和原始格式"""
        # 策略：只在中文标点处分割，但保留换行符和表格结构
        # 不直接分割，而是逐行处理，保持原始格式
        
        lines = text.split('\n')
        sentences = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # 空行保留
            if not line_stripped:
                sentences.append('\n')
                continue
            
            # Markdown标题行保留完整
            if line_stripped.startswith('#'):
                sentences.append(line + '\n')
                continue
            
            # 表格行保留完整
            if '|' in line_stripped:
                sentences.append(line + '\n')
                continue
            
            # 普通文本行按中文标点分割
            # 先替换中文标点为特殊标记
            processed_line = line_stripped
            processed_line = processed_line.replace('。', '<PERIOD>')
            processed_line = processed_line.replace('！', '<EXCLAIM>')
            processed_line = processed_line.replace('？', '<QUESTION>')
            processed_line = processed_line.replace('；', '<SEMICOLON>')
            
            # 分割句子
            parts = re.split(r'<PERIOD>|<EXCLAIM>|<QUESTION>|<SEMICOLON>', processed_line)
            parts = [p.strip() for p in parts if p.strip()]
            
            # 添加句子，每个句子后加标点恢复标记
            for i, part in enumerate(parts):
                # 恢复原始标点
                original_sent = part
                if i == len(parts) - 1:
                    # 最后一个句子后加换行
                    sentences.append(original_sent + '\n')
                else:
                    sentences.append(original_sent)
        
        return sentences
    
    def _has_doi(self, text: str) -> bool:
        """检查文本中是否已包含DOI"""
        return bool(re.search(r'\(doi\s*=\s*10\.\d+/', text, re.IGNORECASE))
    
    def _find_best_match(
        self,
        sentence: str,
        candidates: List[Dict]
    ) -> tuple:
        """
        为句子查找最佳匹配的文档
        
        Returns:
            (best_doc, best_score) 元组
        """
        best_doc = None
        best_score = 0.0
        all_scores = []
        
        for doc in candidates:
            # 截取文档内容进行比较
            doc_text = doc['text'][:self.max_compare_chars]
            
            # 计算文本序列相似度
            try:
                seq_sim = SequenceMatcher(None, sentence, doc_text).ratio()
            except:
                seq_sim = 0.0
            
            # 组合相似度：文本相似度 + 向量相似度
            combined_score = (
                self.seq_weight * seq_sim +
                self.vector_weight * doc['vector_sim']
            )
            
            all_scores.append({
                'doi': doc['doi'],
                'seq_sim': seq_sim,
                'vec_sim': doc['vector_sim'],
                'combined': combined_score
            })
            
            if combined_score > best_score:
                best_score = combined_score
                best_doc = doc
        
        # 记录前3个最高分数（用于调试）
        if all_scores:
            top3 = sorted(all_scores, key=lambda x: x['combined'], reverse=True)[:3]
            logger.debug(f"   Top 3 匹配:")
            for i, score_info in enumerate(top3, 1):
                logger.debug(f"      {i}. DOI={score_info['doi'][:30]}... "
                           f"文本相似度={score_info['seq_sim']:.3f} "
                           f"向量相似度={score_info['vec_sim']:.3f} "
                           f"综合={score_info['combined']:.3f}")
        
        return best_doc, best_score
