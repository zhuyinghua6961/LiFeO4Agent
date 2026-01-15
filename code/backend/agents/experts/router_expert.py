"""
智能路由专家 - Router Expert
功能：分析用户问题，决定调用哪个数据库/专家系统
"""
from typing import Dict, List, Any, Optional
import logging

from backend.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class RouterExpert:
    """智能路由专家 - 分析用户问题并路由到合适的专家系统"""
    
    # 专家系统说明
    EXPERTS = {
        "neo4j": {
            "name": "Neo4j知识图谱精确查询",
            "description": "用于精确的结构化数据查询，如具体数值筛选、材料属性查询",
            "strengths": [
                "精确数值查询（如振实密度>2.8）",
                "单一属性查询（如某材料的导电率）",
                "关系查询（如材料-性能关系）",
                "文献DOI查询",
                "数据统计和聚合"
            ],
            "examples": [
                "振实密度大于2.8的材料有哪些？",
                "LiFePO4的导电率是多少？",
                "使用了球磨工艺的文献有哪些？",
                "比容量最高的材料是什么？"
            ]
        },
        "literature": {
            "name": "文献语义搜索",
            "description": "用于检索相关文献和材料描述，基于语义相似度",
            "strengths": [
                "文献检索（按主题、方法、材料）",
                "材料性能概述",
                "工艺路线查找",
                "材料体系搜索",
                "模糊语义查询"
            ],
            "examples": [
                "有哪些关于高导电性LiFePO4的研究？",
                "水热合成法制备的材料文献",
                "核壳结构的磷酸铁锂材料",
                "碳包覆改性的相关研究"
            ]
        },
        "community": {
            "name": "社区摘要技术分析",
            "description": "用于深层技术分析、机制研究、关系洞察",
            "strengths": [
                "技术机制分析（如老化机制、失效机制）",
                "多因素关系分析（如性能与工艺的关系）",
                "研究趋势分析",
                "数据质量评估",
                "知识图谱结构分析"
            ],
            "examples": [
                "循环稳定性与容量衰减的关系是什么？",
                "电池老化机制的研究进展",
                "材料性能受哪些因素影响？",
                "知识图谱中的数据完整性如何？",
                "不同制备方法对性能的影响规律"
            ]
        }
    }
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        初始化路由专家
        
        Args:
            llm_service: LLM服务实例
        """
        logger.info("🧭 正在初始化智能路由专家...")
        
        self._llm = llm_service
        self._router_prompt = self._build_router_prompt()
        
        logger.info("✅ 智能路由专家初始化完成！\n")
    
    def _build_router_prompt(self) -> str:
        """构建路由系统提示词"""
        
        prompt = """你是一个智能路由专家，负责分析用户问题并决定使用哪个数据库/专家系统。

## 可用的专家系统：

### 1. neo4j - Neo4j知识图谱精确查询
**适用场景：**
- 精确数值查询（如"大于"、"小于"、"最高"、"最低"）
- 单一材料属性查询
- 结构化数据查询
- 需要准确数值的场景

**优势：**
- 精确的数值筛选和比较
- 结构化关系查询
- 快速的单点查询

**示例问题：**
- "振实密度大于2.8的材料有哪些？"
- "LiFePO4的导电率是多少？"
- "比容量最高的材料是什么？"
- "使用了球磨工艺的文献有哪些？"

---

### 2. literature - 文献语义搜索
**适用场景：**
- 文献检索和推荐
- 材料/工艺的描述性查询
- 需要综合多篇文献信息
- 模糊的语义查询

**优势：**
- 基于语义相似度的智能检索
- 可以理解复杂的自然语言描述
- 返回完整的文献摘要

**示例问题：**
- "有哪些关于高导电性LiFePO4的研究？"
- "水热合成法制备的材料有哪些文献？"
- "核壳结构的磷酸铁锂材料"
- "碳包覆改性的相关研究"

---

### 3. community - 社区摘要技术分析
**适用场景：**
- 深层技术机制分析
- 多因素关系研究
- 研究趋势和规律总结
- 数据质量和完整性评估
- 需要跨领域综合分析

**优势：**
- 提供高层次的技术洞察
- 分析因素间的关联关系
- 研究趋势和模式识别

**示例问题：**
- "循环稳定性与容量衰减的关系是什么？"
- "电池老化机制的研究进展"
- "材料性能受哪些因素影响？"
- "不同制备方法对性能的影响规律"
- "知识图谱中数据的完整性如何？"

---

## 路由决策规则：

1. **包含精确数值条件** → neo4j
   - 关键词：大于、小于、等于、最高、最低、范围
   - 示例："密度>2.5"、"最高的容量"

2. **文献检索需求** → literature
   - 关键词：文献、研究、论文、报道
   - 示例："有哪些文献"、"相关研究"

3. **机制/关系/趋势分析** → community
   - 关键词：关系、机制、影响、趋势、规律、为什么
   - 示例："...的关系"、"...如何影响"、"...的机制"

4. **模糊查询，无明确数值** → literature（默认）

