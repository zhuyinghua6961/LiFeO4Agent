"""
语义搜索专家 - Semantic Expert
功能：基于向量数据库进行文献语义搜索
"""
from typing import Dict, List, Any, Optional
import logging
import os
import json
import re
import requests

from backend.services.llm_service import LLMService
from backend.repositories.vector_repository import VectorRepository
from backend.utils.pdf_loader import PDFManager

logger = logging.getLogger(__name__)


class SemanticExpert:
    """语义搜索专家 - 处理基于语义相似度的文献检索"""
    
    def __init__(
        self, 
        vector_repo: VectorRepository,
        llm_service: Optional[LLMService] = None
    ):
        """
        初始化语义搜索专家
        
        Args:
            vector_repo: 向量数据库仓储
            llm_service: LLM服务实例（用于结果增强）
        """
        self._vector_repo = vector_repo
        self._llm = llm_service
        
        # 加载prompt模板
        self._search_prompt = self._build_search_prompt()
        self._semantic_synthesis_prompt = self._load_prompt("semantic_synthesis_prompt_clean.txt")
        self._semantic_synthesis_prompt_robust = self._load_prompt("semantic_synthesis_prompt_robust.txt")
        self._broad_question_prompt = self._load_prompt("broad_question_synthesis_prompt.txt")
        
        # 初始化PDF管理器
        from backend.config.settings import settings
        self._pdf_manager = PDFManager(
            papers_dir=settings.papers_dir,
            mapping_file=settings.doi_to_pdf_mapping
        ) if hasattr(settings, 'papers_dir') else None
        
        # 相似度阈值配置
        self._broad_threshold = getattr(settings, 'similarity_threshold_broad', 0.3)
        self._precise_threshold = getattr(settings, 'similarity_threshold_precise', 0.3)
        
        # BGE API配置（用于生成查询embedding和句子embedding）
        self._bge_api_url = settings.bge_api_url
        
        # 初始化句子级数据库（二级检索）
        self._sentence_collection = self._init_sentence_db()
        
        # 初始化查询扩展和重排序组件
        self._query_expander = None
        self._multi_query_retriever = None
        self._sentence_reranker = None
        
        # 根据配置初始化新组件
        if settings.enable_query_expansion or settings.enable_reranking:
            self._init_expansion_components()
        
        logger.info("📚 语义搜索专家初始化完成")
    
    def _load_prompt(self, filename: str) -> str:
        """加载prompt模板文件"""
        try:
            from backend.config.settings import settings
            prompt_path = os.path.join(settings.base_dir, "config", "prompts", filename)
            
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                logger.warning(f"Prompt文件不存在: {prompt_path}")
                return ""
        except Exception as e:
            logger.error(f"加载prompt失败 ({filename}): {e}")
            return ""
    
    def _init_sentence_db(self):
        """初始化句子级数据库（二级检索）"""
        try:
            import chromadb
            from chromadb.config import Settings
            
            # 句子数据库路径
            sentence_db_path = "/Users/zhuyinghua/Desktop/code/vector_sentence"
            
            client = chromadb.PersistentClient(
                path=sentence_db_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            collection = client.get_collection(
                name="lfp_papers_sentences_v1"
            )
            
            count = collection.count()
            logger.info(f"✅ 句子级数据库连接成功")
            logger.info(f"   路径: {sentence_db_path}")
            logger.info(f"   Collection: lfp_papers_sentences_v1")
            logger.info(f"   句子数量: {count:,}")
            
            return collection
            
        except Exception as e:
            logger.warning(f"⚠️  句子级数据库连接失败: {e}")
            logger.warning(f"   将回退到PDF搜索模式")
            return None
    
    def _init_expansion_components(self):
        """初始化查询扩展和重排序组件"""
        try:
            from backend.agents.query_expander import QueryExpander
            from backend.agents.multi_query_retriever import MultiQueryRetriever
            from backend.agents.sentence_reranker import SentenceReranker
            from backend.config.settings import settings
            
            # 初始化QueryExpander
            self._query_expander = QueryExpander(llm_service=self._llm)
            logger.info("✅ QueryExpander 初始化成功")
            
            # 初始化MultiQueryRetriever
            self._multi_query_retriever = MultiQueryRetriever(
                vector_repo=self._vector_repo,
                bge_api_url=self._bge_api_url
            )
            logger.info("✅ MultiQueryRetriever 初始化成功")
            
            # 初始化SentenceReranker（如果句子数据库可用）
            if self._sentence_collection:
                self._sentence_reranker = SentenceReranker(
                    sentence_collection=self._sentence_collection,
                    bge_api_url=self._bge_api_url
                )
                logger.info("✅ SentenceReranker 初始化成功")
            else:
                logger.warning("⚠️  句子数据库不可用，SentenceReranker 未初始化")
            
        except Exception as e:
            logger.error(f"❌ 初始化查询扩展组件失败: {e}")
            logger.warning("⚠️  将使用原有的单查询策略")
            self._query_expander = None
            self._multi_query_retriever = None
            self._sentence_reranker = None
    
    def _build_search_prompt(self) -> str:
        """构建语义搜索提示词"""
        return """你是一个文献检索专家。你的任务是将用户的自然语言问题转换为语义搜索查询。

## 搜索策略

1. **提取核心概念**：
   - 材料名称（如 LiFePO4, NMC, LCO）
   - 合成方法（如水热法、溶胶凝胶法、球磨法）
   - 改性策略（如碳包覆、离子掺杂、表面改性）
   - 性能指标（如高导电性、高容量、长循环）

2. **构建搜索查询**：
   - 使用简洁的关键词组合
   - 可以包含多个概念，用空格或逗号分隔
   - 保持查询简洁（不超过50字）

3. **搜索结果排序**：
   - 相关性优先
   - 考虑文献的新近度
   - 优先返回包含完整摘要的文献

## 输出要求

只返回搜索查询字符串，不要其他解释。

示例：
- 输入："有哪些关于高导电性LiFePO4的研究？"
- 输出："高导电性 LiFePO4"
- 输入："水热合成法制备的磷酸铁锂材料文献"
- 输出："水热合成 磷酸铁锂"
- 输入："碳包覆改性的相关研究"
- 输出："碳包覆 改性"
"""
    
    def can_handle(self, question: str) -> bool:
        """
        判断是否适合使用语义搜索
        
        Args:
            question: 用户问题
            
        Returns:
            True=适合语义搜索, False=不适合
        """
        question_lower = question.lower()
        
        # 语义搜索关键词
        semantic_keywords = [
            "文献", "论文", "研究", "文章", "报道",
            "关于", "相关", "有哪些", "哪些",
            "搜索", "查找", "寻找", "检索",
            "材料", "方法", "制备", "合成",
            "改性", "包覆", "掺杂", "结构"
        ]
        
        # 如果问题包含这些词，认为适合语义搜索
        return any(kw in question_lower for kw in semantic_keywords)
    
    def generate_search_query(self, question: str) -> str:
        """
        生成语义搜索查询
        
        Args:
            question: 用户问题
            
        Returns:
            搜索查询字符串
        """
        if self._llm is None:
            # 使用规则生成简单查询
            return self._generate_simple_query(question)
        
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            
            messages = [
                SystemMessage(content=self._search_prompt),
                HumanMessage(content=f"用户问题：{question}")
            ]
            
            response = self._llm.invoke(messages)
            query = response.content.strip()
            
            # 去除可能的引号和代码块标记
            query = query.strip('"\'')
            if "```" in query:
                query = query.split("```")[0].strip()
            
            return query
            
        except Exception as e:
            logger.error(f"生成搜索查询失败: {e}")
            return self._generate_simple_query(question)
    
    def _generate_simple_query(self, question: str) -> str:
        """
        使用规则生成简单的搜索查询
        
        Args:
            question: 用户问题
            
        Returns:
            搜索查询字符串
        """
        # 移除常见前缀
        prefixes = [
            "有哪些", "有没有", "请查找", "搜索", "查找",
            "关于", "请给我", "帮我找", "我想找"
        ]
        
        query = question
        for prefix in prefixes:
            if question.startswith(prefix):
                query = question[len(prefix):].strip()
                break
        
        # 移除常见后缀
        suffixes = ["的研究", "的文献", "的文章", "的相关", "的内容", "？", "?"]
        for suffix in suffixes:
            if query.endswith(suffix):
                query = query[:-len(suffix)].strip()
                break
        
        return query if query else question
    
    def search(
        self, 
        question: str, 
        top_k: int = 15,  # 从10增加到15
        with_scores: bool = True,  # 改为默认True，需要相似度分数
        filter_metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        执行语义搜索
        
        Args:
            question: 用户问题
            top_k: 返回结果数量
            with_scores: 是否返回相似度分数
            filter_metadata: 元数据过滤条件
            
        Returns:
            搜索结果
        """
        # 移除 can_handle 检查，允许所有问题进行语义搜索
        
        try:
            # 生成搜索查询
            logger.info("\n" + "="*80)
            logger.info("📝 [步骤2] 提取关键词")
            search_query = self.generate_search_query(question)
            logger.info(f"关键词: {search_query}")
            logger.info("="*80)
            
            # 生成查询的embedding向量（使用BGE API）
            logger.info("\n" + "="*80)
            logger.info("🔢 [步骤3] 生成查询向量(Embedding)")
            logger.info(f"BGE API地址: {self._bge_api_url}")
            logger.info(f"输入文本: {search_query}")
            try:
                response = requests.post(
                    self._bge_api_url,
                    json={"input": [search_query]},
                    timeout=30
                )
                response.raise_for_status()
                query_embedding = response.json()["data"][0]["embedding"]
                logger.info(f"✅ 成功生成embedding")
                logger.info(f"向量维度: {len(query_embedding)}")
                logger.info(f"向量前5维: {query_embedding[:5]}")
                logger.info("="*80)
            except Exception as e:
                logger.error(f"❌ 生成embedding失败: {e}")
                return {
                    "success": False,
                    "error": f"生成查询向量失败: {str(e)}",
                    "error_step": "generate_embedding",
                    "expert": "semantic",
                    "documents": []
                }
            
            # 执行搜索
            logger.info("\n" + "="*80)
            logger.info("🔍 [步骤4] 查询向量数据库")
            logger.info(f"检索数量: top_k={top_k}")
            results = self._vector_repo.search(
                query_embedding=query_embedding,
                n_results=top_k,
                where_filter=filter_metadata
            )
            
            if not results.get('success'):
                logger.error(f"❌ 向量搜索失败: {results.get('error')}")
                return {
                    "success": False,
                    "error": results.get('error', '搜索失败'),
                    "error_step": "vector_search",
                    "expert": "semantic"
                }
            
            # 格式化结果
            documents = []
            docs = results.get('documents', [])
            metadatas = results.get('metadatas', [])
            distances = results.get('distances', [])
            ids = results.get('ids', [])
            
            for i, doc_content in enumerate(docs):
                doc_data = {
                    "id": ids[i] if i < len(ids) else str(i),
                    "content": doc_content,
                }
                if i < len(metadatas) and metadatas[i]:
                    doc_data["metadata"] = metadatas[i]
                if with_scores and i < len(distances):
                    # ChromaDB 使用 cosine 距离 (范围 0-2)
                    # 余弦相似度 = 1 - (cosine_distance / 2)
                    # 距离越小,相似度越高
                    distance = distances[i]
                    similarity = 1 - (distance / 2.0)  # 转换为 0-1 范围的相似度
                    doc_data["score"] = max(0.0, min(1.0, similarity))  # 确保在 0-1 范围内
                documents.append(doc_data)
            
            # 应用相似度过滤
            filtered_documents = self._filter_by_similarity(
                documents=documents,
                question=question,
                with_scores=with_scores
            )
            
            logger.info(f"✅ 检索成功")
            logger.info(f"原始结果数: {len(documents)}")
            logger.info(f"过滤后结果数: {len(filtered_documents)}")
            logger.info("\n前3条检索结果预览:")
            for i, doc in enumerate(filtered_documents[:3], 1):
                score = doc.get('score', 0)
                content_preview = doc.get('content', '')[:100]
                doi = doc.get('metadata', {}).get('DOI', 'N/A')
                logger.info(f"  [{i}] 相似度={score:.4f}, DOI={doi}")
                logger.info(f"      内容: {content_preview}...")
            logger.info("="*80)
            
            return {
                "success": True,
                "expert": "semantic",
                "search_query": search_query,
                "result_count": len(filtered_documents),
                "original_count": len(documents),
                "documents": filtered_documents,
                "question": question
            }
            
        except Exception as e:
            logger.error(f"语义搜索失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_step": "search",
                "expert": "semantic"
            }
    
    def search_with_expansion(
        self,
        question: str,
        top_k: int = 15,
        enable_expansion: bool = True,
        enable_reranking: bool = True
    ) -> Dict[str, Any]:
        """
        使用查询扩展和重排序的检索
        
        Args:
            question: 用户问题
            top_k: 返回结果数量
            enable_expansion: 是否启用查询扩展
            enable_reranking: 是否启用重排序
            
        Returns:
            检索结果，包含以下字段：
            - success: 是否成功
            - expert: 专家类型
            - documents: 文档列表
            - expansion_info: 查询扩展信息（如果启用）
            - retrieval_info: 检索信息
            - reranking_info: 重排序信息（如果启用）
            - timing: 各阶段耗时
        """
        import time
        from backend.config.settings import settings
        
        timing = {}
        overall_start = time.time()
        
        # 检查配置和组件可用性
        enable_expansion = enable_expansion and settings.enable_query_expansion and self._query_expander is not None
        enable_reranking = enable_reranking and settings.enable_reranking and self._sentence_reranker is not None
        
        logger.info("\n" + "="*80)
        logger.info("🚀 开始查询扩展和重排序检索")
        logger.info(f"   问题: {question}")
        logger.info(f"   查询扩展: {'启用' if enable_expansion else '禁用'}")
        logger.info(f"   重排序: {'启用' if enable_reranking else '禁用'}")
        logger.info("="*80)
        
        try:
            # ========== 步骤1: 查询扩展 ==========
            expansion_info = {}
            queries = [question]  # 默认只使用原始查询
            
            if enable_expansion:
                logger.info("\n" + "="*80)
                logger.info("📝 [步骤1] 查询扩展")
                expansion_start = time.time()
                
                try:
                    expansion_result = self._query_expander.expand(question)
                    queries = expansion_result.all_queries
                    expansion_info = {
                        "original_query": expansion_result.original_query,
                        "english_query": expansion_result.english_query,
                        "synonym_query": expansion_result.synonym_query,
                        "all_queries": expansion_result.all_queries,
                        "translation_method": expansion_result.translation_method,
                        "expansion_time": expansion_result.expansion_time
                    }
                    timing["expansion"] = expansion_result.expansion_time
                    
                    logger.info(f"✅ 查询扩展成功: {len(queries)} 个查询")
                    for i, q in enumerate(queries, 1):
                        logger.info(f"   [{i}] {q}")
                    logger.info("="*80)
                    
                except Exception as e:
                    logger.error(f"❌ 查询扩展失败: {e}")
                    logger.warning("⚠️  回退到单查询策略")
                    queries = [question]
                    expansion_info = {"error": str(e), "fallback": True}
                    timing["expansion"] = time.time() - expansion_start
            else:
                logger.info("\n查询扩展已禁用，使用原始查询")
            
            # ========== 步骤2: 多查询检索 ==========
            logger.info("\n" + "="*80)
            logger.info("🔍 [步骤2] 多查询检索")
            retrieval_start = time.time()
            
            retrieval_info = {}
            documents = []
            
            try:
                if enable_expansion and self._multi_query_retriever and len(queries) > 1:
                    # 使用多查询检索器
                    multi_result = self._multi_query_retriever.retrieve(
                        queries=queries,
                        top_k_per_query=20  # 每个查询返回20个结果
                    )
                    
                    # 转换文档格式
                    for doc in multi_result.documents:
                        documents.append({
                            "id": doc.get("id"),
                            "content": doc.get("text"),
                            "metadata": doc.get("metadata"),
                            "score": doc.get("score"),
                            "source_query": doc.get("source_query")
                        })
                    
                    retrieval_info = {
                        "query_count": len(queries),
                        "query_contributions": multi_result.query_contributions,
                        "total_before_dedup": multi_result.total_before_dedup,
                        "total_after_dedup": multi_result.total_after_dedup,
                        "retrieval_time": multi_result.retrieval_time
                    }
                    timing["retrieval"] = multi_result.retrieval_time
                    
                    logger.info(f"✅ 多查询检索成功")
                    logger.info(f"   去重前: {multi_result.total_before_dedup} 个文档")
                    logger.info(f"   去重后: {multi_result.total_after_dedup} 个文档")
                    logger.info("="*80)
                    
                else:
                    # 回退到单查询
                    logger.info("使用单查询检索")
                    search_result = self.search(
                        question=queries[0],
                        top_k=20,
                        with_scores=True
                    )
                    
                    if search_result.get("success"):
                        documents = search_result.get("documents", [])
                        retrieval_info = {
                            "query_count": 1,
                            "result_count": len(documents),
                            "retrieval_time": time.time() - retrieval_start
                        }
                        timing["retrieval"] = retrieval_info["retrieval_time"]
                        
                        logger.info(f"✅ 单查询检索成功: {len(documents)} 个文档")
                        logger.info("="*80)
                    else:
                        raise Exception(search_result.get("error", "检索失败"))
                        
            except Exception as e:
                logger.error(f"❌ 检索失败: {e}")
                timing["retrieval"] = time.time() - retrieval_start
                return {
                    "success": False,
                    "error": f"检索失败: {str(e)}",
                    "expert": "semantic",
                    "expansion_info": expansion_info,
                    "timing": timing
                }
            
            # ========== 步骤3: 句子级重排序 ==========
            reranking_info = {}
            
            if enable_reranking and documents:
                logger.info("\n" + "="*80)
                logger.info("🔄 [步骤3] 句子级重排序")
                reranking_start = time.time()
                
                try:
                    # 限制候选数量
                    candidates_to_rerank = documents[:settings.rerank_top_k]
                    logger.info(f"   候选数量: {len(candidates_to_rerank)}")
                    
                    rerank_result = self._sentence_reranker.rerank(
                        query=question,  # 使用原始问题
                        candidates=candidates_to_rerank,
                        top_k=top_k
                    )
                    
                    documents = rerank_result.documents
                    reranking_info = {
                        "candidates_count": len(candidates_to_rerank),
                        "similarity_scores": rerank_result.similarity_scores,
                        "top_3_changes": rerank_result.top_3_changes,
                        "reranking_time": rerank_result.reranking_time
                    }
                    timing["reranking"] = rerank_result.reranking_time
                    
                    logger.info(f"✅ 重排序成功")
                    logger.info(f"   返回数量: {len(documents)}")
                    logger.info(f"   Top-3变化: {rerank_result.top_3_changes}")
                    logger.info("="*80)
                    
                except Exception as e:
                    logger.error(f"❌ 重排序失败: {e}")
                    logger.warning("⚠️  使用原始排序")
                    documents = documents[:top_k]
                    reranking_info = {"error": str(e), "fallback": True}
                    timing["reranking"] = time.time() - reranking_start
            else:
                # 不使用重排序，直接截取top_k
                documents = documents[:top_k]
                if not enable_reranking:
                    logger.info("\n重排序已禁用")
            
            # ========== 返回结果 ==========
            timing["total"] = time.time() - overall_start
            
            logger.info("\n" + "="*80)
            logger.info("✅ 查询扩展和重排序检索完成")
            logger.info(f"   总耗时: {timing['total']:.2f}s")
            logger.info(f"   - 查询扩展: {timing.get('expansion', 0):.2f}s")
            logger.info(f"   - 检索: {timing.get('retrieval', 0):.2f}s")
            logger.info(f"   - 重排序: {timing.get('reranking', 0):.2f}s")
            logger.info(f"   最终返回: {len(documents)} 个文档")
            logger.info("="*80)
            
            return {
                "success": True,
                "expert": "semantic",
                "question": question,
                "result_count": len(documents),
                "documents": documents,
                "expansion_info": expansion_info,
                "retrieval_info": retrieval_info,
                "reranking_info": reranking_info,
                "timing": timing
            }
            
        except Exception as e:
            logger.error(f"❌ 查询扩展和重排序检索失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # 回退到原有的search方法
            logger.warning("⚠️  回退到原有的单查询策略")
            try:
                fallback_result = self.search(question, top_k=top_k, with_scores=True)
                fallback_result["fallback"] = True
                fallback_result["fallback_reason"] = str(e)
                fallback_result["timing"] = {"total": time.time() - overall_start}
                return fallback_result
            except Exception as fallback_error:
                logger.error(f"❌ 回退策略也失败: {fallback_error}")
                return {
                    "success": False,
                    "error": f"检索失败: {str(e)}, 回退也失败: {str(fallback_error)}",
                    "expert": "semantic",
                    "timing": {"total": time.time() - overall_start}
                }
    
    def search_by_material(self, material: str, top_k: int = 5) -> Dict[str, Any]:
        """
        按材料名称搜索文献（便捷方法）
        
        Args:
            material: 材料名称
            top_k: 结果数量
            
        Returns:
            搜索结果
        """
        return self.search(f"关于{material}的文献", top_k=top_k)
    
    def search_by_method(self, method: str, top_k: int = 5) -> Dict[str, Any]:
        """
        按合成方法搜索文献（便捷方法）
        
        Args:
            method: 合成方法名称
            top_k: 结果数量
            
        Returns:
            搜索结果
        """
        return self.search(f"{method}制备的材料文献", top_k=top_k)
    
    def search_by_modification(
        self, 
        modification: str, 
        material: str = "LiFePO4",
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        按改性策略搜索文献（便捷方法）
        
        Args:
            modification: 改性策略
            material: 材料名称
            top_k: 结果数量
            
        Returns:
            搜索结果
        """
        return self.search(f"{modification}改性的{material}", top_k=top_k)
    
    def find_similar(
        self, 
        document_text: str, 
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        查找相似的文献（便捷方法）
        
        Args:
            document_text: 文档内容
            top_k: 结果数量
            
        Returns:
            相似文献列表
        """
        try:
            results = self._vector_repo.find_similar(
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
                "expert": "semantic",
                "result_count": len(documents),
                "documents": documents
            }
            
        except Exception as e:
            logger.error(f"查找相似文献失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "expert": "semantic"
            }
    
    def aggregate_results(
        self, 
        search_results: Dict[str, Any],
        llm_enhanced: bool = True
    ) -> Dict[str, Any]:
        """
        聚合搜索结果（可选：使用LLM增强）
        
        Args:
            search_results: 搜索结果
            llm_enhanced: 是否使用LLM增强
            
        Returns:
            聚合后的结果
        """
        if not search_results.get("success"):
            return search_results
        
        documents = search_results.get("documents", [])
        
        # 提取关键信息
        summary = {
            "total_found": search_results["result_count"],
            "expert": "semantic",
            "search_query": search_results.get("search_query", ""),
            "key_topics": [],
            "material_mentioned": [],
            "methods_mentioned": []
        }
        
        # 简单提取关键词
        for doc in documents[:10]:  # 只分析前10个
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            
            # 从摘要中提取材料和方法
            if "LiFePO4" in content or "LFP" in content:
                if "LiFePO4" not in summary["material_mentioned"]:
                    summary["material_mentioned"].append("LiFePO4")
            
            if "NMC" in content or "NCM" in content:
                if "NMC" not in summary["material_mentioned"]:
                    summary["material_mentioned"].append("NMC")
            
            # 常见方法
            methods = ["水热", "溶胶凝胶", "球磨", "共沉淀", "喷雾干燥"]
            for method in methods:
                if method in content and method not in summary["methods_mentioned"]:
                    summary["methods_mentioned"].append(method)
        
            return {
                "success": True,
                "expert": "semantic",
                "summary": summary,
                "documents": documents,
                "llm_enhanced": llm_enhanced
            }
    
    def _is_broad_question(self, question: str) -> bool:
        """判断是否为宽泛问题"""
        broad_keywords = [
            "有哪些", "哪些", "什么", "如何", "怎么",
            "综述", "概述", "总结", "介绍", "发展",
            "研究进展", "研究现状", "应用", "前景"
        ]
        return any(kw in question for kw in broad_keywords)
    
    def _filter_by_similarity(
        self,
        documents: List[Dict],
        question: str,
        with_scores: bool = True
    ) -> List[Dict]:
        """根据相似度阈值过滤结果"""
        if not with_scores or not documents:
            return documents
        
        # 判断问题类型，选择阈值
        is_broad = self._is_broad_question(question)
        threshold = self._broad_threshold if is_broad else self._precise_threshold
        
        filtered = []
        filtered_count = 0
        
        for doc in documents:
            score = doc.get('score', 1.0)
            if score >= threshold:
                filtered.append(doc)
            else:
                filtered_count += 1
        
        logger.info(
            f"相似度过滤: 阈值={threshold:.2f} ({'宽泛' if is_broad else '精确'}问题), "
            f"保留={len(filtered)}, 过滤={filtered_count}"
        )
        
        return filtered
    
    def _extract_dois(self, documents: List[Dict]) -> List[str]:
        """从文档中提取DOI"""
        dois = []
        for doc in documents:
            metadata = doc.get('metadata', {})
            # 从metadata中提取DOI
            doi = metadata.get('doi') or metadata.get('DOI')
            if doi:
                dois.append(doi)
            else:
                # 从内容中提取DOI
                content = doc.get('content', '')
                # 修正正则: 排除方括号和其他符号
                doi_match = re.search(r'10\.\d+/[^\s)\]\>]+', content)
                if doi_match:
                    dois.append(doi_match.group())
        return dois
    
    def _load_pdf_contents(
        self,
        dois: List[str],
        max_pages: int = 30,
        max_chars: int = 20000
    ) -> Dict[str, str]:
        """加载多个DOI的PDF内容"""
        if not self._pdf_manager:
            return {}
        
        pdf_contents = {}
        for doi in dois[:3]:  # 最多加载3篇
            content = self._pdf_manager.load_pdf_by_doi(
                doi=doi,
                max_pages=max_pages,
                max_chars=max_chars
            )
            if content:
                pdf_contents[doi] = content
        
        return pdf_contents
    
    def query_with_details(
        self,
        question: str,
        top_k: int = 20,
        load_pdf: bool = True
    ) -> Dict[str, Any]:
        """
        执行查询并返回详细信息（包括PDF加载情况和位置信息）
        
        根据配置自动选择使用查询扩展和重排序，或使用原有的单查询策略。
        
        Args:
            question: 用户问题
            top_k: 返回结果数量
            load_pdf: 是否加载PDF原文
            
        Returns:
            包含answer、pdf_info、doi_locations的字典
        """
        from backend.config.settings import settings
        
        # 根据配置选择检索策略
        use_expansion = settings.enable_query_expansion or settings.enable_reranking
        
        if use_expansion:
            # 使用新的查询扩展和重排序策略
            logger.info("🚀 使用查询扩展和重排序策略")
            search_result = self.search_with_expansion(
                question=question,
                top_k=top_k,
                enable_expansion=settings.enable_query_expansion,
                enable_reranking=settings.enable_reranking
            )
        else:
            # 使用原有的单查询策略（向后兼容）
            logger.info("📚 使用原有的单查询策略")
            search_result = self.search(question, top_k=top_k, with_scores=True)
        
        # 处理检索失败
        if not search_result.get('success'):
            return {
                'answer': '检索失败',
                'pdf_info': {'error': search_result.get('error')},
                'doi_locations': {}
            }
        
        documents = search_result.get('documents', [])
        if not documents:
            return {
                'answer': '未找到相关文献。',
                'pdf_info': {'documents_found': 0},
                'doi_locations': {}
            }
        
        # 判断问题类型
        is_broad = self._is_broad_question(question)
        
        # 初始化PDF信息
        pdf_info = {
            'documents_found': len(documents),
            'is_broad_question': is_broad,
            'dois_found': 0,
            'pdf_loaded': 0,
            'pdf_failed': 0,
            'used_expansion': use_expansion,  # 记录是否使用了查询扩展
            'expansion_info': search_result.get('expansion_info', {}),  # 查询扩展信息
            'retrieval_info': search_result.get('retrieval_info', {}),  # 检索信息
            'reranking_info': search_result.get('reranking_info', {}),  # 重排序信息
            'timing': search_result.get('timing', {})  # 耗时信息
        }
        
        # 宽泛问题：不加载PDF
        if is_broad:
            logger.info("检测到宽泛问题，使用宽泛问题合成模板（不加载PDF）")
            answer, doi_locations = self._synthesize_broad_answer(question, documents)
            return {
                'answer': answer,
                'pdf_info': pdf_info,
                'doi_locations': doi_locations
            }
        
        # 精确问题：加载PDF
        pdf_contents = {}
        if load_pdf and self._pdf_manager:
            logger.info("\n" + "="*80)
            logger.info("📄 [步骤5] 加载PDF原文")
            dois = self._extract_dois(documents)
            pdf_info['dois_found'] = len(dois)
            logger.info(f"提取到 {len(dois)} 个DOI")
            
            if dois:
                pdf_contents = self._load_pdf_contents(dois)
                pdf_info['pdf_loaded'] = len(pdf_contents)
                pdf_info['pdf_failed'] = len(dois) - len(pdf_contents)
                logger.info(f"\n正在加载PDF原文 (最多3篇):")
                for idx, (doi, content) in enumerate(pdf_contents.items(), 1):
                    progress = f"[{idx}/{len(pdf_contents)}]"
                    size_kb = len(content) / 1024
                    logger.info(f"  {progress} ✅ {doi} ({size_kb:.1f}KB)")
                if pdf_info['pdf_failed'] > 0:
                    logger.info(f"  ⚠️  {pdf_info['pdf_failed']} 篇PDF加载失败")
            else:
                logger.info("⚠️  未提取到DOI")
            logger.info("="*80)
        
        answer, doi_locations = self._synthesize_semantic_answer(question, documents, pdf_contents)
        return {
            'answer': answer,
            'pdf_info': pdf_info,
            'doi_locations': doi_locations
        }
    
    def _synthesize_semantic_answer(
        self,
        user_question: str,
        documents: List[Dict],
        pdf_contents: Optional[Dict[str, str]] = None
    ) -> tuple:
        """合成语义搜索答案（精确问题）"""
        from backend.config.settings import settings
        
        # 根据配置选择prompt
        use_robust = getattr(settings, 'use_robust_prompt', True)
        
        if not self._llm:
            return self._format_simple_answer(documents), {}
        
        # 选择prompt模板
        if use_robust and self._semantic_synthesis_prompt_robust:
            logger.info("📝 使用增强型Prompt（适合碎片化文本）")
            return self._synthesize_with_robust_prompt(user_question, documents, pdf_contents)
        elif self._semantic_synthesis_prompt:
            logger.info("📝 使用标准Prompt")
            return self._synthesize_with_standard_prompt(user_question, documents, pdf_contents)
        else:
            return self._format_simple_answer(documents), {}
    
    def _synthesize_with_robust_prompt(
        self,
        user_question: str,
        documents: List[Dict],
        pdf_contents: Optional[Dict[str, str]] = None
    ) -> tuple:
        """使用增强型prompt合成答案（适合碎片化文本）"""
        try:
            # 构建简化的文献列表（不需要上下文扩展）
            logger.info("\n" + "="*80)
            logger.info("📖 [步骤5] 准备文献内容")
            
            literature_list = []
            for i, doc in enumerate(documents[:15], 1):  # 使用前15个文档
                content = doc.get('content', '')
                metadata = doc.get('metadata', {})
                doi = metadata.get('DOI') or metadata.get('doi', f'文献{i}')
                
                lit_text = f"[{i}] DOI: {doi}\n内容: {content}\n"
                literature_list.append(lit_text)
            
            context = "\n".join(literature_list)
            logger.info(f"✅ 准备完成，共 {len(literature_list)} 个文献片段")
            logger.info("="*80)
            
            # 使用增强型prompt模板
            prompt = self._semantic_synthesis_prompt_robust.replace("{question}", user_question)
            prompt = prompt.replace("{context}", context)
            
            logger.info("\n" + "="*80)
            logger.info("📋 [步骤6] 构建增强型Prompt")
            logger.info(f"文献片段: {len(literature_list)} 个")
            logger.info(f"Prompt总长度: {len(prompt):,} 字符")
            logger.info("="*80)
            
            from langchain_core.messages import HumanMessage
            
            logger.info("\n" + "="*80)
            logger.info("🤖 [步骤7] 生成回答")
            response = self._llm.invoke([HumanMessage(content=prompt)])
            pure_answer = response.content.strip()
            logger.info(f"✅ LLM生成纯净答案完成 ({len(pure_answer)} 字符)")
            logger.info("="*80)
            
            # 使用embedding的DOI插入方法
            logger.info("\n" + "="*80)
            logger.info("📌 [步骤8] 基于Embedding的DOI插入")
            answer_with_doi, doi_locations = self._insert_dois_by_embedding(
                answer=pure_answer,
                documents=documents,
                pdf_contents=pdf_contents
            )
            logger.info("="*80)
            
            return answer_with_doi, doi_locations
            
        except Exception as e:
            logger.error(f"增强型答案合成失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._format_simple_answer(documents), {}
    
    def _synthesize_with_standard_prompt(
        self,
        user_question: str,
        documents: List[Dict],
        pdf_contents: Optional[Dict[str, str]] = None
    ) -> tuple:
        """使用标准prompt合成答案（原有逻辑）"""
        if not self._llm or not self._semantic_synthesis_prompt:
            return self._format_simple_answer(documents), {}
        
        try:
            # 构建文献列表（使用上下文扩展）
            # 精确问题：使用10篇文献（从20减少到10，避免prompt过长）
            logger.info("\n" + "="*80)
            logger.info("📖 [步骤5.5] 扩展上下文窗口")
            logger.info(f"原始段落数: {len(documents)}")
            
            literature_list = []
            num_abstracts = 10  # 使用10篇文献
            for i, doc in enumerate(documents[:num_abstracts], 1):
                chunk_id = doc.get('id')
                
                # 获取带上下文的完整内容
                context_result = self._vector_repo.get_chunk_with_context(
                    chunk_id=chunk_id,
                    window=2  # 前后各2个段落
                )
                
                if context_result.get('success'):
                    full_text = context_result['full_text']
                    context_range = context_result['context_range']
                    main_meta = context_result['metadata']
                    
                    logger.info(f"  [{i}] 扩展成功: {context_result['context_chunks']}个段落")
                    logger.info(f"      范围: 第{context_range['start_page']}-{context_range['end_page']}页")
                    logger.info(f"      长度: {len(full_text)} 字符")
                    
                    lit = {
                        "序号": i,
                        "内容": full_text,  # 使用完整上下文，不截断
                        "核心段落": context_result['main_text'][:200] + "...",  # 标注核心段落
                        "上下文信息": f"第{main_meta.get('page')}页第{main_meta.get('chunk_index_in_page', 0)+1}段（含前后各2段）"
                    }
                else:
                    # 如果获取上下文失败，使用原始内容
                    logger.warning(f"  [{i}] 扩展失败，使用原始段落")
                    lit = {
                        "序号": i,
                        "内容": doc.get('content', ''),
                        "核心段落": doc.get('content', '')[:200] + "...",
                        "上下文信息": "仅核心段落"
                    }
                
                if doc.get('metadata'):
                    lit["元数据"] = doc['metadata']
                literature_list.append(lit)
            
            logger.info(f"✅ 上下文扩展完成，共 {len(literature_list)} 篇文献摘要")
            logger.info("="*80)
            
            literature_json = json.dumps(literature_list, ensure_ascii=False, indent=2)
            
            # 添加PDF原文（限制长度，避免prompt过长）
            pdf_section = ""
            if pdf_contents:
                pdf_section = "\n\n## 📄 相关论文原文\n"
                for doi, content in pdf_contents.items():
                    # 限制每篇PDF最多10000字符
                    truncated_content = content[:10000]
                    if len(content) > 10000:
                        truncated_content += "\n... (内容过长，已截断)"
                    pdf_section += f"\n### DOI: {doi}\n{truncated_content}\n"
                    logger.info(f"  添加PDF全文: {doi} ({len(truncated_content)} 字符)")
            
            # 修改Prompt，禁止LLM编造文献引用
            prompt_template = """你是一个严谨的文献综述专家。请基于以下检索到的文献，回答用户问题。

**重要规则**：
1. 基于检索到的文献中的信息来回答问题
2. **绝对禁止**提及具体的"文献X"、"表X"、"图X"等引用标注
3. **绝对禁止**编造任何文献中没有的信息
4. 直接陈述事实，不要添加任何引用标注（系统会自动添加DOI引用）
5. 如果文献中没有相关信息，明确说明"检索到的文献中未提及"
6. 用中文回答，语言要专业、准确、简洁

**检索到的文献**：
{literature_results}

{pdf_contents}

**用户问题**：{user_question}

请直接回答问题，不要提及文献编号或引用标注。
"""
            
            prompt = prompt_template.replace("{user_question}", user_question)
            prompt = prompt.replace("{literature_results}", literature_json)
            prompt = prompt.replace("{pdf_contents}", pdf_section if pdf_section else "")
            
            logger.info("\n" + "="*80)
            logger.info("📋 [步骤6] 构建Prompt")
            logger.info(f"文献摘要: {len(literature_list)} 篇")
            logger.info(f"PDF原文: {len(pdf_contents) if pdf_contents else 0} 篇（完整内容，不截断）")
            if pdf_contents:
                total_pdf_chars = sum(len(content) for content in pdf_contents.values())
                logger.info(f"PDF总字符数: {total_pdf_chars:,} 字符")
            logger.info(f"Prompt总长度: {len(prompt):,} 字符 (~{len(prompt)//4:,} tokens)")
            logger.info("="*80)
            
            from langchain_core.messages import HumanMessage
            
            logger.info("\n" + "="*80)
            logger.info("🤖 [步骤7] 生成回答")
            response = self._llm.invoke([HumanMessage(content=prompt)])
            pure_answer = response.content.strip()
            logger.info(f"✅ LLM生成纯净答案完成 ({len(pure_answer)} 字符)")
            logger.info("="*80)
            
            # 使用新的基于embedding的DOI插入方法
            logger.info("\n" + "="*80)
            logger.info("📌 [步骤8] 基于Embedding的DOI插入")
            answer_with_doi, doi_locations = self._insert_dois_by_embedding(
                answer=pure_answer,
                documents=documents,
                pdf_contents=pdf_contents
            )
            logger.info("="*80)
            
            return answer_with_doi, doi_locations
            
        except Exception as e:
            logger.error(f"语义答案合成失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._format_simple_answer(documents), {}
    
    def _insert_dois_by_embedding(
        self,
        answer: str,
        documents: List[Dict],
        pdf_contents: Optional[Dict[str, str]] = None
    ) -> tuple:
        """
        基于二级检索的DOI插入方法
        
        工作流程：
        【一级检索】段落级数据库
        1. 从检索结果提取候选DOI池
        
        【二级检索】句子级数据库
        2. 拆分答案为句子
        3. 批量生成句子的embedding
        4. 在句子数据库中搜索（只匹配候选DOI）
        5. 相似度>0.6时插入DOI
        
        优先使用句子级数据库，失败时回退到PDF搜索
        
        Args:
            answer: LLM生成的纯净答案
            documents: 检索到的文献列表（一级检索结果）
            pdf_contents: PDF全文内容（回退方案）
            
        Returns:
            (answer_with_doi, doi_locations)
        """
        if not answer:
            return answer, {}
        
        # 如果有句子数据库，使用二级检索
        if self._sentence_collection:
            logger.info("\n" + "="*80)
            logger.info("🎯 使用二级检索模式（句子级数据库）")
            logger.info("="*80)
            return self._insert_dois_by_sentence_db(answer, documents)
        
        # 否则回退到PDF搜索
        else:
            logger.info("\n" + "="*80)
            logger.info("⚠️  回退到PDF搜索模式")
            logger.info("="*80)
            return self._insert_dois_by_pdf_search(answer, documents, pdf_contents)
        
        # 1. 拆分答案为句子
        sentences = self._split_sentences_for_doi(answer)
        logger.info(f"拆分为 {len(sentences)} 个句子")
        
        if not sentences:
            return answer, {}
        
        # 2. 批量生成embedding
        try:
            logger.info(f"正在为 {len(sentences)} 个句子生成embedding...")
            response = requests.post(
                self._bge_api_url,
                json={"input": sentences},
                timeout=60
            )
            response.raise_for_status()
            embeddings = [item["embedding"] for item in response.json()["data"]]
            logger.info(f"✅ 成功生成 {len(embeddings)} 个embedding")
        except Exception as e:
            logger.error(f"❌ 生成embedding失败: {e}")
            return answer, {}
        
        # 3. 准备搜索范围：检索到的文献ID + PDF段落
        doc_ids = [doc.get('id') for doc in documents if doc.get('id')]
        logger.info(f"检索到的文献: {len(doc_ids)} 篇")
        
        # 3.1 将PDF内容分段并生成embedding（用于搜索）
        pdf_chunks = []  # [(doi, chunk_text, chunk_embedding, chunk_index)]
        if pdf_contents:
            logger.info(f"正在处理 {len(pdf_contents)} 篇PDF全文...")
            all_chunks_text = []
            chunk_metadata = []  # [(doi, chunk_index)]
            
            for doi, content in pdf_contents.items():
                # 将PDF按段落分割（每1000字符一段）
                chunk_size = 1000
                for i in range(0, len(content), chunk_size):
                    chunk = content[i:i+chunk_size]
                    if len(chunk) > 100:  # 跳过太短的段落
                        all_chunks_text.append(chunk)
                        chunk_metadata.append((doi, i // chunk_size))
            
            # 批量生成PDF段落的embedding
            if all_chunks_text:
                try:
                    logger.info(f"正在为 {len(all_chunks_text)} 个PDF段落生成embedding...")
                    chunk_response = requests.post(
                        self._bge_api_url,
                        json={"input": all_chunks_text},
                        timeout=120
                    )
                    chunk_response.raise_for_status()
                    chunk_embeddings = [item["embedding"] for item in chunk_response.json()["data"]]
                    
                    # 组装pdf_chunks
                    for i, (chunk_text, (doi, chunk_idx)) in enumerate(zip(all_chunks_text, chunk_metadata)):
                        pdf_chunks.append((doi, chunk_text, chunk_embeddings[i], chunk_idx))
                    
                    logger.info(f"✅ PDF段落embedding生成完成: {len(pdf_chunks)} 个段落")
                except Exception as e:
                    logger.error(f"❌ PDF段落embedding生成失败: {e}")
                    pdf_chunks = []
        
        if not doc_ids and not pdf_chunks:
            logger.warning("⚠️  没有可搜索的内容，无法插入DOI")
            return answer, {}
        
        # 4. 为每个句子搜索最相关的段落（检索到的文献 + PDF段落）
        answer_with_doi = ""
        doi_locations = {}
        matched_count = 0
        similarity_threshold = 0.5  # 相似度阈值
        
        for sentence, embedding in zip(sentences, embeddings):
            # 跳过空行、标题行、表格行
            sent_strip = sentence.strip()
            if not sent_strip or sent_strip.startswith('#') or '|' in sent_strip:
                answer_with_doi += sentence
                continue
            
            try:
                # 4.1 在向量数据库中搜索（检索到的文献）
                best_similarity = 0.0
                best_doi = None
                best_content = None
                best_meta = {}
                best_source = 'abstract'  # 'abstract' or 'pdf'
                
                # 搜索检索到的文献
                if doc_ids:
                    results = self._vector_repo._collection.query(
                        query_embeddings=[embedding],
                        n_results=50,
                        include=["documents", "metadatas", "distances"]
                    )
                    
                    if results and results["metadatas"] and results["metadatas"][0]:
                        result_ids = results.get("ids", [[]])[0]
                        for i, result_id in enumerate(result_ids):
                            if result_id in doc_ids:
                                similarity = 1 - (results["distances"][0][i] / 2.0)
                                
                                if similarity > best_similarity:
                                    meta = results["metadatas"][0][i]
                                    doi = meta.get('doi') or meta.get('DOI', 'N/A')
                                    if doi != 'N/A':
                                        best_similarity = similarity
                                        best_doi = doi
                                        best_content = results["documents"][0][i]
                                        best_meta = meta
                                        best_source = 'abstract'
                
                # 4.2 在PDF段落中搜索（使用余弦相似度）
                if pdf_chunks:
                    import numpy as np
                    # 计算与所有PDF段落的相似度
                    for doi, chunk, chunk_embedding, chunk_idx in pdf_chunks:
                        # 计算余弦相似度
                        similarity = np.dot(embedding, chunk_embedding) / (
                            np.linalg.norm(embedding) * np.linalg.norm(chunk_embedding)
                        )
                        
                        if similarity > best_similarity:
                            best_similarity = float(similarity)
                            best_doi = doi
                            best_content = chunk
                            best_meta = {'page': 0, 'chunk_index_in_page': chunk_idx}
                            best_source = 'pdf'
                
                # 4.3 如果找到了匹配，插入DOI
                if best_doi and best_similarity > similarity_threshold:
                    # 验证引用准确性（检查关键数值）
                    is_valid = self._validate_citation(sent_strip, best_content)
                    
                    # 调整验证逻辑：PDF来源的匹配更宽松
                    should_insert = False
                    if best_source == 'pdf':
                        # PDF来源：相似度>0.5即可插入
                        should_insert = best_similarity >= 0.5
                    else:
                        # 摘要来源：需要验证通过或高相似度
                        should_insert = is_valid or best_similarity >= 0.7
                    
                    if should_insert:
                        answer_with_doi += f"{sent_strip} (doi={best_doi})\n"
                        matched_count += 1
                        
                        # 记录位置信息
                        if best_doi not in doi_locations:
                            doi_locations[best_doi] = []
                        
                        # 计算置信度
                        if is_valid and best_similarity >= 0.7:
                            confidence = 'high'
                        elif (is_valid and best_similarity >= 0.5) or best_similarity >= 0.7:
                            confidence = 'medium'
                        else:
                            confidence = 'low'
                        
                        doi_locations[best_doi].append({
                            'sentence': sent_strip,
                            'page': best_meta.get('page', 0),
                            'chunk_index_in_page': best_meta.get('chunk_index_in_page', 0),
                            'similarity': float(best_similarity),
                            'confidence': confidence,
                            'source_text': best_content,
                            'validated': is_valid,
                            'source': best_source  # 标记来源
                        })
                        
                        logger.debug(f"   ✅ 插入DOI: {best_doi} (相似度={best_similarity:.3f}, 来源={best_source}, 验证={'通过' if is_valid else '未通过'})")
                    else:
                        answer_with_doi += sentence
                        logger.debug(f"   ⚠️  跳过DOI插入: 验证失败且相似度不够 ({best_similarity:.3f})")
                else:
                    answer_with_doi += sentence
                    
            except Exception as e:
                logger.error(f"搜索句子失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
                answer_with_doi += sentence
        
        logger.info(f"✅ DOI插入完成: {matched_count}/{len(sentences)} 个句子匹配成功")
        logger.info(f"插入了 {len(doi_locations)} 个不同的DOI")
        
        return answer_with_doi, doi_locations
    
    def _insert_dois_by_sentence_db(
        self,
        answer: str,
        documents: List[Dict]
    ) -> tuple:
        """
        使用句子级数据库进行二级检索和DOI插入
        
        工作流程:
        1. 从一级检索结果提取候选DOI池
        2. 拆分答案为句子
        3. 批量生成句子embedding
        4. 在句子数据库中搜索（只匹配候选DOI）
        5. 相似度>0.6时插入DOI
        
        Args:
            answer: LLM生成的答案
            documents: 一级检索结果
            
        Returns:
            (answer_with_doi, doi_locations)
        """
        # 1. 提取候选DOI池
        candidate_dois = self._extract_candidate_dois(documents)
        logger.info(f"[一级检索] 候选DOI池: {len(candidate_dois)} 个")
        
        if not candidate_dois:
            logger.warning("⚠️  没有候选DOI，无法插入引用")
            return answer, {}
        
        # 2. 拆分答案为句子
        sentences = self._split_sentences_for_doi(answer)
        logger.info(f"[二级检索] 拆分为 {len(sentences)} 个句子")
        
        if not sentences:
            return answer, {}
        
        # 3. 批量生成句子embedding
        try:
            logger.info(f"[二级检索] 正在为 {len(sentences)} 个句子生成embedding...")
            response = requests.post(
                self._bge_api_url,
                json={"input": sentences},
                timeout=60
            )
            response.raise_for_status()
            embeddings = [item["embedding"] for item in response.json()["data"]]
            logger.info(f"✅ 成功生成 {len(embeddings)} 个embedding")
        except Exception as e:
            logger.error(f"❌ 生成embedding失败: {e}")
            return answer, {}
        
        # 4. 在句子数据库中搜索并插入DOI
        answer_with_doi = ""
        doi_locations = {}
        matched_count = 0
        similarity_threshold = 0.6  # 句子级阈值提高到0.6
        
        for sentence, embedding in zip(sentences, embeddings):
            # 跳过空行、标题行、表格行
            sent_strip = sentence.strip()
            if not sent_strip or sent_strip.startswith('#') or '|' in sent_strip:
                answer_with_doi += sentence
                continue
            
            try:
                # 在句子数据库中搜索
                results = self._sentence_collection.query(
                    query_embeddings=[embedding],
                    n_results=50,  # 多取一些结果用于过滤
                    include=["documents", "metadatas", "distances"]
                )
                
                # 过滤：只保留候选DOI池中的结果
                best_match = None
                best_similarity = 0.0
                
                if results and results["metadatas"] and results["metadatas"][0]:
                    for i, meta in enumerate(results["metadatas"][0]):
                        # 兼容DOI字段（大小写）
                        doi = meta.get('DOI') or meta.get('doi')
                        
                        # 只考虑候选DOI池中的结果
                        if doi and doi in candidate_dois:
                            # 计算相似度
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
                
                # 插入DOI（阈值0.6）
                if best_match and best_similarity > similarity_threshold:
                    answer_with_doi += f"{sent_strip} (doi={best_match['doi']})\n"
                    matched_count += 1
                    
                    # 记录位置信息
                    if best_match['doi'] not in doi_locations:
                        doi_locations[best_match['doi']] = []
                    
                    # 计算置信度
                    if best_similarity > 0.75:
                        confidence = 'high'
                    elif best_similarity > 0.6:
                        confidence = 'medium'
                    else:
                        confidence = 'low'
                    
                    doi_locations[best_match['doi']].append({
                        'sentence': sent_strip,
                        'similarity': float(best_similarity),
                        'confidence': confidence,
                        'source_sentence': best_match['content'],
                        'sentence_index': best_match['metadata'].get('sentence_index'),
                        'has_number': best_match['metadata'].get('has_number'),
                        'has_unit': best_match['metadata'].get('has_unit'),
                        'source': 'sentence_db'  # 标记来源
                    })
                    
                    logger.debug(f"   ✅ 插入DOI: {best_match['doi']} (相似度={best_similarity:.3f}, 置信度={confidence})")
                else:
                    answer_with_doi += sentence
                    if best_match:
                        logger.debug(f"   ⚠️  跳过DOI插入: 相似度不够 ({best_similarity:.3f} < {similarity_threshold})")
                    
            except Exception as e:
                logger.error(f"搜索句子失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
                answer_with_doi += sentence
        
        logger.info(f"✅ [二级检索] DOI插入完成: {matched_count}/{len(sentences)} 个句子匹配成功")
        logger.info(f"插入了 {len(doi_locations)} 个不同的DOI")
        
        return answer_with_doi, doi_locations
    
    def _insert_dois_by_pdf_search(
        self,
        answer: str,
        documents: List[Dict],
        pdf_contents: Optional[Dict[str, str]] = None
    ) -> tuple:
        """
        使用PDF搜索进行DOI插入（回退方案）
        
        这是原有的实现，当句子数据库不可用时使用
        """
        # 简化实现：只在检索到的文献中搜索，不使用PDF
        logger.warning("⚠️  句子数据库不可用，使用简化的DOI插入")
        logger.warning("⚠️  建议检查句子数据库连接")
        
        # 提取候选DOI
        candidate_dois = self._extract_candidate_dois(documents)
        
        if not candidate_dois:
            return answer, {}
        
        # 简单策略：为每个段落的DOI插入一次引用
        answer_with_doi = answer
        doi_locations = {}
        
        for doi in candidate_dois:
            if doi not in doi_locations:
                doi_locations[doi] = [{
                    'sentence': '整体引用',
                    'confidence': 'low',
                    'source': 'fallback'
                }]
        
        return answer_with_doi, doi_locations
    
    def _split_sentences_for_doi(self, text: str) -> List[str]:
        """按中文标点拆分句子（用于DOI插入）"""
        sentences = []
        current = ""
        
        for char in text:
            current += char
            if char in ['。', '！', '？', '\n']:
                sent = current.strip()
                if sent and not sent.startswith('#'):  # 跳过标题
                    sentences.append(sent)
                current = ""
        
        if current.strip():
            sentences.append(current.strip())
        
        return sentences
    
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
            # 兼容 'doi' 和 'DOI' 两种字段名
            doi = meta.get('doi') or meta.get('DOI')
            
            if doi and doi != 'N/A' and 'unknown' not in doi.lower():
                candidate_dois.add(doi)
        
        return candidate_dois
    
    def _validate_citation(self, sentence: str, source_text: str) -> bool:
        """
        验证引用是否准确（检查关键数值）
        
        Args:
            sentence: 答案中的句子
            source_text: 原文片段
            
        Returns:
            True=验证通过, False=验证失败
        """
        import re
        
        # 提取句子中的数值（带单位）
        numbers = re.findall(r'\d+\.?\d*\s*[VvmAhΩ%KkWw]+', sentence)
        
        if not numbers:
            return True  # 没有数值，无法验证，默认通过
        
        # 检查原文是否包含这些数值
        for num in numbers:
            # 清理数值，去除空格，统一大小写
            num_clean = num.replace(' ', '').lower()
            source_clean = source_text.replace(' ', '').lower()
            
            if num_clean not in source_clean:
                logger.debug(f"   ⚠️  数值验证失败: '{num}' 不在原文中")
                return False  # 数值不匹配
        
        logger.debug(f"   ✅ 数值验证通过: {numbers}")
        return True  # 所有数值都匹配
    
    def _synthesize_broad_answer(
        self,
        user_question: str,
        documents: List[Dict]
    ) -> tuple:
        """合成宽泛问题答案"""
        if not self._llm or not self._broad_question_prompt:
            return self._format_simple_answer(documents)
        
        try:
            # 宽泛问题：使用更多摘要（10篇），但不扩展上下文，不加载PDF
            logger.info("\n" + "="*80)
            logger.info("📖 [宽泛问题] 提取文献摘要")
            logger.info(f"使用 10 篇摘要（不扩展上下文，节省token）")
            
            summaries = []
            for i, doc in enumerate(documents[:10], 1):
                # 使用原始内容，不扩展上下文
                content = doc.get('content', '')
                summaries.append({
                    "序号": i,
                    "摘要": content[:1000]  # 每篇最多1000字符
                })
                logger.info(f"  [{i}] 摘要长度: {len(content[:1000])} 字符")
            
            logger.info(f"✅ 摘要提取完成，共 {len(summaries)} 篇")
            logger.info("="*80)
            
            summaries_json = json.dumps(summaries, ensure_ascii=False, indent=2)
            
            prompt = self._broad_question_prompt.replace("{user_question}", user_question)
            prompt = prompt.replace("{literature_summaries}", summaries_json)
            
            logger.info("\n" + "="*80)
            logger.info("📋 [步骤6] 构建Prompt（宽泛问题）")
            logger.info(f"文献摘要: {len(summaries)} 篇（原始内容，不扩展）")
            logger.info(f"Prompt总长度: {len(prompt):,} 字符 (~{len(prompt)//4:,} tokens)")
            logger.info("="*80)
            
            from langchain_core.messages import HumanMessage
            
            response = self._llm.invoke([HumanMessage(content=prompt)])
            return response.content.strip(), {}  # 宽泛问题不插入DOI
            
        except Exception as e:
            logger.error(f"宽泛问题答案合成失败: {e}")
            return self._format_simple_answer(documents)
    
    def _format_simple_answer(self, documents: List[Dict]) -> tuple:
        """简单格式化答案（无LLM时使用）"""
        if not documents:
            return "未找到相关文献。", {}
        
        answer = f"找到 {len(documents)} 篇相关文献：\n\n"
        for i, doc in enumerate(documents[:10], 1):
            content = doc.get('content', '')[:200]
            score = doc.get('score', 0)
            answer += f"{i}. [相似度: {score:.2f}] {content}...\n\n"
        
        if len(documents) > 10:
            answer += f"... 还有 {len(documents) - 10} 篇文献未显示"
        
        return answer, {}
    
    def query(self, question: str, load_pdf: bool = True) -> tuple:
        """执行查询并返回格式化的答案和DOI位置信息"""
        result = self.search(question=question, top_k=20, with_scores=True)  # 改回20，为embedding匹配提供更多候选
        
        if not result.get('success'):
            return f"搜索失败: {result.get('error', '未知错误')}", {}
        
        documents = result.get('documents', [])
        
        if not documents:
            return "未找到相关文献。", {}
        
        # 判断问题类型
        is_broad = self._is_broad_question(question)
        
        # 宽泛问题：不加载PDF，使用宽泛问题模板
        if is_broad:
            logger.info("检测到宽泛问题，使用宽泛问题合成模板")
            return self._synthesize_broad_answer(question, documents)
        
        # 精确问题：加载PDF，使用精确问题模板
        pdf_contents = {}
        if load_pdf and self._pdf_manager:
            logger.info("\n" + "="*80)
            logger.info("📄 [步骤5] 提取DOI并加载PDF原文")
            dois = self._extract_dois(documents)
            logger.info(f"提取到的DOI列表: {dois}")
            if dois:
                pdf_contents = self._load_pdf_contents(dois)
                logger.info(f"✅ 成功加载 {len(pdf_contents)} 篇PDF")
                for doi, content in pdf_contents.items():
                    logger.info(f"  - {doi}: {len(content)} 字符")
            else:
                logger.info("⚠️  未提取到DOI")
            logger.info("="*80)
        
        return self._synthesize_semantic_answer(question, documents, pdf_contents)
