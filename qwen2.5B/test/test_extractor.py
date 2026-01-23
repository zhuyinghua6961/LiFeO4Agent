"""
句子提取器测试

测试句子边界检测、缩写处理、章节层级追踪和位置信息准确性。
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from text_processor.extractor import SentenceExtractor
from text_processor.models import CleanedDocument, TableBlock


class TestSentenceExtractor:
    """句子提取器测试类"""
    
    @pytest.fixture
    def extractor(self):
        """创建句子提取器实例"""
        return SentenceExtractor()
    
    def test_split_sentences_basic(self, extractor):
        """测试基本句子分割"""
        text = "This is the first sentence. This is the second sentence. This is the third."
        sentences = extractor.split_sentences(text)
        
        assert len(sentences) == 3
        assert sentences[0] == "This is the first sentence."
        assert sentences[1] == "This is the second sentence."
        assert sentences[2] == "This is the third."
    
    def test_split_sentences_with_abbreviations(self, extractor):
        """测试缩写处理 - 不应在缩写处分割"""
        text = "Dr. Smith et al. published a paper. The results were significant."
        sentences = extractor.split_sentences(text)
        
        # NLTK 应该能正确处理常见缩写
        assert len(sentences) == 2
        assert "Dr. Smith et al." in sentences[0]
        assert "published a paper" in sentences[0]
    
    def test_split_sentences_with_decimals(self, extractor):
        """测试小数处理 - 不应在小数点处分割"""
        text = "The value is 3.14 meters. Another measurement is 2.5 kg."
        sentences = extractor.split_sentences(text)
        
        assert len(sentences) == 2
        assert "3.14" in sentences[0]
        assert "2.5" in sentences[1]
    
    def test_split_sentences_with_citations(self, extractor):
        """测试引用保留 - 引用应附着在句子上"""
        text = "This is a finding [1]. Another finding is here [2-5]."
        sentences = extractor.split_sentences(text)
        
        assert len(sentences) == 2
        assert "[1]" in sentences[0]
        assert "[2-5]" in sentences[1]
    
    def test_track_section_hierarchy_single_level(self, extractor):
        """测试单层级章节追踪"""
        text = """# Introduction
This is the introduction.

# Methods
This is the methods section."""
        
        section_tree = extractor.track_section_hierarchy(text)
        
        # 应该有根节点和两个子节点
        assert section_tree.root.title == "Document Root"
        assert len(section_tree.root.children) == 2
        assert section_tree.root.children[0].title == "Introduction"
        assert section_tree.root.children[1].title == "Methods"
        assert section_tree.root.children[0].level == 1
        assert section_tree.root.children[1].level == 1
    
    def test_track_section_hierarchy_nested(self, extractor):
        """测试嵌套章节追踪"""
        text = """# Introduction
Introduction text.

## Background
Background text.

## Motivation
Motivation text.

# Methods
Methods text."""
        
        section_tree = extractor.track_section_hierarchy(text)
        
        # 检查根节点
        assert len(section_tree.root.children) == 2
        
        # 检查第一个章节（Introduction）
        intro = section_tree.root.children[0]
        assert intro.title == "Introduction"
        assert intro.level == 1
        assert len(intro.children) == 2
        
        # 检查子章节
        assert intro.children[0].title == "Background"
        assert intro.children[0].level == 2
        assert intro.children[1].title == "Motivation"
        assert intro.children[1].level == 2
        
        # 检查第二个章节（Methods）
        methods = section_tree.root.children[1]
        assert methods.title == "Methods"
        assert methods.level == 1
    
    def test_track_section_hierarchy_flat_list(self, extractor):
        """测试扁平化章节列表"""
        text = """# Introduction
