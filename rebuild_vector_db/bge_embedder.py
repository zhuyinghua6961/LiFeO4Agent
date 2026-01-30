"""
BGE Embedder module for generating embeddings from chunks.

This module reads chunk JSON files with keywords and generates embeddings
using the BGE model API. For chunks, it uses enhanced text (text + keywords).
"""

import time
import json
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    embedding: List[float]
    success: bool
    error_message: Optional[str] = None


class BGEEmbedder:
    """Generates embeddings using BGE model API."""
    
    def __init__(
        self,
        api_url: str = "http://localhost:8001/v1/embeddings",
        batch_size: int = 128,
        max_retries: int = 3,
        retry_delay: int = 2,
        timeout: int = 60
    ):
        """
        Initialize BGE embedder.
        
        Args:
            api_url: BGE model API URL
            batch_size: Batch size for API calls (default: 128)
            max_retries: Maximum number of retries on failure
            retry_delay: Delay between retries in seconds
            timeout: Request timeout in seconds
        """
        self.api_url = api_url
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        
        # Create a session for connection pooling
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
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
        Check if BGE service is healthy.
        
        Returns:
            bool: True if service is healthy
        """
        try:
            health_url = self.api_url.replace('/v1/embeddings', '/health')
            response = self.session.get(health_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('status') == 'healthy'
            return False
        except:
            return False
    
    def create_enhanced_text(self, chunk: Dict[str, Any]) -> str:
        """
        Create enhanced text for chunk by combining text with keywords.
        
        Args:
            chunk: Chunk dictionary with text and metadata.keywords
            
        Returns:
            str: Enhanced text (text + keywords)
        """
        text = chunk.get('text', '')
        keywords = chunk.get('metadata', {}).get('keywords', [])
        
        if keywords:
            # Combine text with keywords
            keywords_str = ' '.join(keywords)
            return f"{text} {keywords_str}"
        else:
            return text
    
    def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List[EmbeddingResult]: List of embedding results
        """
        for attempt in range(self.max_retries):
            try:
                # Call BGE API
                response = self.session.post(
                    self.api_url,
                    json={"input": texts},
                    timeout=self.timeout
                )
                
                # Check response status
                if response.status_code != 200:
                    error_msg = f"API returned status code {response.status_code}"
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    # Return failed results
                    return [
                        EmbeddingResult(
                            embedding=[],
                            success=False,
                            error_message=error_msg
                        )
                        for _ in texts
                    ]
                
                # Parse response
                result = response.json()
                data = result.get('data', [])
                
                # Validate embeddings
                embeddings = []
                for item in data:
                    embedding = item.get('embedding', [])
                    
                    # Validate dimension
                    if len(embedding) != 1024:
                        embeddings.append(
                            EmbeddingResult(
                                embedding=[],
                                success=False,
                                error_message=f"Invalid dimension: {len(embedding)}"
                            )
                        )
                    else:
                        embeddings.append(
                            EmbeddingResult(
                                embedding=embedding,
                                success=True
                            )
                        )
                
                return embeddings
                
            except requests.exceptions.Timeout:
                error_msg = "Request timeout"
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return [
                    EmbeddingResult(
                        embedding=[],
                        success=False,
                        error_message=error_msg
                    )
                    for _ in texts
                ]
            
            except requests.exceptions.ConnectionError:
                error_msg = "Connection error - service may be down"
                if attempt < self.max_retries - 1:
                    print(f"⚠️  Connection error, retrying...")
                    time.sleep(self.retry_delay)
                    continue
                return [
                    EmbeddingResult(
                        embedding=[],
                        success=False,
                        error_message=error_msg
                    )
                    for _ in texts
                ]
            
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return [
                    EmbeddingResult(
                        embedding=[],
                        success=False,
                        error_message=error_msg
                    )
                    for _ in texts
                ]
        
        # Should not reach here
        return [
            EmbeddingResult(
                embedding=[],
                success=False,
                error_message="Max retries exceeded"
            )
            for _ in texts
        ]
    
    def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[EmbeddingResult]:
        """
        Generate embeddings for chunks using enhanced text.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            List[EmbeddingResult]: List of embedding results
        """
        # Create enhanced texts
        enhanced_texts = [self.create_enhanced_text(chunk) for chunk in chunks]
        
        # Process in batches
        all_results = []
        for i in range(0, len(enhanced_texts), self.batch_size):
            batch_texts = enhanced_texts[i:i + self.batch_size]
            batch_results = self.embed_batch(batch_texts)
            all_results.extend(batch_results)
        
        return all_results


def main():
    """Test the BGE embedder."""
    import sys
    
    # Create embedder
    embedder = BGEEmbedder()
    
    # Check service health
    print("Checking BGE service health...")
    if not embedder.check_service_health():
        print("✗ BGE service is not available")
        sys.exit(1)
    print("✓ BGE service is healthy")
    print()
    
    # Test chunks
    test_chunks = [
        {
            "text": "LiFePO4 cathode material shows excellent cycle performance.",
            "metadata": {
                "keywords": ["LiFePO4", "cathode", "cycle performance"]
            }
        },
        {
            "text": "Lithium ion batteries are widely used in electric vehicles.",
            "metadata": {
                "keywords": ["lithium ion battery", "electric vehicle"]
            }
        }
    ]
    
    print(f"Testing with {len(test_chunks)} chunks...")
    
    # Generate embeddings
    results = embedder.embed_chunks(test_chunks)
    
    # Print results
    for i, result in enumerate(results):
        if result.success:
            print(f"✓ Chunk {i}: embedding dimension = {len(result.embedding)}")
        else:
            print(f"✗ Chunk {i}: {result.error_message}")
    
    print()
    print(f"Success rate: {sum(1 for r in results if r.success)}/{len(results)}")


if __name__ == "__main__":
    main()
