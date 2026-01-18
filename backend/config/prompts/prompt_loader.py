"""
提示词加载器
"""
import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PromptLoader:
    """提示词模板加载器"""
    
    def __init__(self, prompts_dir: Optional[str] = None):
        """
        初始化提示词加载器
        
        Args:
            prompts_dir: 提示词文件目录，默认在 config/prompts
        """
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent
        self.prompts_dir = Path(prompts_dir)
        self._cache = {}
    
    def load(self, filename: str) -> str:
        """
        加载提示词文件
        
        Args:
            filename: 文件名（如 system_prompt.txt）
            
        Returns:
            提示词内容
        """
        # 检查缓存
        if filename in self._cache:
            return self._cache[filename]
        
        filepath = self.prompts_dir / filename
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            self._cache[filename] = content
            logger.info(f"✅ 加载提示词文件: {filename}")
            return content
        except FileNotFoundError:
            logger.error(f"❌ 未找到提示词文件: {filepath}")
            raise
        except Exception as e:
            logger.error(f"❌ 加载提示词文件失败: {filename}, {e}")
            raise
    
    def load_with_fallback(self, primary: str, fallback: str) -> str:
        """
        加载提示词，优先使用主文件，失败时使用备用文件
        
        Args:
            primary: 主文件名
            fallback: 备用文件名
            
        Returns:
            提示词内容
        """
        try:
            return self.load(primary)
        except FileNotFoundError:
            logger.warning(f"⚠️ 未找到 {primary}，使用备用文件 {fallback}")
            return self.load(fallback)
    
    def load_system_prompt(self) -> str:
        """加载系统提示词（Cypher查询生成）"""
        return self.load("system_prompt.txt")
    
    def load_synthesis_prompt(self) -> str:
        """加载答案合成提示词"""
        return self.load_with_fallback("synthesis_prompt_v3.txt", "synthesis_prompt.txt")
    
    def load_semantic_synthesis_prompt(self) -> str:
        """加载语义搜索答案合成提示词"""
        return self.load_with_fallback("semantic_synthesis_prompt_v2.txt", "semantic_synthesis_prompt.txt")
    
    def load_broad_question_prompt(self) -> str:
        """加载宽泛问题合成提示词"""
        try:
            return self.load("broad_question_synthesis_prompt.txt")
        except FileNotFoundError:
            logger.warning("⚠️ 宽泛问题合成提示词未找到，将使用内嵌版本")
            return None
    
    def load_hybrid_synthesis_prompt(self) -> str:
        """加载混合增强型答案合成提示词"""
        return self.load("hybrid_synthesis_prompt.txt")
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        logger.info("🧹 提示词缓存已清空")


# 创建全局提示词加载器实例
prompt_loader = PromptLoader()
