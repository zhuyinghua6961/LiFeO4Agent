"""
Batch keyword extraction script for chunks data.

Optimized version with:
- Memory management and garbage collection
- Progress saving and resume capability
- Service health monitoring
- Automatic wait for service restart

This script reads all chunk JSON files, extracts keywords for each chunk using Qwen model,
and updates the JSON files with keywords added to metadata.keywords field.

Only processes Chunks (paragraph-level), NOT Sentences (sentence-level).
"""

import json
import time
import gc
from pathlib import Path
from typing import Dict, Any, List
from tqdm import tqdm
from keyword_extractor import QwenKeywordExtractor


def has_keywords(chunk: Dict[str, Any]) -> bool:
    """
    Check if chunk already has keywords.
    
    Args:
        chunk: Chunk dictionary
        
    Returns:
        bool: True if chunk has keywords
    """
    metadata = chunk.get('metadata', {})
    keywords = metadata.get('keywords')
    return keywords is not None and len(keywords) > 0


def process_chunks_file(
    json_file: Path,
    extractor: QwenKeywordExtractor,
    skip_existing: bool = True,
    output_file: Path = None
) -> Dict[str, Any]:
    """
    Process a single chunks JSON file and add keywords.
    
    Args:
        json_file: Path to chunks JSON file
        extractor: Keyword extractor instance
        skip_existing: Skip chunks that already have keywords
        output_file: Path to output JSON file (if None, overwrites input file)
        
    Returns:
        Dict: Processing statistics
    """
    stats = {
        'total_chunks': 0,
        'processed_chunks': 0,
        'skipped_chunks': 0,
        'failed_chunks': 0,
        'success_rate': 0.0
    }
    
    try:
        # Load JSON file
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        chunks = data.get('chunks', [])
        stats['total_chunks'] = len(chunks)
        
        if not chunks:
            return stats
        
        # Process each chunk
        modified = False
        for chunk in chunks:
            # Skip if already has keywords
            if skip_existing and has_keywords(chunk):
                stats['skipped_chunks'] += 1
                continue
            
            # Extract keywords
            result = extractor.extract_keywords(chunk['text'])
            
            if result.success:
                # Add keywords to metadata
                if 'metadata' not in chunk:
                    chunk['metadata'] = {}
                chunk['metadata']['keywords'] = result.keywords
                stats['processed_chunks'] += 1
                modified = True
            else:
                # Use empty list for failed extractions
                if 'metadata' not in chunk:
                    chunk['metadata'] = {}
                chunk['metadata']['keywords'] = []
                stats['failed_chunks'] += 1
                modified = True
        
        # Save updated JSON if modified
        if modified:
            save_path = output_file if output_file else json_file
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Calculate success rate
        if stats['processed_chunks'] + stats['failed_chunks'] > 0:
            stats['success_rate'] = stats['processed_chunks'] / (stats['processed_chunks'] + stats['failed_chunks'])
        
        # Cleanup memory after processing file
        del data
        del chunks
        gc.collect()
        
        return stats
        
    except Exception as e:
        print(f"Error processing {json_file.name}: {e}")
        return stats


