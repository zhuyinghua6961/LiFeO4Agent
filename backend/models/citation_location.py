"""
引用位置数据模型
用于存储文献引用的精确位置信息
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class CitationLocation:
    """
    引用位置信息
    
    包含从句子级和段落级数据库获取的完整位置信息，
    用于在PDF阅读器中精确定位引用来源。
    """
    
    # 基本信息
    doi: str                           # 文献DOI
    answer_sentence: str               # 答案中的句子
    answer_sentence_index: int         # 句子在答案中的索引（从0开始）
    
    # 原文信息
    source_text: str                   # 原文片段
    page: int                          # 页码
    similarity: float                  # 相似度分数 [0, 1]
    
    # 可选信息
    keywords: List[str] = field(default_factory=list)  # 关键词列表
    sentence_index: Optional[int] = None               # 句子在原文中的索引（从句子级数据库）
    has_number: Optional[bool] = None                  # 是否包含数值（从句子级数据库）
    has_unit: Optional[bool] = None                    # 是否包含单位（从句子级数据库）
    confidence: str = "medium"                         # 置信度等级 (high/medium/low)
    chunk_index_in_page: Optional[int] = None          # 页内段落索引（从段落级数据库）
    chunk_index_global: Optional[int] = None           # 全局段落索引（从段落级数据库）
    
    def __post_init__(self):
        """验证数据有效性"""
        # 验证相似度范围
        if not 0 <= self.similarity <= 1:
            raise ValueError(f"相似度必须在[0, 1]范围内，当前值: {self.similarity}")
        
        # 验证页码
        if self.page < 0:
            raise ValueError(f"页码必须为正整数，当前值: {self.page}")
        
        # 验证答案句子索引
        if self.answer_sentence_index < 0:
            raise ValueError(f"答案句子索引必须为非负整数，当前值: {self.answer_sentence_index}")
        
        # 验证置信度等级
        if self.confidence not in ["high", "medium", "low"]:
            raise ValueError(f"置信度等级必须为 high/medium/low，当前值: {self.confidence}")
        
        # 根据相似度自动设置置信度（如果未明确指定）
        if self.confidence == "medium":  # 默认值
            if self.similarity > 0.75:
                self.confidence = "high"
            elif self.similarity > 0.5:
                self.confidence = "medium"
            else:
                self.confidence = "low"
    
    @classmethod
    def from_sentence_db(
        cls,
        doi: str,
        answer_sentence: str,
        answer_sentence_index: int,
        sentence_text: str,
        sentence_metadata: Dict[str, Any],
        similarity: float,
        page: int = 0,  # 需要从段落级数据库获取
        keywords: Optional[List[str]] = None
    ) -> "CitationLocation":
        """
        从句子级数据库的查询结果创建CitationLocation
        
        Args:
            doi: 文献DOI
            answer_sentence: 答案中的句子
            answer_sentence_index: 句子在答案中的索引
            sentence_text: 原文句子
            sentence_metadata: 句子级数据库的metadata
            similarity: 相似度分数
            page: 页码（需要从段落级数据库获取）
            keywords: 关键词列表
            
        Returns:
            CitationLocation实例
        """
        return cls(
            doi=doi,
            answer_sentence=answer_sentence,
            answer_sentence_index=answer_sentence_index,
            source_text=sentence_text,
            page=page,
            similarity=similarity,
            keywords=keywords or [],
            sentence_index=sentence_metadata.get("sentence_index"),
            has_number=sentence_metadata.get("has_number"),
            has_unit=sentence_metadata.get("has_unit")
        )
    
    @classmethod
    def from_paragraph_db(
        cls,
        doi: str,
        answer_sentence: str,
        answer_sentence_index: int,
        paragraph_text: str,
        paragraph_metadata: Dict[str, Any],
        similarity: float,
        keywords: Optional[List[str]] = None
    ) -> "CitationLocation":
        """
        从段落级数据库的查询结果创建CitationLocation
        
        Args:
            doi: 文献DOI
            answer_sentence: 答案中的句子
            answer_sentence_index: 句子在答案中的索引
            paragraph_text: 原文段落
            paragraph_metadata: 段落级数据库的metadata
            similarity: 相似度分数
            keywords: 关键词列表
            
        Returns:
            CitationLocation实例
        """
        return cls(
            doi=doi,
            answer_sentence=answer_sentence,
            answer_sentence_index=answer_sentence_index,
            source_text=paragraph_text[:500],  # 限制长度
            page=paragraph_metadata.get("page", 0),
            similarity=similarity,
            keywords=keywords or [],
            chunk_index_in_page=paragraph_metadata.get("chunk_index_in_page"),
            chunk_index_global=paragraph_metadata.get("chunk_index_global")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式（用于JSON序列化）
        
        Returns:
            字典格式的引用位置信息
        """
        return {
            "doi": self.doi,
            "answer_sentence": self.answer_sentence,
            "answer_sentence_index": self.answer_sentence_index,
            "source_text": self.source_text,
            "page": self.page,
            "similarity": round(self.similarity, 4),
            "keywords": self.keywords,
            "sentence_index": self.sentence_index,
            "has_number": self.has_number,
            "has_unit": self.has_unit,
            "confidence": self.confidence,
            "chunk_index_in_page": self.chunk_index_in_page,
            "chunk_index_global": self.chunk_index_global
        }
    
    def get_display_location(self) -> str:
        """
        获取用于显示的位置描述
        
        Returns:
            位置描述字符串，例如："第5页第2段"
        """
        if self.chunk_index_in_page is not None:
            # 从0开始的索引转换为从1开始的显示
            return f"第{self.page}页第{self.chunk_index_in_page + 1}段"
        else:
            return f"第{self.page}页"
    
    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"CitationLocation(doi={self.doi}, "
            f"page={self.page}, "
            f"similarity={self.similarity:.3f}, "
            f"confidence={self.confidence})"
        )
