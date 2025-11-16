"""
JSON-aware chunking utilities for splitting structured documents into semantic chunks.
Works with JSON structure to create meaningful chunks.
"""
import json
from typing import List, Dict, Any
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import config


class DocumentChunker:
    """Handles intelligent chunking of JSON documents for vector storage."""
    
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        use_semantic_chunking: bool = True
    ):
        """
        Initialize the document chunker.
        
        Args:
            chunk_size: Size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters
            use_semantic_chunking: If True, creates semantic chunks from JSON structure
        """
        self.chunk_size = chunk_size or config.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or config.CHUNK_OVERLAP
        self.use_semantic_chunking = use_semantic_chunking
        
        # Text splitter for fallback or non-JSON content
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into chunks using JSON-aware semantic chunking.
        
        Args:
            documents: List of Document objects to chunk
            
        Returns:
            List of chunked Document objects
        """
        chunks = []
        
        for doc in documents:
            if self.use_semantic_chunking:
                # Try JSON-aware chunking first
                json_chunks = self._chunk_json_document(doc)
                if json_chunks:
                    chunks.extend(json_chunks)
                    continue
            
            # Fallback to text-based chunking
            doc_chunks = self.text_splitter.split_text(doc.page_content)
            
            for i, chunk_text in enumerate(doc_chunks):
                chunk_metadata = doc.metadata.copy()
                chunk_metadata["chunk_index"] = i
                chunk_metadata["total_chunks"] = len(doc_chunks)
                chunk_metadata["chunk_type"] = "text"
                
                chunk = Document(
                    page_content=chunk_text,
                    metadata=chunk_metadata
                )
                chunks.append(chunk)
        
        return chunks
    
    def _chunk_json_document(self, doc: Document) -> List[Document]:
        """
        Create semantic chunks from JSON document structure.
        Groups related fields together for better embedding quality.
        
        Args:
            doc: Document object with JSON content
            
        Returns:
            List of chunked Document objects, or empty list if not JSON
        """
        try:
            # Try to parse as JSON
            json_data = json.loads(doc.page_content)
            if not isinstance(json_data, dict):
                return []
        except (json.JSONDecodeError, TypeError):
            # Not JSON, return empty to use fallback
            return []
        
        chunks = []
        base_metadata = doc.metadata.copy()
        
        # Remove json_data from metadata (too large for storage)
        if "json_data" in base_metadata:
            del base_metadata["json_data"]
        
        # Define semantic groups for chunking
        # Note: peer_comparison_sample is included but may be empty
        semantic_groups = {
            "fund_overview": [
                "fund_name", "nav", "fund_size", "aum", "summary"
            ],
            "investment_details": [
                "minimum_investments", "returns", "category_info"
            ],
            "costs_and_taxes": [
                "cost_and_tax"
            ],
            "holdings": [
                "top_5_holdings"
            ],
            "performance_metrics": [
                "advanced_ratios"
            ],
            "comparison_data": [
                "peer_comparison_sample"
            ],
            "metadata": [
                "source", "source_url", "last_scraped"
            ]
        }
        
        # Create chunks for each semantic group
        chunk_index = 0
        for group_name, fields in semantic_groups.items():
            group_data = {}
            for field in fields:
                if field in json_data:
                    group_data[field] = json_data[field]
            
            if not group_data:
                continue
            
            # Create readable text representation for this group
            chunk_text = self._format_json_group(group_name, group_data, json_data.get("fund_name", ""))
            
            # If chunk is too large, split it further
            if len(chunk_text) > self.chunk_size:
                sub_chunks = self.text_splitter.split_text(chunk_text)
                for i, sub_chunk in enumerate(sub_chunks):
                    chunk_metadata = base_metadata.copy()
                    chunk_metadata["chunk_index"] = chunk_index
                    chunk_metadata["chunk_type"] = "semantic"
                    chunk_metadata["semantic_group"] = group_name
                    chunk_metadata["sub_chunk"] = i
                    chunk_metadata["total_sub_chunks"] = len(sub_chunks)
                    
                    chunks.append(Document(
                        page_content=sub_chunk,
                        metadata=chunk_metadata
                    ))
                    chunk_index += 1
            else:
                chunk_metadata = base_metadata.copy()
                chunk_metadata["chunk_index"] = chunk_index
                chunk_metadata["chunk_type"] = "semantic"
                chunk_metadata["semantic_group"] = group_name
                
                chunks.append(Document(
                    page_content=chunk_text,
                    metadata=chunk_metadata
                ))
                chunk_index += 1
        
        # Update total_chunks in all metadata
        for chunk in chunks:
            chunk.metadata["total_chunks"] = len(chunks)
        
        return chunks
    
    def _format_json_group(self, group_name: str, group_data: Dict[str, Any], fund_name: str) -> str:
        """
        Format a JSON group into readable text for embedding.
        
        Args:
            group_name: Name of the semantic group
            group_data: Dictionary containing the group's data
            fund_name: Fund name for context
            
        Returns:
            Formatted text string
        """
        lines = []
        
        # Add fund name context if available
        if fund_name:
            lines.append(f"Fund: {fund_name}")
        
        # Format based on group type
        if group_name == "fund_overview":
            if "fund_name" in group_data:
                lines.append(f"Fund Name: {group_data['fund_name']}")
            if "nav" in group_data:
                nav = group_data["nav"]
                lines.append(f"NAV: {nav.get('value', 'N/A')} as of {nav.get('as_of', 'N/A')}")
            if "fund_size" in group_data:
                lines.append(f"Fund Size: {group_data['fund_size']}")
            if "aum" in group_data:
                lines.append(f"AUM (Assets Under Management): {group_data['aum']}")
            if "summary" in group_data:
                summary = group_data["summary"]
                lines.append(f"Category: {summary.get('fund_category', 'N/A')}")
                lines.append(f"Type: {summary.get('fund_type', 'N/A')}")
                lines.append(f"Risk Level: {summary.get('risk_level', 'N/A')}")
                if summary.get('lock_in_period'):
                    lines.append(f"Lock-in Period: {summary['lock_in_period']}")
                if summary.get('rating') is not None:
                    lines.append(f"Rating: {summary['rating']}")
        
        elif group_name == "investment_details":
            if "minimum_investments" in group_data:
                min_inv = group_data["minimum_investments"]
                lines.append("Minimum Investments:")
                lines.append(f"  First Investment: {min_inv.get('min_first_investment', 'N/A')}")
                lines.append(f"  SIP: {min_inv.get('min_sip', 'N/A')}")
                if min_inv.get('min_2nd_investment_onwards'):
                    lines.append(f"  2nd Investment Onwards: {min_inv['min_2nd_investment_onwards']}")
            if "returns" in group_data:
                returns = group_data["returns"]
                lines.append("Returns:")
                for period, value in returns.items():
                    period_name = period.replace('_', ' ').title()
                    lines.append(f"  {period_name}: {value}")
            if "category_info" in group_data:
                cat_info = group_data["category_info"]
                lines.append(f"Category: {cat_info.get('category', 'N/A')}")
                if "category_average_annualised" in cat_info:
                    avg = cat_info["category_average_annualised"]
                    lines.append("Category Average Returns:")
                    for period, value in avg.items():
                        period_name = period.replace('_', ' ').title()
                        lines.append(f"  {period_name}: {value}")
                if "rank_within_category" in cat_info:
                    rank = cat_info["rank_within_category"]
                    lines.append(f"Category Rank: 1Y={rank.get('1y', 'N/A')}, 3Y={rank.get('3y', 'N/A')}, 5Y={rank.get('5y', 'N/A')}")
        
        elif group_name == "costs_and_taxes":
            if "cost_and_tax" in group_data:
                cost = group_data["cost_and_tax"]
                lines.append("Costs and Taxes:")
                lines.append(f"  Expense Ratio: {cost.get('expense_ratio', 'N/A')}")
                if cost.get("expense_ratio_effective_from"):
                    lines.append(f"  Expense Ratio Effective From: {cost['expense_ratio_effective_from']}")
                if cost.get("exit_load"):
                    lines.append(f"  Exit Load: {cost['exit_load']}")
                if cost.get("stamp_duty"):
                    lines.append(f"  Stamp Duty: {cost['stamp_duty']}")
                if cost.get("tax_implication"):
                    lines.append(f"  Tax Implication: {cost['tax_implication']}")
        
        elif group_name == "holdings":
            if "top_5_holdings" in group_data:
                lines.append("Top 5 Holdings:")
                for holding in group_data["top_5_holdings"]:
                    lines.append(f"  {holding.get('name', 'N/A')}: {holding.get('asset_pct', 'N/A')}")
        
        elif group_name == "performance_metrics":
            if "advanced_ratios" in group_data:
                ratios = group_data["advanced_ratios"]
                lines.append("Performance Metrics:")
                for key, value in ratios.items():
                    if value:  # Only include non-empty values
                        key_name = key.replace('_', ' ').title()
                        lines.append(f"  {key_name}: {value}")
        
        elif group_name == "comparison_data":
            if "peer_comparison_sample" in group_data:
                peers = group_data["peer_comparison_sample"]
                if peers and len(peers) > 0:
                    lines.append("Peer Comparison Sample:")
                    for i, peer in enumerate(peers, 1):
                        if isinstance(peer, dict):
                            peer_name = peer.get('name', f'Peer {i}')
                            lines.append(f"  {peer_name}")
                            for key, value in peer.items():
                                if key != 'name' and value:
                                    key_name = key.replace('_', ' ').title()
                                    lines.append(f"    {key_name}: {value}")
        
        elif group_name == "metadata":
            if "source" in group_data:
                source = group_data["source"]
                if isinstance(source, dict):
                    lines.append(f"Source Site: {source.get('site', 'N/A')}")
                    lines.append(f"Source Page Ref: {source.get('page_ref', 'N/A')}")
                else:
                    lines.append(f"Source: {source}")
            if "source_url" in group_data:
                lines.append(f"Source URL: {group_data['source_url']}")
            if "last_scraped" in group_data:
                lines.append(f"Last Scraped: {group_data['last_scraped']}")
        
        # Fallback: if no specific formatting, use JSON
        if not lines:
            lines.append(json.dumps(group_data, ensure_ascii=False, indent=2))
        
        return "\n".join(lines)

