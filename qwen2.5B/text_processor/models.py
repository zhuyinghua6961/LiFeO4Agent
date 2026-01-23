"""
数据模型

定义文本处理过程中使用的数据结构。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any


@dataclass
class TableBlock:
    """表格块"""
    content: str                       # 原始 Markdown 表格
    start_line: int                    # 起始行号
    end_line: int                      # 结束行号
    rows: int                          # 行数
    columns: int                       # 列数
    headers: List[str]                 # 表头


@dataclass
class CleanedDocument:
    """清洗后的文档"""
    text: str                          # 清洗后的文本
    tables: List[TableBlock]           # 提取的表格
    removed_elements: Dict[str, int]   # 删除的元素统计
    original_line_count: int           # 原始行数
    cleaned_line_count: int            # 清洗后行数


@dataclass
class LocationMetadata:
    """位置元数据"""
    section_path: List[str]            # 章节路径 ["1. Introduction", "1.1 Background"]
    section_id: str                    # 章节 ID
    paragraph_index: int               # 段落索引
    sentence_index: int                # 句子索引
    line_range: Tuple[int, int]        # 行号范围
    page_reference: Optional[str]      # 页码引用


@dataclass
class SentenceWithLocation:
    """带位置信息的句子"""
    text: str                          # 句子文本
    location: LocationMetadata         # 位置元数据
    sentence_type: str                 # 句子类型: "text" | "table"


@dataclass
class SectionNode:
    """章节节点"""
    title: str                         # 章节标题
    level: int                         # 层级 (1-6)
    id: str                            # 章节 ID
    children: List['SectionNode']      # 子章节
    start_line: int                    # 起始行号
    end_line: int                      # 结束行号


@dataclass
class SectionTree:
    """章节树"""
    root: SectionNode                  # 根节点
    flat_list: List[SectionNode]       # 扁平化列表


@dataclass
class SentenceEntry:
    """句子条目"""
    id: str                            # 唯一 ID
    text: str                          # 句子文本
    keywords: List[str]                # 关键词
    location: LocationMetadata         # 位置信息


@dataclass
class TableEntry:
    """表格条目"""
    id: str                            # 唯一 ID
    content: str                       # 表格内容
    keywords: List[str]                # 关键词
    location: LocationMetadata         # 位置信息
    metadata: Dict[str, Any]           # 表格元数据


@dataclass
class ProcessingStats:
    """处理统计"""
    total_sentences: int = 0           # 总句子数
    total_tables: int = 0              # 总表格数
    successful_extractions: int = 0    # 成功提取数
    failed_extractions: int = 0        # 失败提取数
    processing_time: float = 0.0       # 处理时间


@dataclass
class ProcessedData:
    """处理后的数据"""
    source_file: str                   # 源文件名
    document_title: str                # 文档标题
    sentences: List[SentenceEntry]     # 句子条目列表
    tables: List[TableEntry]           # 表格条目列表
    processing_stats: ProcessingStats  # 处理统计
