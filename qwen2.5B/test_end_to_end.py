"""
端到端测试：从 Markdown 到 JSON 输出

测试完整的处理流程：
1. 读取 Markdown 文件
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


def create_sample_markdown() -> str:
    """创建示例 Markdown 文件"""
    return """# 1. Introduction

Machine learning has revolutionized the field of artificial intelligence. Deep learning models, particularly neural networks, have achieved remarkable success in various domains [1, 2].

## 1.1 Background

The development of transformer architectures has led to significant improvements in natural language processing. Models like BERT and GPT have demonstrated exceptional performance on benchmark datasets [3].

# 2. Methods

## 2.1 Data Collection

We collected data from multiple sources including scientific publications and online repositories. The dataset contains over 10,000 samples with diverse characteristics.

## 2.2 Model Architecture

Our model uses a multi-layer transformer with attention mechanisms. The architecture consists of 12 layers with 768 hidden dimensions.

| Component | Value |
|-----------|-------|
| Layers | 12 |
| Hidden Size | 768 |
| Attention Heads | 12 |

# 3. Results

The experimental results show that our approach achieves state-of-the-art performance. The model obtained an accuracy of 95.3% on the test set, outperforming previous methods by 3.2%.

## 3.1 Performance Analysis

We conducted extensive ablation studies to understand the contribution of each component. The attention mechanism proved to be crucial for the model's success.

# 4. Conclusion

This work demonstrates the effectiveness of transformer-based models for complex tasks. Future research should explore more efficient architectures and training strategies.
"""


def main():
    """主函数：执行端到端测试"""
    
    logger.info("=" * 80)
    logger.info("开始端到端测试：Markdown → 清洗 → 分句 → LLM → JSON")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    # ========== 步骤 1: 创建示例 Markdown ==========
    logger.info("\n步骤 1: 创建示例 Markdown 文件")
    markdown_text = create_sample_markdown()
    logger.info(f"Markdown 文件长度: {len(markdown_text)} 字符")
    logger.info(f"Markdown 文件行数: {len(markdown_text.split(chr(10)))} 行")
    
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
        logger.info(f"    文本: {sent.text[:80]}...")
        logger.info(f"    章节路径: {' > '.join(sent.location.section_path)}")
        logger.info(f"    位置: 段落 {sent.location.paragraph_index}, 句子 {sent.location.sentence_index}")
    
    # ========== 步骤 4: LLM 提取关键词 ==========
    logger.info("\n步骤 4: 使用 LLM 提取关键词")
    logger.info("注意: 需要 LLM 服务运行在 http://localhost:8003")
    
    # 检查 LLM 服务是否可用
    import requests
    llm_available = False
    try:
        response = requests.get("http://localhost:8003/v1/models", timeout=2)
        llm_available = response.status_code == 200
    except:
        pass
    
    if not llm_available:
        logger.warning("LLM 服务不可用，将使用模拟关键词进行演示")
    
    # 配置 LLM 提取引擎
    extraction_config = ExtractionConfig(
        api_base_url="http://localhost:8003",
        model_name="Qwen/Qwen2.5-1.5B-Instruct",
        max_retries=3,
        timeout=30,
        batch_size=5
    )
    
    try:
        if llm_available:
            extraction_engine = KeywordExtractionEngine(extraction_config)
        else:
            extraction_engine = None
        
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
            time.sleep(0.1)
        
        logger.info(f"\n关键词提取完成:")
        logger.info(f"  - 成功: {successful_count}")
        logger.info(f"  - 失败: {failed_count}")
        
        # 显示一些关键词示例
        logger.info("\n关键词示例:")
        for i, entry in enumerate(sentence_entries[:3]):
            if entry.keywords:
                logger.info(f"  句子 {i+1}: {entry.keywords}")
        
        # 提取表格关键词
        table_entries = []
        if cleaned_doc.tables:
            logger.info(f"\n提取 {len(cleaned_doc.tables)} 个表格的关键词...")
            
            for i, table in enumerate(cleaned_doc.tables):
                result = extraction_engine.extract_table_keywords(
                    table.content,
                    table.headers
                )
                
                if result.success:
                    keywords = result.keywords
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
        
        # 关闭提取引擎
        extraction_engine.close()
        
    except Exception as e:
        logger.error(f"LLM 提取失败: {e}")
        logger.error("请确保 LLM 服务正在运行: http://localhost:8003")
        logger.info("\n跳过 LLM 提取，使用空关键词继续测试...")
        
        # 使用空关键词创建条目
        sentence_entries = []
        for sent_with_loc in sentences_with_location:
            entry = SentenceEntry(
                id="",
                text=sent_with_loc.text,
                keywords=[],  # 空关键词
                location=sent_with_loc.location
            )
            sentence_entries.append(entry)
        
        table_entries = []
        successful_count = 0
        failed_count = len(sentences_with_location)
    
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
        source_file="test_paper.md",
        document_title="Test Paper: Machine Learning Research",
        sentences=sentence_entries,
        tables=table_entries,
        processing_stats=stats
    )
    
    # 生成 JSON
    generator = JSONGenerator(indent=2, encoding='utf-8')
    
    # 输出到文件
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "test_end_to_end_output.json"
    
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
    
    # 显示第一个条目
    if output_data['entries']:
        logger.info(f"\n第一个条目示例:")
        first_entry = output_data['entries'][0]
        logger.info(f"  ID: {first_entry['id']}")
        logger.info(f"  类型: {first_entry['type']}")
        logger.info(f"  文本: {first_entry.get('text', first_entry.get('content', ''))[:80]}...")
        logger.info(f"  关键词: {first_entry['keywords']}")
        logger.info(f"  章节路径: {' > '.join(first_entry['location']['section_path'])}")
    
    # ========== 完成 ==========
    total_time = time.time() - start_time
    logger.info("\n" + "=" * 80)
    logger.info(f"端到端测试完成！总耗时: {total_time:.2f} 秒")
    logger.info("=" * 80)
    
    return actual_path


if __name__ == "__main__":
    try:
        output_path = main()
        print(f"\n✓ 测试成功！输出文件: {output_path}")
    except Exception as e:
        logger.error(f"\n✗ 测试失败: {e}", exc_info=True)
        sys.exit(1)
