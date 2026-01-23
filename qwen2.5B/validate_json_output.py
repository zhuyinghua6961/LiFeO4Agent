"""
验证 JSON 输出格式

检查生成的 JSON 文件是否符合设计文档的要求
"""

import json
from pathlib import Path


def validate_json_output(json_path: Path):
    """验证 JSON 输出格式"""
    
    print(f"验证 JSON 文件: {json_path.name}")
    print("=" * 80)
    
    # 读取 JSON 文件
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    errors = []
    warnings = []
    
    # 1. 检查顶层字段
    print("\n1. 检查顶层字段...")
    required_top_fields = ["source_file", "document_title", "processing_timestamp", 
                          "sentences", "tables", "processing_stats"]
    
    for field in required_top_fields:
        if field not in data:
            errors.append(f"缺少顶层字段: {field}")
        else:
            print(f"  ✓ {field}")
    
    # 2. 检查句子条目
    print("\n2. 检查句子条目...")
    if "sentences" in data:
        sentences = data["sentences"]
        print(f"  - 句子总数: {len(sentences)}")
        
        # 检查前几个句子的格式
        for i, sent in enumerate(sentences[:5]):
            required_sent_fields = ["id", "text", "keywords", "location", "sentence_type"]
            for field in required_sent_fields:
                if field not in sent:
                    errors.append(f"句子 {i} 缺少字段: {field}")
            
            # 检查 location 字段
            if "location" in sent:
                location = sent["location"]
                required_loc_fields = ["section_path", "section_id", "paragraph_index", 
                                      "sentence_index", "line_range", "page_reference"]
                for field in required_loc_fields:
                    if field not in location:
                        errors.append(f"句子 {i} 的 location 缺少字段: {field}")
        
        print(f"  ✓ 检查了前 5 个句子的格式")
        
        # 检查 ID 唯一性
        ids = [s["id"] for s in sentences]
        if len(ids) != len(set(ids)):
            errors.append("句子 ID 不唯一")
        else:
            print(f"  ✓ 所有句子 ID 唯一")
    
    # 3. 检查表格条目
    print("\n3. 检查表格条目...")
    if "tables" in data:
        tables = data["tables"]
        print(f"  - 表格总数: {len(tables)}")
        
        for i, table in enumerate(tables):
            required_table_fields = ["id", "content", "keywords", "location", "metadata"]
            for field in required_table_fields:
                if field not in table:
                    errors.append(f"表格 {i} 缺少字段: {field}")
            
            # 检查 metadata 字段
            if "metadata" in table:
                metadata = table["metadata"]
                required_meta_fields = ["rows", "columns", "headers"]
                for field in required_meta_fields:
                    if field not in metadata:
                        errors.append(f"表格 {i} 的 metadata 缺少字段: {field}")
        
        print(f"  ✓ 检查了所有表格的格式")
    
    # 4. 检查处理统计
    print("\n4. 检查处理统计...")
    if "processing_stats" in data:
        stats = data["processing_stats"]
        required_stats_fields = ["total_sentences", "total_tables", "original_line_count",
                                "cleaned_line_count", "removed_images", 
                                "removed_metadata_lines", "converted_html_tags"]
        
        for field in required_stats_fields:
            if field not in stats:
                errors.append(f"processing_stats 缺少字段: {field}")
            else:
                print(f"  ✓ {field}: {stats[field]}")
    
    # 5. 检查数据一致性
    print("\n5. 检查数据一致性...")
    if "sentences" in data and "processing_stats" in data:
        if len(data["sentences"]) != data["processing_stats"]["total_sentences"]:
            warnings.append(f"句子数量不一致: 实际 {len(data['sentences'])}, 统计 {data['processing_stats']['total_sentences']}")
        else:
            print(f"  ✓ 句子数量一致")
    
    if "tables" in data and "processing_stats" in data:
        if len(data["tables"]) != data["processing_stats"]["total_tables"]:
            warnings.append(f"表格数量不一致: 实际 {len(data['tables'])}, 统计 {data['processing_stats']['total_tables']}")
        else:
            print(f"  ✓ 表格数量一致")
    
    # 6. 检查编码
    print("\n6. 检查编码...")
    # 检查是否有科学记号
    has_subscript = any("_{" in s["text"] for s in data.get("sentences", []))
    has_superscript = any("^{" in s["text"] for s in data.get("sentences", []))
    
    if has_subscript:
        print(f"  ✓ 正确保留下标记号")
    if has_superscript:
        print(f"  ✓ 正确保留上标记号")
    
    # 7. 输出结果
    print("\n" + "=" * 80)
    print("验证结果:")
    
    if errors:
        print(f"\n❌ 发现 {len(errors)} 个错误:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n✅ 没有发现错误")
    
    if warnings:
        print(f"\n⚠️  发现 {len(warnings)} 个警告:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("✅ 没有发现警告")
    
    if not errors and not warnings:
        print("\n🎉 JSON 格式完全符合设计文档要求！")
    
    return len(errors) == 0


def main():
    """主函数"""
    
    json_path = Path("qwen2.5B/output/Enhanced-properties-of-LiFePO4-C-cathode-materials-_2014_Materials-Chemistry_sentences.json")
    
    if not json_path.exists():
        print(f"错误: 文件不存在 {json_path}")
        return
    
    is_valid = validate_json_output(json_path)
    
    if is_valid:
        print("\n✓ 验证通过！")
    else:
        print("\n✗ 验证失败！")


if __name__ == "__main__":
    main()