def batch_extract_keywords(
    chunks_dir: str = "rebuild_vector_db/chunks_data",
    output_dir: str = None,
    skip_existing: bool = True,
    max_files: int = None,
    progress_file: str = "rebuild_vector_db/keyword_extraction_progress.txt"
) -> Dict[str, Any]:
    """
    Batch extract keywords for all chunks JSON files.
    
    Args:
        chunks_dir: Directory containing chunks JSON files
        output_dir: Directory to save output JSON files (if None, overwrites input files)
        skip_existing: Skip chunks that already have keywords
        max_files: Maximum number of files to process (None for all)
        progress_file: File to save progress for resume capability
        
    Returns:
        Dict: Overall statistics
    """
    chunks_path = Path(chunks_dir)
    
    if not chunks_path.exists():
        print(f"Error: Directory {chunks_dir} does not exist")
        return {}
    
    # Create output directory if specified
    output_path = None
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        print(f"Output directory: {output_dir}")
    
    # Find all JSON files
    json_files = sorted(chunks_path.glob("*.json"))
    
    # Load progress if exists
    processed_files = set()
    if Path(progress_file).exists():
        with open(progress_file, 'r') as f:
            processed_files = set(line.strip() for line in f)
        print(f"Loaded progress: {len(processed_files)} files already processed")
    
    # Filter out already processed files
    if skip_existing and processed_files:
        json_files = [f for f in json_files if f.name not in processed_files]
        print(f"Skipping {len(processed_files)} already processed files")
    
    if max_files:
        json_files = json_files[:max_files]
    
    if not json_files:
        print(f"No JSON files to process in {chunks_dir}")
        return {}
    
    print(f"Found {len(json_files)} JSON files to process")
    print(f"Skip existing: {skip_existing}")
    print()
    
    # Create extractor
    extractor = QwenKeywordExtractor()
    
    # Check service health before starting
    if not extractor.check_service_health():
        print("⚠️  Qwen service is not available")
        if not extractor.wait_for_service(max_wait=60):
            print("✗ Cannot start: Qwen service is not available")
            return {}
    
    # Overall statistics
    overall_stats = {
        'total_files': len(json_files),
        'processed_files': 0,
        'total_chunks': 0,
        'processed_chunks': 0,
        'skipped_chunks': 0,
        'failed_chunks': 0,
        'success_rate': 0.0,
        'start_time': time.time()
    }
    
    # Process each file with progress bar
    print("Processing files...")
    for json_file in tqdm(json_files, desc="Extracting keywords", unit="file"):
        # Determine output file path
        output_file = None
        if output_path:
            output_file = output_path / json_file.name
        
        stats = process_chunks_file(json_file, extractor, skip_existing, output_file)
        
        overall_stats['processed_files'] += 1
        overall_stats['total_chunks'] += stats['total_chunks']
        overall_stats['processed_chunks'] += stats['processed_chunks']
        overall_stats['skipped_chunks'] += stats['skipped_chunks']
        overall_stats['failed_chunks'] += stats['failed_chunks']
        
        # Save progress
        with open(progress_file, 'a') as f:
            f.write(f"{json_file.name}\n")
        
        # Periodic garbage collection (every 10 files)
        if overall_stats['processed_files'] % 10 == 0:
            gc.collect()
        
        # Print progress every 100 files
        if overall_stats['processed_files'] % 100 == 0:
            elapsed = time.time() - overall_stats['start_time']
            rate = overall_stats['processed_files'] / elapsed
            remaining = (overall_stats['total_files'] - overall_stats['processed_files']) / rate
            print(f"\nProgress: {overall_stats['processed_files']}/{overall_stats['total_files']} files "
                  f"({overall_stats['processed_chunks']} chunks processed, "
                  f"{overall_stats['skipped_chunks']} skipped, "
                  f"{overall_stats['failed_chunks']} failed) "
                  f"- ETA: {remaining/60:.1f} min")
    
    # Calculate overall success rate
    if overall_stats['processed_chunks'] + overall_stats['failed_chunks'] > 0:
        overall_stats['success_rate'] = overall_stats['processed_chunks'] / (
            overall_stats['processed_chunks'] + overall_stats['failed_chunks']
        )
    
    overall_stats['end_time'] = time.time()
    overall_stats['duration'] = overall_stats['end_time'] - overall_stats['start_time']
    
    return overall_stats


def print_statistics(stats: Dict[str, Any]):
    """Print processing statistics."""
    print()
    print("=" * 60)
    print("Keyword Extraction Statistics")
    print("=" * 60)
    print(f"Total files processed: {stats['processed_files']}/{stats['total_files']}")
    print(f"Total chunks: {stats['total_chunks']}")
    print(f"Processed chunks: {stats['processed_chunks']}")
    print(f"Skipped chunks: {stats['skipped_chunks']}")
    print(f"Failed chunks: {stats['failed_chunks']}")
    print(f"Success rate: {stats['success_rate']*100:.2f}%")
    print(f"Duration: {stats['duration']/60:.2f} minutes")
    
    if stats['processed_chunks'] > 0:
        avg_time = stats['duration'] / stats['processed_chunks']
        print(f"Average time per chunk: {avg_time:.2f} seconds")
    
    print("=" * 60)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch extract keywords for chunks")
    parser.add_argument(
        '--chunks-dir',
        default='rebuild_vector_db/chunks_data',
        help='Directory containing chunks JSON files'
    )
    parser.add_argument(
        '--output-dir',
        default=None,
        help='Directory to save output JSON files (if not specified, overwrites input files)'
    )
    parser.add_argument(
        '--no-skip-existing',
        action='store_true',
        help='Process all chunks, even if they already have keywords'
    )
    parser.add_argument(
        '--max-files',
        type=int,
        default=None,
        help='Maximum number of files to process (for testing)'
    )
    parser.add_argument(
        '--progress-file',
        default='rebuild_vector_db/keyword_extraction_progress.txt',
        help='File to save progress for resume capability'
    )
    
    args = parser.parse_args()
    
    # Run batch extraction
    stats = batch_extract_keywords(
        chunks_dir=args.chunks_dir,
        output_dir=args.output_dir,
        skip_existing=not args.no_skip_existing,
        max_files=args.max_files,
        progress_file=args.progress_file
    )
    
    # Print statistics
    if stats:
        print_statistics(stats)


if __name__ == "__main__":
    main()
