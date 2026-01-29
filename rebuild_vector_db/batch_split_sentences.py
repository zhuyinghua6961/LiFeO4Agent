"""
批量切分 Markdown 文件为句子并保存为 JSON

扫描清洗后的 Markdown 目录，对每个文件调用 SentenceSplitter.split()
保存结果到 JSON 文件：rebuild_vector_db/sentences_data/{filename}_sentences.json

运行方式：
    conda run -n agent python rebuild_vector_db/batch_split_sentences.py
"""

import os
import sys
import json
from pathlib import Path
from tqdm import tqdm
from typing import Dict, Any

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rebuild_vector_db.sentence_splitter import SentenceSplitter


def batch_split_sentences(
    input_dir: str = "qwen2.5B/output/cleaned",
    output_dir: str = "rebuild_vector_db/sentences_data",
    doi_mapping_file: str = "/mnt/fast18/zhu/LiFeO4Agent/doi_to_pdf_mapping.json",
    skip_existing: bool = True
) -> Dict[str, Any]:
    """
    批量切分 Markdown 文件为句子
    
    Args:
        input_dir: 清洗后的 Markdown 目录
        output_dir: JSON 输出目录
        doi_mapping_file: DOI 映射文件路径
        skip_existing: 是否跳过已存在的 JSON 文件
        
    Returns:
        Dict: 处理统计信息
    """
    # 转换为绝对路径
    input_path = Path(project_root) / input_dir
    output_path = Path(project_root) / output_dir
    
    # 创建输出目录
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 扫描所有 Markdown 文件
    md_files = list(input_path.glob("*.md"))
    
    if not md_files:
        print(f"❌ 错误：在 {input_path} 中未找到 .md 文件")
        return {}
    
    print(f"📂 输入目录: {input_path}")
    print(f"📂 输出目录: {output_path}")
    print(f"📄 找到 {len(md_files)} 个 Markdown 文件")
    print(f"🔄 跳过已存在: {'是' if skip_existing else '否'}\n")
    
    # 初始化 SentenceSplitter
    splitter = SentenceSplitter(
        min_sentence_length=10,
        doi_mapping_file=doi_mapping_file,
        filter_references=True
    )
    
    # 统计信息
    stats = {
        'total_files': len(md_files),
        'processed': 0,
        'skipped': 0,
        'failed': 0,
        'total_sentences': 0,
        'errors': []
    }
    
    # 批量处理
    print("🚀 开始批量切分...\n")
    
    for idx, md_file in enumerate(tqdm(md_files, desc="切分进度", unit="文件")):
        try:
            # 生成输出文件名
            output_file = output_path / f"{md_file.stem}_sentences.json"
            
            # 跳过已存在的文件
            if skip_existing and output_file.exists():
                stats['skipped'] += 1
                continue
            
            # 读取 Markdown 文件
            with open(md_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # 切分为句子
            source = md_file.stem.replace('_cleaned', '')
            sentences = splitter.split(text, source=source)
            
            # 转换为字典格式
            sentences_data = {
                'source': source,
                'total_sentences': len(sentences),
                'filtered_references': True,  # SentenceSplitter 默认过滤 REFERENCES
                'sentences': [sentence.to_dict() for sentence in sentences]
            }
            
            # 保存为 JSON
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(sentences_data, f, ensure_ascii=False, indent=2)
            
            # 更新统计
            stats['processed'] += 1
            stats['total_sentences'] += len(sentences)
            
            # 每处理 100 个文件打印一次进度
            if (idx + 1) % 100 == 0:
                tqdm.write(f"✅ 已处理 {idx + 1}/{len(md_files)} 个文件，生成 {stats['total_sentences']} 个句子")
            
        except Exception as e:
            stats['failed'] += 1
            error_info = {
                'file': md_file.name,
                'error': str(e)
            }
            stats['errors'].append(error_info)
            tqdm.write(f"❌ 处理失败: {md_file.name} - {str(e)}")
    
    # 打印统计报告
    print("\n" + "="*80)
    print("📊 批量切分完成！")
    print("="*80)
    print(f"📄 总文件数: {stats['total_files']}")
    print(f"✅ 成功处理: {stats['processed']} 个文件")
    print(f"⏭️  跳过: {stats['skipped']} 个文件")
    print(f"❌ 失败: {stats['failed']} 个文件")
    print(f"📝 总句子数: {stats['total_sentences']}")
    if stats['processed'] > 0:
        print(f"📊 平均每文件: {stats['total_sentences'] / stats['processed']:.1f} 个句子")
    print("="*80)
    print(f"\n💾 JSON 文件保存在: {output_path}")
    
    if stats['errors']:
        print(f"\n⚠️  错误详情:")
        for error in stats['errors'][:10]:  # 只显示前10个错误
            print(f"  - {error['file']}: {error['error']}")
        if len(stats['errors']) > 10:
            print(f"  ... 还有 {len(stats['errors']) - 10} 个错误")
    
    return stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="批量切分 Markdown 文件为句子")
    parser.add_argument(
        "--input-dir",
        default="qwen2.5B/output/cleaned",
        help="输入目录（默认: qwen2.5B/output/cleaned）"
    )
    parser.add_argument(
        "--output-dir",
        default="rebuild_vector_db/sentences_data",
        help="输出目录（默认: rebuild_vector_db/sentences_data）"
    )
    parser.add_argument(
        "--doi-mapping",
        default="/mnt/fast18/zhu/LiFeO4Agent/doi_to_pdf_mapping.json",
        help="DOI 映射文件路径"
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="不跳过已存在的 JSON 文件（重新处理所有文件）"
    )
    
    args = parser.parse_args()
    
    batch_split_sentences(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        doi_mapping_file=args.doi_mapping,
        skip_existing=not args.no_skip_existing
    )
