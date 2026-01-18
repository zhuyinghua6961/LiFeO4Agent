"""
LLM服务
封装大语言模型调用
"""
from typing import Optional, Dict, Any, List, Generator
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
import logging

from backend.config.settings import settings

logger = logging.getLogger(__name__)


class LLMService:
    """LLM服务类"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        初始化LLM服务
        
        Args:
            api_key: API密钥，默认使用配置
            model: 模型名称，默认使用配置
        """
        api_key = api_key or settings.llm_api_key
        base_url = settings.llm_base_url
        model = model or settings.llm_model
        
        if not api_key:
            raise ValueError("未配置LLM API密钥")
        
        self.llm = ChatOpenAI(
            model=model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            timeout=60.0,
            max_retries=3,
            api_key=api_key,
            base_url=base_url
        )
        logger.info(f"✅ LLM服务初始化成功: {model}")
    
    def invoke(self, messages: List[BaseMessage]) -> BaseMessage:
        """
        调用LLM（同步）
        
        Args:
            messages: 消息列表
            
        Returns:
            LLM响应
        """
        return self.llm.invoke(messages)
    
    def stream(self, messages: List[BaseMessage]) -> Generator[BaseMessage, None, None]:
        """
        调用LLM（流式）
        
        Args:
            messages: 消息列表
            
        Yields:
            消息块
        """
        for chunk in self.llm.stream(messages):
            yield chunk
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        简单生成（便捷方法）
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            
        Returns:
            生成的文本
        """
        from langchain_core.messages import HumanMessage, SystemMessage
        
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        
        response = self.invoke(messages)
        return response.content
    
    @property
    def model_name(self) -> str:
        """获取模型名称"""
        return self.llm.model_name if hasattr(self.llm, 'model_name') else str(self.llm.model)


# 创建全局LLM服务实例（懒加载）
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """获取全局LLM服务实例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
