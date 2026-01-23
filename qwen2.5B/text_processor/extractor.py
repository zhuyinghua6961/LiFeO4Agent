"""
句子提取器

负责从清洗后的文本中提取句子，追踪位置信息。
"""

import re
from typing import List, Dict, Tuple, Optional
import nltk
from nltk.tokenize import sent_tokenize

from .models import (
    CleanedDocument, 
    SentenceWithLocation, 
    LocationMetadata,
    SectionNode,
    SectionTree,
    TableBlock
)


class SentenceExtractor:
    """句子提取器"""
    
    def __init__(self, config: Dict = None):
        """
        初始化句子提取器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.min_sentence_length = self.config.get('min_sentence_length', 5)
        self.max_sentence_length = self.config.get('max_sentence_length', 100)
        
        # 确保 NLTK 数据已下载
        try:
            nltk.data.find('tokenizers/punkt_tab')
        except LookupError:
            nltk.download('punkt_tab', quiet=True)
    
    def extract(self, cleaned_doc: CleanedDocument) -> List[SentenceWithLocation]:
        """
        提取句子并记录位置
        
        Args:
            cleaned_doc: 清洗后的文档
            
        Returns:
            List[SentenceWithLocation]: 带位置信息的句子列表
        """
        # 构建章节树
        section_tree = self.track_section_hierarchy(cleaned_doc.text)
        
        # 提取句子
        sentences_with_location = []
        lines = cleaned_doc.text.split('\n')
        
        # 维护当前章节上下文栈
        section_stack = [section_tree.root]
        current_paragraph_index = 0
        current_line_number = 0
        paragraph_buffer = []
        
        for line_idx, line in enumerate(lines):
            current_line_number = line_idx
            
            # 检查是否是章节标题
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
            if heading_match:
                # 处理缓冲区中的段落
                if paragraph_buffer:
                    paragraph_text = ' '.join(paragraph_buffer)
                    paragraph_sentences = self._extract_sentences_from_paragraph(
                        paragraph_text,
                        section_stack,
                        current_paragraph_index,
                        current_line_number - len(paragraph_buffer),
                        current_line_number - 1
                    )
                    sentences_with_location.extend(paragraph_sentences)
                    paragraph_buffer = []
                    current_paragraph_index += 1
                
                # 更新章节栈
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                
                # 从扁平列表中找到对应的章节节点
                matching_section = None
                for section in section_tree.flat_list:
                    if section.title == title and section.level == level:
                        matching_section = section
                        break
                
                if matching_section:
                    # 弹出栈中层级大于等于当前层级的节点
                    while len(section_stack) > 1 and section_stack[-1].level >= level:
                        section_stack.pop()
                    section_stack.append(matching_section)
                
                continue
            
            # 检查是否是空行
            if not line.strip():
                # 处理缓冲区中的段落
                if paragraph_buffer:
                    paragraph_text = ' '.join(paragraph_buffer)
                    paragraph_sentences = self._extract_sentences_from_paragraph(
                        paragraph_text,
                        section_stack,
                        current_paragraph_index,
                        current_line_number - len(paragraph_buffer),
                        current_line_number - 1
                    )
                    sentences_with_location.extend(paragraph_sentences)
                    paragraph_buffer = []
                    current_paragraph_index += 1
                continue
            
            # 添加到段落缓冲区
            paragraph_buffer.append(line.strip())
        
        # 处理最后的段落缓冲区
        if paragraph_buffer:
            paragraph_text = ' '.join(paragraph_buffer)
            paragraph_sentences = self._extract_sentences_from_paragraph(
                paragraph_text,
                section_stack,
                current_paragraph_index,
                current_line_number - len(paragraph_buffer) + 1,
                current_line_number
            )
            sentences_with_location.extend(paragraph_sentences)
        
        return sentences_with_location
    
    def _extract_sentences_from_paragraph(
        self,
        paragraph_text: str,
        section_stack: List[SectionNode],
        paragraph_index: int,
        start_line: int,
        end_line: int
    ) -> List[SentenceWithLocation]:
        """
        从段落中提取句子
        
        Args:
            paragraph_text: 段落文本
            section_stack: 当前章节栈
            paragraph_index: 段落索引
            start_line: 起始行号
            end_line: 结束行号
            
        Returns:
            List[SentenceWithLocation]: 句子列表
        """
        sentences = self.split_sentences(paragraph_text)
        sentences_with_location = []
        
        for sent_idx, sentence in enumerate(sentences):
            # 过滤句子
            if not self._should_include_sentence(sentence):
                continue
            
            # 分配位置元数据
            location = self.assign_location_metadata(
                sentence,
                section_stack,
                paragraph_index,
                sent_idx,
                start_line,
                end_line
            )
            
            sentence_with_loc = SentenceWithLocation(
                text=sentence,
                location=location,
                sentence_type="text"
            )
            sentences_with_location.append(sentence_with_loc)
        
        return sentences_with_location
    
    def split_sentences(self, text: str) -> List[str]:
        """
        智能句子分割
        
        使用 NLTK 进行句子分割，处理缩写和小数
        
        Args:
            text: 输入文本
            
        Returns:
            List[str]: 句子列表
        """
        # 使用 NLTK 的句子分词器
        sentences = sent_tokenize(text)
        
        # 后处理：合并被错误分割的句子
        processed_sentences = []
        i = 0
        while i < len(sentences):
            sentence = sentences[i]
            
            # 检查是否以常见缩写结尾
            # NLTK 通常能处理这些，但我们添加额外的检查
            if i < len(sentences) - 1:
                # 检查下一个句子是否应该合并
                next_sentence = sentences[i + 1]
                
                # 如果当前句子以小写字母开头的下一句，可能是误分割
                if next_sentence and next_sentence[0].islower():
                    sentence = sentence + ' ' + next_sentence
                    i += 1
            
            processed_sentences.append(sentence.strip())
            i += 1
        
        return processed_sentences
    
    def track_section_hierarchy(self, text: str) -> SectionTree:
        """
        追踪章节层级
        
        解析 Markdown 标题，构建章节树结构
        
        Args:
            text: 输入文本
            
        Returns:
            SectionTree: 章节树
        """
        lines = text.split('\n')
        
        # 创建根节点
        root = SectionNode(
            title="Document Root",
            level=0,
            id="root",
            children=[],
            start_line=0,
            end_line=len(lines) - 1
        )
        
        # 维护节点栈
        stack = [root]
        flat_list = []
        section_counter = {}
        
        for line_idx, line in enumerate(lines):
            # 匹配 Markdown 标题
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                
                # 生成章节 ID
                if level not in section_counter:
                    section_counter[level] = 0
                section_counter[level] += 1
                
                # 重置更深层级的计数器
                for l in range(level + 1, 7):
                    if l in section_counter:
                        section_counter[l] = 0
                
                section_id = f"section_{level}_{section_counter[level]}"
                
                # 创建新节点
                node = SectionNode(
                    title=title,
                    level=level,
                    id=section_id,
                    children=[],
                    start_line=line_idx,
                    end_line=len(lines) - 1  # 暂时设置为文档末尾
                )
                
                # 弹出栈中层级大于等于当前层级的节点
                while len(stack) > 1 and stack[-1].level >= level:
                    popped = stack.pop()
                    popped.end_line = line_idx - 1
                
                # 将新节点添加到父节点的子节点列表
                stack[-1].children.append(node)
                stack.append(node)
                flat_list.append(node)
        
        # 关闭所有剩余的节点
        while len(stack) > 1:
            popped = stack.pop()
            popped.end_line = len(lines) - 1
        
        return SectionTree(root=root, flat_list=flat_list)
    
    def assign_location_metadata(
        self,
        sentence: str,
        section_stack: List[SectionNode],
        paragraph_index: int,
        sentence_index: int,
        start_line: int,
        end_line: int
    ) -> LocationMetadata:
        """
        为句子分配位置信息
        
        Args:
            sentence: 句子文本
            section_stack: 当前章节栈
            paragraph_index: 段落索引
            sentence_index: 句子索引
            start_line: 起始行号
            end_line: 结束行号
            
        Returns:
            LocationMetadata: 位置元数据
        """
        # 构建章节路径（排除根节点）
        section_path = [node.title for node in section_stack[1:]]
        
        # 获取当前章节 ID
        section_id = section_stack[-1].id if len(section_stack) > 1 else "root"
        
        # 尝试从句子中提取页码引用
        page_reference = self._extract_page_reference(sentence)
        
        return LocationMetadata(
            section_path=section_path,
            section_id=section_id,
            paragraph_index=paragraph_index,
            sentence_index=sentence_index,
            line_range=(start_line, end_line),
            page_reference=page_reference
        )
    
    def _extract_page_reference(self, sentence: str) -> Optional[str]:
        """
        从句子中提取页码引用
        
        尝试从图片占位符或其他标记中推断页码
        
        Args:
            sentence: 句子文本
            
        Returns:
            Optional[str]: 页码引用，如果找不到则返回 None
        """
        # 查找类似 _page_X 的引用
        page_match = re.search(r'_page_(\d+)', sentence)
        if page_match:
            return f"page_{page_match.group(1)}"
        
        return None
    
    def _should_include_sentence(self, sentence: str) -> bool:
        """
        判断是否应该包含该句子
        
        过滤太短或太长的句子
        
        Args:
            sentence: 句子文本
            
        Returns:
            bool: 是否应该包含
        """
        # 计算词数
        words = sentence.split()
        word_count = len(words)
        
        # 过滤太短的句子
        if word_count < self.min_sentence_length:
            return False
        
        # 标记太长的句子（但仍然包含）
        # 在实际应用中，可能需要进一步处理
        if word_count > self.max_sentence_length:
            # 可以在这里添加日志或标记
            pass
        
        return True
