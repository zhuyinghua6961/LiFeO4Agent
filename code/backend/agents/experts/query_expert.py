"""
精确查询专家 - Query Expert
功能：基于 Neo4j 知识图谱进行精确的结构化数据查询
"""
from typing import Dict, List, Any, Optional, Tuple
import logging
import os
import json
import re

from backend.services.llm_service import LLMService
from backend.services.neo4j_service import Neo4jService
from backend.utils.pdf_loader import PDFManager

logger = logging.getLogger(__name__)


class QueryExpert:
    """精确查询专家 - 处理需要精确数值比较的查询"""
    
    def __init__(
        self, 
        neo4j_service: Neo4jService,
        llm_service: Optional[LLMService] = None
    ):
        """
        初始化精确查询专家
        
        Args:
            neo4j_service: Neo4j服务实例
            llm_service: LLM服务实例（用于生成Cypher查询）
        """
        self._neo4j = neo4j_service
        self._llm = llm_service
        
        # 加载prompt模板
        self._cypher_prompt = self._load_prompt("system_prompt.txt")
        self._synthesis_prompt = self._load_prompt("synthesis_prompt_v3.txt")
        
        # 初始化PDF管理器
        from backend.config.settings import settings
        self._pdf_manager = PDFManager(
            papers_dir=settings.papers_dir,
            mapping_file=settings.doi_to_pdf_mapping
        ) if hasattr(settings, 'papers_dir') else None
        
        logger.info("🎯 精确查询专家初始化完成")
    
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
                return self._build_cypher_prompt() if filename == "system_prompt.txt" else ""
        except Exception as e:
            logger.error(f"加载prompt失败 ({filename}): {e}")
            return self._build_cypher_prompt() if filename == "system_prompt.txt" else ""
    
    def _build_cypher_prompt(self) -> str:
        """构建Cypher查询生成提示词"""
        return """你是一个Cypher查询生成专家。你的任务是将用户关于材料的问题转换为精确的Cypher查询。

## Neo4j 知识图谱结构

节点类型：
- Material：材料节点，包含以下属性：
  - material_name: 材料名称（包含DOI）
  - tap_density: 振实密度
  - compaction_density: 压实密度
  - discharge_capacity: 放电容量
  - coulombic_efficiency: 库伦效率
  - synthesis_method: 合成方法
  - preparation_method: 制备方法
  - precursor: 前驱体
  - carbon_source: 碳源
  - carbon_content: 碳含量
  - coating_material: 包覆材料
  - particle_size: 粒径
  - surface_area: 比表面积
  - cycling_stability: 循环稳定性
  - conductivity: 导电性

## 查询规则

1. **数值比较查询**：
   - "大于X" → `WHERE m.property > X`
   - "小于X" → `WHERE m.property < X`
   - "等于X" → `WHERE m.property = X`
   - "最高/最大" → `ORDER BY m.property DESC LIMIT 1`

2. **文本包含查询**：
   - 使用 "CONTAINS" 进行模糊匹配
   - 示例：`WHERE m.synthesis_method CONTAINS '球磨'`

3. **单位处理**：
   - 注意密度单位（mg/cm³, g/cm³ 等）
   - 对于密度查询，确保正确处理单位

4. **返回格式**：
   - 只需要返回材料的相关属性
   - 不要返回过多无关属性

## 输出要求

只返回Cypher查询代码，不要其他解释。如果无法生成查询，返回空字符串。

示例：
- 输入："振实密度大于2.8的材料有哪些？"
- 输出：
```cypher
MATCH (m:Material)
WHERE m.tap_density > 2.8
RETURN m.material_name, m.tap_density, m.compaction_density, m.discharge_capacity
ORDER BY m.tap_density DESC
```
"""
    
    def can_handle(self, question: str) -> bool:
        """
        判断是否适合使用精确查询
        
        Args:
            question: 用户问题
            
        Returns:
            True=适合精确查询, False=不适合
        """
        question_lower = question.lower()
        
        # 精确查询关键词
        precise_keywords = [
            "大于", "小于", "等于", "高于", "低于",
            "最高", "最低", "最大", "最小",
            ">=", "<=", ">", "<", "=",
            "哪些", "哪个", "多少", "数值",
            "密度", "容量", "导电率", "粒径"
        ]
        
        return any(kw in question_lower for kw in precise_keywords)
    
    def generate_cypher(self, question: str) -> str:
        """
        生成Cypher查询语句
        
        Args:
            question: 用户问题
            
        Returns:
            Cypher查询语句
        """
        if self._llm is None:
            # 使用规则生成简单查询
            return self._generate_simple_cypher(question)
        
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            
            messages = [
                SystemMessage(content=self._cypher_prompt),
                HumanMessage(content=f"用户问题：{question}")
            ]
            
            response = self._llm.invoke(messages)
            cypher = response.content.strip()
            
            # 提取代码块中的Cypher
            if "```cypher" in cypher:
                cypher = cypher.split("```cypher")[1].split("```")[0].strip()
            elif "```" in cypher:
                cypher = cypher.split("```")[1].split("```")[0].strip()
            
            return cypher
            
        except Exception as e:
            logger.error(f"生成Cypher失败: {e}")
            return self._generate_simple_cypher(question)
    
    def _generate_simple_cypher(self, question: str) -> str:
        """
        使用规则生成简单的Cypher查询
        
        Args:
            question: 用户问题
            
        Returns:
            Cypher查询语句
        """
        question_lower = question.lower()
        
        # 提取属性名
        property_map = {
            "振实密度": "tap_density",
            "压实密度": "compaction_density",
            "放电容量": "discharge_capacity",
            "比容量": "discharge_capacity",
            "容量": "discharge_capacity",
            "导电率": "conductivity",
            "导电性": "conductivity",
            "库伦效率": "coulombic_efficiency",
            "粒径": "particle_size",
            "比表面积": "surface_area",
            "循环稳定性": "cycling_stability",
            "碳含量": "carbon_content"
        }
        
        property_name = None
        for cn_name, en_name in property_map.items():
            if cn_name in question:
                property_name = en_name
                break
        
        if property_name is None:
            return ""
        
        # 提取比较操作符
        comparison = ">"
        if "小于" in question_lower or "低于" in question_lower or "<" in question:
            comparison = "<"
        elif "等于" in question_lower or "=" in question:
            comparison = "="
        
        # 提取数值
        import re
        number_match = re.search(r'[\d.]+', question)
        if number_match:
            value = number_match.group()
        else:
            return ""
        
        # 生成Cypher
        cypher = f"""
MATCH (m:Material)
WHERE m.{property_name} IS NOT NULL AND m.{property_name} {comparison} {value}
RETURN m.material_name, m.{property_name}
ORDER BY m.{property_name} DESC
"""
        
        return cypher.strip()
    
    def execute_query(self, question: str) -> Dict[str, Any]:
        """
        执行精确查询
        
        Args:
            question: 用户问题
            
        Returns:
            查询结果
        """
        if not self.can_handle(question):
            return {
                "success": False,
                "error": "问题不适合精确查询",
                "expert": "query"
            }
        
        try:
            # 生成Cypher查询
            cypher = self.generate_cypher(question)
            
            if not cypher:
                return {
                    "success": False,
                    "error": "无法生成查询语句",
                    "expert": "query"
                }
            
            logger.info(f"生成的Cypher查询: {cypher}")
            
            # 执行查询
            results = self._neo4j.execute_cypher(cypher)
            
            # 格式化结果
            materials = []
            for record in results:
                materials.append(dict(record))
            
            return {
                "success": True,
                "expert": "query",
                "cypher_query": cypher,
                "result_count": len(materials),
                "materials": materials[:100],  # 限制返回数量
                "question": question
            }
            
        except Exception as e:
            logger.error(f"精确查询失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "expert": "query"
            }
    
    def query_by_property(
        self, 
        property_name: str, 
        threshold: float,
        comparison: str = ">",
        limit: int = 100
    ) -> List[Dict]:
        """
        按属性查询材料（便捷方法）
        
        Args:
            property_name: 属性名
            threshold: 阈值
            comparison: 比较符
            limit: 结果限制
            
        Returns:
            材料列表
        """
        return self._neo4j.query_material(
            property_name=property_name,
            threshold=threshold,
            comparison=comparison,
            limit=limit
        )
    
    def query_by_density(
        self,
        density_type: str,
        threshold: float,
        comparison: str = ">",
        limit: int = 100
    ) -> List[Dict]:
        """
        按密度查询材料（便捷方法）
        
        Args:
            density_type: 密度类型 (tap_density, compaction_density)
            threshold: 阈值
            comparison: 比较符
            limit: 结果限制
            
        Returns:
            材料列表
        """
        return self._neo4j.query_by_density(
            density_type=density_type,
            threshold=threshold,
            comparison=comparison,
            limit=limit
        )
    
    def get_top_materials(
        self, 
        property_name: str, 
        limit: int = 10,
        ascending: bool = False
    ) -> List[Dict]:
        """
        获取属性值最高/最低的材料
        
        Args:
            property_name: 属性名
            limit: 结果数量
            ascending: 是否升序
            
        Returns:
            材料列表
        """
        return self._neo4j.get_top_materials(
            property_name=property_name,
            limit=limit,
            ascending=ascending
        )
    
    def _extract_dois(self, materials: List[Dict]) -> List[str]:
        """从材料列表中提取DOI"""
        dois = []
        for material in materials:
            material_name = material.get('material_name', '')
            doi_match = re.search(r'10\.\d+/[^\s)]+', material_name)
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
    
    def _synthesize_answer(
        self,
        user_question: str,
        query_results: List[Dict],
        pdf_contents: Optional[Dict[str, str]] = None
    ) -> str:
        """合成最终答案"""
        if not self._llm or not self._synthesis_prompt:
            return self._format_simple_answer(query_results)
        
        try:
            # 构建prompt
            query_results_json = json.dumps(query_results, ensure_ascii=False, indent=2)
            
            # 添加PDF原文
            pdf_section = ""
            if pdf_contents:
                pdf_section = "\n\n## 📄 相关论文原文摘要\n"
                for doi, content in pdf_contents.items():
                    pdf_section += f"\n### DOI: {doi}\n{content[:5000]}\n"  # 限制每篇长度
            
            prompt = self._synthesis_prompt.replace("{user_question}", user_question)
            prompt = prompt.replace("{query_results}", query_results_json)
            prompt = prompt.replace("{pdf_contents}", pdf_section if pdf_section else "无PDF原文")
            
            from langchain_core.messages import HumanMessage
            
            response = self._llm.invoke([HumanMessage(content=prompt)])
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"答案合成失败: {e}")
            return self._format_simple_answer(query_results)
    
    def _format_simple_answer(self, query_results: List[Dict]) -> str:
        """简单格式化答案（无LLM时使用）"""
        if not query_results:
            return "未找到符合条件的材料。"
        
        answer = f"找到 {len(query_results)} 条结果：\n\n"
        for i, material in enumerate(query_results[:10], 1):
            answer += f"{i}. "
            for key, value in material.items():
                if value is not None:
                    answer += f"{key}: {value}, "
            answer = answer.rstrip(", ") + "\n"
        
        if len(query_results) > 10:
            answer += f"\n... 还有 {len(query_results) - 10} 条结果未显示"
        
        return answer
    
    def query(self, question: str, load_pdf: bool = True) -> str:
        """
        执行查询并返回格式化的答案
        
        Args:
            question: 用户问题
            load_pdf: 是否加载PDF原文
            
        Returns:
            格式化的答案
        """
        result = self.execute_query(question)
        
        if not result.get('success'):
            return f"查询失败: {result.get('error', '未知错误')}"
        
        materials = result.get('materials', [])
        
        # 加载PDF原文
        pdf_contents = {}
        if load_pdf and self._pdf_manager:
            dois = self._extract_dois(materials)
            if dois:
                pdf_contents = self._load_pdf_contents(dois)
                logger.info(f"加载了 {len(pdf_contents)} 篇PDF原文")
        
        # 合成答案
        return self._synthesize_answer(question, materials, pdf_contents)
