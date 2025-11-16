"""
RAG chain implementation using Gemini LLM and vector retrieval.
"""
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from vector_store.chroma_store import ChromaVectorStore
import config
import re
from urllib.parse import urlparse, urlunparse


def normalize_url(url: str) -> Optional[str]:
    """
    Normalize and validate a URL to ensure it's a full URL.
    
    Args:
        url: URL string to normalize
        
    Returns:
        Normalized full URL (with http:// or https://) or None if invalid
    """
    if not url or not isinstance(url, str):
        return None
    
    url = url.strip()
    if not url:
        return None
    
    # Remove any trailing punctuation that might have been included incorrectly
    url = url.rstrip('.,;:!?)')
    
    # If URL doesn't start with http:// or https://, try to add https://
    if not url.startswith(('http://', 'https://')):
        # Check if it looks like a domain
        if re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}', url):
            url = 'https://' + url
        else:
            # If it doesn't look like a valid domain, return None
            return None
    
    # Validate URL structure
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return None
        # Reconstruct URL to ensure it's properly formatted
        normalized = urlunparse(parsed)
        return normalized
    except Exception:
        return None


def extract_urls_from_text(text: str) -> List[str]:
    """
    Extract all full URLs from text.
    
    Args:
        text: Text to extract URLs from
        
    Returns:
        List of normalized full URLs
    """
    if not text:
        return []
    
    # Pattern to match http:// or https:// URLs
    url_pattern = r'https?://[^\s\)\]\>\"\'\n]+'
    matches = re.findall(url_pattern, text, re.IGNORECASE)
    
    normalized_urls = []
    for match in matches:
        normalized = normalize_url(match)
        if normalized and normalized not in normalized_urls:
            normalized_urls.append(normalized)
    
    return normalized_urls


