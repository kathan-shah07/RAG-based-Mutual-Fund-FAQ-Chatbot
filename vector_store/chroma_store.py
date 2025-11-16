"""
ChromaDB vector store integration for storing and retrieving embeddings.
"""
import chromadb
from chromadb.config import Settings
from typing import List, Optional, Dict, Any
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from datetime import datetime, timedelta
import config
import time


class ChromaVectorStore:
    """Manages vector storage and retrieval using ChromaDB."""
    
    def __init__(
        self,
        collection_name: str = None,
        db_path: str = None,
        embedding_model: str = None
    ):
        """
        Initialize the ChromaDB vector store.
        
        Args:
            collection_name: Name of the ChromaDB collection
            db_path: Path to the ChromaDB database
            embedding_model: Name of the Gemini embedding model
        """
        self.collection_name = collection_name or config.COLLECTION_NAME
        self.db_path = db_path or config.CHROMA_DB_PATH
        self.embedding_model = embedding_model or config.GEMINI_EMBEDDING_MODEL
        
        # Initialize embeddings
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=self.embedding_model,
            google_api_key=config.GEMINI_API_KEY
        )
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def _batch_embed_documents(self, texts: List[str], batch_size: int = 10, delay: float = 1.0, max_retries: int = 2) -> List[List[float]]:
        """
        Generate embeddings in batches to avoid API quota issues.
        Uses smaller batches and exponential backoff for retries.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts per batch (default: 10 for free tier)
            delay: Delay between batches in seconds (default: 1.0)
            max_retries: Maximum number of retries per batch (reduced to 2 to minimize failed calls)
            
        Returns:
            List of embeddings
        """
        all_embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size
        api_call_count = 0
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            
            retry_count = 0
            success = False
            
            while retry_count <= max_retries and not success:
                try:
                    # Generate embeddings for this batch
                    api_call_count += 1
                    batch_embeddings = self.embeddings.embed_documents(batch)
                    all_embeddings.extend(batch_embeddings)
                    success = True
                    
                    if retry_count > 0:
                        print(f"[OK] Batch {batch_num}/{total_batches} succeeded after {retry_count} retry(ies)")
                    else:
                        print(f"[OK] Batch {batch_num}/{total_batches} completed (API call #{api_call_count})")
                    
                    # Add delay between batches to respect rate limits
                    if i + batch_size < len(texts):
                        time.sleep(delay)
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    if "quota" in error_msg or "429" in error_msg or "resource" in error_msg:
                        # Check if quota is completely exhausted (limit: 0)
                        if "limit: 0" in error_msg or "free_tier_requests" in error_msg:
                            print(f"[ERROR] API quota completely exhausted (limit: 0)")
                            print(f"[INFO] No retries will be attempted to avoid additional failed API calls")
                            print(f"[INFO] Please check: https://ai.dev/usage?tab=rate-limit")
                            print(f"[INFO] Quota typically resets daily. Try again later.")
                            raise
                        
                        # For other quota errors, retry with backoff
                        retry_count += 1
                        if retry_count <= max_retries:
                            # Exponential backoff: 5s, 10s, 20s
                            wait_time = 5 * (2 ** (retry_count - 1))
                            print(f"[WARN] API quota exceeded at batch {batch_num}/{total_batches}")
                            print(f"[INFO] Retry {retry_count}/{max_retries} - Waiting {wait_time} seconds...")
                            time.sleep(wait_time)
                        else:
                            print(f"[ERROR] Failed after {max_retries} retries")
                            print(f"[INFO] Quota limit reached. Please check: https://ai.dev/usage?tab=rate-limit")
                            print(f"[INFO] Quota typically resets daily. Try again later.")
                            raise
                    else:
                        # Non-quota error, raise immediately
                        raise
            
            if not success:
                raise Exception(f"Failed to embed batch {batch_num} after {max_retries} retries")
        
        print(f"[INFO] Total API calls made: {api_call_count}")
        return all_embeddings
    
    def add_documents(self, documents: List[Document], batch_size: int = 50) -> List[str]:
        """
        Add documents to the vector store with batching support.
        
        Args:
            documents: List of Document objects to add
            batch_size: Number of documents to process per batch
            
        Returns:
            List of document IDs
        """
        if not documents:
            return []
        
        # Extract texts and metadata
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        
        # Generate embeddings in batches (smaller batch size for free tier)
        if batch_size > 10:
            print(f"[INFO] Using batch size 10 (recommended for free tier)")
            batch_size = 10
        print(f"[INFO] Generating embeddings for {len(texts)} documents in batches of {batch_size}...")
        embeddings = self._batch_embed_documents(texts, batch_size=batch_size, delay=1.0)
        
        # Generate unique IDs
        ids = [f"{doc.metadata.get('source_file', 'doc')}_{doc.metadata.get('chunk_index', 0)}_{i}" 
               for i, doc in enumerate(documents)]
        
        # Add to ChromaDB
        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        return ids
    
    def upsert_documents(self, documents: List[Document], batch_size: int = 50, skip_existing: bool = True) -> List[str]:
        """
        Upsert documents to the vector store with batching support (update if exists, insert if not).
        
        Args:
            documents: List of Document objects to upsert
            batch_size: Number of documents to process per batch
            skip_existing: If True, skip documents that already exist (avoids API calls)
            
        Returns:
            List of document IDs
        """
        if not documents:
            return []
        
        # Generate unique IDs
        ids = [f"{doc.metadata.get('source_file', 'doc')}_{doc.metadata.get('chunk_index', 0)}_{i}" 
               for i, doc in enumerate(documents)]
        
        # Check which documents already exist (to avoid unnecessary API calls)
        existing_ids = set()
        if skip_existing:
            try:
                # Get all existing IDs from collection
                existing_count = self.collection.count()
                if existing_count > 0:
                    # Get all existing IDs (ChromaDB allows getting all IDs)
                    all_existing = self.collection.get()
                    if all_existing and all_existing.get('ids'):
                        existing_ids = set(all_existing['ids'])
                        # Check if any of our IDs match existing ones
                        matching_ids = [id for id in ids if id in existing_ids]
                        if matching_ids:
                            print(f"[INFO] Found {len(matching_ids)} existing document(s) - will skip embedding generation")
            except Exception as e:
                print(f"[WARN] Could not check existing documents: {e}")
                # Continue without skipping if check fails
        
        # Filter out documents that already exist
        new_documents = []
        # Separate new and existing documents
        new_ids = []
        existing_ids_to_update = []
        for i, doc in enumerate(documents):
            if ids[i] not in existing_ids:
                new_documents.append(doc)
                new_ids.append(ids[i])
            else:
                existing_ids_to_update.append(ids[i])
        
        # Update ingestion timestamp for all documents (new and existing)
        ingestion_timestamp = datetime.now().isoformat()
        
        # Update timestamps for existing documents
        if existing_ids_to_update:
            existing_metadatas = []
            for doc_id in existing_ids_to_update:
                # Get existing metadata
                existing_doc = self.collection.get(ids=[doc_id], include=["metadatas"])
                if existing_doc and existing_doc.get('metadatas') and len(existing_doc['metadatas']) > 0:
                    existing_metadata = existing_doc['metadatas'][0].copy()
                    # Update ingestion timestamp
                    existing_metadata['ingestion_timestamp'] = ingestion_timestamp
                    existing_metadatas.append(existing_metadata)
            
            if existing_metadatas:
                # Update metadata for existing documents
                self.collection.update(
                    ids=existing_ids_to_update,
                    metadatas=existing_metadatas
                )
                print(f"[INFO] Updated ingestion timestamp for {len(existing_ids_to_update)} existing document(s)")
        
        if not new_documents:
            print(f"[INFO] All {len(documents)} document(s) already exist in database - updated timestamps only")
            return ids
        
        print(f"[INFO] Processing {len(new_documents)} new document(s) (updating {len(existing_ids_to_update)} existing)")
        
        # Extract texts and metadata for new documents only
        # Clean metadata to remove large objects that can't be stored in ChromaDB
        # Add ingestion timestamp to track when data was ingested
        texts = []
        metadatas = []
        for doc in new_documents:
            texts.append(doc.page_content)
            # Clean metadata - remove json_data and other large objects
            clean_metadata = {}
            for key, value in doc.metadata.items():
                # Only store simple types (str, int, float, bool, None)
                if isinstance(value, (str, int, float, bool, type(None))):
                    clean_metadata[key] = value
            # Add ingestion timestamp
            clean_metadata['ingestion_timestamp'] = ingestion_timestamp
            metadatas.append(clean_metadata)
        
        # Generate embeddings in batches (smaller batch size for free tier)
        if batch_size > 10:
            print(f"[INFO] Using batch size 10 (recommended for free tier)")
            batch_size = 10
        print(f"[INFO] Generating embeddings for {len(texts)} documents in batches of {batch_size}...")
        embeddings = self._batch_embed_documents(texts, batch_size=batch_size, delay=1.0)
        
        # Upsert to ChromaDB (only new documents)
        self.collection.upsert(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=new_ids
        )
        
        return ids
    
    def similarity_search(
        self,
        query: str,
        k: int = None,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Perform similarity search in the vector store.
        
        Args:
            query: Query text to search for
            k: Number of results to return
            filter: Optional metadata filter
            
        Returns:
            List of Document objects
        """
        k = k or config.TOP_K_RESULTS
        
        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)
        
        # Build where clause for filtering
        where = filter if filter else None
        
        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=where
        )
        
        # Convert results to Document objects
        documents = []
        if results["documents"] and len(results["documents"][0]) > 0:
            for i in range(len(results["documents"][0])):
                doc = Document(
                    page_content=results["documents"][0][i],
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {}
                )
                documents.append(doc)
        
        return documents
    
    def similarity_search_with_score(
        self,
        query: str,
        k: int = None,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[tuple[Document, float]]:
        """
        Perform similarity search with relevance scores.
        
        Args:
            query: Query text to search for
            k: Number of results to return
            filter: Optional metadata filter
            
        Returns:
            List of tuples (Document, score)
        """
        k = k or config.TOP_K_RESULTS
        
        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)
        
        # Build where clause for filtering
        where = filter if filter else None
        
        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        # Convert results to Document objects with scores
        documents_with_scores = []
        if results["documents"] and len(results["documents"][0]) > 0:
            for i in range(len(results["documents"][0])):
                doc = Document(
                    page_content=results["documents"][0][i],
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {}
                )
                # Convert distance to similarity score (1 - distance for cosine similarity)
                distance = results["distances"][0][i] if results["distances"] else 0.0
                score = 1 - distance  # Cosine distance to similarity
                documents_with_scores.append((doc, score))
        
        return documents_with_scores
    
    def delete_collection(self):
        """Delete the entire collection."""
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the collection.
        
        Returns:
            Dictionary with collection information
        """
        count = self.collection.count()
        latest_timestamp = self.get_latest_ingestion_timestamp()
        return {
            "collection_name": self.collection_name,
            "document_count": count,
            "db_path": self.db_path,
            "latest_ingestion_timestamp": latest_timestamp
        }
    
    def get_latest_ingestion_timestamp(self) -> Optional[datetime]:
        """
        Get the latest ingestion timestamp from vector database.
        Checks all documents' metadata for ingestion_timestamp.
        
        Returns:
            Latest ingestion datetime or None if no data exists
        """
        try:
            # Get all documents with metadata
            all_docs = self.collection.get(include=["metadatas"])
            
            if not all_docs or not all_docs.get('metadatas'):
                return None
            
            latest_timestamp = None
            
            for metadata in all_docs['metadatas']:
                # Check for ingestion_timestamp (stored as ISO string)
                ingestion_ts = metadata.get('ingestion_timestamp')
                if ingestion_ts:
                    try:
                        # Parse ISO format timestamp
                        if isinstance(ingestion_ts, str):
                            ts = datetime.fromisoformat(ingestion_ts.replace('Z', '+00:00'))
                        elif isinstance(ingestion_ts, (int, float)):
                            ts = datetime.fromtimestamp(ingestion_ts)
                        else:
                            continue
                        
                        if latest_timestamp is None or ts > latest_timestamp:
                            latest_timestamp = ts
                    except (ValueError, TypeError, OSError):
                        continue
                
                # Fallback: check file_mod_time
                file_mod_time = metadata.get('file_mod_time')
                if file_mod_time:
                    try:
                        if isinstance(file_mod_time, (int, float)):
                            ts = datetime.fromtimestamp(file_mod_time)
                            if latest_timestamp is None or ts > latest_timestamp:
                                latest_timestamp = ts
                    except (ValueError, TypeError, OSError):
                        continue
            
            return latest_timestamp
            
        except Exception as e:
            print(f"[WARN] Could not retrieve latest ingestion timestamp: {e}")
            return None
    
    def check_if_data_needs_update(self, interval_hours: float) -> tuple[bool, Optional[datetime], Optional[datetime]]:
        """
        Check if data in vector database needs update based on interval.
        
        Args:
            interval_hours: Number of hours after which data should be updated
            
        Returns:
            Tuple of (needs_update: bool, latest_timestamp: Optional[datetime], next_update_time: Optional[datetime])
        """
        latest_timestamp = self.get_latest_ingestion_timestamp()
        
        if latest_timestamp is None:
            # No data exists, needs update
            return True, None, None
        
        now = datetime.now()
        time_since_ingestion = now - latest_timestamp
        interval_delta = timedelta(hours=interval_hours)
        
        needs_update = time_since_ingestion >= interval_delta
        next_update_time = latest_timestamp + interval_delta if not needs_update else None
        
        return needs_update, latest_timestamp, next_update_time
    
    def get_existing_urls(self) -> set[str]:
        """
        Get all unique source URLs currently in the vector database.
        
        Returns:
            Set of normalized URLs
        """
        try:
            # Get all documents with metadata
            all_docs = self.collection.get(include=["metadatas"])
            
            if not all_docs or not all_docs.get('metadatas'):
                return set()
            
            urls = set()
            for metadata in all_docs['metadatas']:
                source_url = metadata.get('source_url')
                if source_url:
                    # Normalize URL (remove trailing slashes, convert to lowercase for comparison)
                    normalized = source_url.strip().rstrip('/').lower()
                    if normalized:
                        urls.add(normalized)
            
            return urls
            
        except Exception as e:
            print(f"[WARN] Could not retrieve existing URLs: {e}")
            return set()
    
    def find_new_urls(self, config_urls: List[str]) -> List[str]:
        """
        Compare config URLs with URLs in vector database to find new ones.
        
        Args:
            config_urls: List of URLs from config
            
        Returns:
            List of new URLs that are not in the vector database
        """
        existing_urls = self.get_existing_urls()
        
        new_urls = []
        for url in config_urls:
            if not url:
                continue
            # Normalize URL for comparison
            normalized = url.strip().rstrip('/').lower()
            if normalized and normalized not in existing_urls:
                new_urls.append(url)  # Return original URL, not normalized
        
        return new_urls
    
    def get_all_funds(self) -> List[Document]:
        """
        Retrieve all unique fund documents from the vector store.
        Returns all chunks for each fund to ensure complete information.
        
        Returns:
            List of Document objects, all chunks for all funds
        """
        try:
            # Get all documents from the collection
            all_docs = self.collection.get(include=["documents", "metadatas"])
            
            if not all_docs or not all_docs.get('documents'):
                return []
            
            # Return all documents that have a fund_name (filter out any metadata-only docs)
            documents = []
            for i, metadata in enumerate(all_docs.get('metadatas', [])):
                fund_name = metadata.get('fund_name', '')
                if fund_name:  # Only include documents with fund names
                    doc = Document(
                        page_content=all_docs['documents'][i],
                        metadata=metadata
                    )
                    documents.append(doc)
            
            return documents
            
        except Exception as e:
            print(f"[WARN] Could not retrieve all funds: {e}")
            return []

