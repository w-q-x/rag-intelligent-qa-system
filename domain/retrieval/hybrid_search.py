
"""
Hybrid search engine combining vector search and keyword search, 
with query rewrite and Rerank features
"""
import os
import re
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    print("Warning: rank-bm25 not installed, keyword search disabled")

from infrastructure.rag.vector_store import vector_store
from llm import chat_service

load_dotenv()

VECTOR_TOP_K = int(os.getenv("VECTOR_SEARCH_TOP_K", "20"))
KEYWORD_TOP_K = int(os.getenv("KEYWORD_SEARCH_TOP_K", "20"))
RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", "5"))


class HybridSearchEngine:
    """Hybrid search engine combining vector search and keyword search"""
    
    def __init__(self):
        self.chat_service = chat_service
        self.vector_store = vector_store
        self.bm25_index = None
        self._cached_corpus = []
    
    def search(
        self,
        query: str,
        metadata_filter: Optional[Dict] = None,
        enable_query_rewrite: bool = True,
        enable_rerank: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search, combining vector search and keyword search,
        with query rewrite and Rerank features
        """
        # 1. Query rewrite
        processed_query = query
        if enable_query_rewrite:
            processed_query = self._rewrite_query(query)
        
        # 2. Perform both searches
        vector_results = self._vector_search(processed_query, metadata_filter)
        keyword_results = self._keyword_search(processed_query, metadata_filter)
        
        # 3. RRF fusion
        fused_results = self._rrf_fusion(vector_results, keyword_results)
        
        # 4. Rerank
        final_results = fused_results
        if enable_rerank and len(fused_results) > 0:
            final_results = self._rerank(processed_query, fused_results)
        
        # Return top K
        return final_results[:RERANK_TOP_K]
    
    def _rewrite_query(self, query: str) -> str:
        """Rewrite the query to improve search results"""
        prompt = f"""You are an expert at rewriting user questions to improve knowledge base retrieval.

Original question: {query}

Please rewrite the question to be more clear, specific, and include relevant keywords that might appear in the knowledge base. Keep it concise, no more than 2 sentences.

Rewritten question:"""
        
        try:
            response = self.chat_service.chat_completion([{"role": "user", "content": prompt}])
            rewritten = response.strip()
            print(f"Query rewritten: {query} -> {rewritten}")
            return rewritten
        except Exception as e:
            print(f"Query rewrite failed: {e}")
            return query
    
    def _vector_search(
        self,
        query: str,
        metadata_filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Perform vector search using ChromaDB with HNSW index"""
        return self.vector_store.search(
            query,
            top_k=VECTOR_TOP_K,
            metadata_filter=metadata_filter
        )
    
    def _keyword_search(
        self,
        query: str,
        metadata_filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Perform keyword search using BM25 algorithm"""
        if not BM25_AVAILABLE:
            return []
            
        try:
            # Get all active chunks to build BM25 index
            all_chunks = self._get_all_active_chunks(metadata_filter)
            
            if not all_chunks:
                return []
            
            # Build BM25 index
            corpus = [self._tokenize(chunk["text"]) for chunk in all_chunks]
            bm25 = BM25Okapi(corpus)
            
            # Search
            tokenized_query = self._tokenize(query)
            scores = bm25.get_scores(tokenized_query)
            
            # Sort and get top K
            scored_results = list(zip(all_chunks, scores))
            scored_results.sort(key=lambda x: x[1], reverse=True)
            
            # Format results
            results = []
            for chunk, score in scored_results[:KEYWORD_TOP_K]:
                result = chunk.copy()
                result["bm25_score"] = score
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"Keyword search failed: {e}")
            return []
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization: remove special characters and split"""
        # Keep only Chinese characters, English letters, and digits
        cleaned = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', text)
        # Split into tokens: Chinese characters are individual tokens, English words are kept together
        tokens = []
        for part in cleaned.split():
            if any('\u4e00' <= c <= '\u9fff' for c in part):
                tokens.extend(list(part))
            else:
                tokens.append(part.lower())
        return tokens
    
    def _get_all_active_chunks(
        self,
        metadata_filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Get all active chunks from vector store for BM25 indexing"""
        try:
            all_docs = self.vector_store.collection.get()
            chunks = []
            
            if not all_docs or 'ids' not in all_docs or len(all_docs['ids']) == 0:
                return []
            
            for i in range(len(all_docs['ids'])):
                metadata = all_docs['metadatas'][i] if 'metadatas' in all_docs else {}
                
                if metadata.get('status') == 'deleted':
                    continue
                
                # Apply metadata filter
                if metadata_filter:
                    match = True
                    for key, value in metadata_filter.items():
                        if metadata.get(key) != value:
                            match = False
                            break
                    if not match:
                        continue
                
                text = all_docs['documents'][i] if 'documents' in all_docs else ""
                
                chunks.append({
                    "small_chunk_id": metadata.get('small_chunk_id', all_docs['ids'][i]),
                    "big_chunk_id": metadata.get('big_chunk_id'),
                    "doc_id": metadata.get('doc_id'),
                    "text": text,
                    "metadata": metadata
                })
            
            return chunks
        except Exception as e:
            print(f"Get chunks failed: {e}")
            return []
    
    def _rrf_fusion(
        self,
        vector_results: List[Dict],
        keyword_results: List[Dict]
    ) -> List[Dict]:
        """
        RRF (Reciprocal Rank Fusion) to combine search results
        Formula: score = sum( 1/(k + rank) ), where k=60
        """
        k = 60
        scores = {}
        
        # Process vector search results
        for rank, result in enumerate(vector_results, 1):
            chunk_id = result.get("small_chunk_id", result.get("chunk_id", str(rank)))
            if chunk_id not in scores:
                scores[chunk_id] = {"result": result, "score": 0}
            scores[chunk_id]["score"] += 1 / (k + rank)
        
        # Process keyword search results
        for rank, result in enumerate(keyword_results, 1):
            chunk_id = result.get("small_chunk_id", result.get("chunk_id", str(rank)))
            if chunk_id not in scores:
                scores[chunk_id] = {"result": result, "score": 0}
            scores[chunk_id]["score"] += 1 / (k + rank)
        
        # Sort
        sorted_items = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
        return [item["result"] for item in sorted_items]
    
    def _rerank(
        self,
        query: str,
        candidates: List[Dict]
    ) -> List[Dict]:
        """
        Rerank using LLM - asks LLM to reorder candidates by relevance
        """
        if len(candidates) <= 1:
            return candidates
        
        # Prepare candidates text
        candidates_text = []
        for i, candidate in enumerate(candidates):
            text = candidate.get('text', '')
            candidates_text.append(f"[{i + 1}] {text[:200]}..." if len(text) > 200 else f"[{i + 1}] {text}")
        
        prompt = f"""You are an expert at ranking knowledge base results by relevance to the user query.

User query: {query}

Candidate results:
{chr(10).join(candidates_text)}

Please reorder these candidates by relevance, putting the most relevant first. Return ONLY the indices separated by commas (e.g., 3,1,2). Do NOT include any other text.

Reordered indices:"""
        
        try:
            response = self.chat_service.chat_completion([{"role": "user", "content": prompt}])
            # Parse the indices
            indices = [int(x.strip()) - 1 for x in response.split(',') if x.strip().isdigit()]
            
            # Reorder
            reranked = []
            seen = set()
            for idx in indices:
                if 0 <= idx < len(candidates) and idx not in seen:
                    reranked.append(candidates[idx])
                    seen.add(idx)
            
            # Add any missing candidates at the end
            for i in range(len(candidates)):
                if i not in seen:
                    reranked.append(candidates[i])
            
            return reranked
            
        except Exception as e:
            print(f"Rerank failed: {e}")
            return candidates


# Initialize hybrid search engine
hybrid_search_engine = HybridSearchEngine()

__all__ = ["HybridSearchEngine", "hybrid_search_engine"]

