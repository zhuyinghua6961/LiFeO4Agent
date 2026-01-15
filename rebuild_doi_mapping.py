#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重建 DOI 到 PDF 映射文件
从 PDF 文件中提取 DOI 信息
"""
import json
import re
import os
from pathlib import Path
from typing import Dict, List, Optional
import PyPDF2
from tqdm import tqdm
import concurrent.futures

# 路径配置
PAPERS_DIR = "/Users/zhuyinghua/Desktop/agent/main/papers"
OUTPUT_FILE = "/Users/zhuyinghua/Desktop/agent/main/doi_to_pdf_mapping_new.json"
BACKUP_FILE = "/Users/zhuyinghua/Desktop/agent/main/doi_to_pdf_mapping_backup.json"

# DOI 正则表达式模式
DOI_PATTERNS = [
    r'10\.\d{4,}/[^\s\>\]\)]+',  # 标准DOI格式
    r'doi:\s*10\.\d{4,}/[^\s\>\]\)]+',  # doi: 前缀
    r'DOI:\s*10\.\d{4,}/[^\s\>\]\)]+',  # DOI: 前缀
]

def extract_doi_from_text(text: str) -> Optional[str]:
    """从文本中提取DOI"""
    if not text:
        return None
    
    # 尝试所有模式
    for pattern in DOI_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # 清理DOI
            doi = matches[0].lower()
            doi = doi.replace('doi:', '').replace('DOI:', '').strip()
            # 移除末尾的标点符号
            doi = re.sub(r'[.,;:\)\]>]+$', '', doi)
            return doi
    
    return None

def extract_doi_from_filename(filename: str) -> Optional[str]:
    """从文件名中尝试提取DOI"""
    # 移除 .pdf 扩展名
    name = filename.replace('.pdf', '')
    
    # 尝试匹配标准DOI模式
    match = re.search(r'10\.\d{4,}[/_][^\s]+', name)
    if match:
        doi = match.group(0)
        # 将下划线替换为斜杠
        doi = doi.replace('_', '/')
        return doi
    
    return None

def extract_doi_from_pdf(pdf_path: Path) -> Optional[str]:
    """从PDF文件中提取DOI"""
    try:
        # 首先尝试从文件名提取
        doi_from_name = extract_doi_from_filename(pdf_path.name)
        if doi_from_name:
            return doi_from_name
        
        # 尝试从PDF内容提取
        with open(pdf_path, 'rb') as f:
            try:
                reader = PyPDF2.PdfReader(f)
                
                # 尝试从元数据提取
                if reader.metadata:
                    for key in ['/Subject', '/Title', '/Keywords']:
                        if key in reader.metadata:
                            doi = extract_doi_from_text(str(reader.metadata[key]))
                            if doi:
                                return doi
                
                # 从前3页提取文本
                num_pages = min(3, len(reader.pages))
                for i in range(num_pages):
                    try:
                        text = reader.pages[i].extract_text()
                        if text:
                            doi = extract_doi_from_text(text)
                            if doi:
                                return doi
                    except:
                        continue
            except Exception as e:
                pass
        
        return None
    except Exception as e:
        return None

def process_single_pdf(pdf_path: Path) -> tuple:
    """处理单个PDF文件"""
    doi = extract_doi_from_pdf(pdf_path)
    return (pdf_path.name, doi)

def build_mapping(papers_dir: str, use_parallel: bool = True) -> Dict[str, str]:
    """构建DOI到PDF的映射"""
    papers_path = Path(papers_dir)
    pdf_files = list(papers_path.glob("*.pdf"))
    
    print(f"📁 找到 {len(pdf_files)} 个PDF文件")
    print(f"🔍 开始提取DOI信息...")
    
    mapping = {}
    failed = []
    
    if use_parallel:
        # 并行处理
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(process_single_pdf, pdf): pdf for pdf in pdf_files}
            
            with tqdm(total=len(pdf_files), desc="处理PDF") as pbar:
                for future in concurrent.futures.as_completed(futures):
                    filename, doi = future.result()
                    if doi:
                        mapping[doi] = filename
                    else:
                        failed.append(filename)
                    pbar.update(1)
    else:
        # 串行处理
        for pdf_path in tqdm(pdf_files, desc="处理PDF"):
            filename, doi = process_single_pdf(pdf_path)
            if doi:
                mapping[doi] = filename
            else:
                failed.append(filename)
    
    print(f"\n✅ 成功提取: {len(mapping)} 个DOI")
    print(f"❌ 失败: {len(failed)} 个文件")
    
    return mapping, failed

def save_mapping(mapping: Dict[str, str], output_file: str):
    """保存映射到JSON文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print(f"💾 映射文件已保存: {output_file}")

