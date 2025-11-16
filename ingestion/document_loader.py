"""
Document loader for JSON files from the data directory.
Works directly with JSON structure without unnecessary text conversion.
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document


class JSONDocumentLoader:
    """Loads and processes JSON documents from the data directory."""
    
    def __init__(self, data_dir: str):
        """
        Initialize the JSON document loader.
        
        Args:
            data_dir: Path to the directory containing JSON files
        """
        self.data_dir = Path(data_dir)
    
    def load_documents(self) -> List[Document]:
        """
        Load all JSON files from the data directory and convert them to LangChain Documents.
        Preserves JSON structure for better chunking and embedding.
        
        Returns:
            List of Document objects
        """
        documents = []
        
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {self.data_dir}")
        
        # Find all JSON files recursively
        json_files = list(self.data_dir.rglob("*.json"))
        
        if not json_files:
            raise ValueError(f"No JSON files found in {self.data_dir}")
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Process each item in the JSON array
                if isinstance(data, list):
                    for idx, item in enumerate(data):
                        doc = self._json_to_document(item, json_file, idx)
                        if doc:
                            documents.append(doc)
                elif isinstance(data, dict):
                    doc = self._json_to_document(data, json_file, 0)
                    if doc:
                        documents.append(doc)
                    
            except json.JSONDecodeError as e:
                print(f"[ERROR] Invalid JSON in {json_file}: {e}")
                continue
            except Exception as e:
                print(f"[ERROR] Error loading {json_file}: {e}")
                continue
        
        if not documents:
            raise ValueError(f"No valid documents loaded from {self.data_dir}")
        
        return documents
    
    def _json_to_document(self, data: Dict[Any, Any], source_file: Path, index: int) -> Optional[Document]:
        """
        Convert a JSON object to a LangChain Document.
        Preserves JSON structure for structured chunking.
        
        Args:
            data: JSON data dictionary
            source_file: Path to the source file
            index: Index of the item in the array
            
        Returns:
            Document object with JSON content and metadata, or None if invalid
        """
        if not isinstance(data, dict):
            return None
        
        # Store JSON as structured text (JSON string) for better embedding
        # This preserves structure while being embeddable
        json_text = json.dumps(data, ensure_ascii=False, indent=2)
        
        # Extract comprehensive metadata
        # Store all important fields for filtering and retrieval
        summary = data.get("summary", {})
        source = data.get("source", {})
        
        # Get file modification time for tracking data freshness
        file_mod_time = os.path.getmtime(source_file) if source_file.exists() else None
        
        metadata = {
            "source": str(source_file),
            "source_file": source_file.name,
            "index": index,
            "fund_name": data.get("fund_name", ""),
            "fund_category": summary.get("fund_category", ""),
            "fund_type": summary.get("fund_type", ""),
            "risk_level": summary.get("risk_level", ""),
            "lock_in_period": summary.get("lock_in_period", ""),
            "source_site": source.get("site", "") if isinstance(source, dict) else "",
            "source_page_ref": source.get("page_ref", "") if isinstance(source, dict) else "",
            "source_url": data.get("source_url", ""),
            "last_scraped": data.get("last_scraped", ""),
            "file_mod_time": file_mod_time,  # Track file modification time for freshness checks
        }
        
        return Document(page_content=json_text, metadata=metadata)
    

