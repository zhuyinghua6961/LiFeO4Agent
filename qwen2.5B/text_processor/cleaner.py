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
        self.deep_clean_enabled = self.config.get('deep_clean', True)  # 深度清洗（修复 Marker 输出问题）
    
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
            'html_tags': 0,
            'citations': 0,
            'dehyphenated_lines': 0
        }
        
        # 步骤 0: 深度清洗（修复 Marker/OCR 导致的格式问题）
        text = markdown_text
        if self.deep_clean_enabled:
            text, deep_clean_stats = self.deep_clean_marker_output(text)
            removed_elements.update(deep_clean_stats)
        
        # 提取表格（在清洗之前）
        tables = []
        if self.preserve_tables_enabled:
            tables = self.identify_tables(text)
        
        # 执行清洗步骤
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
    
    def deep_clean_marker_output(self, text: str) -> Tuple[str, Dict[str, int]]:
        """
        深度清洗 Marker 输出：修复 OCR/PDF 转换导致的格式问题（增强版）
        
        专门处理：
        1. 预处理：标准化换行、删除图片和 HTML 标签
        2. 删除格式噪音：页眉、图注、页码
        3. 修复跨行连字符（De-hyphenation）
        4. 强化引用清理（4种模式）
        5. 修复常见 OCR 错误
        6. 激进的硬换行合并（跨段落合并）
        
        Args:
            text: 输入文本
            
        Returns:
            Tuple[str, Dict]: (清洗后的文本, 统计信息)
        """
        stats = {
            'citations': 0,
            'dehyphenated_lines': 0,
            'merged_lines': 0,
            'figure_captions_removed': 0,
            'header_footer_removed': 0,
            'ocr_errors_fixed': 0
        }
        
        # 步骤 1: 预处理 - 标准化换行
        text = text.replace('\r\n', '\n')
        
        # 步骤 2: 去除所有 HTML 标签（包括 <span id="page-x">）
        text = re.sub(r'<[^>]+>', '', text)
        
        # 步骤 3: 去除 Markdown 分隔符
        text = re.sub(r'^\s*[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
        
        # 步骤 4: 删除格式噪音（页眉、图注等）
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # 跳过页眉页脚
            if re.match(r'^(www\.|http|Article|DOI:|Published|Received|Accepted)', line_stripped, re.IGNORECASE):
                stats['header_footer_removed'] += 1
                continue
            
            # 跳过图注（Figure X. 或 Table X. 开头的行）
            if re.match(r'^(Figure|Fig\.|Table|Scheme)\s+\d+\.?\s*[\(:]', line_stripped, re.IGNORECASE):
                stats['figure_captions_removed'] += 1
                continue
            
            # 跳过纯数字行（可能是页码）
            if re.match(r'^\d+$', line_stripped):
                stats['header_footer_removed'] += 1
                continue
            
            cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        # 步骤 5: 修复跨行连字符（De-hyphenation）
        # 修复 Li-\nlean 这种跨行连字符
        dehyphen_matches = re.findall(r'(\w+)-\s*\n\s*([a-z])', text)
        stats['dehyphenated_lines'] = len(dehyphen_matches)
        text = re.sub(r'(\w+)-\s*\n\s*([a-z])', r'\1-\2', text)
        
        # 修复 Li - lean 这种中间有空格的
        text = re.sub(r'(\w+)-\s+([a-z])', r'\1-\2', text)
        
        # 步骤 6: 强化引用清理（4种模式）
        citation_count = 0
        
        # 模式 1: 句号后紧跟数字引用（可能有空格）
        # 例如: possible. 1-3 Li-ion -> possible. Li-ion
        pattern1 = r'(\.|!|\?)\s+(\d+(?:[–-]\d+)?(?:,\s*\d+)*)\s+([A-Z])'
        citations1 = re.findall(pattern1, text)
        text = re.sub(pattern1, r'\1 \3', text)
        citation_count += len(citations1)
        
        # 模式 2: 句号后紧跟数字引用（无空格）
        # 例如: batteries.4-7 Li -> batteries. Li
        pattern2 = r'\.(\d+(?:[–-]\d+)?(?:,\d+)*)\s*([A-Z])'
        citations2 = re.findall(pattern2, text)
        text = re.sub(pattern2, r'. \2', text)
        citation_count += len(citations2)
        
        # 模式 3: 方括号引用 [1], [1-3], [1, 2]
        pattern3 = r'\[\d+(?:[–-]\d+)?(?:,\s*\d+)*\]'
        citations3 = re.findall(pattern3, text)
        text = re.sub(pattern3, '', text)
        citation_count += len(citations3)
        
        # 模式 4: 上标引用 ^{1}, ^{1-3}
        pattern4 = r'\^{(\d+(?:[–-]\d+)?(?:,\s*\d+)*)}'
        citations4 = re.findall(pattern4, text)
        text = re.sub(pattern4, '', text)
        citation_count += len(citations4)
        
        stats['citations'] = citation_count
        
        # 步骤 7: 修复常见 OCR 错误
        ocr_fixes = [
            (r'\bLilean\b', 'Li-lean'),  # Lilean -> Li-lean
            (r'\bLiion\b', 'Li-ion'),    # Liion -> Li-ion
            (r'\bLimetal\b', 'Li-metal'), # Limetal -> Li-metal
        ]
        
        for pattern, replacement in ocr_fixes:
            matches = re.findall(pattern, text)
            if matches:
                text = re.sub(pattern, replacement, text)
                stats['ocr_errors_fixed'] += len(matches)
        
        # 步骤 8: 激进的硬换行合并（跨段落合并）
        text, merged_count = self._merge_hard_line_breaks_enhanced(text)
        stats['merged_lines'] = merged_count
        
        # 步骤 9: 去除多余的空行（超过2个的空行变成2个）
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 清理行首行尾空格
        lines = text.split('\n')
        text = '\n'.join(line.rstrip() for line in lines)
        
        return text, stats
    
    def _merge_hard_line_breaks(self, text: str) -> Tuple[str, int]:
        """
        合并硬换行：将 PDF 排版导致的换行合并成连续文本（保守版）
        
        逐行判断，保留标题和列表结构
        
        Args:
            text: 输入文本
            
        Returns:
            Tuple[str, int]: (合并后的文本, 合并的行数)
        """
        lines = text.split('\n')
        merged_lines = []
        buffer = ""
        merged_count = 0
        
        for line in lines:
            line = line.strip()
            
            # 情况 A: 空行（段落分隔）
            if not line:
                if buffer:
                    merged_lines.append(buffer)
                    buffer = ""
                merged_lines.append("")  # 保持原有的段落间距
                continue
            
            # 情况 B: 缓冲区为空，直接填入
            if not buffer:
                buffer = line
                continue
            
            # 情况 C: 缓冲区有内容，需要判断是否合并
            
            # C1. 如果前一行以连字符结尾 (xxx- \n yyy) -> 直接拼 (xxx-yyy)
            if buffer.endswith('-'):
                buffer += line
                merged_count += 1
            
            # C2. 如果前一行以句末标点结尾 -> 认为是真换行 -> 写入并开始新行
            elif buffer.endswith(('.', '!', '?', ':', '。', '！', '？')):
                merged_lines.append(buffer)
                buffer = line
            
            # C3. 如果当前行以 Markdown 标题开头 -> 认为是新段落
            elif re.match(r'^#+\s+', line):
                merged_lines.append(buffer)
                buffer = line
            
            # C4. 如果当前行以列表标记开头 -> 认为是新列表项
            elif re.match(r'^[-*+]\s+', line) or re.match(r'^\d+\.\s+', line):
                merged_lines.append(buffer)
                buffer = line
            
            # C5. 其他情况（断行）-> 加空格拼 (xxx \n yyy -> xxx yyy)
            else:
                buffer += " " + line
                merged_count += 1
        
        # 处理最后的缓冲区
        if buffer:
            merged_lines.append(buffer)
        
        return "\n".join(merged_lines), merged_count
    
    def _merge_hard_line_breaks_enhanced(self, text: str) -> Tuple[str, int]:
        """
        合并硬换行：将 PDF 排版导致的换行合并成连续文本（增强版）
        
        跨段落判断，更激进的合并策略，但保留标题和列表
        
        Args:
            text: 输入文本
            
        Returns:
            Tuple[str, int]: (合并后的文本, 合并的行数)
        """
        # 策略：按双换行切分段落，然后判断是否需要合并
        paragraphs = re.split(r'\n\s*\n', text)
        merged_paragraphs = []
        buffer = ""
        merge_count = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 检查是否是标题（以 # 开头）
            if re.match(r'^#+\s+', para):
                # 标题不合并，先保存 buffer
                if buffer:
                    merged_paragraphs.append(buffer)
                    buffer = ""
                merged_paragraphs.append(para)
                continue
            
            # 检查是否是列表项
            if re.match(r'^[-*+]\s+', para) or re.match(r'^\d+\.\s+', para):
                # 列表不合并
                if buffer:
                    merged_paragraphs.append(buffer)
                    buffer = ""
                merged_paragraphs.append(para)
                continue
            
            # 普通段落：判断是否需要合并
            if buffer:
                # 如果 buffer 以连字符结尾，直接拼接
                if buffer.endswith('-'):
                    buffer += para
                    merge_count += 1
                # 如果 buffer 以句末标点结尾，说明上一段结束了
                elif buffer.endswith(('.', '!', '?', ':', '。', '！', '？', '"', '"')):
                    merged_paragraphs.append(buffer)
                    buffer = para
                # 否则，说明上一段没结束，需要合并
                else:
                    buffer += " " + para
                    merge_count += 1
            else:
                buffer = para
        
        # 处理最后的 buffer
        if buffer:
            merged_paragraphs.append(buffer)
        
        return "\n\n".join(merged_paragraphs), merge_count
    
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
