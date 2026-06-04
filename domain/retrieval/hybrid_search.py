
"""
娣峰悎妫€绱㈠紩鎿?鏀寔: 鏌ヨ閲嶅啓 鈫?鍏冩暟鎹繃婊?鈫?骞惰鍙屾绱?鍚戦噺+鍏抽敭璇? 鈫?RRF铻嶅悎 鈫?Rerank绮炬帓
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
    """娣峰悎妫€绱㈠紩鎿?""
    
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
        瀹屾暣娣峰悎妫€绱㈡祦绋?        
        娴佺▼: 鏌ヨ閲嶅啓 鈫?鍏冩暟鎹繃婊?鈫?骞惰鍙屾绱?鈫?RRF铻嶅悎 鈫?Rerank绮炬帓
        """
        # 1. 鏌ヨ閲嶅啓
        processed_query = query
        if enable_query_rewrite:
            processed_query = self._rewrite_query(query)
        
        # 2. 骞惰鍙岃矾妫€绱?        vector_results = self._vector_search(processed_query, metadata_filter)
        keyword_results = self._keyword_search(processed_query, metadata_filter)
        
        # 3. RRF缁撴灉铻嶅悎
        fused_results = self._rrf_fusion(vector_results, keyword_results)
        
        # 4. Rerank绮炬帓
        final_results = fused_results
        if enable_rerank and len(fused_results) > 0:
            final_results = self._rerank(processed_query, fused_results)
        
        # 纭繚鍙繑鍥濼op K
        return final_results[:RERANK_TOP_K]
    
    def _rewrite_query(self, query: str) -> str:
        """鏌ヨ閲嶅啓锛氬皢鍙ｈ鍖栬浆涓烘爣鍑嗘绱㈣鍙ワ紝琛ュ叏璇箟"""
        prompt = f"""浣犳槸涓€涓笓涓氱殑鏌ヨ浼樺寲鍔╂墜銆傝灏嗕互涓嬬敤鎴锋煡璇㈡敼鍐欎负鏇撮€傚悎鍦ㄧ煡璇嗗簱涓悳绱㈢殑鏍囧噯璇彞锛?
瑕佹眰锛?1. 濡傛灉鏌ヨ鍙ｈ鍖栵紝璇疯浆涓烘寮忕殑涔﹂潰璇?2. 濡傛灉鏌ヨ瀛樺湪姝т箟鎴栬涔変笉瀹屾暣锛岃鍚堢悊琛ュ叏
3. 淇濈暀鍘熷鏌ヨ鐨勬牳蹇冩剰鍥撅紝涓嶈鏀瑰彉鍘熸剰
4. 鍙繑鍥炴敼鍐欏悗鐨勬煡璇㈣鍙ワ紝涓嶈鏈変换浣曢澶栬В閲?
鍘熷鏌ヨ: {query}

