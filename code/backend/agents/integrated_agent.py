"""
集成智能Agent - 自动路由到合适的专家系统
Integrated Intelligent Agent with Auto-Routing
"""
import os
import logging
from typing import Dict, Any, Optional, Generator
from dotenv import load_dotenv

from backend.agents.experts import RouterExpert, QueryExpert, SemanticExpert, CommunityExpert
from backend.services import LLMService, Neo4jService, VectorService
from backend.repositories.vector_repository import VectorRepository, CommunityVectorRepository

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class IntegratedAgent:
    """集成智能Agent - 带自动路由功能"""
    
    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        neo4j_service: Optional[Neo4jService] = None,
        vector_service: Optional[VectorService] = None
    ):
        """
        初始化集成Agent
        
        Args:
            llm_service: LLM服务实例
            neo4j_service: Neo4j服务实例
            vector_service: 向量服务实例
        """
        logger.info("🚀 正在初始化集成智能Agent...")
        
        # 初始化服务（使用传入的或创建新的）
        self._llm_service = llm_service or LLMService()
        self._neo4j_service = neo4j_service
        self._vector_service = vector_service
        
        # 1. 初始化路由专家
        logger.info("📍 初始化路由专家...")
        self._router = RouterExpert(llm_service=self._llm_service)
        
        # 2. 初始化专家系统（懒加载）
        self._query_expert = None
        self._semantic_expert = None
        self._community_expert = None
        
        logger.info("✅ 集成智能Agent初始化完成！\n")
    
    @property
    def query_expert(self) -> QueryExpert:
        """懒加载精确查询专家"""
        if self._query_expert is None:
            logger.info("📊 初始化精确查询专家...")
            if self._neo4j_service is None:
                from backend.services import get_neo4j_service
                self._neo4j_service = get_neo4j_service()
            self._query_expert = QueryExpert(
                neo4j_service=self._neo4j_service,
                llm_service=self._llm_service
            )
        return self._query_expert
    
    @property
    def semantic_expert(self) -> SemanticExpert:
        """懒加载语义搜索专家"""
        if self._semantic_expert is None:
            logger.info("📚 初始化语义搜索专家...")
            vector_repo = VectorRepository()
            self._semantic_expert = SemanticExpert(
                vector_repo=vector_repo,
                llm_service=self._llm_service
            )
        return self._semantic_expert
    
    @property
    def community_expert(self) -> CommunityExpert:
        """懒加载社区摘要专家"""
        if self._community_expert is None:
            logger.info("🏘️ 初始化社区摘要专家...")
            community_repo = CommunityVectorRepository()
            self._community_expert = CommunityExpert(
                community_repo=community_repo,
                llm_service=self._llm_service
            )
        return self._community_expert
    
    def query(self, user_question: str, auto_route: bool = True) -> Dict[str, Any]:
        """
        处理用户查询（带自动路由）
        
        Args:
            user_question: 用户问题
            auto_route: 是否自动路由
            
        Returns:
            查询结果字典
        """
        logger.info(f"\n{'='*80}\n🔍 处理用户查询: {user_question}\n{'='*80}")
        
        if not auto_route:
            return {
                "mode": "manual",
                "message": "请手动选择专家系统",
                "user_question": user_question
            }
        
        try:
            # 1. 路由决策
            routing_result = self._router.route(user_question)
            
            if not routing_result.get("success", True):
                logger.warning(f"⚠️ 路由失败，使用降级策略")
            
            expert_name = routing_result.get("primary_expert", "literature")
            confidence = routing_result.get("confidence", 0.0)
            reasoning = routing_result.get("reasoning", "")
            
            logger.info(f"📍 路由决策: {expert_name} (置信度: {confidence:.2f})")
            logger.info(f"   理由: {reasoning}")
            
            # 2. 调用对应的专家系统
            if expert_name == "neo4j":
                result = self._query_neo4j(user_question)
            elif expert_name == "literature":
                result = self._query_literature(user_question)
            elif expert_name == "community":
                result = self._query_community(user_question)
            else:
                logger.warning(f"未知的专家系统: {expert_name}，使用文献专家")
                result = self._query_literature(user_question)
            
            # 3. 添加路由信息到结果中
            result["routing_info"] = routing_result
            result["expert_used"] = expert_name
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 查询执行失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "expert_used": "unknown",
                "user_question": user_question
            }
    
    def query_stream(self, user_question: str) -> Generator[Dict[str, Any], None, None]:
        """
        流式处理用户查询
        
        Args:
            user_question: 用户问题
            
        Yields:
            查询结果块
        """
        try:
            # 发送开始信号
            yield {"type": "start", "question": user_question}
            
            # 步骤1: 生成搜索关键词
            yield {
                "type": "step",
                "step": "generate_keywords",
                "message": "📝 正在生成搜索关键词...",
                "status": "processing"
            }
            
            try:
                search_query = self.semantic_expert.generate_search_query(user_question)
                yield {
                    "type": "step",
                    "step": "generate_keywords",
                    "message": f"✅ 搜索关键词: {search_query}",
                    "status": "success",
                    "data": {"keywords": search_query}
                }
            except Exception as e:
                yield {
                    "type": "step",
                    "step": "generate_keywords",
                    "message": f"⚠️ 关键词生成失败,使用原始问题",
                    "status": "warning",
                    "error": str(e)
                }
                search_query = user_question
            
            # 步骤2: 调用BGE API生成向量
            yield {
                "type": "step",
                "step": "generate_embedding",
                "message": "🔢 正在调用BGE API生成查询向量...",
                "status": "processing"
            }
            
            # 步骤3: 查询向量数据库
            yield {
                "type": "step",
                "step": "query_vector_db",
                "message": "🔍 正在查询向量数据库...",
                "status": "processing"
            }
            
            # 执行文献检索
            search_result = self.semantic_expert.search(user_question, top_k=20, with_scores=True)
            
            if not search_result.get('success'):
                error_step = search_result.get('error_step', 'unknown')
                error_msg = search_result.get('error', '未知错误')
                
                # 根据错误步骤返回友好提示
                if error_step == 'generate_embedding':
                    yield {
                        "type": "step",
                        "step": "generate_embedding",
                        "message": f"❌ BGE API调用失败: {error_msg}",
                        "status": "error",
                        "error": error_msg
                    }
                    yield {
                        "type": "error",
                        "error": "BGE embedding服务不可用,请检查API连接",
                        "details": error_msg
                    }
                elif error_step == 'vector_search':
                    yield {
                        "type": "step",
                        "step": "query_vector_db",
                        "message": f"❌ 向量数据库查询失败: {error_msg}",
                        "status": "error",
                        "error": error_msg
                    }
                    yield {
                        "type": "error",
                        "error": "向量数据库查询失败",
                        "details": error_msg
                    }
                else:
                    yield {
                        "type": "error",
                        "error": f"搜索失败: {error_msg}",
                        "details": error_msg
                    }
                # 发送完成信号,即使出错也要结束流
                yield {"type": "done", "references": [], "metadata": {}}
                return
            
            documents = search_result.get('documents', [])
            doc_count = len(documents)
            
            # BGE API 和向量查询成功
            yield {
                "type": "step",
                "step": "generate_embedding",
                "message": "✅ 查询向量生成成功",
                "status": "success"
            }
            
            yield {
                "type": "step",
                "step": "query_vector_db",
                "message": f"✅ 找到 {doc_count} 条相关文献",
                "status": "success",
                "data": {"count": doc_count}
            }
            
            if doc_count == 0:
                yield {
                    "type": "step",
                    "step": "no_results",
                    "message": "❌ 未找到相关文献",
                    "status": "warning"
                }
                yield {
                    "type": "content",
                    "content": "抱歉,没有找到与您问题相关的文献。请尝试使用不同的关键词。"
                }
                yield {"type": "done", "references": [], "metadata": {}}
                return
            
            # 步骤4: 构建Prompt
            yield {
                "type": "step",
                "step": "build_prompt",
                "message": "🛠️ 正在构建提示词...",
                "status": "processing"
            }
            
            # 步骤5: 调用LLM生成答案
            yield {
                "type": "step",
                "step": "call_llm",
                "message": "🤖 正在调用LLM生成综合答案...",
                "status": "processing"
            }
            
            # 初始化结果
            answer = ""
            references = []
            metadata = {}
            
            # 执行完整查询生成答案
            try:
                result = self._query_literature(user_question)
                
                if not result.get("success"):
                    yield {
                        "type": "step",
                        "step": "call_llm",
                        "message": f"❌ LLM调用失败: {result.get('error', '未知错误')}",
                        "status": "error",
                        "error": result.get('error')
                    }
                    yield {
                        "type": "error",
                        "error": "LLM答案生成失败",
                        "details": result.get('error', '未知错误')
                    }
                    # 发送完成信号
                    yield {"type": "done", "references": [], "metadata": {}}
                    return
                
                answer = result.get("answer", "")
                references = result.get("references", [])
                metadata = result.get("metadata", {})
                pdf_info = result.get("pdf_info", {})
                
                # 显示PDF加载信息（不显示失败数量）
                if pdf_info:
                    pdf_loaded = pdf_info.get('pdf_loaded', 0)
                    dois_found = pdf_info.get('dois_found', 0)
                    
                    if pdf_loaded > 0:
                        yield {
                            "type": "step",
                            "step": "load_pdf",
                            "message": f"📄 已加载 {pdf_loaded} 篇PDF原文传给LLM",
                            "status": "success",
                            "data": pdf_info
                        }
                    elif dois_found > 0:
                        yield {
                            "type": "step",
                            "step": "load_pdf",
                            "message": "⚠️ 找到DOI但未能加载PDF原文",
                            "status": "warning",
                            "data": pdf_info
                        }
                    else:
                        yield {
                            "type": "step",
                            "step": "load_pdf",
                            "message": "⚠️ 文献中未找到DOI，仅使用摘要",
                            "status": "warning"
                        }
                
                yield {
                    "type": "step",
                    "step": "build_prompt",
                    "message": "✅ 提示词构建完成",
                    "status": "success"
                }
                
                yield {
                    "type": "step",
                    "step": "call_llm",
                    "message": "✅ LLM响应成功",
                    "status": "success"
                }
                
            except Exception as e:
                logger.error(f"答案生成失败: {e}", exc_info=True)
                yield {
                    "type": "step",
                    "step": "call_llm",
                    "message": f"❌ 答案生成异常: {str(e)}",
                    "status": "error",
                    "error": str(e)
                }
                yield {
                    "type": "error",
                    "error": "答案生成过程中发生异常",
                    "details": str(e)
                }
                # 发送完成信号
                yield {"type": "done", "references": [], "metadata": {}}
                return
            
            # 3. 流式输出答案（分块）
            if answer:
                chunk_size = 50  # 每50个字符一块
                for i in range(0, len(answer), chunk_size):
                    chunk = answer[i:i+chunk_size]
                    yield {"type": "content", "content": chunk}
            else:
                # 答案为空时也要发送内容和完成信号
                yield {
                    "type": "content",
                    "content": "抱歉,虽然找到了相关文献,但未能生成完整的答案。请尝试重新提问或换个角度描述您的问题。"
                }
            
            # 4. 发送完成信号
            yield {
                "type": "done",
                "references": references,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ 流式查询失败: {e}", exc_info=True)
            yield {"type": "error", "error": str(e)}
            # 确保发送完成信号
            yield {"type": "done", "references": [], "metadata": {}}
    
    def _query_neo4j(self, question: str) -> Dict[str, Any]:
        """使用Neo4j知识图谱查询"""
        logger.info("🗃️ 使用Neo4j知识图谱查询...")
        try:
            result = self.query_expert.execute_query(question)
            result["expert_used"] = "neo4j"
            return result
        except Exception as e:
            logger.error(f"Neo4j查询失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "expert_used": "neo4j"
            }
    
    def _query_literature(self, question: str, n_results: int = 10) -> Dict[str, Any]:
        """使用文献语义搜索"""
        logger.info("\n" + "="*80)
        logger.info("📝 [步骤1] 用户提问")
        logger.info(f"问题: {question}")
        logger.info("="*80)
        try:
            # 使用query()方法，会调用LLM生成综合答案（RAG模式）
            # 返回值中包含pdf_info信息
            query_result = self.semantic_expert.query_with_details(question, load_pdf=True)
            answer = query_result.get('answer', '')
            pdf_info = query_result.get('pdf_info', {})
            
            # 同时获取检索结果以提取引用
            search_result = self.semantic_expert.search(question, top_k=n_results, with_scores=True)
            
            # 提取文献引用（包含相似度）
            references = []
            if search_result.get('success') and search_result.get('documents'):
                for doc in search_result['documents'][:5]:  # 取前5篇作为引用
                    metadata = doc.get('metadata', {})
                    ref = {
                        'doi': metadata.get('DOI', metadata.get('doi', '')),
                        'title': metadata.get('title', ''),
                        'similarity': doc.get('score')  # 添加相似度分数
                    }
                    references.append(ref)
            
            return {
                "success": True,
                "answer": answer,
                "references": references,
                "expert_used": "literature",
                "pdf_info": pdf_info
            }
        except Exception as e:
            logger.error(f"文献搜索失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "expert_used": "literature"
            }
    
    def _query_community(self, question: str, n_results: int = 5) -> Dict[str, Any]:
        """使用社区摘要分析"""
        logger.info("🏘️ 使用社区摘要分析...")
        try:
            result = self.community_expert.analyze(question, top_k=n_results)
            result["expert_used"] = "community"
            return result
        except Exception as e:
            logger.error(f"社区分析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "expert_used": "community"
            }
    
    def query_with_expert(
        self,
        user_question: str,
        expert_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        使用指定的专家系统查询（不经过路由）
        
        Args:
            user_question: 用户问题
            expert_name: 专家系统名称 (neo4j/literature/community)
            **kwargs: 额外参数
            
        Returns:
            查询结果
        """
        logger.info(f"🎯 手动指定使用专家: {expert_name}")
        
        if expert_name == "neo4j":
            return self._query_neo4j(user_question)
        elif expert_name == "literature":
            n_results = kwargs.get("n_results", 10)
            return self._query_literature(user_question, n_results)
        elif expert_name == "community":
            n_results = kwargs.get("n_results", 5)
            return self._query_community(user_question, n_results)
        else:
            return {
                "success": False,
                "error": f"未知的专家系统: {expert_name}",
                "user_question": user_question
            }


# 全局单例
_integrated_agent: Optional[IntegratedAgent] = None


def get_integrated_agent() -> IntegratedAgent:
    """获取全局集成Agent实例"""
    global _integrated_agent
    if _integrated_agent is None:
        _integrated_agent = IntegratedAgent()
    return _integrated_agent
