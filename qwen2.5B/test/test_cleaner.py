"""
Markdown 清洗器单元测试

测试 MarkdownCleaner 类的各项功能。
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from text_processor.cleaner import MarkdownCleaner
from text_processor.models import CleanedDocument, TableBlock


class TestMarkdownCleaner:
    """测试 MarkdownCleaner 类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.cleaner = MarkdownCleaner()
    
    def test_remove_images_basic(self):
        """测试基本的图片占位符删除"""
        text = "This is text ![](_page_1_figure_0.png) more text"
        cleaned, count = self.cleaner.remove_images(text)
        
        assert count == 1
        assert "![](_page_1_figure_0.png)" not in cleaned
        assert "This is text" in cleaned
        assert "more text" in cleaned
    
    def test_remove_images_multiple(self):
        """测试删除多个图片占位符"""
        text = """
        Introduction ![](_page_1_figure_0.png) text
        More content ![](_page_2_figure_1.png) here
        Final ![](_page_3_figure_2.png) section
        """
        cleaned, count = self.cleaner.remove_images(text)
        
        assert count == 3
        assert "![](_page_" not in cleaned
    
    def test_remove_images_no_images(self):
        """测试没有图片的情况"""
        text = "This is plain text without any images"
        cleaned, count = self.cleaner.remove_images(text)
        
        assert count == 0
        assert cleaned == text
    
    def test_convert_html_tags_subscript(self):
        """测试下标标签转换"""
        text = "H<sub>2</sub>O is water"
        cleaned, count = self.cleaner.convert_html_tags(text)
        
        assert count == 1
        assert "H_{2}O" in cleaned
        assert "<sub>" not in cleaned
    
    def test_convert_html_tags_superscript(self):
        """测试上标标签转换"""
        text = "E = mc<sup>2</sup>"
        cleaned, count = self.cleaner.convert_html_tags(text)
        
        assert count == 1
        assert "mc^{2}" in cleaned
        assert "<sup>" not in cleaned
    
    def test_convert_html_tags_mixed(self):
        """测试混合 HTML 标签转换"""
        text = "CO<sub>2</sub> and x<sup>2</sup> with <b>bold</b> and <i>italic</i>"
        cleaned, count = self.cleaner.convert_html_tags(text)
        
        assert count == 4
        assert "CO_{2}" in cleaned
        assert "x^{2}" in cleaned
        assert "**bold**" in cleaned
        assert "*italic*" in cleaned
    
    def test_convert_html_tags_case_insensitive(self):
        """测试 HTML 标签大小写不敏感"""
        text = "H<SUB>2</SUB>O and E<SUP>2</SUP>"
        cleaned, count = self.cleaner.convert_html_tags(text)
        
        assert count == 2
        assert "H_{2}O" in cleaned
        assert "E^{2}" in cleaned
    
    def test_remove_metadata_abstract(self):
        """测试删除摘要元数据"""
        text = """
# Abstract
This is the abstract content
that spans multiple lines

# 1. Introduction
This is the introduction
"""
        cleaned, count = self.cleaner.remove_metadata(text)
        
        assert count > 0
        assert "# 1. Introduction" in cleaned
        assert "This is the introduction" in cleaned
    
    def test_remove_metadata_author_info(self):
        """测试删除作者信息"""
        text = """
Author: John Doe
Affiliation: University
Email: john@example.com

# 1. Introduction
Content here
"""
        cleaned, count = self.cleaner.remove_metadata(text)
        
        assert count > 0
        assert "# 1. Introduction" in cleaned
        assert "Content here" in cleaned
    
    def test_identify_tables_basic(self):
        """测试基本表格识别"""
        text = """
Some text before

| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Cell 1   | Cell 2   | Cell 3   |
| Cell 4   | Cell 5   | Cell 6   |

Some text after
"""
        tables = self.cleaner.identify_tables(text)
        
        assert len(tables) == 1
        assert tables[0].columns == 3
        assert tables[0].rows == 2
        assert "Header 1" in tables[0].headers
        assert "Header 2" in tables[0].headers
        assert "Header 3" in tables[0].headers
    
    def test_identify_tables_multiple(self):
        """测试识别多个表格"""
        text = """
| Table 1 | Col 2 |
|---------|-------|
| Data 1  | Data 2|

Some text

| Table 2 | Col 2 | Col 3 |
|---------|-------|-------|
| Data A  | Data B| Data C|
"""
        tables = self.cleaner.identify_tables(text)
        
        assert len(tables) == 2
        assert tables[0].columns == 2
        assert tables[1].columns == 3
    
    def test_identify_tables_no_tables(self):
        """测试没有表格的情况"""
        text = "This is plain text without any tables"
        tables = self.cleaner.identify_tables(text)
        
        assert len(tables) == 0
    
    def test_clean_full_document(self):
        """测试完整文档清洗"""
        text = """
# Abstract
This is abstract

Author: John Doe

# 1. Introduction
This is H<sub>2</sub>O ![](_page_1_figure_0.png) research.

| Method | Result |
|--------|--------|
| A      | 95%    |

The formula is E = mc<sup>2</sup>.
"""
        result = self.cleaner.clean(text)
        
        assert isinstance(result, CleanedDocument)
        assert result.removed_elements['images'] == 1
        assert result.removed_elements['html_tags'] == 2
        assert len(result.tables) == 1
        assert "H_{2}O" in result.text
        assert "mc^{2}" in result.text
        assert "![](_page_" not in result.text
    
    def test_preserve_citations(self):
        """测试保留引用"""
        text = "This research [1] shows that [34-36] citations are preserved."
        result = self.cleaner.clean(text)
        
        assert "[1]" in result.text
        assert "[34-36]" in result.text
    
    def test_preserve_section_structure(self):
        """测试保留章节结构"""
        text = """
# 1. Introduction
Content

## 1.1 Background
More content

### 1.1.1 Details
Even more
"""
        result = self.cleaner.clean(text)
        
        assert "# 1. Introduction" in result.text
        assert "## 1.1 Background" in result.text
        assert "### 1.1.1 Details" in result.text
    
    def test_edge_case_empty_text(self):
        """测试边界情况：空文本"""
        text = ""
        result = self.cleaner.clean(text)
        
        assert result.text == ""
        assert len(result.tables) == 0
        assert result.removed_elements['images'] == 0
    
    def test_edge_case_only_images(self):
        """测试边界情况：只有图片"""
        text = "![](_page_1_figure_0.png)\n![](_page_2_figure_1.png)"
        result = self.cleaner.clean(text)
        
        assert result.removed_elements['images'] == 2
        assert "![](_page_" not in result.text
    
    def test_config_disable_image_removal(self):
        """测试配置：禁用图片删除"""
        cleaner = MarkdownCleaner(config={'remove_images': False})
        text = "Text ![](_page_1_figure_0.png) more"
        result = cleaner.clean(text)
        
        assert "![](_page_1_figure_0.png)" in result.text
        assert result.removed_elements['images'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
