"""
关键词提取引擎单元测试

测试 KeywordExtractionEngine 类的各项功能。
"""

import pytest
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from model_service.extraction import (
    KeywordExtractionEngine,
    ExtractionConfig,
    ExtractionResult
)


class TestKeywordExtractionEngine:
    """测试 KeywordExtractionEngine 类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.config = ExtractionConfig(
            api_base_url="http://localhost:8003",
            model_name="Qwen/Qwen2.5-1.5B-Instruct",
            max_retries=3,
            timeout=30,
            batch_size=10
        )
        self.engine = KeywordExtractionEngine(self.config)
    
    def teardown_method(self):
        """每个测试方法后的清理"""
        self.engine.close()
    
    def test_build_sentence_prompt(self):
        """测试句子提示词构建"""
        sentence = "The study investigates the effects of temperature on enzyme activity."
        prompt = self.engine.build_prompt(sentence, is_table=False)
        
        assert sentence in prompt
        assert "关键词" in prompt
        assert "JSON" in prompt
        assert "1-5" in prompt
        assert "技术术语" in prompt
    
    def test_build_table_prompt(self):
        """测试表格提示词构建"""
        table_content = "| Method | Accuracy |\n|--------|----------|\n| A | 95% |"
        prompt = self.engine.build_prompt(table_content, is_table=True)
        
        assert table_content in prompt
        assert "表格" in prompt
        assert "表头" in prompt
        assert "数据类型" in prompt
        assert "JSON" in prompt
    
    def test_parse_response_valid_json(self):
        """测试解析有效的 JSON 响应"""
        response = {
            'choices': [{
                'message': {
                    'content': '{"keywords": ["enzyme", "temperature", "activity"]}'
                }
            }]
        }
        
        keywords = self.engine.parse_response(response)
        
        assert len(keywords) == 3
        assert "enzyme" in keywords
        assert "temperature" in keywords
        assert "activity" in keywords
    
    def test_parse_response_with_extra_text(self):
        """测试解析带额外文本的响应"""
        response = {
            'choices': [{
                'message': {
                    'content': '这是关键词：\n{"keywords": ["protein", "structure"]}\n希望有帮助'
                }
            }]
        }
        
        keywords = self.engine.parse_response(response)
        
        assert len(keywords) == 2
        assert "protein" in keywords
        assert "structure" in keywords
    
    def test_parse_response_invalid_json(self):
        """测试解析无效 JSON"""
        response = {
            'choices': [{
                'message': {
                    'content': 'This is not valid JSON'
                }
            }]
        }
        
        with pytest.raises(ValueError, match="响应中未找到 JSON 对象"):
            self.engine.parse_response(response)
    
    def test_parse_response_missing_keywords_field(self):
        """测试缺少 keywords 字段"""
        response = {
            'choices': [{
                'message': {
                    'content': '{"results": ["keyword1", "keyword2"]}'
                }
            }]
        }
        
        with pytest.raises(ValueError, match="缺少 'keywords' 字段"):
            self.engine.parse_response(response)
    
    def test_parse_response_keywords_not_list(self):
        """测试 keywords 不是列表"""
        response = {
            'choices': [{
                'message': {
                    'content': '{"keywords": "not a list"}'
                }
            }]
        }
        
        with pytest.raises(ValueError, match="应该是列表"):
            self.engine.parse_response(response)
    
    def test_filter_stopwords_chinese(self):
        """测试过滤中文停用词"""
        keywords = ["研究", "的", "方法", "是", "实验"]
        filtered = self.engine._filter_and_normalize_keywords(keywords)
        
        assert "研究" in filtered
        assert "方法" in filtered
        assert "实验" in filtered
        assert "的" not in filtered
        assert "是" not in filtered
    
    def test_filter_stopwords_english(self):
        """测试过滤英文停用词"""
        keywords = ["protein", "the", "structure", "and", "function"]
        filtered = self.engine._filter_and_normalize_keywords(keywords)
        
        assert "protein" in filtered
        assert "structure" in filtered
        assert "function" in filtered
        assert "the" not in filtered
        assert "and" not in filtered
    
    def test_normalize_keywords_lowercase(self):
        """测试关键词规范化为小写"""
        keywords = ["Protein", "Structure", "Function"]
        filtered = self.engine._filter_and_normalize_keywords(keywords)
        
        # 包含大写字母的词保留原样
        assert "Protein" in filtered or "protein" in filtered
    
    def test_normalize_keywords_preserve_acronyms(self):
        """测试保留缩写词的大写"""
        keywords = ["DNA", "RNA", "PCR", "CRISPR"]
        filtered = self.engine._filter_and_normalize_keywords(keywords)
        
        # 全大写的缩写应该保留
        assert "DNA" in filtered
        assert "RNA" in filtered
        assert "PCR" in filtered
        assert "CRISPR" in filtered
    
    def test_filter_empty_keywords(self):
        """测试过滤空关键词"""
        keywords = ["valid", "", "  ", "another"]
        filtered = self.engine._filter_and_normalize_keywords(keywords)
        
        assert len(filtered) == 2
        assert "valid" in filtered
        assert "another" in filtered
    
    def test_filter_non_string_keywords(self):
        """测试过滤非字符串关键词"""
        keywords = ["valid", 123, None, "another", ["list"]]
        filtered = self.engine._filter_and_normalize_keywords(keywords)
        
        assert len(filtered) == 2
        assert "valid" in filtered
        assert "another" in filtered
    
    @patch('model_service.extraction.KeywordExtractionEngine._call_llm')
    def test_extract_keywords_success(self, mock_call_llm):
        """测试成功提取关键词"""
        # 模拟 LLM 响应
        mock_call_llm.return_value = {
            'choices': [{
                'message': {
                    'content': '{"keywords": ["enzyme", "temperature", "activity"]}'
                }
            }]
        }
        
        sentence = "The study investigates enzyme activity at different temperatures."
        result = self.engine.extract_keywords(sentence)
        
        assert result.success is True
        assert len(result.keywords) == 3
        assert result.retry_count == 0
        assert result.error_message is None
    
    @patch('model_service.extraction.KeywordExtractionEngine._call_llm')
    def test_extract_keywords_retry_on_timeout(self, mock_call_llm):
        """测试超时重试逻辑"""
        import requests
        
        # 前两次超时，第三次成功
        mock_call_llm.side_effect = [
            requests.exceptions.Timeout("Timeout 1"),
            requests.exceptions.Timeout("Timeout 2"),
            {
                'choices': [{
                    'message': {
                        'content': '{"keywords": ["keyword1", "keyword2"]}'
                    }
                }]
            }
        ]
        
        sentence = "Test sentence"
        result = self.engine.extract_keywords(sentence)
        
        assert result.success is True
        assert len(result.keywords) == 2
        assert result.retry_count == 2
    
    @patch('model_service.extraction.KeywordExtractionEngine._call_llm')
    def test_extract_keywords_max_retries_exceeded(self, mock_call_llm):
        """测试超过最大重试次数"""
        import requests
        
        # 所有尝试都超时
        mock_call_llm.side_effect = requests.exceptions.Timeout("Timeout")
        
        sentence = "Test sentence"
        result = self.engine.extract_keywords(sentence)
        
        assert result.success is False
        assert len(result.keywords) == 0
        assert result.error_message is not None
        assert "超时" in result.error_message
    
    @patch('model_service.extraction.KeywordExtractionEngine._call_llm')
    def test_extract_keywords_rate_limit(self, mock_call_llm):
        """测试速率限制处理"""
        import requests
        
        # 模拟速率限制错误
        mock_response = Mock()
        mock_response.status_code = 429
        error = requests.exceptions.HTTPError(response=mock_response)
        
        mock_call_llm.side_effect = [
            error,
            {
                'choices': [{
                    'message': {
                        'content': '{"keywords": ["keyword1"]}'
                    }
                }]
            }
        ]
        
        sentence = "Test sentence"
        result = self.engine.extract_keywords(sentence)
        
        assert result.success is True
        assert len(result.keywords) == 1
    
    @patch('model_service.extraction.KeywordExtractionEngine.extract_keywords')
    def test_extract_batch(self, mock_extract):
        """测试批量提取"""
        # 模拟提取结果
        mock_extract.side_effect = [
            ExtractionResult(keywords=["k1", "k2"], success=True),
            ExtractionResult(keywords=["k3", "k4"], success=True),
            ExtractionResult(keywords=[], success=False, error_message="Error")
        ]
        
        sentences = ["Sentence 1", "Sentence 2", "Sentence 3"]
        results = self.engine.extract_batch(sentences)
        
        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is True
        assert results[2].success is False
    
    def test_extract_table_keywords(self):
        """测试表格关键词提取"""
        table_content = "| Method | Accuracy |\n|--------|----------|\n| A | 95% |"
        headers = ["Method", "Accuracy"]
        
        with patch.object(self.engine, 'extract_keywords') as mock_extract:
            mock_extract.return_value = ExtractionResult(
                keywords=["method", "accuracy", "performance"],
                success=True
            )
            
            result = self.engine.extract_table_keywords(table_content, headers)
            
            assert result.success is True
            assert len(result.keywords) == 3
            
            # 验证调用时包含了表头信息
            call_args = mock_extract.call_args
            assert "Method" in call_args[0][0]
            assert "Accuracy" in call_args[0][0]
            assert call_args[1]['is_table'] is True
    
    def test_failed_sentences_tracking(self):
        """测试失败句子追踪"""
        with patch.object(self.engine, '_call_llm') as mock_call:
            import requests
            mock_call.side_effect = requests.exceptions.Timeout("Timeout")
            
            sentence1 = "Failed sentence 1"
            sentence2 = "Failed sentence 2"
            
            self.engine.extract_keywords(sentence1)
            self.engine.extract_keywords(sentence2)
            
            failed = self.engine.get_failed_sentences()
            
            assert len(failed) == 2
            assert any(sentence1 in f[0] for f in failed)
            assert any(sentence2 in f[0] for f in failed)
    
    def test_clear_failed_sentences(self):
        """测试清空失败句子列表"""
        with patch.object(self.engine, '_call_llm') as mock_call:
            import requests
            mock_call.side_effect = requests.exceptions.Timeout("Timeout")
            
            self.engine.extract_keywords("Failed sentence")
            assert len(self.engine.get_failed_sentences()) == 1
            
            self.engine.clear_failed_sentences()
            assert len(self.engine.get_failed_sentences()) == 0
    
    def test_session_connection_pool(self):
        """测试会话连接池配置"""
        assert self.engine.session is not None
        
        # 验证适配器已配置
        adapter = self.engine.session.get_adapter("http://")
        assert adapter is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
