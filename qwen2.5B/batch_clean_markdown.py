"""
批量清洗 Marker 输出的 Markdown 文件

使用增强版 MarkdownCleaner 批量处理 marker_service/outputs/ 目录下的所有 .md 文件
清洗后的文件保存到 qwen2.5B/output/cleaned/ 目录

运行方式：
    conda run -n agent python qwen2.5B/batch_clean_markdown.py
"""

import os
import sys
from pathlib import Path
from tqdm import tqdm

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from qwen2.5B.text_processor.cleaner import MarkdownCleaner


def batch_clean_markdown(
    input_dir: str = "marker_service/outputs",
    output_dir: str = "qwen2.5B/output/cleaned",
    file_pattern: str = "*.md"
):
    """
    批量清洗 Markdown 文件
    
    Args:
        input_dir: 输入目录（Marker 输出目录）
        output_dir: 输出目录（清洗后文件保存目录）
        file_pattern: 文件匹配模式（默认 *.md）
    """
    # 转换为绝对路径
    input_path = Path(project_root) / input_dir
    output_path = Path(project_root) / output_dir
    
    # 创建输出目录
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 扫描所有 Markdown 文件
    md_files = list(input_path.glob(file_pattern))
    
    if not md_files:
        print(f"❌ 错误：在 {input_path} 中未找到 .md 文件")
        return
    
    print(f"📂 输入目录: {input_path}")
    print(f"📂 输出目录: {output_path}")
    print(f"📄 找到 {len(md_files)} 个 Markdown 文件\n")
    
    # 初始化清洗器（启用深度清洗）
    cleaner = MarkdownCleaner(config={'deep_clean': True})
    
    # 统计信息
    stats = {
        'total': len(md_files),
        'success': 0,
        'failed': 0,
        'total_citations_removed': 0,
        'total_merged_lines': 0,
        'total_ocr_fixed': 0
    }
    
    # 批量处理
    print("🚀 开始批量清洗...\n")
    
    for md_file in tqdm(md_files, desc="清洗进度", unit="文件"):
        try:
            # 读取原始文件
            with open(md_file, 'r', encoding='utf-8') as f:
                raw_content = f.read()
            
            # 清洗
            cleaned_doc = cleaner.clean(raw_content)
            
            # 保存清洗后的文件
            output_file = output_path / f"{md_file.stem}_cleaned.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_doc.text)
            
            # 更新统计
            stats['success'] += 1
            stats['total_citations_removed'] += cleaned_doc.removed_elements.get('citations', 0)
            stats['total_merged_lines'] += cleaned_doc.removed_elements.get('merged_lines', 0)
            stats['total_ocr_fixed'] += cleaned_doc.removed_elements.get('ocr_errors_fixed', 0)
            
        except Exception as e:
            stats['failed'] += 1
            tqdm.write(f"❌ 处理失败: {md_file.name} - {str(e)}")
    
    # 打印统计报告
    print("\n" + "="*80)
    print("📊 批量清洗完成！")
    print("="*80)
    print(f"✅ 成功: {stats['success']} 个文件")
    print(f"❌ 失败: {stats['failed']} 个文件")
    print(f"📝 总共删除引用: {stats['total_citations_removed']} 个")
    print(f"🔗 总共合并硬换行: {stats['total_merged_lines']} 处")
    print(f"🔧 总共修复 OCR 错误: {stats['total_ocr_fixed']} 处")
    print("="*80)
    print(f"\n💾 清洗后的文件保存在: {output_path}")


if __name__ == "__main__":
    # 支持命令行参数
    import argparse
    
    parser = argparse.ArgumentParser(description="批量清洗 Marker Markdown 文件")
    parser.add_argument(
        "--input-dir",
        default="marker_service/outputs",
        help="输入目录（默认: marker_service/outputs）"
    )
    parser.add_argument(
        "--output-dir",
        default="qwen2.5B/output/cleaned",
        help="输出目录（默认: qwen2.5B/output/cleaned）"
    )
    parser.add_argument(
        "--pattern",
        default="*.md",
        help="文件匹配模式（默认: *.md）"
    )
    
    args = parser.parse_args()
    
    batch_clean_markdown(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        file_pattern=args.pattern
    )
