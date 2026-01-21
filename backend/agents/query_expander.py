"""
查询扩展器
负责将单一查询扩展为多个查询（中文、英文、同义词）
"""
import json
import logging
import re
from typing import List, Optional, Dict
from dataclasses import dataclass
from pathlib import Path

from backend.services.llm_service import LLMService
from backend.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class QueryExpansionResult:
    """查询扩展结果"""
    original_query: str          # 原始查询
    english_query: str           # 英文查询
    synonym_query: str           # 同义词查询
    all_queries: List[str]       # 所有查询（去重）
    expansion_time: float        # 扩展耗时（秒）
    translation_method: str      # 翻译方法（llm/rule）


class QueryExpander:
    """查询扩展器类"""
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        初始化查询扩展器
        
        Args:
            llm_service: LLM服务实例，如果为None则创建新实例
        """
        self.llm_service = llm_service
        self.term_mapping: Dict[str, str] = {}
        self.synonyms: Dict[str, List[str]] = {}
        
        # 加载术语映射表
        self._load_term_mapping()
        
        # 加载同义词库
        self._load_synonyms()
        
        logger.info("✅ QueryExpander 初始化成功")
    
    def _load_term_mapping(self):
        """加载术语映射表"""
        try:
            term_mapping_path = Path(settings.term_mapping_file)
            if term_mapping_path.exists():
                with open(term_mapping_path, 'r', encoding='utf-8') as f:
                    self.term_mapping = json.load(f)
                logger.info(f"✅ 加载术语映射表: {len(self.term_mapping)} 个术语")
            else:
                logger.warning(f"⚠️ 术语映射表不存在: {term_mapping_path}")
        except Exception as e:
            logger.error(f"❌ 加载术语映射表失败: {e}")
    
    def _load_synonyms(self):
        """加载同义词库"""
        try:
            synonym_path = Path(settings.synonym_file)
            if synonym_path.exists():
                with open(synonym_path, 'r', encoding='utf-8') as f:
                    self.synonyms = json.load(f)
                logger.info(f"✅ 加载同义词库: {len(self.synonyms)} 组同义词")
            else:
                logger.warning(f"⚠️ 同义词库不存在: {synonym_path}")
        except Exception as e:
            logger.error(f"❌ 加载同义词库失败: {e}")
    
    def _contains_chinese(self, text: str) -> bool:
        """
        检测文本是否包含中文
        
        Args:
            text: 输入文本
            
        Returns:
            是否包含中文
        """
        return bool(re.search(r'[\u4e00-\u9fff]', text))
    
    def translate_to_english(self, query: str) -> tuple[str, str]:
        """
        翻译为英文
        
        Args:
            query: 原始查询
            
        Returns:
            (英文查询, 翻译方法)
        """
        # 如果不包含中文，直接返回原查询
        if not self._contains_chinese(query):
            return query, "none"
        
        # 尝试使用LLM翻译
        if self.llm_service:
            try:
                english_query = self._translate_with_llm(query)
                if english_query and english_query.strip():
                    logger.info(f"✅ LLM翻译成功: {query} -> {english_query}")
                    return english_query, "llm"
            except Exception as e:
                logger.warning(f"⚠️ LLM翻译失败: {e}，回退到规则翻译")
        
        # 回退到术语映射表
        english_query = self._translate_with_rules(query)
        logger.info(f"✅ 规则翻译: {query} -> {english_query}")
        return english_query, "rule"
    
    def _translate_with_llm(self, query: str) -> str:
        """
        使用LLM翻译
        
        Args:
            query: 中文查询
            
        Returns:
            英文查询
        """
        system_prompt = """你是一个专业的科技文献翻译助手，专注于材料科学领域。
请将用户的中文查询翻译成英文，保持专业术语的准确性。
只返回翻译结果，不要添加任何解释。"""
        
        user_prompt = f"请将以下中文查询翻译成英文：{query}"
        
        response = self.llm_service.generate(user_prompt, system_prompt)
        return response.strip()
    
    def _translate_with_rules(self, query: str) -> str:
        """
        使用规则翻译（术语映射表）
        
        Args:
            query: 中文查询
            
        Returns:
            英文查询
        """
        english_query = query
        
        # 替换已知术语
        for chinese_term, english_term in self.term_mapping.items():
            if chinese_term in english_query:
                english_query = english_query.replace(chinese_term, english_term)
        
        return english_query
    
    def generate_synonyms(self, query: str) -> str:
        """
        生成同义词查询
        
        Args:
            query: 原始查询
            
        Returns:
            同义词查询
        """
        synonym_query = query
        
        # 查找同义词
        for term, synonym_list in self.synonyms.items():
            if term in query:
                # 使用第一个同义词替换
                if synonym_list:
                    synonym_query = query.replace(term, synonym_list[0])
                    logger.info(f"✅ 找到同义词: {term} -> {synonym_list[0]}")
                    break
        
        return synonym_query
    
    def expand(self, query: str) -> QueryExpansionResult:
        """
        扩展查询
        
        Args:
            query: 原始查询
            
        Returns:
            查询扩展结果
        """
        import time
        start_time = time.time()
        
        # 1. 原始查询
        original_query = query.strip()
        
        # 2. 英文翻译
        english_query, translation_method = self.translate_to_english(original_query)
        
        # 3. 同义词查询
        synonym_query = self.generate_synonyms(original_query)
        
        # 4. 合并去重
        all_queries = [original_query]
        
        # 添加英文查询（如果不同）
        if english_query != original_query and english_query not in all_queries:
            all_queries.append(english_query)
        
        # 添加同义词查询（如果不同）
        if synonym_query != original_query and synonym_query not in all_queries:
            all_queries.append(synonym_query)
        
        # 限制查询数量
        all_queries = all_queries[:settings.max_queries]
        
        expansion_time = time.time() - start_time
        
        result = QueryExpansionResult(
            original_query=original_query,
            english_query=english_query,
            synonym_query=synonym_query,
            all_queries=all_queries,
            expansion_time=expansion_time,
            translation_method=translation_method
        )
        
        logger.info(f"✅ 查询扩展完成: {len(all_queries)} 个查询, 耗时 {expansion_time:.2f}s")
        logger.info(f"   查询列表: {all_queries}")
        
        return result