鏀瑰啓鍚庣殑鏌ヨ:"""
        
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
        """鍚戦噺妫€绱紙浣跨敤ChromaDB鐨凥NSW绱㈠紩锛?""
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
        """鍏抽敭璇嶆绱紙浣跨敤BM25绠楁硶锛?""
        if not BM25_AVAILABLE:
            return []
            
        try:
            # 鍏堣幏鍙栨墍鏈夊皬鍧楃敤浜庢瀯寤築M25绱㈠紩
            all_chunks = self._get_all_active_chunks(metadata_filter)
            
            if not all_chunks:
                return []
            
            # 鏋勫缓BM25绱㈠紩
            corpus = [self._tokenize(chunk["text"]) for chunk in all_chunks]
            bm25 = BM25Okapi(corpus)
            
            # 鎼滅储
            tokenized_query = self._tokenize(query)
            scores = bm25.get_scores(tokenized_query)
            
            # 鎺掑簭骞跺彇Top K
            scored_results = list(zip(all_chunks, scores))
            scored_results.sort(key=lambda x: x[1], reverse=True)
            
            # 鏍煎紡鍖栫粨鏋?            results = []
            for chunk, score in scored_results[:KEYWORD_TOP_K]:
                result = chunk.copy()
                result["bm25_score"] = score
                results.append(result)
            
            return results
        
        except Exception as e:
            print(f"Keyword search failed: {e}")
            return []
    
    def _tokenize(self, text: str) -> List[str]:
        """绠€鍗曠殑鍒嗚瘝锛堜腑鏂囨寜瀛楃锛岃嫳鏂囨寜鍗曡瘝锛?""
        # 淇濈暀涓枃銆佽嫳鏂囥€佹暟瀛?        cleaned = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', text)
        # 涓枃姣忎釜瀛楃涓€涓猼oken锛岃嫳鏂囨瘡涓崟璇嶄竴涓猼oken
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
        """鑾峰彇鎵€鏈夋椿璺冪殑灏忓潡锛堢敤浜嶣M25绱㈠紩锛?""
        try:
            all_docs = self.vector_store.collection.get()
            chunks = []
            
            if not all_docs or 'ids' not in all_docs or len(all_docs['ids']) == 0:
                return []
            
            for i in range(len(all_docs['ids'])):
                metadata = all_docs['metadatas'][i] if 'metadatas' in all_docs else {}
                
                if metadata.get('status') == 'deleted':
                    continue
                
                # 搴旂敤鍏冩暟鎹繃婊?                if metadata_filter:
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
        RRF (Reciprocal Rank Fusion) 缁撴灉铻嶅悎
        鍏紡: score = sum( 1/(k + rank) )锛屽叾涓?k=60
        """
        k = 60
        scores = {}
        
        # 鍚戦噺妫€绱㈢粨鏋?        for rank, result in enumerate(vector_results, 1):
            chunk_id = result.get("small_chunk_id", result.get("chunk_id", str(rank)))
            if chunk_id not in scores:
                scores[chunk_id] = {"result": result, "score": 0}
            scores[chunk_id]["score"] += 1 / (k + rank)
        
        # 鍏抽敭璇嶆绱㈢粨鏋?        for rank, result in enumerate(keyword_results, 1):
            chunk_id = result.get("small_chunk_id", result.get("chunk_id", str(rank)))
            if chunk_id not in scores:
                scores[chunk_id] = {"result": result, "score": 0}
            scores[chunk_id]["score"] += 1 / (k + rank)
        
        # 鎺掑簭
        sorted_items = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
        return [item["result"] for item in sorted_items]
    
    def _rerank(
        self,
        query: str,
        candidates: List[Dict]
    ) -> List[Dict]:
        """
        Rerank绮炬帓锛堜娇鐢↙LM锛?        瀵瑰€欓€夌粨鏋滆繘琛岀浉鍏虫€ч噸鎺掑簭
        """
        if len(candidates) <= 1:
            return candidates
        
        # 鏋勫缓鍊欓€夋枃鏈?        candidates_text = []
        for i, candidate in enumerate(candidates):
            text = candidate.get('text', '')
            candidates_text.append(f"[{i+1}] {text[:200]}..." if len(text) > 200 else f"[{i+1}] {text}")
        
        prompt = f"""浣犳槸涓€涓笓涓氱殑鐩稿叧鎬ц瘎浼板姪鎵嬨€傝鏍规嵁浠ヤ笅鏌ヨ锛屽鍊欓€夋枃鏈繘琛岀浉鍏虫€ц瘎鍒嗭紙0-100锛夛細

鏌ヨ: {query}

鍊欓€夋枃鏈?
{chr(10).join(candidates_text)}

瑕佹眰:
1. 鎸夌浉鍏虫€т粠楂樺埌浣庢帓搴?2. 鍙繑鍥炴帓搴忓悗鐨勭储寮曪紝鐢ㄩ€楀彿鍒嗛殧锛屼緥濡? 3,1,2
3. 涓嶈鏈変换浣曢澶栬В閲?
鎺掑簭缁撴灉:"""
        
        try:
            response = self.chat_service.chat_completion([{"role": "user", "content": prompt}])
            # 瑙ｆ瀽鎺掑簭缁撴灉
            indices = [int(x.strip()) - 1 for x in response.split(',') if x.strip().isdigit()]
            
            # 閲嶆帓搴?            reranked = []
            seen = set()
            for idx in indices:
                if 0 <= idx < len(candidates) and idx not in seen:
                    reranked.append(candidates[idx])
                    seen.add(idx)
            
            # 娣诲姞鏈閫変腑鐨?            for i in range(len(candidates)):
                if i not in seen:
                    reranked.append(candidates[i])
            
            return reranked
        
        except Exception as e:
            print(f"Rerank failed: {e}")
            return candidates


# 鍒涘缓鍗曚緥
hybrid_search_engine = HybridSearchEngine()

__all__ = ["HybridSearchEngine", "hybrid_search_engine"]

