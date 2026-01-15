#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查 DOI 到 PDF 映射的一致性
"""
import json
import os
from pathlib import Path
from collections import defaultdict

# 路径配置
MAPPING_FILE = "/Users/zhuyinghua/Desktop/agent/main/doi_to_pdf_mapping.json"
PAPERS_DIR = "/Users/zhuyinghua/Desktop/agent/main/papers"

def load_mapping():
    """加载DOI映射文件"""
    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_pdf_files():
    """获取papers目录下的所有PDF文件"""
    papers_path = Path(PAPERS_DIR)
    if not papers_path.exists():
        print(f"❌ papers目录不存在: {PAPERS_DIR}")
        return []
    
    pdf_files = list(papers_path.glob("*.pdf"))
    return [f.name for f in pdf_files]

def check_mapping_consistency():
    """检查映射一致性"""
    print("=" * 80)
    print("📊 DOI到PDF映射一致性检查")
    print("=" * 80)
    
    # 加载映射
    print("\n1. 加载DOI映射文件...")
    mapping = load_mapping()
    print(f"   映射文件中的DOI数量: {len(mapping)}")
    
    # 获取实际PDF文件
    print("\n2. 扫描papers目录...")
    actual_pdfs = set(get_pdf_files())
    print(f"   实际PDF文件数量: {len(actual_pdfs)}")
    
    # 映射中的PDF文件
    mapped_pdfs = set(mapping.values())
    print(f"   映射中引用的PDF数量: {len(mapped_pdfs)}")
    
    print("\n" + "=" * 80)
    print("📋 一致性分析")
    print("=" * 80)
    
    # 1. 映射中有但实际不存在的PDF
    missing_pdfs = mapped_pdfs - actual_pdfs
    if missing_pdfs:
        print(f"\n❌ 映射中引用但实际不存在的PDF文件 ({len(missing_pdfs)}个):")
        for i, pdf in enumerate(sorted(missing_pdfs)[:20], 1):
            # 找出引用这个PDF的DOI
            dois = [doi for doi, p in mapping.items() if p == pdf]
            print(f"   {i}. {pdf}")
            print(f"      关联DOI: {', '.join(dois[:3])}{'...' if len(dois) > 3 else ''}")
        if len(missing_pdfs) > 20:
            print(f"   ... 还有 {len(missing_pdfs) - 20} 个未显示")
    else:
        print("\n✅ 所有映射的PDF文件都存在")
    
    # 2. 实际存在但未在映射中的PDF
    unmapped_pdfs = actual_pdfs - mapped_pdfs
    if unmapped_pdfs:
        print(f"\n⚠️  存在但未在映射中的PDF文件 ({len(unmapped_pdfs)}个):")
        for i, pdf in enumerate(sorted(unmapped_pdfs)[:20], 1):
            print(f"   {i}. {pdf}")
        if len(unmapped_pdfs) > 20:
            print(f"   ... 还有 {len(unmapped_pdfs) - 20} 个未显示")
    else:
        print("\n✅ 所有PDF文件都已在映射中")
    
    # 3. 多个DOI映射到同一个PDF
    print("\n" + "=" * 80)
    print("🔄 重复映射检查")
    print("=" * 80)
    
    pdf_to_dois = defaultdict(list)
    for doi, pdf in mapping.items():
        pdf_to_dois[pdf].append(doi)
    
    duplicate_mappings = {pdf: dois for pdf, dois in pdf_to_dois.items() if len(dois) > 1}
    if duplicate_mappings:
        print(f"\n⚠️  多个DOI映射到同一个PDF的情况 ({len(duplicate_mappings)}个PDF):")
        for i, (pdf, dois) in enumerate(sorted(duplicate_mappings.items())[:10], 1):
            print(f"   {i}. {pdf}")
            print(f"      关联 {len(dois)} 个DOI: {', '.join(dois[:5])}{'...' if len(dois) > 5 else ''}")
        if len(duplicate_mappings) > 10:
            print(f"   ... 还有 {len(duplicate_mappings) - 10} 个未显示")
    else:
        print("\n✅ 没有重复映射")
    
    # 4. 统计总结
    print("\n" + "=" * 80)
    print("📊 统计总结")
    print("=" * 80)
    
    valid_mappings = len([doi for doi, pdf in mapping.items() if pdf in actual_pdfs])
    invalid_mappings = len(mapping) - valid_mappings
    
    print(f"\n   DOI总数: {len(mapping)}")
    print(f"   有效映射: {valid_mappings} ({valid_mappings/len(mapping)*100:.1f}%)")
    print(f"   失效映射: {invalid_mappings} ({invalid_mappings/len(mapping)*100:.1f}%)")
    print(f"   实际PDF文件: {len(actual_pdfs)}")
    print(f"   未映射的PDF: {len(unmapped_pdfs)}")
    print(f"   覆盖率: {len(mapped_pdfs & actual_pdfs) / len(actual_pdfs) * 100:.1f}%")
    
    # 5. 建议
    print("\n" + "=" * 80)
    print("💡 建议")
    print("=" * 80)
    
    if missing_pdfs:
        print(f"\n   1. 清理 {len(missing_pdfs)} 个无效的映射条目")
    if unmapped_pdfs:
        print(f"   2. 为 {len(unmapped_pdfs)} 个未映射的PDF文件添加DOI映射")
    if duplicate_mappings:
        print(f"   3. 检查 {len(duplicate_mappings)} 个重复映射,确认是否合理")
    
    if not missing_pdfs and not unmapped_pdfs:
        print("\n   ✅ 映射文件与实际文件完全一致!")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    try:
        check_mapping_consistency()
    except FileNotFoundError as e:
        print(f"❌ 文件未找到: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {e}")
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
