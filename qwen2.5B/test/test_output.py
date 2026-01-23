"""
输出模块单元测试

测试 JSON 生成器的功能。
"""

import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from output.generator import JSONGenerator
from text_processor.models import (
    ProcessedData,
    SentenceEntry,
    TableEntry,
    LocationMetadata,
    ProcessingStats
)


class TestJSONGenerator:
    """测试 JSON 生成器"""
    
    @pytest.fixture
    def generator(self):
        """创建 JSON 生成器实例"""
        return JSONGenerator(indent=2, encoding='utf-8')
    
    @pytest.fixture
    def sample_location(self):
        """创建示例位置元数据"""
        return LocationMetadata(
            section_path=["1. Introduction", "1.1 Background"],
            section_id="1.1",
            paragraph_index=0,
            sentence_index=0,
            line_range=(10, 12),
            page_reference="page_1"
        )
    
    @pytest.fixture
    def sample_sentence_entry(self, sample_location):
        """创建示例句子条目"""
        return SentenceEntry(
            id="test_1_1_p0_s0",
            text="This is a test sentence about machine learning.",
            keywords=["machine learning", "test"],
            location=sample_location
        )
    
    @pytest.fixture
    def sample_table_entry(self, sample_location):
        """创建示例表格条目"""
        return TableEntry(
            id="test_1_1_p0_s1",
            content="| Header1 | Header2 |\n|---------|---------|",
            keywords=["table", "data"],
            location=sample_location,
            metadata={"rows": 2, "columns": 2}
        )
    
    @pytest.fixture
    def sample_processed_data(self, sample_sentence_entry, sample_table_entry):
        """创建示例处理数据"""
        return ProcessedData(
            source_file="test_paper.md",
            document_title="Test Paper",
            sentences=[sample_sentence_entry],
            tables=[sample_table_entry],
            processing_stats=ProcessingStats(
                total_sentences=1,
                total_tables=1,
                successful_extractions=2,
                failed_extractions=0,
                processing_time=1.5
            )
        )
    
    def test_generate_id(self, generator):
        """测试 ID 生成"""
        # 测试基本 ID 生成
        id1 = generator.generate_id("doc1", "1.1", 0, 0)
        assert id1 == "doc1_1_1_p0_s0"
        
        # 测试不同参数
        id2 = generator.generate_id("doc2", "2.3", 5, 10)
        assert id2 == "doc2_2_3_p5_s10"
        
        # 测试 section_id 中的特殊字符处理
        id3 = generator.generate_id("doc1", "1.2.3", 0, 0)
        assert id3 == "doc1_1_2_3_p0_s0"
    
    def test_generate_id_uniqueness(self, generator):
        """测试 ID 唯一性"""
        # 生成多个 ID
        ids = set()
        for p_idx in range(3):
            for s_idx in range(5):
                id_str = generator.generate_id("doc1", "1.1", p_idx, s_idx)
                ids.add(id_str)
        
        # 验证所有 ID 都是唯一的
        assert len(ids) == 3 * 5
    
    def test_format_location_metadata(self, generator, sample_location):
        """测试位置元数据格式化"""
        formatted = generator.format_location_metadata(sample_location)
        
        # 验证所有字段都存在
        assert "section_path" in formatted
        assert "section_id" in formatted
        assert "paragraph_index" in formatted
        assert "sentence_index" in formatted
        assert "line_range" in formatted
        assert "page_reference" in formatted
        
        # 验证值正确
        assert formatted["section_path"] == ["1. Introduction", "1.1 Background"]
        assert formatted["section_id"] == "1.1"
        assert formatted["paragraph_index"] == 0
        assert formatted["sentence_index"] == 0
        assert formatted["line_range"]["start"] == 10
        assert formatted["line_range"]["end"] == 12
        assert formatted["page_reference"] == "page_1"
    
    def test_format_sentence_entry(self, generator, sample_location):
        """测试句子条目格式化"""
        sentence = "This is a test sentence."
        keywords = ["test", "sentence"]
        doc_id = "test_doc"
        
        formatted = generator.format_sentence_entry(
            sentence, keywords, sample_location, doc_id
        )
        
        # 验证所有字段
        assert "id" in formatted
        assert "type" in formatted
        assert "text" in formatted
        assert "keywords" in formatted
        assert "location" in formatted
        
        # 验证值
        assert formatted["type"] == "sentence"
        assert formatted["text"] == sentence
        assert formatted["keywords"] == keywords
        assert formatted["id"].startswith(doc_id)
    
    def test_format_table_entry(self, generator, sample_location):
        """测试表格条目格式化"""
        content = "| A | B |\n|---|---|"
        keywords = ["table"]
        doc_id = "test_doc"
        metadata = {"rows": 2, "columns": 2}
        
        formatted = generator.format_table_entry(
            content, keywords, sample_location, doc_id, metadata
        )
        
        # 验证所有字段
        assert "id" in formatted
        assert "type" in formatted
        assert "content" in formatted
        assert "keywords" in formatted
        assert "location" in formatted
        assert "table_metadata" in formatted
        
        # 验证值
        assert formatted["type"] == "table"
        assert formatted["content"] == content
        assert formatted["keywords"] == keywords
        assert formatted["table_metadata"] == metadata
    
    def test_add_metadata(self, generator):
        """测试元数据添加"""
        output = {"entries": []}
        source_file = "test.md"
        document_title = "Test Document"
        stats = ProcessingStats(
            total_sentences=10,
            total_tables=2,
            successful_extractions=12,
            failed_extractions=0,
            processing_time=5.5
        )
        
        result = generator.add_metadata(output, source_file, document_title, stats)
        
        # 验证元数据存在
        assert "metadata" in result
        metadata = result["metadata"]
        
        # 验证所有必需字段
        assert "source_file" in metadata
        assert "document_title" in metadata
        assert "processing_timestamp" in metadata
        assert "statistics" in metadata
        
        # 验证值
        assert metadata["source_file"] == source_file
        assert metadata["document_title"] == document_title
        
        # 验证统计信息
        statistics = metadata["statistics"]
        assert statistics["total_sentences"] == 10
        assert statistics["total_tables"] == 2
        assert statistics["successful_extractions"] == 12
        assert statistics["failed_extractions"] == 0
        assert statistics["processing_time_seconds"] == 5.5
        
        # 验证时间戳格式
        timestamp = metadata["processing_timestamp"]
        # 应该能够解析为 datetime
        datetime.fromisoformat(timestamp)
    
    def test_generate_json(self, generator, sample_processed_data):
        """测试 JSON 生成"""
        json_str = generator.generate(sample_processed_data)
        
        # 验证是有效的 JSON
        data = json.loads(json_str)
        
        # 验证顶层结构
        assert "entries" in data
        assert "metadata" in data
        
        # 验证条目数量
        assert len(data["entries"]) == 2  # 1 句子 + 1 表格
        
        # 验证元数据
        metadata = data["metadata"]
        assert metadata["source_file"] == "test_paper.md"
        assert metadata["document_title"] == "Test Paper"
    
    def test_json_format_correctness(self, generator, sample_processed_data):
        """测试 JSON 格式正确性"""
        json_str = generator.generate(sample_processed_data)
        data = json.loads(json_str)
        
        # 验证句子条目格式
        sentence_entry = data["entries"][0]
        assert sentence_entry["type"] == "sentence"
        assert "id" in sentence_entry
        assert "text" in sentence_entry
        assert "keywords" in sentence_entry
        assert "location" in sentence_entry
        
        # 验证表格条目格式
        table_entry = data["entries"][1]
        assert table_entry["type"] == "table"
        assert "id" in table_entry
        assert "content" in table_entry
        assert "keywords" in table_entry
        assert "location" in table_entry
        assert "table_metadata" in table_entry
    
    def test_write_to_file(self, generator):
        """测试文件写入"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.json"
            json_str = '{"test": "data"}'
            
            # 写入文件
            actual_path = generator.write_to_file(json_str, str(output_path))
            
            # 验证文件存在
            assert Path(actual_path).exists()
            
            # 验证内容
            with open(actual_path, 'r', encoding='utf-8') as f:
                content = f.read()
            assert content == json_str
    
    def test_write_to_file_encoding(self, generator):
        """测试文件编码"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.json"
            # 包含中文和特殊字符
            json_str = '{"text": "这是中文测试 α β γ"}'
            
            # 写入文件
            actual_path = generator.write_to_file(json_str, str(output_path))
            
            # 读取并验证
            with open(actual_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 验证中文和特殊字符正确保存
            assert "这是中文测试" in content
            assert "α β γ" in content
    
    def test_write_to_file_existing(self, generator):
        """测试文件已存在的情况"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.json"
            
            # 第一次写入
            json_str1 = '{"version": 1}'
            path1 = generator.write_to_file(json_str1, str(output_path))
            
            # 第二次写入（不覆盖）
            json_str2 = '{"version": 2}'
            path2 = generator.write_to_file(json_str2, str(output_path), overwrite=False)
            
            # 验证生成了不同的文件
            assert path1 != path2
            
            # 验证两个文件都存在
            assert Path(path1).exists()
            assert Path(path2).exists()
            
            # 验证第二个文件名包含时间戳
            assert "_" in Path(path2).stem
    
    def test_write_to_file_overwrite(self, generator):
        """测试覆盖已存在的文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.json"
            
            # 第一次写入
            json_str1 = '{"version": 1}'
            path1 = generator.write_to_file(json_str1, str(output_path))
            
            # 第二次写入（覆盖）
            json_str2 = '{"version": 2}'
            path2 = generator.write_to_file(json_str2, str(output_path), overwrite=True)
            
            # 验证路径相同
            assert path1 == path2
            
            # 验证内容被覆盖
            with open(path2, 'r', encoding='utf-8') as f:
                content = f.read()
            assert '"version": 2' in content
    
    def test_generate_and_write(self, generator, sample_processed_data):
        """测试生成并写入"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.json"
            
            # 生成并写入
            actual_path = generator.generate_and_write(
                sample_processed_data,
                str(output_path)
            )
            
            # 验证文件存在
            assert Path(actual_path).exists()
            
            # 验证内容
            with open(actual_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 验证结构
            assert "entries" in data
            assert "metadata" in data
            assert len(data["entries"]) == 2
    
    def test_json_indentation(self):
        """测试 JSON 缩进"""
        generator = JSONGenerator(indent=4)
        
        stats = ProcessingStats()
        data = ProcessedData(
            source_file="test.md",
            document_title="Test",
            sentences=[],
            tables=[],
            processing_stats=stats
        )
        
        json_str = generator.generate(data)
        
        # 验证有缩进（多行）
        lines = json_str.split('\n')
        assert len(lines) > 1
        
        # 验证缩进空格数
        # 查找有缩进的行
        indented_lines = [line for line in lines if line.startswith('    ')]
        assert len(indented_lines) > 0
