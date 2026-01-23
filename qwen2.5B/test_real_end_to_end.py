"""
真实端到端测试：使用真实 Markdown 文件

测试完整的处理流程：
1. 读取真实 Markdown 文件（从 marker_service/outputs）
2. 清洗文本
3. 提取句子和位置信息
4. 使用 LLM 提取关键词
5. 生成并保存 JSON 文件
"""

import sys
import time
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from text_processor.cleaner import MarkdownCleaner
from text_processor.extractor import SentenceExtractor
from text_processor.models import (
    ProcessedData,
    SentenceEntry,
    TableEntry,
    ProcessingStats
)
from model_service.extraction import KeywordExtractionEngine, ExtractionConfig
from output.generator import JSONGenerator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """主函数：执行端到端测试"""
    
    logger.info("=" * 80)
    logger.info("真实端到端测试：Markdown → 清洗 → 分句 → LLM → JSON")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    # ========== 步骤 1: 读取真实 Markdown 文件 ==========
    logger.info("\n步骤 1: 读取真实 Markdown 文件")
    
    # 选择一个较小的文件进行测试
    markdown_dir = Path(__file__).parent.parent / "marker_service" / "outputs"
    markdown_files = list(markdown_dir.glob("*.md"))
    
    if not markdown_files:
        logger.error("未找到 Markdown 文件！")
        return
    
    # 选择第一个文件
    markdown_file = markdown_files[0]
    logger.info(f"使用文件: {markdown_file.name}")
    
    with open(markdown_file, 'r', encoding='utf-8') as f:
        markdown_text = f.read()
    
    logger.info(f"文件大小: {len(markdown_text)} 字符")
    logger.info(f"文件行数: {len(markdown_text.split(chr(10)))} 行")
    
    # ========== 步骤 2: 清洗 Markdown ==========
    logger.info("\n步骤 2: 清洗 Markdown 文本")
    cleaner = MarkdownCleaner()
    cleaned_doc = cleaner.clean(markdown_text)
    
    logger.info(f"清洗完成:")
    logger.info(f"  - 原始行数: {cleaned_doc.original_line_count}")
    logger.info(f"  - 清洗后行数: {cleaned_doc.cleaned_line_count}")
    logger.info(f"  - 删除的图片: {cleaned_doc.removed_elements.get('images', 0)}")
    logger.info(f"  - 转换的 HTML 标签: {cleaned_doc.removed_elements.get('html_tags', 0)}")
    logger.info(f"  - 删除的元数据行: {cleaned_doc.removed_elements.get('metadata_lines', 0)}")
    logger.info(f"  - 识别的表格: {len(cleaned_doc.tables)}")
    
    # ========== 步骤 3: 提取句子 ==========
    logger.info("\n步骤 3: 提取句子和位置信息")
    extractor = SentenceExtractor()
    sentences_with_location = extractor.extract(cleaned_doc)
    
    logger.info(f"提取完成:")
    logger.info(f"  - 提取的句子数: {len(sentences_with_location)}")
    
    # 显示前几个句子
    logger.info("\n前 3 个句子示例:")
    for i, sent in enumerate(sentences_with_location[:3]):
        logger.info(f"\n  句子 {i+1}:")
        logger.info(f"    文本: {sent.text[:100]}...")
        logger.info(f"    章节路径: {' > '.join(sent.location.section_path) if sent.location.section_path else '(根)'}")
        logger.info(f"    位置: 段落 {sent.location.paragraph_index}, 句子 {sent.location.sentence_index}")
    
    # 限制处理的句子数量（用于快速测试）
    max_sentences = 20
    if len(sentences_with_location) > max_sentences:
        logger.info(f"\n注意: 为了快速测试，只处理前 {max_sentences} 个句子")
        sentences_with_location = sentences_with_location[:max_sentences]
    
    # ========== 步骤 4: LLM 提取关键词 ==========
    logger.info("\n步骤 4: 使用 LLM 提取关键词")
    
    # 配置 LLM 提取引擎
    extraction_config = ExtractionConfig(
        api_base_url="http://localhost:8003",
        model_name="Qwen/Qwen2.5-1.5B-Instruct",
        max_retries=3,
        timeout=30,
        batch_size=5
    )
    
    extraction_engine = KeywordExtractionEngine(extraction_config)
    
    # 提取句子关键词
    sentence_entries = []
    successful_count = 0
    failed_count = 0
    
    logger.info(f"开始提取 {len(sentences_with_location)} 个句子的关键词...")
    
    for i, sent_with_loc in enumerate(sentences_with_location):
        if (i + 1) % 5 == 0:
            logger.info(f"  进度: {i+1}/{len(sentences_with_location)}")
        
        # 提取关键词
        result = extraction_engine.extract_keywords(sent_with_loc.text, is_table=False)
        
        if result.success:
            successful_count += 1
            keywords = result.keywords
            logger.debug(f"  句子 {i+1} 关键词: {keywords}")
        else:
            failed_count += 1
            keywords = []
            logger.warning(f"  句子 {i+1} 提取失败: {result.error_message}")
        
        # 创建句子条目
        entry = SentenceEntry(
            id="",  # 将由 JSONGenerator 生成
            text=sent_with_loc.text,
            keywords=keywords,
            location=sent_with_loc.location
        )
        sentence_entries.append(entry)
        
        # 避免过快请求
        time.sleep(0.2)
    
    logger.info(f"\n关键词提取完成:")
    logger.info(f"  - 成功: {successful_count}")
    logger.info(f"  - 失败: {failed_count}")
    
    # 显示一些关键词示例
    logger.info("\n关键词示例:")
    for i, entry in enumerate(sentence_entries[:5]):
        if entry.keywords:
            logger.info(f"  句子 {i+1}: {entry.keywords}")
            logger.info(f"    原文: {entry.text[:80]}...")
    
    # 提取表格关键词
    table_entries = []
    if cleaned_doc.tables:
        logger.info(f"\n提取 {min(len(cleaned_doc.tables), 3)} 个表格的关键词...")
        
        for i, table in enumerate(cleaned_doc.tables[:3]):  # 只处理前3个表格
            result = extraction_engine.extract_table_keywords(
                table.content,
                table.headers
            )
            
            if result.success:
                keywords = result.keywords
                logger.info(f"  表格 {i+1} 关键词: {keywords}")
            else:
                keywords = []
                logger.warning(f"  表格 {i+1} 提取失败: {result.error_message}")
            
            # 创建表格条目
            # 为表格创建位置信息
            location = sentences_with_location[0].location if sentences_with_location else None
            if location:
                entry = TableEntry(
                    id="",  # 将由 JSONGenerator 生成
                    content=table.content,
                    keywords=keywords,
                    location=location,
                    metadata={
                        "rows": table.rows,
                        "columns": table.columns,
                        "headers": table.headers
                    }
                )
                table_entries.append(entry)
            
            time.sleep(0.2)
    
    # 关闭提取引擎
    extraction_engine.close()
    
    # ========== 步骤 5: 生成 JSON 输出 ==========
    logger.info("\n步骤 5: 生成 JSON 输出")
    
    # 创建处理统计
    processing_time = time.time() - start_time
    stats = ProcessingStats(
        total_sentences=len(sentence_entries),
        total_tables=len(table_entries),
        successful_extractions=successful_count,
        failed_extractions=failed_count,
        processing_time=processing_time
    )
    
    # 创建处理数据
    processed_data = ProcessedData(
        source_file=markdown_file.name,
        document_title=markdown_file.stem,
        sentences=sentence_entries,
        tables=table_entries,
        processing_stats=stats
    )
    
    # 生成 JSON
    generator = JSONGenerator(indent=2, encoding='utf-8')
    
    # 输出到文件
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"{markdown_file.stem}_output.json"
    
    actual_path = generator.generate_and_write(
        processed_data,
        str(output_path),
        overwrite=True
    )
    
    logger.info(f"JSON 文件已生成: {actual_path}")
    
    # 读取并显示部分内容
    import json
    with open(actual_path, 'r', encoding='utf-8') as f:
        output_data = json.load(f)
    
    logger.info(f"\nJSON 输出统计:")
    logger.info(f"  - 总条目数: {len(output_data['entries'])}")
    logger.info(f"  - 句子条目: {sum(1 for e in output_data['entries'] if e['type'] == 'sentence')}")
    logger.info(f"  - 表格条目: {sum(1 for e in output_data['entries'] if e['type'] == 'table')}")
    
    # 显示前几个条目
    logger.info(f"\n前 3 个条目:")
    for i, entry in enumerate(output_data['entries'][:3]):
        logger.info(f"\n  条目 {i+1}:")
        logger.info(f"    ID: {entry['id']}")
        logger.info(f"    类型: {entry['type']}")
        text_key = 'text' if entry['type'] == 'sentence' else 'content'
        logger.info(f"    内容: {entry.get(text_key, '')[:80]}...")
        logger.info(f"    关键词: {entry['keywords']}")
    
    # ========== 完成 ==========
    total_time = time.time() - start_time
    logger.info("\n" + "=" * 80)
    logger.info(f"真实端到端测试完成！总耗时: {total_time:.2f} 秒")
    logger.info(f"输出文件: {actual_path}")
    logger.info("=" * 80)
    
    return actual_path


if __name__ == "__main__":
    try:
        output_path = main()
        print(f"\n✓ 测试成功！输出文件: {output_path}")
    except Exception as e:
        logger.error(f"\n✗ 测试失败: {e}", exc_info=True)
        sys.exit(1)