5. **复杂问题** → 可以返回多个专家（按优先级排序）

---

## 输出格式要求：

请以JSON格式输出，包含以下字段：

```json
{
  "primary_expert": "neo4j|literature|community",
  "confidence": 0.0-1.0,
  "reasoning": "选择该专家的理由（1-2句话）",
  "secondary_expert": "可选的次要专家（如果需要）",
  "query_type": "问题类型标签",
  "suggested_keywords": ["关键词1", "关键词2"]
}
```

**重要提示：**
- 只返回JSON，不要其他解释
- primary_expert必须是: neo4j, literature, community 三者之一
- confidence是你对这个选择的信心（0-1之间）
- reasoning要简洁明了

现在，请分析用户的问题并返回路由决策。"""
        
        return prompt
    
    def route(self, user_question: str) -> Dict[str, Any]:
        """
        分析用户问题并路由到合适的专家系统
        
        Args:
            user_question: 用户问题
            
        Returns:
            路由决策字典
        """
        logger.info(f"🔍 分析用户问题: {user_question}")
        
        # 如果没有LLM，使用降级策略
        if self._llm is None:
            fallback_expert = self._fallback_routing(user_question)
            return {
                "success": False,
                "error": "LLM服务未初始化",
                "primary_expert": fallback_expert,
                "confidence": 0.5,
                "reasoning": "使用关键词匹配降级",
                "user_question": user_question
            }
        
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            
            messages = [
                SystemMessage(content=self._router_prompt),
                HumanMessage(content=f"用户问题：{user_question}")
            ]
            
            response = self._llm.invoke(messages)
            result_text = response.content.strip()
            
            # 提取JSON（去除可能的markdown代码块标记）
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            # 解析JSON
            import json
            routing_decision = json.loads(result_text)
            
            # 验证返回的expert是否有效
            valid_experts = ["neo4j", "literature", "community"]
            if routing_decision.get("primary_expert") not in valid_experts:
                logger.warning(f"⚠️  无效的专家选择，使用默认值")
                routing_decision["primary_expert"] = "literature"
            
            logger.info(f"✅ 路由决策: {routing_decision['primary_expert']} "
                       f"(置信度: {routing_decision.get('confidence', 0):.2f})")
            logger.info(f"   理由: {routing_decision.get('reasoning', 'N/A')}")
            
            return {
                "success": True,
                "user_question": user_question,
                **routing_decision
            }
            
        except Exception as e:
            logger.error(f"❌ 路由失败: {e}")
            
            # 降级策略：使用简单的关键词匹配
            fallback_expert = self._fallback_routing(user_question)
            
            return {
                "success": False,
                "error": str(e),
                "primary_expert": fallback_expert,
                "confidence": 0.5,
                "reasoning": "API调用失败，使用关键词匹配降级",
                "user_question": user_question
            }
    
    def _fallback_routing(self, question: str) -> str:
        """
        降级路由策略（基于关键词）
        
        Args:
            question: 用户问题
            
        Returns:
            专家系统名称
        """
        question_lower = question.lower()
        
        # Neo4j关键词
        neo4j_keywords = ["大于", "小于", "等于", "最高", "最低", ">", "<", "=", "数值", "多少"]
        if any(kw in question_lower for kw in neo4j_keywords):
            return "neo4j"
        
        # Community关键词
        community_keywords = ["关系", "机制", "影响", "趋势", "规律", "为什么", "如何", "分析", "评估"]
        if any(kw in question_lower for kw in community_keywords):
            return "community"
        
        # 默认使用literature
        return "literature"
    
    def get_expert_info(self, expert_name: str) -> Dict[str, Any]:
        """
        获取专家系统的详细信息
        
        Args:
            expert_name: 专家系统名称
            
        Returns:
            专家信息字典
        """
        return self.EXPERTS.get(expert_name, {})
    
    def explain_routing(self, routing_result: Dict[str, Any]) -> str:
        """
        解释路由决策（用户友好的文本）
        
        Args:
            routing_result: 路由结果
            
        Returns:
            解释文本
        """
        if not routing_result.get("success"):
            return f"⚠️  路由失败: {routing_result.get('error')}\n使用降级策略: {routing_result['primary_expert']}"
        
        expert_name = routing_result["primary_expert"]
        expert_info = self.EXPERTS.get(expert_name, {})
        
        output = []
        output.append("🧭 智能路由分析结果")
        output.append("=" * 60)
        output.append(f"📍 推荐专家: {expert_info.get('name', expert_name)}")
        output.append(f"🎯 置信度: {routing_result.get('confidence', 0):.0%}")
        output.append(f"💡 理由: {routing_result.get('reasoning', 'N/A')}")
        
        if routing_result.get('secondary_expert'):
            sec_info = self.EXPERTS.get(routing_result['secondary_expert'], {})
            output.append(f"📌 备选专家: {sec_info.get('name', routing_result['secondary_expert'])}")
        
        if routing_result.get('query_type'):
            output.append(f"🏷️  问题类型: {routing_result['query_type']}")
        
        output.append("=" * 60)
        
        return "\n".join(output)
