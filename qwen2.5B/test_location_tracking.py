"""
测试位置追踪功能

验证句子的位置信息是否准确
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from text_processor.cleaner import MarkdownCleaner
from text_processor.extractor import SentenceExtractor


def test_location_tracking():
    """测试位置追踪的准确性"""
    
    paper_path = Path("marker_service/outputs/Enhanced-properties-of-LiFePO4-C-cathode-materials-_2014_Materials-Chemistry.md")
    
    if not paper_path.exists():
        print(f"文件不存在: {paper_path}")
        return
    
    print("位置追踪功能测试")
    print("=" * 80)
    
    # 读取文件
    with open(paper_path, 'r', encoding='utf-8') as f:
        markdown_text = f.read()
    
    # 清洗和提取
    cleaner = MarkdownCleaner()
    extractor = SentenceExtractor()
    
    cleaned_doc = cleaner.clean(markdown_text)
    sentences = extractor.extract(cleaned_doc)
    
    print(f"\n总共提取了 {len(sentences)} 个句子\n")
    
    # 测试 1: 验证章节路径的层级结构
    print("测试 1: 章节层级结构")
    print("-" * 80)
    
    section_hierarchy = {}
    for sent in sentences:
        if sent.location.section_path:
            depth = len(sent.location.section_path)
            if depth not in section_hierarchy:
                section_hierarchy[depth] = set()
            section_hierarchy[depth].add(' > '.join(sent.location.section_path))
    
    for depth in sorted(section_hierarchy.keys()):
        print(f"\n层级 {depth}:")
        for section in sorted(list(section_hierarchy[depth]))[:5]:
            print(f"  - {section}")
        if len(section_hierarchy[depth]) > 5:
            print(f"  ... 还有 {len(section_hierarchy[depth]) - 5} 个章节")
    
    # 测试 2: 验证段落和句子索引的连续性
    print("\n\n测试 2: 段落和句子索引连续性")
    print("-" * 80)
    
    # 检查每个章节内的段落索引
    section_paragraphs = {}
    for sent in sentences:
        section_id = sent.location.section_id
        if section_id not in section_paragraphs:
            section_paragraphs[section_id] = {}
        
        para_idx = sent.location.paragraph_index
        if para_idx not in section_paragraphs[section_id]:
            section_paragraphs[section_id][para_idx] = []
        
        section_paragraphs[section_id][para_idx].append(sent.location.sentence_index)
    
    # 显示一些章节的段落统计
    print("\n章节段落统计（前 5 个章节）:")
    for i, (section_id, paragraphs) in enumerate(list(section_paragraphs.items())[:5]):
        print(f"\n  章节 {section_id}:")
        print(f"    段落数: {len(paragraphs)}")
        print(f"    句子数: {sum(len(sents) for sents in paragraphs.values())}")
        
        # 检查句子索引是否连续
        for para_idx, sent_indices in sorted(paragraphs.items())[:3]:
            print(f"    段落 {para_idx}: {len(sent_indices)} 个句子, 索引: {sent_indices}")
    
    # 测试 3: 验证行号范围
    print("\n\n测试 3: 行号范围验证")
    print("-" * 80)
    
    # 检查行号是否递增
    prev_end_line = -1
    line_order_issues = 0
    
    for i, sent in enumerate(sentences[:50]):  # 只检查前 50 个
        start_line, end_line = sent.location.line_range
        
        if start_line > end_line:
            print(f"  警告: 句子 {i} 的起始行 ({start_line}) 大于结束行 ({end_line})")
            line_order_issues += 1
        
        # 行号应该大致递增（允许一些重叠，因为段落可能跨行）
        if start_line < prev_end_line - 10:  # 允许 10 行的回退
            print(f"  注意: 句子 {i} 的起始行 ({start_line}) 远小于前一句的结束行 ({prev_end_line})")
        
        prev_end_line = end_line
    
    if line_order_issues == 0:
        print("  ✓ 所有句子的行号范围都是有效的")
    else:
        print(f"  发现 {line_order_issues} 个行号顺序问题")
    
    # 测试 4: 显示一些完整的位置信息示例
    print("\n\n测试 4: 完整位置信息示例")
    print("-" * 80)
    
    # 选择一些有代表性的句子
    example_indices = [10, 50, 100, 150, 200] if len(sentences) > 200 else [10, 50, 100]
    
    for idx in example_indices:
        if idx < len(sentences):
            sent = sentences[idx]
            print(f"\n句子 {idx}:")
            print(f"  文本: {sent.text[:80]}...")
            print(f"  章节路径: {' > '.join(sent.location.section_path) if sent.location.section_path else '(根节点)'}")
            print(f"  章节 ID: {sent.location.section_id}")
            print(f"  段落索引: {sent.location.paragraph_index}")
            print(f"  句子索引: {sent.location.sentence_index}")
            print(f"  行号范围: {sent.location.line_range[0]} - {sent.location.line_range[1]}")
            print(f"  页码引用: {sent.location.page_reference or '无'}")
    
    # 测试 5: 验证引用保留
    print("\n\n测试 5: 引用保留验证")
    print("-" * 80)
    
    citation_patterns = ['[1]', '[2]', '[3]', '[10]', '[1-3]', '[10-12]']
    found_citations = {}
    
    for sent in sentences:
        for pattern in citation_patterns:
            if pattern in sent.text:
                if pattern not in found_citations:
                    found_citations[pattern] = []
                found_citations[pattern].append(sent.text[:100])
    
    print(f"\n找到的引用模式:")
    for pattern, examples in sorted(found_citations.items()):
        print(f"  {pattern}: {len(examples)} 次")
        if examples:
            print(f"    示例: {examples[0]}...")
    
    # 测试 6: 章节树结构验证
    print("\n\n测试 6: 章节树结构")
    print("-" * 80)
    
    # 重新构建章节树来验证
    section_tree = extractor.track_section_hierarchy(cleaned_doc.text)
    
    def print_tree(node, indent=0):
        """递归打印树结构"""
        if node.title != "Document Root":
            print("  " * indent + f"- {node.title} (Level {node.level}, Lines {node.start_line}-{node.end_line})")
        for child in node.children[:3]:  # 只显示前 3 个子节点
            print_tree(child, indent + 1)
        if len(node.children) > 3:
            print("  " * (indent + 1) + f"... 还有 {len(node.children) - 3} 个子章节")
    
    print("\n章节树结构:")
    print_tree(section_tree.root)
    
    print("\n" + "=" * 80)
    print("位置追踪测试完成！✓")


if __name__ == "__main__":
    test_location_tracking()
