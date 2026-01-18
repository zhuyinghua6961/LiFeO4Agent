"""
PDF加载工具
处理PDF文件读取和解析
"""
import logging
import os
import re
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("⚠️ PyMuPDF未安装，PDF功能将不可用")


class PDFLoader:
    """PDF文件加载器"""
    
    def __init__(self, pdf_path: str):
        """
        初始化PDF加载器
        
        Args:
            pdf_path: PDF文件路径
        """
        if not PDF_AVAILABLE:
            raise ImportError("PyMuPDF未安装，请先安装: pip install PyMuPDF")
        
        self.pdf_path = Path(pdf_path)
        self._text: Optional[str] = None
        self._metadata: Dict[str, Any] = {}
    
    @property
    def text(self) -> str:
        """获取PDF文本内容（懒加载）"""
        if self._text is None:
            self._text = self.extract_text()
        return self._text
    
    def extract_text(
        self,
        max_pages: int = 50,
        exclude_references: bool = True
    ) -> str:
        """
        从PDF中提取文本内容
        
        Args:
            max_pages: 最多提取的页数
            exclude_references: 是否排除参考文献部分
            
        Returns:
            提取的文本内容
        """
        if self._text is not None and not max_pages and not exclude_references:
            return self._text
        
        try:
            doc = fitz.open(str(self.pdf_path))
            text_content = []
            
            # 提取元数据
            metadata = doc.metadata
            if metadata and metadata.get('title'):
                text_content.append(f"标题: {metadata['title']}")
                self._metadata = metadata
            
            # 提取每一页的文本
            total_pages = min(doc.page_count, max_pages)
            all_pages_text = []
            
            for page_num in range(total_pages):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    all_pages_text.append((page_num + 1, text))
            
            doc.close()
            
            # 排除参考文献部分
            if exclude_references and all_pages_text:
                all_pages_text = self._exclude_references_section(all_pages_text)
            
            # 格式化输出
            for page_num, text in all_pages_text:
                text_content.append(f"\n--- 第 {page_num} 页 ---\n{text}")
            
            full_text = "\n".join(text_content)
            
            if not self._text:
                self._text = full_text
            
            logger.info(f"✅ PDF文本提取完成: {len(full_text)} 字符")
            return full_text
            
        except Exception as e:
            logger.error(f"❌ PDF提取失败: {e}")
            return f"[错误] PDF提取失败: {str(e)}"
    
    def _exclude_references_section(
        self,
        pages_text: List[Tuple[int, str]]
    ) -> List[Tuple[int, str]]:
        """排除参考文献部分"""
        if not pages_text:
            return pages_text
        
        # 参考文献关键词
        reference_keywords = [
            'references', 'bibliography', '参考文献',
            'cited references', 'literature cited'
        ]
        
        # 从后往前查找参考文献起始位置
        reference_start_idx = None
        
        for i in range(len(pages_text) - 1, -1, -1):
            page_num, text = pages_text[i]
            text_lower = text.lower()
            
            for keyword in reference_keywords:
                if keyword in text_lower:
                    pattern = rf'^\s*{re.escape(keyword)}\s*[：:]*\s*$'
                    if re.search(pattern, text_lower, re.MULTILINE | re.IGNORECASE):
                        reference_start_idx = i
                        break
            
            if reference_start_idx is not None:
                break
        
        # 验证
        if reference_start_idx is not None:
            reference_text = '\n'.join([t for _, t in pages_text[reference_start_idx:]])
            doi_count = len(re.findall(r'10\.\d+/[^\s]+', reference_text))
            
            if doi_count >= 3:
                return pages_text[:reference_start_idx]
        
        return pages_text


class PDFManager:
    """PDF管理器 - 处理DOI到PDF的映射"""
    
    def __init__(self, papers_dir: str, mapping_file: Optional[str] = None):
        """
        初始化PDF管理器
        
        Args:
            papers_dir: PDF存储目录
            mapping_file: DOI到PDF映射文件路径
        """
        self.papers_dir = Path(papers_dir)
        self.mapping_file = mapping_file
        self._doi_to_pdf: Optional[Dict[str, str]] = None
    
    @property
    def doi_to_pdf_mapping(self) -> Dict[str, str]:
        """获取DOI到PDF的映射（懒加载）"""
        if self._doi_to_pdf is None:
            self._doi_to_pdf = self._load_mapping()
        return self._doi_to_pdf
    
    def _load_mapping(self) -> Dict[str, str]:
        """加载DOI到PDF的映射"""
        mapping = {}
        
        # 从映射文件加载
        if self.mapping_file and os.path.exists(self.mapping_file):
            try:
                import json
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    file_mapping = json.load(f)
                    # 转换为完整路径
                    for doi, pdf_file in file_mapping.items():
                        pdf_path = self.papers_dir / pdf_file
                        if pdf_path.exists():
                            mapping[doi] = str(pdf_path)
                logger.info(f"加载DOI映射: {len(mapping)} 个")
            except Exception as e:
                logger.warning(f"加载映射文件失败: {e}")
        
        return mapping
    
    def get_pdf_path(self, doi: str) -> Optional[str]:
        """根据DOI获取PDF路径"""
        if doi in self.doi_to_pdf_mapping:
            return self.doi_to_pdf_mapping[doi]
        return None
    
    def load_pdf_by_doi(
        self,
        doi: str,
        max_pages: int = 30,
        max_chars: int = 20000
    ) -> Optional[str]:
        """根据DOI加载PDF内容"""
        pdf_path = self.get_pdf_path(doi)
        if not pdf_path:
            return None
        
        try:
            loader = PDFLoader(pdf_path)
            text = loader.extract_text(max_pages=max_pages, exclude_references=True)
            
            # 限制字符数
            if len(text) > max_chars:
                text = text[:max_chars] + f"\n\n[注意：PDF原文共{len(text)}字符，仅显示前{max_chars}字符]"
            
            return text
        except Exception as e:
            logger.error(f"加载PDF失败 ({doi}): {e}")
            return None

