"""
RebuildPipeline module for coordinating the rebuild process.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List


@dataclass
class RebuildConfig:
    """Configuration for rebuild pipeline."""
    # Chunk splitting config
    chunk_size: int = 550
    chunk_overlap: int = 100
    
    # Sentence splitting config
    min_sentence_length: int = 10
    
    # BGE API config
    bge_api_url: str = "http://localhost:8001/v1/embeddings"
    embedding_batch_size: int = 32
    max_retries: int = 3
    retry_delay: int = 2
    
    # ChromaDB config
    chunk_db_path: str = "./chroma_chunks_v2"
    sentence_db_path: str = "./chroma_sentences_v2"
    chunk_collection_name: str = "literature_chunks_v2"
    sentence_collection_name: str = "literature_sentences_v2"
    insert_batch_size: int = 100
    
    # DOI mapping config
    doi_mapping_file: str = "/mnt/fast18/zhu/LiFeO4Agent/doi_to_pdf_mapping.json"
    
    # Processing config
    skip_existing: bool = False
    dry_run: bool = False
    log_level: str = "INFO"


@dataclass
class ProcessingStats:
    """Statistics for processing."""
    # File statistics
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    
    # Chunk statistics
    total_chunks: int = 0
    successful_chunks: int = 0
    failed_chunks: int = 0
    
    # Sentence statistics
    total_sentences: int = 0
    successful_sentences: int = 0
    failed_sentences: int = 0
    
    # Embedding statistics
    embedding_success_rate: float = 0.0
    embedding_failures: List[str] = None
    
    # Database statistics
    chunk_db_count: int = 0
    sentence_db_count: int = 0
    
    # Time statistics
    start_time: datetime = None
    end_time: datetime = None
    total_duration: float = 0.0
    
    # Error log
    errors: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.embedding_failures is None:
            self.embedding_failures = []
        if self.errors is None:
            self.errors = []


class RebuildPipeline:
    """Coordinates the entire rebuild process."""
    
    def __init__(self, config: RebuildConfig):
        """
        Initialize the rebuild pipeline.
        
        Args:
            config: Rebuild configuration
        """
        self.config = config
    
    def rebuild_chunk_database(
        self,
        input_dir: str,
        output_db: str,
        skip_existing: bool = False
    ) -> Dict[str, Any]:
        """
        Rebuild chunk-level database.
        
        Args:
            input_dir: Input directory with cleaned Markdown files
            output_db: Output database path
            skip_existing: Skip already processed files
            
        Returns:
            Dict[str, Any]: Processing statistics
        """
        # Implementation will be added in task 6
        pass
    
    def rebuild_sentence_database(
        self,
        input_dir: str,
        output_db: str,
        skip_existing: bool = False
    ) -> Dict[str, Any]:
        """
        Rebuild sentence-level database.
        
        Args:
            input_dir: Input directory with cleaned Markdown files
            output_db: Output database path
            skip_existing: Skip already processed files
            
        Returns:
            Dict[str, Any]: Processing statistics
        """
        # Implementation will be added in task 6
        pass
    
    def generate_report(self, stats: Dict[str, Any]) -> str:
        """
        Generate processing report.
        
        Args:
            stats: Processing statistics
            
        Returns:
            str: HTML report
        """
        # Implementation will be added in task 6
        pass