def backup_old_mapping(old_file: str, backup_file: str):
    """备份旧的映射文件"""
    if os.path.exists(old_file):
        import shutil
        shutil.copy2(old_file, backup_file)
        print(f"📦 旧映射文件已备份: {backup_file}")

def analyze_results(mapping: Dict[str, str], failed: List[str]):
    """分析结果统计"""
    print("\n" + "="*80)
    print("📊 统计报告")
    print("="*80)
    
    # 基本统计
    total = len(mapping) + len(failed)
    success_rate = len(mapping) / total * 100 if total > 0 else 0
    
    print(f"\n总计处理: {total} 个PDF文件")
    print(f"成功提取DOI: {len(mapping)} 个 ({success_rate:.1f}%)")
    print(f"未能提取DOI: {len(failed)} 个 ({100-success_rate:.1f}%)")
    
    # 检查重复
    from collections import Counter
    pdf_counts = Counter(mapping.values())
    duplicates = {pdf: count for pdf, count in pdf_counts.items() if count > 1}
    
    if duplicates:
        print(f"\n⚠️  重复映射: {len(duplicates)} 个PDF被多个DOI引用")
        print("前5个重复最多的PDF:")
        for pdf, count in sorted(duplicates.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {pdf}: {count} 个DOI")
    
    # 显示失败样例
    if failed:
        print(f"\n❌ 未能提取DOI的文件示例 (前10个):")
        for f in failed[:10]:
            print(f"  - {f}")
        if len(failed) > 10:
            print(f"  ... 还有 {len(failed)-10} 个")

def main():
    """主函数"""
    print("="*80)
    print("🔨 重建 DOI 到 PDF 映射文件")
    print("="*80)
    
    # 检查依赖
    try:
        import PyPDF2
    except ImportError:
        print("❌ 缺少依赖: PyPDF2")
        print("请运行: pip install PyPDF2")
        return
    
    try:
        import tqdm
    except ImportError:
        print("❌ 缺少依赖: tqdm")
        print("请运行: pip install tqdm")
        return
    
    # 备份旧文件
    old_mapping_file = "/Users/zhuyinghua/Desktop/agent/main/doi_to_pdf_mapping.json"
    backup_old_mapping(old_mapping_file, BACKUP_FILE)
    
    # 构建映射
    mapping, failed = build_mapping(PAPERS_DIR, use_parallel=True)
    
    # 保存结果
    save_mapping(mapping, OUTPUT_FILE)
    
    # 保存失败列表
    failed_file = "/Users/zhuyinghua/Desktop/agent/main/failed_pdf_extraction.txt"
    if failed:
        with open(failed_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(failed))
        print(f"📝 失败列表已保存: {failed_file}")
    
    # 分析结果
    analyze_results(mapping, failed)
    
    print("\n" + "="*80)
    print("✅ 完成!")
    print("="*80)
    print(f"\n新映射文件: {OUTPUT_FILE}")
    print(f"旧映射备份: {BACKUP_FILE}")
    print(f"\n下一步:")
    print(f"1. 检查新映射文件: {OUTPUT_FILE}")
    print(f"2. 如果满意,替换旧文件:")
    print(f"   mv {OUTPUT_FILE} {old_mapping_file}")

if __name__ == "__main__":
    main()
