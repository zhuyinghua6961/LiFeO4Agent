"""
JSON 生成器

将处理后的数据生成结构化的 JSON 输出。
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from text_processor.models import (
    ProcessedData,
    SentenceEntry,
    TableEntry,
    LocationMetadata,
    ProcessingStats
)

logger = logging.getLogger(__name__)


class JSONGenerator:
    """JSON 生成器"""
    
    def __init__(self, indent: int = 2, encoding: str = 'utf-8'):
        """
        初始化 JSON 生成器
        
        Args:
            indent: JSON 缩进空格数
            encoding: 文件编码
        """
        self.indent = indent
        self.encoding = encoding
    
    def generate_id(
        self,
        doc_id: str,
        section_id: str,
        paragraph_index: int,
        sentence_index: int
    ) -> str:
        """
        生成唯一 ID
        
        格式: doc_id_section_p_index_s_index
        
        Args:
            doc_id: 文档 ID
            section_id: 章节 ID
            paragraph_index: 段落索引
            sentence_index: 句子索引
            
        Returns:
            str: 唯一 ID
        """
        # 清理 section_id 中的特殊字符
        clean_section_id = section_id.replace('.', '_').replace(' ', '_')
        
        return f"{doc_id}_{clean_section_id}_p{paragraph_index}_s{sentence_index}"
    
    def format_location_metadata(self, location: LocationMetadata) -> Dict[str, Any]:
        """
        格式化位置元数据
        
        Args:
            location: 位置元数据
            
        Returns:
            Dict: 格式化后的位置信息
        """
        return {
            "section_path": location.section_path,
            "section_id": location.section_id,
            "paragraph_index": location.paragraph_index,
            "sentence_index": location.sentence_index,
            "line_range": {
                "start": location.line_range[0],
                "end": location.line_range[1]
            },
            "page_reference": location.page_reference
        }
    
    def format_sentence_entry(
        self,
        sentence: str,
        keywords: List[str],
        location: LocationMetadata,
        doc_id: str
    ) -> Dict[str, Any]:
        """
        格式化句子条目
        
        Args:
            sentence: 句子文本
            keywords: 关键词列表
            location: 位置元数据
            doc_id: 文档 ID
            
        Returns:
            Dict: 格式化后的句子条目
        """
        # 生成唯一 ID
        entry_id = self.generate_id(
            doc_id,
            location.section_id,
            location.paragraph_index,
            location.sentence_index
        )
        
        return {
            "id": entry_id,
            "type": "sentence",
            "text": sentence,
            "keywords": keywords,
            "location": self.format_location_metadata(location)
        }
    
    def format_table_entry(
        self,
        content: str,
        keywords: List[str],
        location: LocationMetadata,
        doc_id: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        格式化表格条目
        
        Args:
            content: 表格内容
            keywords: 关键词列表
            location: 位置元数据
            doc_id: 文档 ID
            metadata: 表格元数据
            
        Returns:
            Dict: 格式化后的表格条目
        """
        # 生成唯一 ID
        entry_id = self.generate_id(
            doc_id,
            location.section_id,
            location.paragraph_index,
            location.sentence_index
        )
        
        return {
            "id": entry_id,
            "type": "table",
            "content": content,
            "keywords": keywords,
            "location": self.format_location_metadata(location),
            "table_metadata": metadata
        }
    
    def add_metadata(
        self,
        output: Dict[str, Any],
        source_file: str,
        document_title: str,
        processing_stats: ProcessingStats
    ) -> Dict[str, Any]:
        """
        添加文档级元数据
        
        Args:
            output: 输出字典
            source_file: 源文件名
            document_title: 文档标题
            processing_stats: 处理统计信息
            
        Returns:
            Dict: 添加元数据后的输出
        """
        output["metadata"] = {
            "source_file": source_file,
            "document_title": document_title,
            "processing_timestamp": datetime.now().isoformat(),
            "statistics": {
                "total_sentences": processing_stats.total_sentences,
                "total_tables": processing_stats.total_tables,
                "successful_extractions": processing_stats.successful_extractions,
                "failed_extractions": processing_stats.failed_extractions,
                "processing_time_seconds": processing_stats.processing_time
            }
        }
        
        return output
    
    def generate(self, processed_data: ProcessedData) -> str:
        """
        生成 JSON 输出
        
        Args:
            processed_data: 处理后的数据
            
        Returns:
            str: JSON 字符串
        """
        # 提取文档 ID（从源文件名）
        doc_id = Path(processed_data.source_file).stem
        
        # 构建输出结构
        output = {
            "entries": []
        }
        
        # 添加句子条目
        for sentence_entry in processed_data.sentences:
            formatted_entry = self.format_sentence_entry(
                sentence_entry.text,
                sentence_entry.keywords,
                sentence_entry.location,
                doc_id
            )
            output["entries"].append(formatted_entry)
        
        # 添加表格条目
        for table_entry in processed_data.tables:
            formatted_entry = self.format_table_entry(
                table_entry.content,
                table_entry.keywords,
                table_entry.location,
                doc_id,
                table_entry.metadata
            )
            output["entries"].append(formatted_entry)
        
        # 添加元数据
        output = self.add_metadata(
            output,
            processed_data.source_file,
            processed_data.document_title,
            processed_data.processing_stats
        )
        
        # 转换为 JSON 字符串
        json_str = json.dumps(output, ensure_ascii=False, indent=self.indent)
        
        return json_str
    
    def write_to_file(
        self,
        json_str: str,
        output_path: str,
        overwrite: bool = False
    ) -> str:
        """
        写入 JSON 到文件
        
        Args:
            json_str: JSON 字符串
            output_path: 输出文件路径
            overwrite: 是否覆盖已存在的文件
            
        Returns:
            str: 实际写入的文件路径
        """
        output_file = Path(output_path)
        
        # 处理文件已存在的情况
        if output_file.exists() and not overwrite:
            # 添加时间戳后缀
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = output_file.stem
            suffix = output_file.suffix
            new_name = f"{stem}_{timestamp}{suffix}"
            output_file = output_file.parent / new_name
            logger.info(f"文件已存在，使用新文件名: {output_file}")
        
        # 确保输出目录存在
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        with open(output_file, 'w', encoding=self.encoding) as f:
            f.write(json_str)
        
        logger.info(f"JSON 输出已写入: {output_file}")
        
        return str(output_file)
    
    def generate_and_write(
        self,
        processed_data: ProcessedData,
        output_path: str,
        overwrite: bool = False
    ) -> str:
        """
        生成 JSON 并写入文件
        
        Args:
            processed_data: 处理后的数据
            output_path: 输出文件路径
            overwrite: 是否覆盖已存在的文件
            
        Returns:
            str: 实际写入的文件路径
        """
        # 生成 JSON
        json_str = self.generate(processed_data)
        
        # 写入文件
        actual_path = self.write_to_file(json_str, output_path, overwrite)
        
        return actual_path
