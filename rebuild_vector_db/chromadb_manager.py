"""
ChromaDB Manager module for managing vector database operations.

This module handles creating collections and inserting data into ChromaDB.
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from pathlib import Path


class ChromaDBManager:
    """Manages ChromaDB operations for vector storage."""
    
    def __init__(self, db_path: str):
        """
        Initialize ChromaDB manager.
        
        Args:
            db_path: Path to ChromaDB database directory
        """
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
    
    def create_collection(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
        reset: bool = False
    ):
        """
        Create or get a collection.
        
        Args:
            name: Collection name
            metadata: Collection metadata (e.g., {"hnsw:space": "cosine"})
            reset: If True, delete existing collection first
            
        Returns:
            Collection object
        """
        if reset:
            try:
                self.client.delete_collection(name=name)
                print(f"✓ Deleted existing collection: {name}")
            except:
                pass
        
        # Default metadata for cosine similarity
        if metadata is None:
            metadata = {"hnsw:space": "cosine"}
        
        try:
            collection = self.client.get_or_create_collection(
                name=name,
                metadata=metadata
            )
            print(f"✓ Collection ready: {name}")
            return collection
        except Exception as e:
            print(f"✗ Failed to create collection {name}: {e}")
            raise
    
    def batch_insert(
        self,
        collection,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Batch insert data into collection.
        
        Args:
            collection: ChromaDB collection
            ids: List of document IDs
            documents: List of document texts
            embeddings: List of embedding vectors
            metadatas: List of metadata dictionaries
            batch_size: Batch size for insertion
            
        Returns:
            Dict: Statistics about insertion
        """
        stats = {
            'total': len(ids),
            'inserted': 0,
            'failed': 0,
            'failed_ids': []
        }
        
        # Process in batches
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_docs = documents[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]
            
            try:
                collection.add(
                    ids=batch_ids,
                    documents=batch_docs,
                    embeddings=batch_embeddings,
                    metadatas=batch_metadatas
                )
                stats['inserted'] += len(batch_ids)
            except Exception as e:
                print(f"✗ Batch insertion failed: {e}")
                stats['failed'] += len(batch_ids)
                stats['failed_ids'].extend(batch_ids)
        
        return stats
    
    def verify_collection(self, collection) -> Dict[str, Any]:
        """
        Verify collection data integrity.
        
        Args:
            collection: ChromaDB collection
            
        Returns:
            Dict: Verification statistics
        """
        try:
            count = collection.count()
            
            # Sample a few documents to verify
            if count > 0:
                sample = collection.get(limit=min(5, count))
                
                has_docs = sample.get('documents') is not None and len(sample.get('documents', [])) > 0
                has_embs = sample.get('embeddings') is not None and len(sample.get('embeddings', [])) > 0
                has_metas = sample.get('metadatas') is not None and len(sample.get('metadatas', [])) > 0
                
                return {
                    'count': count,
                    'has_documents': has_docs,
                    'has_embeddings': has_embs,
                    'has_metadatas': has_metas,
                    'sample_ids': sample.get('ids', [])[:3]
                }
            else:
                return {
                    'count': 0,
                    'has_documents': False,
                    'has_embeddings': False,
                    'has_metadatas': False
                }
        except Exception as e:
            return {
                'error': str(e)
            }
    
    def get_collection(self, name: str):
        """
        Get an existing collection.
        
        Args:
            name: Collection name
            
        Returns:
            Collection object or None
        """
        try:
            return self.client.get_collection(name=name)
        except:
            return None
    
    def list_collections(self) -> List[str]:
        """
        List all collections.
        
        Returns:
            List of collection names
        """
        collections = self.client.list_collections()
        return [c.name for c in collections]


def main():
    """Test ChromaDB manager."""
    import tempfile
    
    # Create temporary database
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Testing ChromaDB manager with temp dir: {tmpdir}")
        print()
        
        # Initialize manager
        manager = ChromaDBManager(tmpdir)
        
        # Create collection
        collection = manager.create_collection(
            name="test_collection",
            metadata={"hnsw:space": "cosine"},
            reset=True
        )
        print()
        
        # Test data
        test_ids = ["doc1", "doc2", "doc3"]
        test_docs = [
            "LiFePO4 cathode material",
            "Lithium ion battery",
            "Electric vehicle application"
        ]
        test_embeddings = [
            [0.1] * 1024,
            [0.2] * 1024,
            [0.3] * 1024
        ]
        test_metadatas = [
            {"source": "paper1", "doi": "10.1234/test1"},
            {"source": "paper2", "doi": "10.1234/test2"},
            {"source": "paper3", "doi": "10.1234/test3"}
        ]
        
        # Insert data
        print("Inserting test data...")
        stats = manager.batch_insert(
            collection,
            test_ids,
            test_docs,
            test_embeddings,
            test_metadatas,
            batch_size=2
        )
        print(f"✓ Inserted: {stats['inserted']}/{stats['total']}")
        print()
        
        # Verify collection
        print("Verifying collection...")
        verification = manager.verify_collection(collection)
        if 'error' in verification:
            print(f"✗ Verification error: {verification['error']}")
        else:
            print(f"✓ Count: {verification['count']}")
            print(f"✓ Has documents: {verification['has_documents']}")
            print(f"✓ Has embeddings: {verification['has_embeddings']}")
            print(f"✓ Has metadatas: {verification['has_metadatas']}")
            if verification.get('sample_ids'):
                print(f"✓ Sample IDs: {verification['sample_ids']}")
        print()
        
        # List collections
        print("Listing collections...")
        collections = manager.list_collections()
        print(f"✓ Collections: {collections}")


if __name__ == "__main__":
    main()