class RAGChain:
    """RAG chain for generating answers using retrieved context."""
    
    def __init__(
        self,
        vector_store: ChromaVectorStore,
        model_name: str = None,
        temperature: float = 0.7
    ):
        """
        Initialize the RAG chain.
        
        Args:
            vector_store: ChromaVectorStore instance
            model_name: Name of the Gemini model to use
            temperature: Temperature for LLM generation
        """
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        self.vector_store = vector_store
        self.model_name = model_name or config.GEMINI_MODEL
        self.temperature = temperature
        
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=config.GEMINI_API_KEY,
            temperature=self.temperature,
            convert_system_message_to_human=True
        )
        
        # Create retriever
        self.retriever = self._create_retriever()
        
        # Simple conversation history storage
        self.conversation_history = []
    
    def _create_retriever(self):
        """Create a retriever from the vector store."""
        # Custom retriever that uses our vector store
        class CustomRetriever:
            def __init__(self, vector_store: ChromaVectorStore, k: int = None):
                self.vector_store = vector_store
                self.k = k or config.TOP_K_RESULTS
            
            def get_relevant_documents(self, query: str) -> List[Document]:
                return self.vector_store.similarity_search(query, k=self.k)
        
        return CustomRetriever(self.vector_store)
    
    def query(
        self,
        question: str,
        return_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Query the RAG chain with a question (delegates to query_with_retrieval).
        
        Args:
            question: User's question
            return_sources: Whether to return source documents
            
        Returns:
            Dictionary with answer and optionally sources
        """
        return self.query_with_retrieval(question, return_scores=False)
    
    def _is_parameter_only_query(self, question: str) -> tuple[bool, Optional[str]]:
        """
        Detect if the query is asking for a specific parameter across all funds.
        
        Args:
            question: User's question
            
        Returns:
            Tuple of (is_parameter_query: bool, parameter_name: Optional[str])
        """
        question_lower = question.lower()
        
        # Common parameter names and their variations
        parameter_patterns = {
            'aum': ['aum', 'assets under management', 'assets under mgmt'],
            'fund_size': ['fund size', 'size of fund'],
            'expense_ratio': ['expense ratio', 'ter', 'total expense ratio'],
            'nav': ['nav', 'net asset value'],
            'returns': ['returns', 'return', 'performance'],
            'exit_load': ['exit load', 'exit load charges'],
            'min_sip': ['minimum sip', 'min sip', 'sip minimum', 'minimum investment'],
            'risk_level': ['risk level', 'risk', 'riskometer'],
            'category': ['category', 'fund category'],
            'lock_in': ['lock in', 'lock-in', 'lockin period']
        }
        
        # Check for parameter keywords
        for param_name, patterns in parameter_patterns.items():
            for pattern in patterns:
                if pattern in question_lower:
                    # Check if a specific fund name is mentioned
                    # Look for common fund name patterns (fund names usually have capital letters or specific formats)
                    # But also check for explicit fund indicators
                    fund_indicators = [' of ', ' for ', ' fund', ' scheme', ' plan']
                    has_specific_fund = any(
                        indicator in question_lower and 
                        not any(word in question_lower for word in ['all', 'every', 'each', 'list', 'show', 'table', 'compare'])
                        for indicator in fund_indicators
                    )
                    
                    # If no specific fund is mentioned, OR if user explicitly asks for all/every/list/show, treat as parameter-only query
                    if not has_specific_fund or any(word in question_lower for word in ['all', 'every', 'each', 'list', 'show', 'table', 'compare']):
                        return True, param_name
        
        return False, None
    
    def query_with_retrieval(
        self,
        question: str,
        k: int = None,
        return_scores: bool = False
    ) -> Dict[str, Any]:
        """
        Query with explicit retrieval step and custom k value.
        
        Args:
            question: User's question
            k: Number of documents to retrieve
            return_scores: Whether to return similarity scores
            
        Returns:
            Dictionary with answer, retrieved documents, and sources
        """
        k = k or config.TOP_K_RESULTS
        
        # Check if this is a parameter-only query (e.g., "show me AUM for all funds")
        is_parameter_query, parameter_name = self._is_parameter_only_query(question)
        
        # If it's a parameter-only query, retrieve all funds
        if is_parameter_query:
            documents = self.vector_store.get_all_funds()
            scores = None
        else:
            # Retrieve relevant documents - increase k slightly for better coverage
            # This helps ensure we get all relevant funds when comparing or querying multiple items
            retrieval_k = max(k, 5) if "compare" in question.lower() or "multiple" in question.lower() else k
            
            if return_scores:
                retrieved_docs = self.vector_store.similarity_search_with_score(question, k=retrieval_k)
                documents = [doc for doc, score in retrieved_docs]
                scores = [score for doc, score in retrieved_docs]
            else:
                retrieved_docs = self.vector_store.similarity_search(question, k=retrieval_k)
                documents = retrieved_docs
                scores = None
        
        # Create context from retrieved documents
        context = "\n\n".join([doc.page_content for doc in documents])
        
        # Extract and normalize source URLs from retrieved documents for citation
        # Collect ALL unique source URLs from all retrieved documents
        source_urls = []
        seen_urls = set()  # Track normalized URLs to avoid duplicates
        for doc in documents:
            url = doc.metadata.get("source_url", "")
            if url:
                normalized_url = normalize_url(url)
                if normalized_url and normalized_url not in seen_urls:
                    source_urls.append(normalized_url)
                    seen_urls.add(normalized_url)
        
        # Get all unique normalized source URLs for citations
        all_citations = ", ".join(source_urls) if source_urls else "N/A"
        primary_citation = source_urls[0] if source_urls else ""
        
        # Generate answer using LLM
        parameter_instruction = ""
        if is_parameter_query:
            parameter_instruction = f"""

CRITICAL: The user is asking for {parameter_name.upper()} across ALL available funds. 
- You MUST extract {parameter_name} for EVERY fund mentioned in the context
- Format your answer as a TABLE with columns: Fund Name and {parameter_name.replace('_', ' ').title()}
- Include ALL funds from the context in the table
- If a fund doesn't have {parameter_name} data, write "N/A" in that cell
- Example format:
  | Fund Name | {parameter_name.replace('_', ' ').title()} |
  |---|---|
  | Fund A | Value 1 |
  | Fund B | Value 2 |
"""
        
        prompt = f"""You are a factual mutual fund information assistant. Your role is to answer factual queries only and provide accurate information.

IMPORTANT GUIDELINES:

1. ANSWER FACTUAL QUERIES ONLY:
   - Answer questions about factual information such as:
     * "Expense ratio of [fund]?"
     * "ELSS lock-in?"
     * "Minimum SIP?"
     * "Exit load?"
     * "Riskometer/benchmark?"
     * "How to download capital-gains statement?"
   - Provide clear, accurate answers based solely on the provided context.

2. CRITICAL: DISTINGUISH BETWEEN AUM AND FUND SIZE:
   - AUM (Assets Under Management) and Fund Size are DIFFERENT fields
   - AUM refers to "AUM (Assets Under Management)" in the context
   - Fund Size refers to "Fund Size" in the context
   - NEVER confuse or mix these two fields
   - When asked about AUM, use ONLY the "AUM (Assets Under Management)" value
   - When asked about Fund Size, use ONLY the "Fund Size" value
   - If the context shows both fields separately, respect that distinction

3. FORMATTING REQUIREMENTS:

   A. TEXT-ONLY ANSWERS:
   - For plain text answers, ensure all numeric values are clearly presented.
   - Format numbers with proper spacing and units (e.g., "1.5%", "₹500", "3 years").
   - Use clear, structured sentences with proper punctuation.
   - Break long paragraphs into shorter, readable sections.

   B. TABLE ANSWERS:
   - If your answer contains structured data (e.g., multiple funds with properties, comparisons), format it as a proper markdown table:
     * Use pipe-separated format: | Column1 | Column2 | Column3 |
     * Include header row with separators: |---|---|---|
     * Ensure all columns are aligned properly
     * Include all relevant data in the table
     * Example:
       | Fund Name | Expense Ratio | Minimum SIP |
       |---|---| ---|
       | Fund A | 1.5% | ₹500 |
       | Fund B | 1.2% | ₹1000 |
   - Tables should be well-structured with clear headers and consistent formatting.
   - When the user asks for a parameter (like AUM, expense ratio, NAV, etc.) without specifying a fund, ALWAYS return a table showing that parameter for ALL funds in the context.

   C. LISTS:
   - If your answer contains a list of items, format it as bullet points using markdown:
     * Use "- " for each item
     * Example: "- Item 1\n- Item 2\n- Item 3"
   - Ensure consistent formatting throughout the list.
{parameter_instruction}

4. CITATION REQUIREMENTS:

   IMPORTANT: DO NOT include URLs or citation links in your answer text. Citations will be handled separately by the system.
   - Simply provide your answer without any "Source:" or URL references.
   - The system will automatically add proper citations based on the sources used.
   - Focus on providing clear, factual answers based on the context.

   C. NO CITATIONS FOR REFUSALS:
   - DO NOT include any citation links when refusing opinion/advice questions or out-of-scope questions.
   - DO NOT include URLs or citations in refusal messages.

4. REFUSE OPINIONATED/PORTFOLIO/OUT-OF-SCOPE QUESTIONS:
   - If asked opinionated or portfolio questions (e.g., "Should I buy/sell?", "What should I invest in?", "Is this a good investment?"), politely decline WITHOUT including any citation link or irrelevant context.
   - If asked questions outside the scope of mutual fund information, politely decline WITHOUT citations.
   - Refusal message format: "I can only provide factual information about mutual funds and cannot give investment advice or recommendations. Please ask about specific facts like expense ratios, lock-in periods, or fund details."
   - Keep refusal messages concise and clear - do not include any URLs, citations, or additional context.
   - Do not provide opinions, recommendations, or investment advice.

6. ANSWER LENGTH REQUIREMENT:
   - CRITICAL: Keep your answer to a MAXIMUM of 3 sentences.
   - Be concise and direct - provide only the essential information requested.
   - If the answer requires more detail, prioritize the most important facts in the first 3 sentences.
   - For tables or lists, keep the introductory text to 3 sentences maximum.
   - DO NOT add any extra information that is not directly related to the question asked.

7. ANSWER QUALITY AND RELEVANCE:
   - Ensure all answers are clean, well-structured, and easy to read.
   - Use proper formatting (tables, lists, or structured text) based on the content type.
   - Format numeric values clearly in text answers (e.g., "1.5%", "₹500", "3 years").
   - Maintain consistency in formatting throughout your response.
   - CRITICAL: Only answer what is asked. Do not add unrelated information, general advice, or extra context that wasn't requested.
   - If the question is specific, provide only that specific information without adding background or additional details unless directly relevant.

Context:
{context}

Question: {question}

Provide a clear, factual answer based on the context. Use proper formatting (tables for structured data, lists for items, structured text for simple answers). DO NOT include any URLs or citation links in your answer - citations will be added automatically by the system.

CRITICAL: Your answer MUST be limited to a maximum of 3 sentences. Be concise and direct. 

IMPORTANT: When answering questions about NAV (Net Asset Value), expense ratios, fund sizes, or any specific fund data:
- Carefully check ALL retrieved context for the requested information
- If multiple funds are mentioned in the context, extract data for ALL of them
- For comparison questions, include data for all relevant funds found in the context
- If NAV or other data exists in the context, include it in your answer
- Only say "not provided" or "not available" if you have thoroughly checked the context and the data is truly missing

If the question asks for opinions, investment advice, or is out of scope, politely decline without any citation links or irrelevant context. If the answer is not in the context, say so clearly."""
        
        response = self.llm.invoke(prompt)
        answer = response.content if hasattr(response, 'content') else str(response)
        
        # Remove any URLs that the LLM might have included in the answer text
        # We handle citations separately, so URLs in the answer text should be removed
        import re
        url_pattern = r'\s*(?:Source\s*\d*:?\s*)?https?://[^\s\)\]\>\"\'\n]+'
        answer = re.sub(url_pattern, '', answer, flags=re.IGNORECASE)
        # Clean up any leftover "Source:" labels without URLs
        answer = re.sub(r'\s*Source\s*\d*:?\s*$', '', answer, flags=re.IGNORECASE | re.MULTILINE)
        answer = answer.strip()
        
        # Extract URLs from the answer text (in case LLM still included URLs despite instructions)
        answer_urls = extract_urls_from_text(answer)
        
        # Combine source URLs with URLs found in answer, ensuring all are normalized
        # Use a set to track seen URLs to avoid duplicates
        all_citation_urls = list(source_urls)  # Start with normalized source URLs
        seen_citation_urls = set(source_urls)
        for url in answer_urls:
            if url and url not in seen_citation_urls:
                all_citation_urls.append(url)
                seen_citation_urls.add(url)
        
        # Extract latest source date for "Last updated" line
        latest_date = None
        for doc in documents:
            # Check for last_scraped date
            last_scraped = doc.metadata.get("last_scraped", "")
            if last_scraped:
                # Try to parse and compare dates
                try:
                    from datetime import datetime
                    # Try common date formats
                    for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y", "%m/%d/%Y"]:
                        try:
                            parsed_date = datetime.strptime(str(last_scraped), fmt)
                            if latest_date is None or parsed_date > latest_date:
                                latest_date = parsed_date
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass
            
            # Also check file_mod_time as fallback
            file_mod_time = doc.metadata.get("file_mod_time")
            if file_mod_time:
                try:
                    from datetime import datetime
                    mod_date = datetime.fromtimestamp(file_mod_time)
                    if latest_date is None or mod_date > latest_date:
                        latest_date = mod_date
                except Exception:
                    pass
        
        # Format the date string
        last_updated_str = ""
        if latest_date:
            try:
                last_updated_str = latest_date.strftime("%Y-%m-%d")
            except Exception:
                last_updated_str = str(latest_date)
        
        # Prepare response
        result = {
            "answer": answer,
            "question": question,
            "retrieved_documents": len(documents),
            "citation_url": primary_citation,  # Primary citation URL for easy access
            "citation_urls": all_citation_urls,  # All citation URLs for proper traceback
            "last_updated": last_updated_str,  # Latest source date for transparency
            "sources": []
        }
        
        # Add source information with normalized URLs
        for i, doc in enumerate(documents):
            metadata = doc.metadata.copy()
            # Ensure source_url in metadata is normalized
            if "source_url" in metadata and metadata["source_url"]:
                normalized_meta_url = normalize_url(metadata["source_url"])
                if normalized_meta_url:
                    metadata["source_url"] = normalized_meta_url
            
            source_info = {
                "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                "metadata": metadata
            }
            if scores:
                source_info["similarity_score"] = scores[i]
            result["sources"].append(source_info)
        
        return result
    
    def clear_memory(self):
        """Clear the conversation memory."""
        self.conversation_history = []

