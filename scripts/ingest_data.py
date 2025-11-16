"""
Standalone script to ingest data into the vector store.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.document_loader import JSONDocumentLoader
from ingestion.chunker import DocumentChunker
from vector_store.chroma_store import ChromaVectorStore
import config


def main():
    """Ingest documents from the data directory."""
    print("Starting document ingestion...")
    
    try:
        # Initialize components
        print("1. Loading documents...")
        loader = JSONDocumentLoader(config.DATA_DIR)
        
        # Check if data directory exists and has files
        import os
        from pathlib import Path
        data_dir = Path(config.DATA_DIR)
        if not data_dir.exists():
            print(f"   [WARN] Data directory does not exist: {data_dir}")
            print("   [INFO] Skipping ingestion - no data directory")
            return
        
        json_files = list(data_dir.rglob("*.json"))
        if len(json_files) == 0:
            print(f"   [WARN] No JSON files found in {data_dir}")
            print("   [INFO] Skipping ingestion - no files to process")
            return
        
        documents = loader.load_documents()
        print(f"   Loaded {len(documents)} documents")
        
        print("2. Chunking documents...")
        chunker = DocumentChunker()
        chunks = chunker.chunk_documents(documents)
        print(f"   Created {len(chunks)} chunks")
        
        print("3. Initializing vector store...")
        vector_store = ChromaVectorStore()
        
        print("4. Generating embeddings and storing...")
        doc_ids = vector_store.upsert_documents(chunks)
        print(f"   Stored {len(doc_ids)} chunks in vector store")
        
        # Get collection info
        collection_info = vector_store.get_collection_info()
        print("\n[SUCCESS] Ingestion complete!")
        print(f"   Collection: {collection_info['collection_name']}")
        print(f"   Total documents: {collection_info['document_count']}")
        print(f"   Database path: {collection_info['db_path']}")
        
    except Exception as e:
        print(f"\n[ERROR] Error during ingestion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