## Background
# Methods"""
        
        section_tree = extractor.track_section_hierarchy(text)
        
        # 扁平列表应包含所有章节（不包括根节点）
        assert len(section_tree.flat_list) == 3
        assert section_tree.flat_list[0].title == "Introduction"
        assert section_tree.flat_list[1].title == "Background"
        assert section_tree.flat_list[2].title == "Methods"
    
    def test_assign_location_metadata(self, extractor):
        """测试位置信息分配"""
        # 创建简单的章节栈
        text = "# Introduction\n## Background"
        section_tree = extractor.track_section_hierarchy(text)
        
        # 模拟章节栈
        section_stack = [
            section_tree.root,
            section_tree.flat_list[0],  # Introduction
            section_tree.flat_list[1]   # Background
        ]
        
        sentence = "This is a test sentence."
        location = extractor.assign_location_metadata(
            sentence,
            section_stack,
            paragraph_index=0,
            sentence_index=0,
            start_line=5,
            end_line=5
        )
        
        # 验证位置信息
        assert location.section_path == ["Introduction", "Background"]
        assert location.section_id == section_tree.flat_list[1].id
        assert location.paragraph_index == 0
        assert location.sentence_index == 0
        assert location.line_range == (5, 5)
    
    def test_extract_page_reference(self, extractor):
        """测试页码引用提取"""
        sentence = "This is a sentence with _page_42 reference."
        page_ref = extractor._extract_page_reference(sentence)
        
        assert page_ref == "page_42"
    
    def test_extract_page_reference_none(self, extractor):
        """测试无页码引用的情况"""
        sentence = "This is a sentence without page reference."
        page_ref = extractor._extract_page_reference(sentence)
        
        assert page_ref is None
    
    def test_should_include_sentence_too_short(self, extractor):
        """测试过滤太短的句子"""
        short_sentence = "Too short."  # 只有 2 个词
        
        assert not extractor._should_include_sentence(short_sentence)
    
    def test_should_include_sentence_valid(self, extractor):
        """测试有效句子"""
        valid_sentence = "This is a valid sentence with enough words."
        
        assert extractor._should_include_sentence(valid_sentence)
    
    def test_should_include_sentence_long(self, extractor):
        """测试长句子仍然被包含"""
        # 创建一个超过 100 词的句子
        long_sentence = " ".join(["word"] * 150)
        
        # 长句子应该仍然被包含（只是可能被标记）
        assert extractor._should_include_sentence(long_sentence)
    
    def test_extract_full_document(self, extractor):
        """测试完整文档提取"""
        text = """# Introduction

This is the first sentence. This is the second sentence.

## Background

This is a background sentence with citation [1].

# Methods

This is a methods sentence."""
        
        cleaned_doc = CleanedDocument(
            text=text,
            tables=[],
            removed_elements={},
            original_line_count=len(text.split('\n')),
            cleaned_line_count=len(text.split('\n'))
        )
        
        sentences = extractor.extract(cleaned_doc)
        
        # 应该提取到多个句子
        assert len(sentences) > 0
        
        # 检查第一个句子
        first_sentence = sentences[0]
        assert first_sentence.text == "This is the first sentence."
        assert first_sentence.sentence_type == "text"
        assert "Introduction" in first_sentence.location.section_path
        
        # 检查带引用的句子
        citation_sentences = [s for s in sentences if "[1]" in s.text]
        assert len(citation_sentences) > 0
        assert "Background" in citation_sentences[0].location.section_path
    
    def test_extract_with_multiline_paragraph(self, extractor):
        """测试跨行段落的句子提取"""
        text = """# Introduction

This is a sentence that spans
multiple lines in the source.
It should be reconstructed as one sentence."""
        
        cleaned_doc = CleanedDocument(
            text=text,
            tables=[],
            removed_elements={},
            original_line_count=len(text.split('\n')),
            cleaned_line_count=len(text.split('\n'))
        )
        
        sentences = extractor.extract(cleaned_doc)
        
        # 应该将跨行文本合并为一个句子
        assert len(sentences) > 0
        # 检查句子是否包含完整内容
        full_text = ' '.join([s.text for s in sentences])
        assert "spans" in full_text
        assert "multiple lines" in full_text
        assert "reconstructed" in full_text
    
    def test_section_hierarchy_line_numbers(self, extractor):
        """测试章节行号追踪"""
        text = """# Introduction
Line 1
Line 2

# Methods
Line 3"""
        
        section_tree = extractor.track_section_hierarchy(text)
        
        # 检查章节的起始行号
        intro = section_tree.root.children[0]
        assert intro.start_line == 0  # "# Introduction" 在第 0 行
        
        methods = section_tree.root.children[1]
        assert methods.start_line == 4  # "# Methods" 在第 4 行
