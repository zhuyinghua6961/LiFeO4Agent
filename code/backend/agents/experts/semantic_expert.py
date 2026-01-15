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
        self._semantic_synthesis_prompt = self._load_prompt("semantic_synthesis_prompt_v2.txt")
        self._broad_question_prompt = self._load_prompt("broad_question_synthesis_prompt.txt")
        
        # 初始化PDF管理器
        from backend.config.settings import settings
        self._pdf_manager = PDFManager(
            papers_dir=settings.papers_dir,
            mapping_file=settings.doi_to_pdf_mapping
        ) if hasattr(settings, 'papers_dir') else None
        
        # 相似度阈值配置
        self._broad_threshold = getattr(settings, 'broad_similarity_threshold', 0.65)
        self._precise_threshold = getattr(settings, 'precise_similarity_threshold', 0.5)
        
        # BGE API配置（用于生成查询embedding）
        self._bge_api_url = settings.bge_api_url
        
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
        top_k: int = 10,
        with_scores: bool = False,
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
            logger.info("📝 [步骤2] 生成搜索关键词")
            logger.info(f"原始问题: {question}")
            search_query = self.generate_search_query(question)
            logger.info(f"生成的搜索关键词: {search_query}")
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
                    "expert": "semantic",
                    "documents": []
                }
            
            # 执行搜索
            logger.info("\n" + "="*80)
            logger.info("🔍 [步骤4] 查询向量数据库(ChromaDB)")
            logger.info(f"请求返回数量: top_k={top_k}")
            logger.info(f"过滤条件: {filter_metadata}")
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
                    # ChromaDB 返回的是距离，需要转换为相似度分数
                    doc_data["score"] = 1 - distances[i] if distances[i] <= 1 else 0
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
                "expert": "semantic"
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
    
    def _synthesize_semantic_answer(
        self,
        user_question: str,
        documents: List[Dict],
        pdf_contents: Optional[Dict[str, str]] = None
    ) -> str:
        """合成语义搜索答案（精确问题）"""
        if not self._llm or not self._semantic_synthesis_prompt:
            return self._format_simple_answer(documents)
        
        try:
            # 构建文献列表
            literature_list = []
            for i, doc in enumerate(documents[:10], 1):
                lit = {
                    "序号": i,
                    "内容": doc.get('content', '')[:500]
                }
                if doc.get('metadata'):
                    lit["元数据"] = doc['metadata']
                literature_list.append(lit)
            
            literature_json = json.dumps(literature_list, ensure_ascii=False, indent=2)
            
            # 添加PDF原文
            pdf_section = ""
            if pdf_contents:
                pdf_section = "\n\n## 📄 相关论文原文摘要\n"
                for doi, content in pdf_contents.items():
                    pdf_section += f"\n### DOI: {doi}\n{content[:5000]}\n"
            
            prompt = self._semantic_synthesis_prompt.replace("{user_question}", user_question)
            prompt = prompt.replace("{literature_results}", literature_json)
            prompt = prompt.replace("{pdf_contents}", pdf_section if pdf_section else "无PDF原文")
            
            logger.info("\n" + "="*80)
            logger.info("📋 [步骤6] 构建完整Prompt")
            logger.info(f"用户问题: {user_question}")
            logger.info(f"文献数量: {len(literature_list)} 篇")
            logger.info(f"PDF原文: {len(pdf_contents)} 篇")
            logger.info(f"\nPrompt总长度: {len(prompt)} 字符")
            logger.info("\n完整Prompt内容:")
            logger.info("-"*80)
            logger.info(prompt)
            logger.info("-"*80)
            logger.info("="*80)
            
            from langchain_core.messages import HumanMessage
            
            logger.info("\n" + "="*80)
            logger.info("🤖 [步骤7] 调用LLM生成答案")
            logger.info("正在等待LLM响应...")
            response = self._llm.invoke([HumanMessage(content=prompt)])
            logger.info("✅ LLM响应成功")
            logger.info(f"\n生成的答案长度: {len(response.content)} 字符")
            logger.info("\nLLM生成的完整答案:")
            logger.info("-"*80)
            logger.info(response.content)
            logger.info("-"*80)
            logger.info("="*80)
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"语义答案合成失败: {e}")
            return self._format_simple_answer(documents)
    
    def _synthesize_broad_answer(
        self,
        user_question: str,
        documents: List[Dict]
    ) -> str:
        """合成宽泛问题答案"""
        if not self._llm or not self._broad_question_prompt:
            return self._format_simple_answer(documents)
        
        try:
            # 提取文献摘要
            summaries = []
            for i, doc in enumerate(documents[:15], 1):
                summaries.append({
                    "序号": i,
                    "摘要": doc.get('content', '')[:800]
                })
            
            summaries_json = json.dumps(summaries, ensure_ascii=False, indent=2)
            
            prompt = self._broad_question_prompt.replace("{user_question}", user_question)
            prompt = prompt.replace("{literature_summaries}", summaries_json)
            
            from langchain_core.messages import HumanMessage
            
            response = self._llm.invoke([HumanMessage(content=prompt)])
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"宽泛问题答案合成失败: {e}")
            return self._format_simple_answer(documents)
    
    def _format_simple_answer(self, documents: List[Dict]) -> str:
        """简单格式化答案（无LLM时使用）"""
        if not documents:
            return "未找到相关文献。"
        
        answer = f"找到 {len(documents)} 篇相关文献：\n\n"
        for i, doc in enumerate(documents[:10], 1):
            content = doc.get('content', '')[:200]
            score = doc.get('score', 0)
            answer += f"{i}. [相似度: {score:.2f}] {content}...\n\n"
        
        if len(documents) > 10:
            answer += f"... 还有 {len(documents) - 10} 篇文献未显示"
        
        return answer
    
    def query(self, question: str, load_pdf: bool = True) -> str:
        """执行查询并返回格式化的答案"""
        result = self.search(question=question, top_k=20, with_scores=True)
        
        if not result.get('success'):
            return f"搜索失败: {result.get('error', '未知错误')}"
        
        documents = result.get('documents', [])
        
        if not documents:
            return "未找到相关文献。"
        
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
