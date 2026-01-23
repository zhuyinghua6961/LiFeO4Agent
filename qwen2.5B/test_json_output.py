"""
测试 JSON 输出

处理一篇论文并按照设计文档要求输出为 JSON 格式
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from text_processor.cleaner import MarkdownCleaner
from text_processor.extractor import SentenceExtractor
from text_processor.models import SentenceWithLocation, LocationMetadata


def location_to_dict(location: LocationMetadata) -> Dict[str, Any]:
    """将 LocationMetadata 转换为字典"""
    return {
        "section_path": location.section_path,
        "section_id": location.section_id,
        "paragraph_index": location.paragraph_index,
        "sentence_index": location.sentence_index,
        "line_range": list(location.line_range),
        "page_reference": location.page_reference
    }


def sentence_to_dict(sentence: SentenceWithLocation, sentence_id: str) -> Dict[str, Any]:
    """将句子转换为字典（符合 SentenceEntry 格式）"""
    return {
        "id": sentence_id,
        "text": sentence.text,
        "keywords": [],  # 暂时为空，等待 LLM 提取
        "location": location_to_dict(sentence.location),
        "sentence_type": sentence.sentence_type
    }


def generate_sentence_id(source_file: str, location: LocationMetadata, sent_idx: int) -> str:
    """
    生成唯一的句子 ID
    
    格式: doc_id_section_p_index_s_index
    例如: paper1_section_1_1_p_0_s_0
    """
    # 从文件名生成 doc_id
    doc_id = Path(source_file).stem.replace('-', '_')[:30]  # 限制长度
    
    # 构建 ID
    section_id = location.section_id.replace('_', '')
    para_idx = location.paragraph_index
    sent_idx_in_para = location.sentence_index
    
    return f"{doc_id}_{section_id}_p{para_idx}_s{sent_idx_in_para}"


def process_paper_to_json(paper_path: Path, output_path: Path = None):
    """
    处理论文并输出为 JSON
    
    Args:
        paper_path: 论文 Markdown 文件路径
        output_path: 输出 JSON 文件路径（可选）
    """
    
    print(f"处理论文: {paper_path.name}")
    print("=" * 80)
    
    # 读取文件
    with open(paper_path, 'r', encoding='utf-8') as f:
        markdown_text = f.read()
    
    # 1. 清洗 Markdown
    print("\n步骤 1: 清洗 Markdown...")
    cleaner = MarkdownCleaner()
    cleaned_doc = cleaner.clean(markdown_text)
    
    print(f"  - 删除图片: {cleaned_doc.removed_elements.get('images', 0)}")
    print(f"  - 删除元数据行: {cleaned_doc.removed_elements.get('metadata_lines', 0)}")
    print(f"  - 转换 HTML 标签: {cleaned_doc.removed_elements.get('html_tags', 0)}")
    print(f"  - 识别表格: {len(cleaned_doc.tables)}")
    
    # 2. 提取句子
    print("\n步骤 2: 提取句子...")
    extractor = SentenceExtractor()
    sentences = extractor.extract(cleaned_doc)
    
    print(f"  - 提取句子数: {len(sentences)}")
    
    # 3. 构建 JSON 输出
    print("\n步骤 3: 构建 JSON 输出...")
    
    # 提取文档标题（从第一个 H1 标题）
    document_title = "Unknown"
    for line in cleaned_doc.text.split('\n'):
        if line.strip().startswith('# '):
            document_title = line.strip()[2:].strip()
            break
    
    # 构建句子条目列表
    sentence_entries = []
    for idx, sent in enumerate(sentences):
        sent_id = generate_sentence_id(paper_path.name, sent.location, idx)
        sent_dict = sentence_to_dict(sent, sent_id)
        sentence_entries.append(sent_dict)
    
    # 构建表格条目列表
    table_entries = []
    for idx, table in enumerate(cleaned_doc.tables):
        table_id = f"{Path(paper_path.name).stem}_table_{idx}"
        table_entry = {
            "id": table_id,
            "content": table.content,
            "keywords": [],  # 暂时为空，等待 LLM 提取
            "location": {
                "section_path": [],  # 需要从句子中推断
                "section_id": "unknown",
                "paragraph_index": -1,
                "sentence_index": -1,
                "line_range": [table.start_line, table.end_line],
                "page_reference": None
            },
            "metadata": {
                "rows": table.rows,
                "columns": table.columns,
                "headers": table.headers
            }
        }
        table_entries.append(table_entry)
    
    # 构建完整的输出结构
    output_data = {
        "source_file": paper_path.name,
        "document_title": document_title,
        "processing_timestamp": datetime.now().isoformat(),
        "sentences": sentence_entries,
        "tables": table_entries,
        "processing_stats": {
            "total_sentences": len(sentences),
            "total_tables": len(cleaned_doc.tables),
            "original_line_count": cleaned_doc.original_line_count,
            "cleaned_line_count": cleaned_doc.cleaned_line_count,
            "removed_images": cleaned_doc.removed_elements.get('images', 0),
            "removed_metadata_lines": cleaned_doc.removed_elements.get('metadata_lines', 0),
            "converted_html_tags": cleaned_doc.removed_elements.get('html_tags', 0)
        }
    }
    
    # 4. 输出 JSON
    print("\n步骤 4: 输出 JSON...")
    
    # 如果没有指定输出路径，使用默认路径
    if output_path is None:
        output_dir = Path("qwen2.5B/output")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"{paper_path.stem}_sentences.json"
    
    # 写入 JSON 文件
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"  - 输出文件: {output_path}")
    print(f"  - 文件大小: {output_path.stat().st_size / 1024:.2f} KB")
    
    # 5. 显示统计信息
    print("\n" + "=" * 80)
    print("处理完成！")
    print("\n统计信息:")
    print(f"  - 文档标题: {document_title}")
    print(f"  - 总句子数: {len(sentences)}")
    print(f"  - 总表格数: {len(cleaned_doc.tables)}")
    print(f"  - 处理时间: {datetime.now().isoformat()}")
    
    # 6. 显示 JSON 结构示例
    print("\nJSON 结构示例（前 3 个句子）:")
    print("-" * 80)
    print(json.dumps(output_data["sentences"][:3], ensure_ascii=False, indent=2))
    
    if output_data["tables"]:
        print("\n表格条目示例（第 1 个表格）:")
        print("-" * 80)
        print(json.dumps(output_data["tables"][0], ensure_ascii=False, indent=2))
    
    return output_data


def main():
    """主函数"""
    
    # 选择一篇论文进行测试
    paper_path = Path("marker_service/outputs/Enhanced-properties-of-LiFePO4-C-cathode-materials-_2014_Materials-Chemistry.md")
    
    if not paper_path.exists():
        print(f"错误: 文件不存在 {paper_path}")
        return
    
    # 处理论文并输出 JSON
    output_data = process_paper_to_json(paper_path)
    
    print("\n" + "=" * 80)
    print("✓ JSON 输出测试完成！")
    print(f"\n输出文件已保存到: qwen2.5B/output/{paper_path.stem}_sentences.json")


if __name__ == "__main__":
    main()
