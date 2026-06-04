
"""
Small-to-Big鍒嗗潡妯″潡
鏅鸿兘閫掑綊鍒嗗潡 + 婊戠獥閲嶅彔鍒嗗潡
瀹炵幇鍙屽眰鍒嗗潡绛栫暐锛氬皬鍧楃敤浜庢绱紝澶у潡鐢ㄤ簬鐢熸垚
"""
import os
import uuid
from typing import List, Dict, Any, Tuple
import tiktoken

from dotenv import load_dotenv
load_dotenv()

# 鍒嗗潡閰嶇疆
SMALL_CHUNK_MIN_TOKENS = int(os.getenv("SMALL_CHUNK_MIN_TOKENS", "200"))
SMALL_CHUNK_MAX_TOKENS = int(os.getenv("SMALL_CHUNK_MAX_TOKENS", "300"))
BIG_CHUNK_MIN_TOKENS = int(os.getenv("BIG_CHUNK_MIN_TOKENS", "1500"))
BIG_CHUNK_MAX_TOKENS = int(os.getenv("BIG_CHUNK_MAX_TOKENS", "2000"))
CHUNK_OVERLAP_RATIO = float(os.getenv("CHUNK_OVERLAP_RATIO", "0.15"))


class SmallBigChunker:
    """Small-to-Big鍙屽眰鍒嗗潡鍣?""

    def __init__(self):
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None

    def count_tokens(self, text: str) -> int:
        """璁＄畻Token鏁?""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        # 绠€鍗曞洖閫€锛氭寜瀛楃鏁颁及绠?        return int(len(text) / 4)

    def chunk_document(
        self,
        elements: List[Dict[str, Any]],
        doc_id: str = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        鎵цSmall-to-Big鍒嗗潡
        杩斿洖: (small_chunks, big_chunks)
        
        澶у潡锛?500-2000 tokens锛屼綔涓虹敓鎴愪笂涓嬫枃鍗曞厓
        灏忓潡锛?00-300 tokens锛屼綔涓烘绱㈠崟鍏?        """
        # 1. 鍏堝悎骞舵墍鏈夊厓绱犱负瀹屾暣鏂囨湰锛屽苟淇濈暀鏂囨。绾у厓鏁版嵁
        full_text = "\n\n".join([elem["text"] for elem in elements])
        
        # 鑾峰彇鏂囨。绾у厓鏁版嵁锛堜粠绗竴涓厓绱犺幏鍙栵級
        doc_metadata = elements[0]["metadata"] if elements else {}

        # 2. 鐢熸垚澶у潡
        big_chunks = self._build_big_chunks(full_text, doc_id, doc_metadata)

        # 3. 瀵规瘡涓ぇ鍧楃敓鎴愬皬鍧?        small_chunks = []
        for big_chunk in big_chunks:
            big_small_chunks = self._build_small_chunks(big_chunk)
            small_chunks.extend(big_small_chunks)

        return small_chunks, big_chunks

    def _build_big_chunks(
        self,
        text: str,
        doc_id: str,
        doc_metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """鏋勫缓澶у潡锛?500-2000 tokens锛?""
        chunks = []
        paragraphs = text.split("\n\n")

        current_chunk = ""
        current_tokens = 0

        for para in paragraphs:
            para_tokens = self.count_tokens(para)

            # 濡傛灉娣诲姞褰撳墠娈佃惤浼氳秴杩囦笂闄愶紝鍏堜繚瀛樺綋鍓峜hunk
            if current_tokens + para_tokens > BIG_CHUNK_MAX_TOKENS and current_tokens >= BIG_CHUNK_MIN_TOKENS:
                big_chunk_id = str(uuid.uuid4())
                chunks.append({
                    "big_chunk_id": big_chunk_id,
                    "doc_id": doc_id,
                    "text": current_chunk.strip(),
                    "token_count": current_tokens,
                    "metadata": doc_metadata,
                    "created_at": doc_metadata.get("parse_date", "")
                })
                current_chunk = para
                current_tokens = para_tokens
            else:
                current_chunk += ("\n\n" + para if current_chunk else para)
                current_tokens += para_tokens

        if current_chunk:
            big_chunk_id = str(uuid.uuid4())
            chunks.append({
                "big_chunk_id": big_chunk_id,
                "doc_id": doc_id,
                "text": current_chunk.strip(),
                "token_count": current_tokens,
                "metadata": doc_metadata,
                "created_at": doc_metadata.get("parse_date", "")
            })

        return chunks

    def _build_small_chunks(self, big_chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        瀵瑰崟涓ぇ鍧楄繘琛屽皬鍧楀垏鍒?        浣跨敤鏅鸿兘閫掑綊鍒嗗潡 + 婊戠獥閲嶅彔
        姣忎釜灏忓潡 200-300 tokens
        """
        small_chunks = []
        text = big_chunk["text"]
        big_chunk_id = big_chunk["big_chunk_id"]
        doc_id = big_chunk["doc_id"]
        doc_metadata = big_chunk.get("metadata", {})

        # 1. 鍏堟寜璇箟杈圭晫閫掑綊鍒嗗潡
        semantic_chunks = self._smart_recursive_split(text)

        # 2. 鍐嶅簲鐢ㄦ粦绐楅噸鍙犱繚璇佷笂涓嬫枃杩炵画鎬?        final_small_chunks = self._sliding_window_merge(semantic_chunks)

        # 3. 濉厖鍏冩暟鎹?        for idx, chunk_text in enumerate(final_small_chunks):
            small_chunks.append({
                "small_chunk_id": str(uuid.uuid4()),
                "big_chunk_id": big_chunk_id,
                "doc_id": doc_id,
                "text": chunk_text,
                "token_count": self.count_tokens(chunk_text),
                "metadata": {
                    "chunk_index": idx,
                    "chunk_type": "paragraph",
                    "access_level": doc_metadata.get("access_level", "public"),
                    "scope": doc_metadata.get("scope", "general"),
                    "source_file": doc_metadata.get("source_file", ""),
                    "file_type": doc_metadata.get("file_type", ""),
                    "page_number": doc_metadata.get("page_number", 0)
                },
                "created_at": doc_metadata.get("parse_date", "")
            })

        return small_chunks

    def _smart_recursive_split(self, text: str) -> List[str]:
        """
        鏅鸿兘閫掑綊鍒嗗潡锛氭寜璇箟杈圭晫浼樺厛鍒囧垎
        鍒囧垎椤哄簭锛氬弻鎹㈣ 鈫?鍗曟崲琛?鈫?鍙ュ彿 鈫?閫楀彿
        """
        chunks = []
        tokens = self.count_tokens(text)

        if tokens <= SMALL_CHUNK_MAX_TOKENS:
            return [text]

        # 灏濊瘯鎸変紭鍏堢骇鍒嗗壊
        separators = ["\n\n", "\n", "銆?, "锛?, "锛?, ".", "!", "?", "锛?, ","]

        for sep in separators:
            parts = text.split(sep)
            if len(parts) > 1:
                current_chunk = ""
                current_tokens = 0

                for part in parts:
                    part_with_sep = part + sep
                    part_tokens = self.count_tokens(part_with_sep)

                    if current_tokens + part_tokens > SMALL_CHUNK_MAX_TOKENS:
                        if current_tokens >= SMALL_CHUNK_MIN_TOKENS:
                            chunks.append(current_chunk.strip())
                            current_chunk = part
                            current_tokens = self.count_tokens(part)
                        else:
                            # 濡傛灉褰撳墠chunk澶皬锛岀洿鎺ユ坊鍔?                            current_chunk += (sep + part if current_chunk else part)
                            current_tokens += part_tokens
                    else:
                        current_chunk += (sep + part if current_chunk else part)
                        current_tokens += part_tokens

                if current_chunk:
                    chunks.append(current_chunk.strip())

                # 楠岃瘉鍒囧垎缁撴灉
                if all(self.count_tokens(c) <= SMALL_CHUNK_MAX_TOKENS for c in chunks):
                    return chunks

        # 鍏滃簳锛氱洿鎺ユ寜token鏁伴噺鍒囧垎
        return self._hard_token_split(text)

    def _hard_token_split(self, text: str) -> List[str]:
        """寮哄埗鎸塼oken鏁伴噺鍒囧垎锛堝厹搴曟柟妗堬級"""
        chunks = []
        
        if self.tokenizer:
            tokens = self.tokenizer.encode(text)
            for i in range(0, len(tokens), SMALL_CHUNK_MAX_TOKENS):
                chunk_tokens = tokens[i:i + SMALL_CHUNK_MAX_TOKENS]
                chunk_text = self.tokenizer.decode(chunk_tokens)
                chunks.append(chunk_text)
        else:
            # 绠€鍗曞洖閫€锛氭寜瀛楃鏁板垏鍒?            chunk_size = SMALL_CHUNK_MAX_TOKENS * 4
            for i in range(0, len(text), chunk_size):
                chunks.append(text[i:i + chunk_size])

        return chunks

    def _sliding_window_merge(self, chunks: List[str]) -> List[str]:
        """
        婊戠獥閲嶅彔鍒嗗潡
        鍚堝苟杩囧皬鐨刢hunk锛屼繚璇佹瘡涓猚hunk 200-300 tokens
        娣诲姞10%-20%閲嶅彔
        """
        result = []

        i = 0
        while i < len(chunks):
            current = chunks[i]
            current_tokens = self.count_tokens(current)

            # 鍚戝悗鍚堝苟锛岀洿鍒拌揪鍒扮洰鏍囧ぇ灏?            j = i + 1
            while j < len(chunks) and current_tokens < SMALL_CHUNK_MIN_TOKENS:
                merged = current + "\n\n" + chunks[j]
                merged_tokens = self.count_tokens(merged)
                if merged_tokens <= SMALL_CHUNK_MAX_TOKENS:
                    current = merged
                    current_tokens = merged_tokens
                    j += 1
                else:
                    break

            result.append(current)
            i = j

        return result


small_big_chunker = SmallBigChunker()

__all__ = ["SmallBigChunker", "small_big_chunker"]

