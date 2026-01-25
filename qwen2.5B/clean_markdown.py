"""
使用新的 cleaner 处理 Markdown 文件并保存到根目录

用法:
    python clean_markdown.py <input_file>
    
示例:
    python clean_markdown.py ../marker_service/outputs/sample.md
    
输出文件会保存到项目根目录，使用原文件名
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from text_processor.cleaner import MarkdownCleaner


def clean_and_save(input_file: str):
    """
    清洗 Markdown 文件并保存到项目根目录
    
    Args:
        input_file: 输入文件路径
    """
    input_path = Path(input_file)
    
    # 检查文件是否存在
    if not input_path.exists():
        print(f"❌ 错误：文件不存在 {input_path}")
        return False
    
    print("=" * 80)
    print(f"清洗 Markdown 文件: {input_path.name}")
    print("=" * 80)
    
    # 读取原始文件
    print(f"\n📖 读取文件: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        original_text = f.read()
    
    print(f"原始大小: {len(original_text)} 字符, {len(original_text.split(chr(10)))} 行")
    
    # 创建清洗器（启用深度清洗）
    cleaner = MarkdownCleaner(config={'deep_clean': True})
    
    # 执行清洗
    print("\n🧹 执行深度清洗...")
    cleaned_doc = cleaner.clean(original_text)
    
    # 显示清洗统计
    print("\n" + "=" * 80)
    print("清洗统计:")
    print("-" * 80)
    print(f"  原始行数: {cleaned_doc.original_line_count}")
    print(f"  清洗后行数: {cleaned_doc.cleaned_line_count}")
    print(f"  删除的图片: {cleaned_doc.removed_elements.get('images', 0)}")
    print(f"  删除的引用: {cleaned_doc.removed_elements.get('citations', 0)}")
    print(f"  修复的跨行连字符: {cleaned_doc.removed_elements.get('dehyphenated_lines', 0)}")
    print(f"  合并的硬换行: {cleaned_doc.removed_elements.get('merged_lines', 0)}")
    print(f"  转换的 HTML 标签: {cleaned_doc.removed_elements.get('html_tags', 0)}")
    print(f"  删除的元数据行: {cleaned_doc.removed_elements.get('metadata_lines', 0)}")
    print(f"  识别的表格: {len(cleaned_doc.tables)}")
    
    print(f"\n清洗后大小: {len(cleaned_doc.text)} 字符, {len(cleaned_doc.text.split(chr(10)))} 行")
    
    # 保存到项目根目录，使用原文件名
    output_path = Path(__file__).parent.parent / input_path.name
    print(f"\n💾 保存清洗后的文件: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(cleaned_doc.text)
    
    print("\n✅ 完成！文件已保存。")
    print("=" * 80)
    
    return True


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python clean_markdown.py <input_file>")
        print("\n示例:")
        print("  python clean_markdown.py ../marker_service/outputs/sample.md")
        sys.exit(1)
    
    input_file = sys.argv[1]
    success = clean_and_save(input_file)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
