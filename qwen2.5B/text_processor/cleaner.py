"""
Markdown 清洗器

负责清洗科学论文 Markdown 文件，删除不需要的元素，保留有意义的内容。
"""

import re
from typing import List, Dict, Tuple
from .models import CleanedDocument, TableBlock


class MarkdownCleaner:
    """Markdown 清洗器"""
    
    def __init__(self, config: Dict = None):
        """
        初始化清洗器
        
        Args:
            config: 清洗配置字典
        """
        self.config = config or {}
        self.remove_images_enabled = self.config.get('remove_images', True)
        self.convert_html_enabled = self.config.get('convert_html', True)
        self.remove_metadata_enabled = self.config.get('remove_metadata', True)
        self.preserve_tables_enabled = self.config.get('preserve_tables', True)
        self.preserve_citations_enabled = self.config.get('preserve_citations', True)
    
    def clean(self, markdown_text: str) -> CleanedDocument:
        """
        清洗 markdown 文本
        
        Args:
            markdown_text: 原始 markdown 文本
            
        Returns:
            CleanedDocument: 清洗后的文档对象
        """
        original_line_count = len(markdown_text.split('\n'))
        removed_elements = {
            'images': 0,
            'metadata_lines': 0,
            'html_tags': 0
        }
        
        # 提取表格（在清洗之前）
        tables = []
        if self.preserve_tables_enabled:
            tables = self.identify_tables(markdown_text)
        
        # 执行清洗步骤
        text = markdown_text
        
        if self.remove_images_enabled:
            text, img_count = self.remove_images(text)
            removed_elements['images'] = img_count
        
        if self.convert_html_enabled:
            text, html_count = self.convert_html_tags(text)
            removed_elements['html_tags'] = html_count
        
        if self.remove_metadata_enabled:
            text, meta_count = self.remove_metadata(text)
            removed_elements['metadata_lines'] = meta_count
        
        cleaned_line_count = len(text.split('\n'))
        
        return CleanedDocument(
            text=text,
            tables=tables,
            removed_elements=removed_elements,
            original_line_count=original_line_count,
            cleaned_line_count=cleaned_line_count
        )
    
    def remove_images(self, text: str) -> Tuple[str, int]:
        """
        删除图片占位符
        
        删除匹配模式 ![](_page_*) 的图片引用
        
        Args:
            text: 输入文本
            
        Returns:
            Tuple[str, int]: (清洗后的文本, 删除的图片数量)
        """
        # 匹配 ![](_page_*) 格式的图片占位符
        pattern = r'!\[\]\(_page_[^)]*\)'
        
        # 计算匹配数量
        matches = re.findall(pattern, text)
        count = len(matches)
        
        # 删除图片占位符
        cleaned_text = re.sub(pattern, '', text)
        
        return cleaned_text, count
    
    def convert_html_tags(self, text: str) -> Tuple[str, int]:
        """
        转换 HTML 标签为纯文本等效形式
        
        转换 <sub>, <sup> 等标签，保留科学记号
        
        Args:
            text: 输入文本
            
        Returns:
            Tuple[str, int]: (转换后的文本, 转换的标签数量)
        """
        count = 0
        
        # 转换下标 <sub>text</sub> -> _{text}
        sub_pattern = r'<sub>(.*?)</sub>'
        sub_matches = re.findall(sub_pattern, text, re.IGNORECASE)
        count += len(sub_matches)
        text = re.sub(sub_pattern, r'_{\1}', text, flags=re.IGNORECASE)
        
        # 转换上标 <sup>text</sup> -> ^{text}
        sup_pattern = r'<sup>(.*?)</sup>'
        sup_matches = re.findall(sup_pattern, text, re.IGNORECASE)
        count += len(sup_matches)
        text = re.sub(sup_pattern, r'^{\1}', text, flags=re.IGNORECASE)
        
        # 转换斜体 <i>text</i> 或 <em>text</em> -> *text*
        i_pattern = r'<i>(.*?)</i>'
        i_matches = re.findall(i_pattern, text, re.IGNORECASE)
        count += len(i_matches)
        text = re.sub(i_pattern, r'*\1*', text, flags=re.IGNORECASE)
        
        em_pattern = r'<em>(.*?)</em>'
        em_matches = re.findall(em_pattern, text, re.IGNORECASE)
        count += len(em_matches)
        text = re.sub(em_pattern, r'*\1*', text, flags=re.IGNORECASE)
        
        # 转换粗体 <b>text</b> 或 <strong>text</strong> -> **text**
        b_pattern = r'<b>(.*?)</b>'
        b_matches = re.findall(b_pattern, text, re.IGNORECASE)
        count += len(b_matches)
        text = re.sub(b_pattern, r'**\1**', text, flags=re.IGNORECASE)
        
        strong_pattern = r'<strong>(.*?)</strong>'
        strong_matches = re.findall(strong_pattern, text, re.IGNORECASE)
        count += len(strong_matches)
        text = re.sub(strong_pattern, r'**\1**', text, flags=re.IGNORECASE)
        
        return text, count
    
    def remove_metadata(self, text: str) -> Tuple[str, int]:
        """
        删除期刊元数据和作者信息
        
        删除常见的元数据块，如作者单位、期刊信息、文章信息等
        
        Args:
            text: 输入文本
            
        Returns:
            Tuple[str, int]: (清洗后的文本, 删除的行数)
        """
        lines = text.split('\n')
        cleaned_lines = []
        removed_count = 0
        
        # 元数据关键词模式
        metadata_patterns = [
            r'^#+\s*(abstract|keywords?|author|affiliation|correspondence|received|accepted|published|doi|copyright|license|citation)',
            r'^\*+\s*(correspondence|email|tel|fax):',
            r'^(author|affiliation|email|correspondence|tel|fax|address):',  # 添加简单的键值对模式
            r'^©\s*\d{4}',  # 版权符号
            r'^published\s+by',
            r'^journal\s+of',
            r'^volume\s+\d+',
            r'^issue\s+\d+',
            r'^pages?\s+\d+',
            r'^issn',
            r'^e-?issn',
        ]
        
        in_metadata_block = False
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # 检查是否是元数据行
            is_metadata = False
            for pattern in metadata_patterns:
                if re.match(pattern, line_lower, re.IGNORECASE):
                    is_metadata = True
                    in_metadata_block = True
                    break
            
            # 如果在元数据块中，继续跳过直到遇到空行或新章节
            if in_metadata_block:
                if line.strip() == '' or re.match(r'^#+\s+\d+\.?\s+', line):
                    in_metadata_block = False
                    cleaned_lines.append(line)
                else:
                    removed_count += 1
                    continue
            
            if not is_metadata:
                cleaned_lines.append(line)
            else:
                removed_count += 1
        
        return '\n'.join(cleaned_lines), removed_count
    
    def identify_tables(self, text: str) -> List[TableBlock]:
        """
        识别 Markdown 表格
        
        识别并提取表格的行列信息，保留表格的完整结构
        
        Args:
            text: 输入文本
            
        Returns:
            List[TableBlock]: 表格块列表
        """
        lines = text.split('\n')
        tables = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # 检查是否是表格分隔行（如 |---|---|）
            if re.match(r'^\|?[\s\-:|]+\|[\s\-:|]+', line):
                # 找到表格的起始行（表头）
                if i > 0:
                    start_line = i - 1
                    header_line = lines[start_line].strip()
                    
                    # 验证表头行是否是有效的表格行
                    if '|' in header_line:
                        # 提取表头
                        headers = [h.strip() for h in header_line.split('|') if h.strip()]
                        columns = len(headers)
                        
                        # 找到表格的结束行
                        end_line = i + 1
                        while end_line < len(lines) and '|' in lines[end_line]:
                            end_line += 1
                        end_line -= 1
                        
                        # 计算行数（不包括表头和分隔行）
                        rows = end_line - i
                        
                        # 提取表格内容
                        table_content = '\n'.join(lines[start_line:end_line + 1])
                        
                        # 创建 TableBlock
                        table = TableBlock(
                            content=table_content,
                            start_line=start_line,
                            end_line=end_line,
                            rows=rows,
                            columns=columns,
                            headers=headers
                        )
                        tables.append(table)
                        
                        # 跳过已处理的表格行
                        i = end_line + 1
                        continue
            
            i += 1
        
        return tables
