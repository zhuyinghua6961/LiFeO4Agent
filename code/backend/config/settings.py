"""
全局配置管理
"""
import os
from dotenv import load_dotenv
from typing import Optional
from pathlib import Path
from .paths import (
    PAPERS_DIR_STR,
    VECTOR_DATABASE_PATH_STR,
    COMMUNITY_VECTOR_DB_PATH_STR,
    DOI_TO_PDF_MAPPING_STR,
)


class Settings:
    """全局配置类"""
    
    def __init__(self, config_path: str = None):
        """
        初始化配置
        
        Args:
            config_path: 配置文件路径
        """
        # 设置基础目录
        self.base_dir = Path(__file__).parent.parent
        
        if config_path is None:
            # 默认使用 backend 目录下的 config.env
            config_path = self.base_dir / "config.env"
        else:
            config_path = Path(config_path)
        load_dotenv(config_path)
        
        # Neo4j配置
        self.neo4j_url: str = os.getenv("NEO4J_URL", "bolt://localhost:7687")
        self.neo4j_username: str = os.getenv("NEO4J_USERNAME", "neo4j")
        self.neo4j_password: str = os.getenv("NEO4J_PASSWORD", "password")
        
        # LLM配置 - 阿里百炼
        self.dashscope_api_key: Optional[str] = os.getenv("DASHSCOPE_API_KEY")
        self.dashscope_base_url: str = os.getenv(
            "DASHSCOPE_BASE_URL", 
            "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.dashscope_model: str = os.getenv("DASHSCOPE_MODEL", "deepseek-v3.1")
        
        # LLM配置 - OpenAI兼容
        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.openai_base_url: Optional[str] = os.getenv("OPENAI_BASE_URL")
        self.openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o")
        
        # 向量数据库路径
        self.vector_db_path: str = os.getenv(
            "VECTOR_DB_PATH",
            VECTOR_DATABASE_PATH_STR
        )
        self.community_vector_db_path: str = os.getenv(
            "COMMUNITY_VECTOR_DB_PATH",
            COMMUNITY_VECTOR_DB_PATH_STR
        )
        
        # BGE模型配置
        self.bge_model_path: str = os.getenv(
            "BGE_MODEL_PATH",
            "/home/研究生/研一下/bge-3/BGE"
        )
        self.bge_api_url: str = os.getenv(
            "BGE_API_URL",
            "http://172.18.8.31:8001/v1/embeddings"
        )
        
        # PDF存储路径
        self.papers_dir: str = os.getenv(
            "PAPERS_DIR",
            PAPERS_DIR_STR
        )
        
        # DOI到PDF映射文件路径
        self.doi_to_pdf_mapping: str = os.getenv(
            "DOI_TO_PDF_MAPPING",
            DOI_TO_PDF_MAPPING_STR
        )
        
        # 其他配置
        self.llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.5"))
        self.llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))
        self.similarity_threshold_broad: float = float(os.getenv("SIMILARITY_THRESHOLD_BROAD", "0.3"))
        self.similarity_threshold_precise: float = float(os.getenv("SIMILARITY_THRESHOLD_PRECISE", "0.3"))
        
        # API 服务配置
        self.api_host: str = os.getenv("API_HOST", "0.0.0.0")
        self.api_port: int = int(os.getenv("API_PORT", "8000"))
        self.debug: bool = os.getenv("DEBUG", "False").lower() == "true"
        
        # MySQL配置
        self.mysql_host: str = os.getenv("MYSQL_HOST", "localhost")
        self.mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
        self.mysql_user: str = os.getenv("MYSQL_USER", "root")
        self.mysql_password: str = os.getenv("MYSQL_PASSWORD", "")
        self.mysql_database: str = os.getenv("MYSQL_DATABASE", "material_kb")
        
        # JWT配置
        self.jwt_secret: str = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
        self.jwt_expire: int = int(os.getenv("JWT_EXPIRE", "86400"))  # 24小时
        
    @property
    def llm_api_key(self) -> Optional[str]:
        """获取LLM API密钥（优先使用阿里百炼）"""
        return self.dashscope_api_key or self.openai_api_key
    
    @property
    def llm_base_url(self) -> Optional[str]:
        """获取LLM基础URL"""
        if self.dashscope_api_key:
            return self.dashscope_base_url
        return self.openai_base_url
    
    @property
    def llm_model(self) -> str:
        """获取LLM模型"""
        if self.dashscope_api_key:
            return self.dashscope_model
        return self.openai_model


# 全局配置实例
settings = Settings()
