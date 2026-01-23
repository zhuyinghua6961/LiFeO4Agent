"""
测试多个真实科学论文的句子提取

批量测试多个 Markdown 文件
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from text_processor.cleaner import MarkdownCleaner
from text_processor.extractor import SentenceExtractor


def test_multiple_papers():
    """测试多个论文"""
    
    # 选择几个不同的论文文件
    paper_files = [
        "Enhanced-properties-of-LiFePO4-C-cathode-materials-_2014_Materials-Chemistry.md",
        "High-performance-3D-directional-porous-LiFePO4-C-materia_2018_Applied-Surfac.md",
        "Cupric-ion-substituted-LiFePO4-C-composites-with-enhanced-el_2014_Electrochi.md",
    ]
    
    outputs_dir = Path("marker_service/outputs")
    
    cleaner = MarkdownCleaner()
    extractor = SentenceExtractor()
    
    print("批量测试句子提取器")
    print("=" * 80)
    
    total_sentences = 0
    total_papers = 0
    
    for paper_file in paper_files:
        paper_path = outputs_dir / paper_file
        
        if not paper_path.exists():
            print(f"\n跳过不存在的文件: {paper_file}")
            continue
        
        total_papers += 1
        
        print(f"\n处理文件 {total_papers}: {paper_file}")
        print("-" * 80)
        
        try:
            # 读取文件
            with open(paper_path, 'r', encoding='utf-8') as f:
                markdown_text = f.read()
            
            # 清洗
            cleaned_doc = cleaner.clean(markdown_text)
            
            # 提取句子
            sentences = extractor.extract(cleaned_doc)
            
            total_sentences += len(sentences)
            
            # 统计信息
            print(f"  原始行数: {len(markdown_text.split(chr(10)))}")
            print(f"  清洗后行数: {cleaned_doc.cleaned_line_count}")
            print(f"  删除图片: {cleaned_doc.removed_elements.get('images', 0)}")
            print(f"  识别表格: {len(cleaned_doc.tables)}")
            print(f"  提取句子: {len(sentences)}")
            
            # 显示章节统计
            section_counts = {}
            for sent in sentences:
                section_path = ' > '.join(sent.location.section_path[:2]) if sent.location.section_path else '(根节点)'
                section_counts[section_path] = section_counts.get(section_path, 0) + 1
            
            print(f"  主要章节:")
            for section, count in sorted(section_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"    - {section}: {count} 句")
            
            # 显示一个示例句子
            if sentences:
                example = sentences[len(sentences) // 2]  # 取中间的句子
                print(f"  示例句子:")
                print(f"    文本: {example.text[:80]}...")
                print(f"    章节: {' > '.join(example.location.section_path[:2]) if example.location.section_path else '(根节点)'}")
            
            print("  ✓ 处理成功")
            
        except Exception as e:
            print(f"  ✗ 处理失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print(f"总结:")
    print(f"  处理论文数: {total_papers}")
    print(f"  总提取句子数: {total_sentences}")
    print(f"  平均每篇句子数: {total_sentences / total_papers if total_papers > 0 else 0:.1f}")
    print("\n所有测试完成！✓")


if __name__ == "__main__":
    test_multiple_papers()
