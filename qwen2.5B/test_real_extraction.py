"""
测试真实科学论文的句子提取

使用 marker_service/outputs 中的真实 Markdown 文件测试句子提取器
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from text_processor.cleaner import MarkdownCleaner
from text_processor.extractor import SentenceExtractor
from text_processor.models import CleanedDocument


def test_real_paper_extraction():
    """测试真实论文的句子提取"""
    
    # 读取一个真实的 Markdown 文件
    paper_path = Path(__file__).parent.parent.parent / "marker_service" / "outputs" / "Enhanced-properties-of-LiFePO4-C-cathode-materials-_2014_Materials-Chemistry.md"
    
    # 如果文件不存在，尝试相对路径
    if not paper_path.exists():
        paper_path = Path("marker_service/outputs/Enhanced-properties-of-LiFePO4-C-cathode-materials-_2014_Materials-Chemistry.md")
    
    if not paper_path.exists():
        print(f"文件不存在: {paper_path}")
        return
    
    print(f"正在处理文件: {paper_path.name}")
    print("=" * 80)
    
    # 读取文件内容
    with open(paper_path, 'r', encoding='utf-8') as f:
        markdown_text = f.read()
    
    print(f"\n原始文件统计:")
    print(f"  - 总字符数: {len(markdown_text)}")
    print(f"  - 总行数: {len(markdown_text.split(chr(10)))}")
    
    # 1. 清洗 Markdown
    print("\n步骤 1: 清洗 Markdown...")
    cleaner = MarkdownCleaner()
    cleaned_doc = cleaner.clean(markdown_text)
    
    print(f"\n清洗后统计:")
    print(f"  - 清洗后行数: {cleaned_doc.cleaned_line_count}")
    print(f"  - 删除的图片: {cleaned_doc.removed_elements.get('images', 0)}")
    print(f"  - 删除的元数据行: {cleaned_doc.removed_elements.get('metadata_lines', 0)}")
    print(f"  - 转换的 HTML 标签: {cleaned_doc.removed_elements.get('html_tags', 0)}")
    print(f"  - 识别的表格: {len(cleaned_doc.tables)}")
    
    # 2. 提取句子
    print("\n步骤 2: 提取句子...")
    extractor = SentenceExtractor()
    sentences = extractor.extract(cleaned_doc)
    
    print(f"\n提取结果:")
    print(f"  - 总句子数: {len(sentences)}")
    
    # 3. 显示前 10 个句子的详细信息
    print("\n前 10 个句子的详细信息:")
    print("-" * 80)
    
    for i, sent in enumerate(sentences[:10], 1):
        print(f"\n句子 {i}:")
        print(f"  文本: {sent.text[:100]}{'...' if len(sent.text) > 100 else ''}")
        print(f"  章节路径: {' > '.join(sent.location.section_path) if sent.location.section_path else '(根节点)'}")
        print(f"  章节 ID: {sent.location.section_id}")
        print(f"  段落索引: {sent.location.paragraph_index}")
        print(f"  句子索引: {sent.location.sentence_index}")
        print(f"  行号范围: {sent.location.line_range}")
        print(f"  页码引用: {sent.location.page_reference or '无'}")
    
    # 4. 统计章节分布
    print("\n\n章节分布统计:")
    print("-" * 80)
    
    section_counts = {}
    for sent in sentences:
        section_path = ' > '.join(sent.location.section_path) if sent.location.section_path else '(根节点)'
        section_counts[section_path] = section_counts.get(section_path, 0) + 1
    
    for section, count in sorted(section_counts.items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f"  {section}: {count} 个句子")
    
    # 5. 显示一些带引用的句子
    print("\n\n带引用的句子示例:")
    print("-" * 80)
    
    citation_sentences = [s for s in sentences if '[' in s.text and ']' in s.text]
    for i, sent in enumerate(citation_sentences[:5], 1):
        print(f"\n{i}. {sent.text[:150]}{'...' if len(sent.text) > 150 else ''}")
        print(f"   章节: {' > '.join(sent.location.section_path) if sent.location.section_path else '(根节点)'}")
    
    # 6. 显示表格信息
    if cleaned_doc.tables:
        print("\n\n表格信息:")
        print("-" * 80)
        for i, table in enumerate(cleaned_doc.tables[:3], 1):
            print(f"\n表格 {i}:")
            print(f"  行数: {table.rows}")
            print(f"  列数: {table.columns}")
            print(f"  表头: {table.headers}")
            print(f"  位置: 第 {table.start_line} - {table.end_line} 行")
            print(f"  内容预览:\n{table.content[:200]}...")
    
    print("\n" + "=" * 80)
    print("测试完成！")


if __name__ == "__main__":
    test_real_paper_extraction()
