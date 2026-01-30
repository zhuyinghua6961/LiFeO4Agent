"""
Check the quality of the chunk database being built.
"""

import sys
from chromadb_manager import ChromaDBManager


def check_database_quality():
    """Check database quality and progress."""
    
    print("=" * 70)
    print("Chunk Database Quality Check")
    print("=" * 70)
    print()
    
    # Initialize ChromaDB manager
    db_manager = ChromaDBManager("./chroma_chunks_v2")
    
    # List all collections
    print("Collections in database:")
    collections = db_manager.list_collections()
    for col_name in collections:
        print(f"  - {col_name}")
    print()
    
    if not collections:
        print("✗ No collections found in database")
        return
    
    # Get the main collection
    collection_name = "literature_chunks_v2"
    collection = db_manager.get_collection(collection_name)
    
    if not collection:
        print(f"✗ Collection '{collection_name}' not found")
        return
    
    print(f"Checking collection: {collection_name}")
    print()
    
    # Get collection count
    count = collection.count()
    print(f"Total records: {count:,}")
    print()
    
    if count == 0:
        print("✗ Collection is empty")
        return
    
    # Sample some records
    print("Sampling records...")
    sample_size = min(10, count)
    sample = collection.get(limit=sample_size, include=['documents', 'embeddings', 'metadatas'])
    
    print(f"✓ Retrieved {len(sample['ids'])} sample records")
    print()
    
    # Check data integrity
    print("Data Integrity Check:")
    print("-" * 70)
    
    has_ids = sample.get('ids') is not None and len(sample.get('ids', [])) > 0
    has_docs = sample.get('documents') is not None and len(sample.get('documents', [])) > 0
    has_embs = sample.get('embeddings') is not None and len(sample.get('embeddings', [])) > 0
    has_metas = sample.get('metadatas') is not None and len(sample.get('metadatas', [])) > 0
    
    print(f"✓ Has IDs: {has_ids}")
    print(f"✓ Has Documents: {has_docs}")
    print(f"✓ Has Embeddings: {has_embs}")
    print(f"✓ Has Metadatas: {has_metas}")
    print()
    
    # Check embedding dimensions
    if has_embs and len(sample['embeddings']) > 0:
        emb_dims = [len(emb) for emb in sample['embeddings']]
        print(f"Embedding dimensions: {emb_dims[0]} (all: {all(d == 1024 for d in emb_dims)})")
        print()
    
    # Check metadata fields
    if has_metas and len(sample['metadatas']) > 0:
        print("Metadata fields in first record:")
        first_meta = sample['metadatas'][0]
        for key, value in first_meta.items():
            value_str = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
            print(f"  - {key}: {value_str}")
        print()
        
        # Check keywords
        keywords_present = sum(1 for m in sample['metadatas'] if m.get('keywords'))
        print(f"Records with keywords: {keywords_present}/{len(sample['metadatas'])}")
        print()
    
    # Show sample documents
    print("Sample Documents:")
    print("-" * 70)
    for i in range(min(3, len(sample['ids']))):
        doc_id = sample['ids'][i]
        doc_text = sample['documents'][i][:100] + "..." if len(sample['documents'][i]) > 100 else sample['documents'][i]
        keywords = sample['metadatas'][i].get('keywords', '')
        source = sample['metadatas'][i].get('source', 'Unknown')
        
        print(f"\nRecord {i+1}:")
        print(f"  ID: {doc_id}")
        print(f"  Source: {source}")
        print(f"  Keywords: {keywords}")
        print(f"  Text: {doc_text}")
    
    print()
    print("=" * 70)
    print(f"Database Status: {'✓ HEALTHY' if count > 0 else '✗ EMPTY'}")
    print(f"Total Records: {count:,}")
    print("=" * 70)


if __name__ == "__main__":
    try:
        check_database_quality()
    except Exception as e:
        print(f"✗ Error checking database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
