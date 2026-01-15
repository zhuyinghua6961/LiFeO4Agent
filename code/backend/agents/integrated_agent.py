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
            
            # 1. 路由决策 - 当前仅使用文献检索
            yield {"type": "thinking", "content": "📚 正在检索文献..."}
            
            # 强制使用文献检索，不使用Neo4j和Community
            expert_name = "literature"
            routing_result = {
                "primary_expert": "literature",
                "confidence": 1.0,
                "reasoning": "使用文献检索系统"
            }
            
            # 发送路由信息
            yield {
                "type": "metadata",
                "expert": expert_name,
                "confidence": routing_result.get("confidence", 1.0),
                "reasoning": routing_result.get("reasoning", "")
            }
            
            # 初始化结果
            answer = ""
            references = []
            metadata = {}
            
            # 2. 执行文献检索并生成综合答案
            yield {"type": "thinking", "content": "📚 正在检索文献并生成综合答案..."}
            result = self._query_literature(user_question)
            answer = result.get("answer", "")
            references = result.get("references", [])
            metadata = result.get("metadata", {})
            
            # 3. 流式输出答案（分块）
            if answer:
                chunk_size = 50  # 每50个字符一块
                for i in range(0, len(answer), chunk_size):
                    chunk = answer[i:i+chunk_size]
                    yield {"type": "content", "content": chunk}
            else:
                yield {"type": "error", "error": "未能生成答案"}
            
            # 4. 发送完成信号
            yield {
                "type": "done",
                "references": references,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ 流式查询失败: {e}", exc_info=True)
            yield {"type": "error", "error": str(e)}
    
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
        logger.info("="*80)
        logger.info("📚 [步骤1] 收到用户问题")
        logger.info(f"问题内容: {question}")
        logger.info("="*80)
        try:
            # 使用query()方法，会调用LLM生成综合答案（RAG模式）
            answer = self.semantic_expert.query(question, load_pdf=True)
            
            # 同时获取检索结果以提取引用
            search_result = self.semantic_expert.search(question, top_k=n_results, with_scores=True)
            
            # 提取文献引用
            references = []
            if search_result.get('success') and search_result.get('documents'):
                for doc in search_result['documents'][:5]:  # 取前5篇作为引用
                    metadata = doc.get('metadata', {})
                    ref = {
                        'doi': metadata.get('DOI', metadata.get('doi', '')),
                        'title': metadata.get('title', '')
                    }
                    references.append(ref)
            
            return {
                "success": True,
                "answer": answer,
                "references": references,
                "expert_used": "literature"
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
