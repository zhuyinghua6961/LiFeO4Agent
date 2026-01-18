"""
社区摘要专家 - Community Expert
功能：基于社区摘要向量数据库进行技术分析和关系洞察
"""
from typing import Dict, List, Any, Optional
import logging

from backend.services.llm_service import LLMService
from backend.repositories.vector_repository import CommunityVectorRepository

logger = logging.getLogger(__name__)


class CommunityExpert:
    """社区摘要专家 - 处理技术机制分析、多因素关系研究等"""
    
    def __init__(
        self, 
        community_repo: Optional[CommunityVectorRepository] = None,
        llm_service: Optional[LLMService] = None
    ):
        """
        初始化社区摘要专家
        
        Args:
            community_repo: 社区向量数据库仓储
            llm_service: LLM服务实例
        """
        self._community_repo = community_repo or CommunityVectorRepository()
        self._llm = llm_service
        
        logger.info("🏘️ 社区摘要专家初始化完成")
    
    def can_handle(self, question: str) -> bool:
        """
        判断是否适合使用社区摘要分析
        
        Args:
            question: 用户问题
            
        Returns:
            True=适合社区分析, False=不适合
        """
        question_lower = question.lower()
        
        # 技术分析类关键词
        technical_keywords = [
            "机制", "mechanism", "关系", "relationship",
            "影响", "impact", "趋势", "trend",
            "规律", "pattern", "分析", "analysis",
            "为什么", "why", "如何", "how",
            "研究进展", "progress", "发展", "development"
        ]
        
        return any(kw in question_lower for kw in technical_keywords)
    
    def search(
        self,
        query: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        搜索社区摘要
        
        Args:
            query: 搜索查询
            top_k: 返回数量
            
        Returns:
            搜索结果
        """
        try:
            results = self._community_repo.search(
                query=query,
                n_results=top_k
            )
            
            if not results.get("success"):
                return {
                    "success": False,
                    "error": results.get("error", "社区搜索失败"),
                    "documents": [],
                    "metadatas": [],
                    "distances": []
                }
            
            return {
                "success": True,
                "query_type": "community_analysis",
                "documents": results.get("documents", []),
                "metadatas": results.get("metadatas", []),
                "distances": results.get("distances", []),
                "result_count": len(results.get("documents", []))
            }
            
        except Exception as e:
            logger.error(f"社区搜索失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "documents": [],
                "metadatas": [],
                "distances": []
            }
    
    def analyze(
        self,
        query: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        综合分析（搜索 + LLM 合成）
        
        Args:
            query: 分析查询
            top_k: 检索数量
            
        Returns:
            分析结果
        """
        # 1. 搜索社区摘要
        search_results = self.search(query, top_k)
        
        if not search_results.get("success"):
            return search_results
        
        # 2. 使用 LLM 合成答案（如果有 LLM 服务）
        if self._llm and search_results.get("documents"):
            try:
                # 格式化社区摘要
                formatted_summaries = []
                for i, (doc, metadata) in enumerate(zip(
                    search_results["documents"],
                    search_results["metadatas"]
                ), 1):
                    summary_text = f"""
社区摘要 {i}:
  - 级别: {metadata.get('level', 'Unknown')}
  - 实体数: {len(metadata.get('entities', []))}
  - 内容: {doc}
"""
                    formatted_summaries.append(summary_text)
                
                summaries_text = "\n".join(formatted_summaries)
                
                # 构建提示词
                prompt = f"""基于以下社区摘要，回答用户的问题。

【用户问题】
{query}

【社区摘要信息】
{summaries_text}

请提供深入的技术分析和洞察。"""
                
                from langchain_core.messages import HumanMessage, SystemMessage
                messages = [
                    SystemMessage(content="你是一个材料科学技术分析专家，擅长从社区级别的知识中提取洞察。"),
                    HumanMessage(content=prompt)
                ]
                
                answer = self._llm.invoke(messages).content
                
                search_results["final_answer"] = answer
                
            except Exception as e:
                logger.error(f"LLM 合成答案失败: {e}")
                search_results["llm_error"] = str(e)
        
        return search_results
