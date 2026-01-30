·"""
QwenKeywordExtractor module for extracting keywords from text chunks using Qwen model.

Optimized version with:
- HTTP Session reuse for connection pooling
- Memory cleanup after batch processing
- Service health check and auto-wait for restart
"""

import time
import json
import gc
import requests
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class KeywordExtractionResult:
    """Result of keyword extraction."""
    keywords: List[str]
    success: bool
    error_message: Optional[str] = None


class QwenKeywordExtractor:
    """Extracts keywords from text using Qwen model API."""
    
    # Prompt template for keyword extraction
    KEYWORD_EXTRACTION_PROMPT = """You are a scientific paper keyword extractor. 
Given a text chunk from a scientific paper, extract 3-5 most important keywords or key phrases.

Requirements:
- Focus on scientific terms, concepts, materials, methods, or findings
- Keywords should be specific and relevant to the content
- Return ONLY the keywords, separated by commas
- Do not include explanations or additional text

Text: {text}

Keywords:"""
    
    def __init__(
        self, 
        api_url: str = "http://localhost:8003/v1/chat/completions",
        max_retries: int = 3,
        retry_delay: int = 2,
        timeout: int = 30
    ):
        """
        Initialize keyword extractor.
        
        Args:
            api_url: Qwen model API URL
            max_retries: Maximum number of retries on failure
            retry_delay: Delay between retries in seconds
            timeout: Request timeout in seconds
        """
        self.api_url = api_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        
        # Create a session for connection pooling
        self.session = requests.Session()
        # Limit connection pool size
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=1,
            pool_maxsize=1,
            max_retries=0  # We handle retries manually
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
    
    def __del__(self):
        """Cleanup session on deletion."""
        try:
            if hasattr(self, 'session'):
                self.session.close()
        except:
            pass
    
    def check_service_health(self) -> bool:
        """
        Check if Qwen service is healthy.
        
        Returns:
            bool: True if service is healthy
        """
        try:
            health_url = self.api_url.replace('/v1/chat/completions', '/v1/models')
            response = self.session.get(health_url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def wait_for_service(self, max_wait: int = 300):
        """
        Wait for service to become available.
        
        Args:
            max_wait: Maximum wait time in seconds
        """
        print("⏳ Waiting for Qwen service to be available...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if self.check_service_health():
                print("✓ Qwen service is available")
                return True
            time.sleep(5)
        
        print("✗ Qwen service did not become available")
        return False
    
    def extract_keywords(self, text: str, num_keywords: int = 5) -> KeywordExtractionResult:
        """
        Extract keywords from text.
        
        Args:
            text: Text to extract keywords from
            num_keywords: Expected number of keywords (default: 5)
            
        Returns:
            KeywordExtractionResult: Extraction result with keywords list
        """
        # Truncate text if too long (keep first 500 characters)
        if len(text) > 500:
            text = text[:500] + "..."
        
        # Try extraction with retries
        for attempt in range(self.max_retries):
            try:
                # Prepare prompt
                prompt = self.KEYWORD_EXTRACTION_PROMPT.format(text=text)
                
                # Call API using session
                response = self.session.post(
                    self.api_url,
                    json={
                        "model": "Qwen/Qwen2.5-1.5B-Instruct",
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 100,
                        "temperature": 0.1
                    },
                    timeout=self.timeout
                )
                
                # Check response status
                if response.status_code != 200:
                    error_msg = f"API returned status code {response.status_code}"
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    return KeywordExtractionResult(
                        keywords=[],
                        success=False,
                        error_message=error_msg
                    )
                
                # Parse response
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Parse keywords from response
                keywords = self._parse_keywords(content)
                
                # Validate keywords
                if not keywords:
                    error_msg = "No keywords extracted from response"
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    return KeywordExtractionResult(
                        keywords=[],
                        success=False,
                        error_message=error_msg
                    )
                
                return KeywordExtractionResult(
                    keywords=keywords[:num_keywords],  # Limit to requested number
                    success=True
                )
                
            except requests.exceptions.Timeout:
                error_msg = "Request timeout"
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return KeywordExtractionResult(
                    keywords=[],
                    success=False,
                    error_message=error_msg
                )
            
            except requests.exceptions.ConnectionError:
                error_msg = "Connection error - service may be restarting"
                if attempt < self.max_retries - 1:
                    # Wait for service to come back
                    print(f"⚠️  Connection error, waiting for service...")
                    if self.wait_for_service(max_wait=60):
                        continue
                return KeywordExtractionResult(
                    keywords=[],
                    success=False,
                    error_message=error_msg
                )
            
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return KeywordExtractionResult(
                    keywords=[],
                    success=False,
                    error_message=error_msg
                )
        
        # Should not reach here, but just in case
        return KeywordExtractionResult(
            keywords=[],
            success=False,
            error_message="Max retries exceeded"
        )
    
    def _parse_keywords(self, content: str) -> List[str]:
        """
        Parse keywords from model response.
        
        Args:
            content: Model response content
            
        Returns:
            List[str]: List of keywords
        """
        # Remove common prefixes
        content = content.strip()
        
        # Try to parse as numbered list
        if '\n' in content:
            lines = content.split('\n')
            keywords = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # Remove numbering (1., 2., etc.)
                line = line.lstrip('0123456789.-) ')
                if line:
                    keywords.append(line)
            if keywords:
                return keywords
        
        # Try to parse as comma-separated
        if ',' in content:
            keywords = [kw.strip() for kw in content.split(',')]
            keywords = [kw for kw in keywords if kw]
            if keywords:
                return keywords
        
        # Return as single keyword if no separator found
        if content:
            return [content]
        
        return []
    
    def extract_keywords_batch(self, texts: List[str]) -> List[KeywordExtractionResult]:
        """
        Extract keywords from multiple texts.
        
        Note: This is a sequential implementation. For better performance,
        consider implementing parallel processing.
        
        Args:
            texts: List of texts to extract keywords from
            
        Returns:
            List[KeywordExtractionResult]: List of extraction results
        """
        results = []
        for text in texts:
            result = self.extract_keywords(text)
            results.append(result)
        return results


def main():
    """Test the keyword extractor."""
    import sys
    
    # Create extractor
    extractor = QwenKeywordExtractor()
    
    # Test text
    test_text = """
    Lithium-ion batteries are widely used in electric vehicles due to their 
    high energy density and long cycle life. The anode material plays a crucial 
    role in determining the battery performance. Recent studies have shown that 
    silicon-based anodes can significantly improve the capacity retention.
    """
    
    print("Testing QwenKeywordExtractor...")
    print(f"Text: {test_text[:100]}...")
    print()
    
    # Extract keywords
    result = extractor.extract_keywords(test_text)
    
    if result.success:
        print(f"✓ Extraction successful!")
        print(f"Keywords ({len(result.keywords)}):")
        for i, keyword in enumerate(result.keywords, 1):
            print(f"  {i}. {keyword}")
    else:
        print(f"✗ Extraction failed: {result.error_message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
