"""
关键词提取引擎

使用 LLM 从句子和表格中提取关键词。
"""

import json
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


@dataclass
class ExtractionConfig:
    """提取配置"""
    api_base_url: str
    model_name: str
    max_retries: int = 3
    timeout: int = 30
    batch_size: int = 10
    temperature: float = 0.1
    max_tokens: int = 100


@dataclass
class ExtractionResult:
    """提取结果"""
    keywords: List[str]
    success: bool
    error_message: Optional[str] = None
    retry_count: int = 0


class KeywordExtractionEngine:
    """关键词提取引擎"""
    
    # 中文停用词列表
    STOPWORDS = {
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一',
        '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有',
        '看', '好', '自己', '这', '那', '里', '为', '与', '及', '等', '或', '但',
        '而', '之', '于', '以', '及其', '等等', '如', '若', '则', '即', '且', '并',
        '因', '由', '从', '对', '向', '往', '把', '被', '让', '给', '用', '比',
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
        'that', 'these', 'those', 'it', 'its', 'they', 'them', 'their'
    }
    
    def __init__(self, config: ExtractionConfig):
        """
        初始化关键词提取引擎
        
        Args:
            config: 提取配置
        """
        self.config = config
        self.session = self._create_session()
        self.failed_sentences: List[Tuple[str, str]] = []  # (sentence, error)
        
    def _create_session(self) -> requests.Session:
        """
        创建带连接池的 HTTP 会话
        
        Returns:
            requests.Session: 配置好的会话对象
        """
        session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session

    def build_prompt(self, sentence: str, is_table: bool = False) -> str:
        """
        构建提示词
        
        Args:
            sentence: 输入句子或表格内容
            is_table: 是否为表格
            
        Returns:
            str: 构建好的提示词
        """
        if is_table:
            return self._build_table_prompt(sentence)
        else:
            return self._build_sentence_prompt(sentence)
    
    def _build_sentence_prompt(self, sentence: str) -> str:
        """
        构建句子关键词提取提示词
        
        Args:
            sentence: 输入句子
            
        Returns:
            str: 提示词
        """
        prompt = f"""请从以下科学论文句子中提取1-5个最重要的关键词。

要求：
1. 关键词应该是名词或名词短语
2. 保留技术术语、化学式、专有名词
3. 不要提取停用词（如"的"、"是"、"在"等）
4. 关键词应该能够代表句子的核心概念
5. 以JSON格式输出，格式为: {{"keywords": ["关键词1", "关键词2", ...]}}

句子：
{sentence}

请直接输出JSON，不要有其他内容："""
        
        return prompt
    
    def _build_table_prompt(self, table_content: str) -> str:
        """
        构建表格关键词提取提示词
        
        Args:
            table_content: 表格内容
            
        Returns:
            str: 提示词
        """
        prompt = f"""请从以下科学论文表格中提取1-5个最重要的关键词。

要求：
1. 关键词应该包括表格的主题、数据类型、测量单位等
2. 提取表头中的关键信息
3. 识别数据的类型和范围
4. 保留技术术语和专有名词
5. 以JSON格式输出，格式为: {{"keywords": ["关键词1", "关键词2", ...]}}

表格：
{table_content}

请直接输出JSON，不要有其他内容："""
        
        return prompt
    
    def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """
        调用 LLM API
        
        Args:
            prompt: 提示词
            
        Returns:
            Dict: API 响应
            
        Raises:
            requests.exceptions.RequestException: 请求失败
        """
        url = f"{self.config.api_base_url}/v1/chat/completions"
        
        payload = {
            "model": self.config.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }
        
        response = self.session.post(
            url,
            json=payload,
            timeout=self.config.timeout
        )
        
        response.raise_for_status()
        return response.json()
    
    def parse_response(self, response: Dict[str, Any]) -> List[str]:
        """
        解析 LLM 响应
        
        Args:
            response: LLM API 响应
            
        Returns:
            List[str]: 提取的关键词列表
            
        Raises:
            ValueError: 解析失败
        """
        try:
            # 提取响应内容
            content = response['choices'][0]['message']['content']
            
            # 尝试解析 JSON
            # 有时 LLM 会在 JSON 前后添加额外文本，需要提取 JSON 部分
            content = content.strip()
            
            # 查找 JSON 对象
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                raise ValueError(f"响应中未找到 JSON 对象: {content}")
            
            json_str = content[start_idx:end_idx+1]
            data = json.loads(json_str)
            
            # 提取关键词
            if 'keywords' not in data:
                raise ValueError(f"JSON 中缺少 'keywords' 字段: {data}")
            
            keywords = data['keywords']
            
            if not isinstance(keywords, list):
                raise ValueError(f"'keywords' 应该是列表: {keywords}")
            
            # 验证关键词数量
            if len(keywords) < 1 or len(keywords) > 5:
                logger.warning(f"关键词数量不在 1-5 范围内: {len(keywords)}")
            
            # 过滤和规范化关键词
            filtered_keywords = self._filter_and_normalize_keywords(keywords)
            
            return filtered_keywords
            
        except (KeyError, json.JSONDecodeError, IndexError) as e:
            raise ValueError(f"解析响应失败: {e}, 响应: {response}")
    
    def _filter_and_normalize_keywords(self, keywords: List[str]) -> List[str]:
        """
        过滤停用词并规范化关键词
        
        Args:
            keywords: 原始关键词列表
            
        Returns:
            List[str]: 过滤和规范化后的关键词列表
        """
        filtered = []
        
        for keyword in keywords:
            if not isinstance(keyword, str):
                continue
            
            # 去除首尾空格
            keyword = keyword.strip()
            
            if not keyword:
                continue
            
            # 转换为小写（用于停用词检查）
            keyword_lower = keyword.lower()
            
            # 过滤停用词
            if keyword_lower in self.STOPWORDS:
                logger.debug(f"过滤停用词: {keyword}")
                continue
            
            # 规范化为小写（保留原始大小写用于技术术语）
            # 如果包含大写字母（可能是缩写或专有名词），保留原样
            if keyword.isupper() or any(c.isupper() for c in keyword):
                filtered.append(keyword)
            else:
                filtered.append(keyword_lower)
        
        return filtered
    
    def extract_keywords(self, sentence: str, is_table: bool = False) -> ExtractionResult:
        """
        从句子或表格中提取关键词
        
        Args:
            sentence: 输入句子或表格内容
            is_table: 是否为表格
            
        Returns:
            ExtractionResult: 提取结果
        """
        retry_count = 0
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                # 构建提示词
                prompt = self.build_prompt(sentence, is_table)
                
                # 调用 LLM
                response = self._call_llm(prompt)
                
                # 解析响应
                keywords = self.parse_response(response)
                
                return ExtractionResult(
                    keywords=keywords,
                    success=True,
                    retry_count=retry_count
                )
                
            except requests.exceptions.Timeout as e:
                retry_count += 1
                last_error = f"超时错误: {e}"
                logger.warning(f"提取关键词超时 (尝试 {attempt + 1}/{self.config.max_retries}): {sentence[:50]}...")
                time.sleep(2 ** attempt)  # 指数退避
                
            except requests.exceptions.HTTPError as e:
                retry_count += 1
                
                # 检查是否为速率限制错误
                if e.response.status_code == 429:
                    last_error = f"速率限制: {e}"
                    logger.warning(f"遇到速率限制 (尝试 {attempt + 1}/{self.config.max_retries})")
                    time.sleep(5 * (attempt + 1))  # 更长的等待时间
                else:
                    last_error = f"HTTP 错误: {e}"
                    logger.error(f"HTTP 错误 {e.response.status_code}: {e}")
                    break  # 其他 HTTP 错误不重试
                    
            except ValueError as e:
                retry_count += 1
                last_error = f"解析错误: {e}"
                logger.error(f"解析响应失败 (尝试 {attempt + 1}/{self.config.max_retries}): {e}")
                time.sleep(1)
                
            except Exception as e:
                retry_count += 1
                last_error = f"未知错误: {e}"
                logger.error(f"提取关键词时发生错误 (尝试 {attempt + 1}/{self.config.max_retries}): {e}")
                time.sleep(1)
        
        # 所有重试都失败
        self.failed_sentences.append((sentence[:100], last_error or "未知错误"))
        
        return ExtractionResult(
            keywords=[],
            success=False,
            error_message=last_error,
            retry_count=retry_count
        )
    
    def extract_batch(self, sentences: List[str], is_table: bool = False) -> List[ExtractionResult]:
        """
        批量提取关键词
        
        Args:
            sentences: 句子列表
            is_table: 是否为表格
            
        Returns:
            List[ExtractionResult]: 提取结果列表
        """
        results = []
        
        logger.info(f"开始批量提取关键词，共 {len(sentences)} 个{'表格' if is_table else '句子'}")
        
        for i, sentence in enumerate(sentences):
            if (i + 1) % 10 == 0:
                logger.info(f"进度: {i + 1}/{len(sentences)}")
            
            result = self.extract_keywords(sentence, is_table)
            results.append(result)
            
            # 避免过快请求
            if i < len(sentences) - 1:
                time.sleep(0.1)
        
        # 统计结果
        success_count = sum(1 for r in results if r.success)
        failed_count = len(results) - success_count
        
        logger.info(f"批量提取完成: 成功 {success_count}, 失败 {failed_count}")
        
        return results
    
    def extract_table_keywords(self, table_content: str, headers: List[str]) -> ExtractionResult:
        """
        从表格中提取关键词
        
        Args:
            table_content: 表格内容（Markdown 格式）
            headers: 表头列表
            
        Returns:
            ExtractionResult: 提取结果
        """
        # 构建增强的表格内容，包含表头信息
        enhanced_content = f"表头: {', '.join(headers)}\n\n{table_content}"
        
        return self.extract_keywords(enhanced_content, is_table=True)
    
    def get_failed_sentences(self) -> List[Tuple[str, str]]:
        """
        获取失败的句子列表
        
        Returns:
            List[Tuple[str, str]]: (句子, 错误信息) 列表
        """
        return self.failed_sentences.copy()
    
    def clear_failed_sentences(self):
        """清空失败句子列表"""
        self.failed_sentences.clear()
    
    def close(self):
        """关闭会话"""
        self.session.close()
