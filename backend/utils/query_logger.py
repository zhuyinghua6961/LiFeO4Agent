"""
查询失败日志记录工具
用于记录查询扩展和检索失败的案例，以便后续分析和改进
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class QueryFailureLogger:
    """查询失败日志记录器"""
    
    def __init__(self, log_file_path: str):
        """
        初始化日志记录器
        
        Args:
            log_file_path: 日志文件路径
        """
        self.log_file_path = Path(log_file_path)
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 配置标准日志
        self.logger = logging.getLogger("query_failure")
        self.logger.setLevel(logging.INFO)
        
        # 避免重复添加handler
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file_path, encoding='utf-8')
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log_translation_failure(
        self,
        original_query: str,
        error: str,
        fallback_used: bool = False
    ) -> None:
        """
        记录翻译失败
        
        Args:
            original_query: 原始查询
            error: 错误信息
            fallback_used: 是否使用了回退策略
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "translation_failure",
            "query": original_query,
            "error": error,
            "fallback_used": fallback_used
        }
        self.logger.error(json.dumps(log_entry, ensure_ascii=False))
    
    def log_synonym_failure(
        self,
        original_query: str,
        error: str
    ) -> None:
        """
        记录同义词生成失败
        
        Args:
            original_query: 原始查询
            error: 错误信息
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "synonym_failure",
            "query": original_query,
            "error": error
        }
        self.logger.error(json.dumps(log_entry, ensure_ascii=False))
    
    def log_retrieval_failure(
        self,
        query: str,
        error: str,
        query_type: str = "unknown"
    ) -> None:
        """
        记录检索失败
        
        Args:
            query: 查询文本
            error: 错误信息
            query_type: 查询类型（original/english/synonym）
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "retrieval_failure",
            "query": query,
            "query_type": query_type,
            "error": error
        }
        self.logger.error(json.dumps(log_entry, ensure_ascii=False))
    
    def log_reranking_failure(
        self,
        query: str,
        candidate_count: int,
        error: str
    ) -> None:
        """
        记录重排序失败
        
        Args:
            query: 查询文本
            candidate_count: 候选文献数量
            error: 错误信息
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "reranking_failure",
            "query": query,
            "candidate_count": candidate_count,
            "error": error
        }
        self.logger.error(json.dumps(log_entry, ensure_ascii=False))
    
    def log_empty_result(
        self,
        query: str,
        expanded_queries: Optional[list] = None
    ) -> None:
        """
        记录空结果（未找到相关文献）
        
        Args:
            query: 原始查询
            expanded_queries: 扩展后的查询列表
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "empty_result",
            "query": query,
            "expanded_queries": expanded_queries or []
        }
        self.logger.warning(json.dumps(log_entry, ensure_ascii=False))
    
    def log_performance_warning(
        self,
        operation: str,
        duration: float,
        threshold: float,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        记录性能警告
        
        Args:
            operation: 操作名称
            duration: 实际耗时（秒）
            threshold: 阈值（秒）
            details: 额外详情
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "performance_warning",
            "operation": operation,
            "duration": duration,
            "threshold": threshold,
            "details": details or {}
        }
        self.logger.warning(json.dumps(log_entry, ensure_ascii=False))
