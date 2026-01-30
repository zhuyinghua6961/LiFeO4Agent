"""
Build chunk-level vector database from JSON files with keywords.

This script reads chunk JSON files (with keywords), generates embeddings using BGE,
and inserts them into ChromaDB for vector search.
"""

import json
import time
import gc
import sys
from pathlib import Path
from typing import Dict, Any, List
from tqdm import tqdm

from bge_embedder import BGEEmbedder
from chromadb_manager import ChromaDBManager


def load_chunks_from_json(json_file: Path) -> List[Dict[str, Any]]:
    """
    Load chunks from JSON file.
    
    Args:
        json_file: Path to chunks JSON file
        
    Returns:
        List of chunk dictionaries
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('chunks', [])
    except Exception as e:
        print(f"✗ Error loading {json_file.name}: {e}", flush=True)
        return []


def build_chunk_database(
    chunks_dir: str = "/mnt/fast18/zhu/LiFeO4Agent/rebuild_vector_db/chunks_data_with_keywords",
    db_path: str = "./chroma_chunks_v2",
    collection_name: str = "literature_chunks_v2",
    max_files: int = None,
    reset_db: bool = False
) -> Dict[str, Any]:
    """
    Build chunk-level vector database.
    
    Args:
        chunks_dir: Directory containing chunks JSON files with keywords
        db_path: Path to ChromaDB database
        collection_name: Name of the collection
        max_files: Maximum number of files to process (None for all)
        reset_db: If True, reset the database before building
        
    Returns:
        Dict: Processing statistics
    """
    chunks_path = Path(chunks_dir)
    
    if not chunks_path.exists():
        print(f"✗ Error: Directory {chunks_dir} does not exist", flush=True)
        return {}
    
    # Find all JSON files
    json_files = sorted(chunks_path.glob("*.json"))
    
    if max_files:
        json_files = json_files[:max_files]
    
    if not json_files:
        print(f"✗ No JSON files found in {chunks_dir}", flush=True)
        return {}
    
    print(f"Found {len(json_files)} JSON files to process", flush=True)
    print(flush=True)
    
    # Initialize components
    print("Initializing components...", flush=True)
    embedder = BGEEmbedder(
        api_url="http://localhost:8001/v1/embeddings",
        batch_size=128
    )
    
    # Check BGE service
    if not embedder.check_service_health():
        print("✗ BGE service is not available", flush=True)
        return {}
    print("✓ BGE service is healthy", flush=True)
    
    # Initialize ChromaDB
    db_manager = ChromaDBManager(db_path)
    collection = db_manager.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
        reset=reset_db
    )
    print(flush=True)
    
    # Overall statistics
    overall_stats = {
        'total_files': len(json_files),
        'processed_files': 0,
        'total_chunks': 0,
        'successful_embeddings': 0,
        'failed_embeddings': 0,
        'inserted_chunks': 0,
        'failed_insertions': 0,
        'start_time': time.time()
    }
    
    # Process each file
    print("Processing files and building database...", flush=True)
    sys.stdout.flush()
    
    # Disable tqdm in non-interactive mode (nohup)
    use_tqdm = sys.stdout.isatty()
    
    file_iterator = tqdm(json_files, desc="Building database", unit="file", disable=not use_tqdm)
    
    for file_idx, json_file in enumerate(file_iterator, 1):
        # Load chunks
        chunks = load_chunks_from_json(json_file)
        
        if not chunks:
            continue
        
        overall_stats['total_chunks'] += len(chunks)
        
        # Generate embeddings
        embedding_results = embedder.embed_chunks(chunks)
        
        # Prepare data for insertion
        ids = []
        documents = []
        embeddings = []
        metadatas = []
        
        for chunk, emb_result in zip(chunks, embedding_results):
            if emb_result.success:
                overall_stats['successful_embeddings'] += 1
                
                # Prepare metadata (flatten for ChromaDB)
                metadata = {
                    'source': chunk.get('source', ''),
                    'chunk_index': chunk.get('chunk_index', 0),
                    'start_index': chunk.get('start_index', 0),
                    'end_index': chunk.get('end_index', 0),
                    'section': chunk.get('section', 'Unknown'),
                    'text_type': chunk.get('text_type', 'text'),
                    'doi': chunk.get('doi', ''),
                    'keywords': ','.join(chunk.get('metadata', {}).get('keywords', []))
                }
                
                ids.append(chunk.get('chunk_id', ''))
                documents.append(chunk.get('text', ''))
                embeddings.append(emb_result.embedding)
                metadatas.append(metadata)
            else:
                overall_stats['failed_embeddings'] += 1
        
        # Insert into database
        if ids:
            insert_stats = db_manager.batch_insert(
                collection,
                ids,
                documents,
                embeddings,
                metadatas,
                batch_size=100
            )
            overall_stats['inserted_chunks'] += insert_stats['inserted']
            overall_stats['failed_insertions'] += insert_stats['failed']
        
        # Explicitly delete large objects to free memory
        del chunks
        del embedding_results
        del ids
        del documents
        del embeddings
        del metadatas
        
        overall_stats['processed_files'] += 1
        
        # More frequent garbage collection for better memory management
        if overall_stats['processed_files'] % 5 == 0:
            gc.collect()
        
        # Print progress every 100 files (always print in non-interactive mode)
        if overall_stats['processed_files'] % 100 == 0:
            elapsed = time.time() - overall_stats['start_time']
            rate = overall_stats['processed_files'] / elapsed
            remaining = (overall_stats['total_files'] - overall_stats['processed_files']) / rate
            progress_msg = (f"\nProgress: {overall_stats['processed_files']}/{overall_stats['total_files']} files "
                          f"({overall_stats['inserted_chunks']} chunks inserted) "
                          f"- ETA: {remaining/60:.1f} min")
            print(progress_msg, flush=True)
            sys.stdout.flush()
        
        # In non-interactive mode, print progress every 10 files
        if not use_tqdm and overall_stats['processed_files'] % 10 == 0:
            elapsed = time.time() - overall_stats['start_time']
            rate = overall_stats['processed_files'] / elapsed
            remaining = (overall_stats['total_files'] - overall_stats['processed_files']) / rate
            progress_msg = (f"Progress: {overall_stats['processed_files']}/{overall_stats['total_files']} files "
                          f"({overall_stats['inserted_chunks']} chunks) - ETA: {remaining/60:.1f} min")
            print(progress_msg, flush=True)
            sys.stdout.flush()
    
    overall_stats['end_time'] = time.time()
    overall_stats['duration'] = overall_stats['end_time'] - overall_stats['start_time']
    
    # Verify database
    print("\nVerifying database...", flush=True)
    sys.stdout.flush()
    verification = db_manager.verify_collection(collection)
    overall_stats['db_count'] = verification.get('count', 0)
    
    return overall_stats


def print_statistics(stats: Dict[str, Any]):
    """Print processing statistics."""
    print(flush=True)
    print("=" * 70, flush=True)
    print("Chunk Database Build Statistics", flush=True)
    print("=" * 70, flush=True)
    print(f"Total files processed: {stats['processed_files']}/{stats['total_files']}", flush=True)
    print(f"Total chunks: {stats['total_chunks']}", flush=True)
    print(f"Successful embeddings: {stats['successful_embeddings']}", flush=True)
    print(f"Failed embeddings: {stats['failed_embeddings']}", flush=True)
    print(f"Inserted chunks: {stats['inserted_chunks']}", flush=True)
    print(f"Failed insertions: {stats['failed_insertions']}", flush=True)
    print(f"Database count: {stats.get('db_count', 'N/A')}", flush=True)
    print(f"Duration: {stats['duration']/60:.2f} minutes", flush=True)
    
    if stats['successful_embeddings'] > 0:
        success_rate = stats['successful_embeddings'] / stats['total_chunks'] * 100
        print(f"Embedding success rate: {success_rate:.2f}%", flush=True)
    
    if stats['inserted_chunks'] > 0:
        avg_time = stats['duration'] / stats['inserted_chunks']
        print(f"Average time per chunk: {avg_time:.3f} seconds", flush=True)
    
    print("=" * 70, flush=True)
    sys.stdout.flush()


def main():
    """Main entry point."""
    import argparse
    
    # Force unbuffered output for real-time logging
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    
    parser = argparse.ArgumentParser(description="Build chunk-level vector database")
    parser.add_argument(
        '--chunks-dir',
        default='/mnt/fast18/zhu/LiFeO4Agent/rebuild_vector_db/chunks_data_with_keywords',
        help='Directory containing chunks JSON files with keywords'
    )
    parser.add_argument(
        '--db-path',
        default='./chroma_chunks_v2',
        help='Path to ChromaDB database'
    )
    parser.add_argument(
        '--collection-name',
        default='literature_chunks_v2',
        help='Name of the collection'
    )
    parser.add_argument(
        '--max-files',
        type=int,
        default=None,
        help='Maximum number of files to process (for testing)'
    )
    parser.add_argument(
        '--reset-db',
        action='store_true',
        help='Reset the database before building'
    )
    
    args = parser.parse_args()
    
    # Run build
    stats = build_chunk_database(
        chunks_dir=args.chunks_dir,
        db_path=args.db_path,
        collection_name=args.collection_name,
        max_files=args.max_files,
        reset_db=args.reset_db
    )
    
    # Print statistics
    if stats:
        print_statistics(stats)


if __name__ == "__main__":
    main()
