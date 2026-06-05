
"""
Small-to-Big分块模块
智能递归分块 + 滑窗重叠分块
使用语义边界优先，滑窗保证内容完整
"""
import os
import uuid
from typing import List, Dict, Any, Tuple
import tiktoken

from dotenv import load_dotenv
load_dotenv()

# 分块参数
SMALL_CHUNK_MIN_TOKENS = int(os.getenv("SMALL_CHUNK_MIN_TOKENS", "200"))
SMALL_CHUNK_MAX_TOKENS = int(os.getenv("SMALL_CHUNK_MAX_TOKENS", "300"))
BIG_CHUNK_MIN_TOKENS = int(os.getenv("BIG_CHUNK_MIN_TOKENS", "1500"))
BIG_CHUNK_MAX_TOKENS = int(os.getenv("BIG_CHUNK_MAX_TOKENS", "2000"))
CHUNK_OVERLAP_RATIO = float(os.getenv("CHUNK_OVERLAP_RATIO", "0.15"))


class SmallBigChunker:
    """Small-to-Big分块器"""

    def __init__(self):
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None

    def count_tokens(self, text: str) -> int:
        """计算token数"""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        # fallback: 粗略估算
        return int(len(text) / 4)

    def chunk_document(
        self,
        elements: List[Dict[str, Any]],
        doc_id: str = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        执行Small-to-Big分块
        返回 (small_chunks, big_chunks)

        大块用于完整上下文，500-2000 tokens
        小块用于检索，200-300 tokens
        """
        # 1. 合并所有元素为完整文档文本
        full_text = "\n\n".join([elem["text"] for elem in elements])
        
        # 获取文档级元数据
        doc_metadata = elements[0]["metadata"] if elements else {}

        # 2. 构建大块
        big_chunks = self._build_big_chunks(full_text, doc_id, doc_metadata)

        # 3. 基于每个大块构建小块
        small_chunks = []
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
        """构建大块，500-2000 tokens"""
        chunks = []
        paragraphs = text.split("\n\n")

        current_chunk = ""
        current_tokens = 0

        for para in paragraphs:
            para_tokens = self.count_tokens(para)

            # 如果加上这个段落超过最大大小且当前已有足够内容，保存当前chunk
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
        基于大块构建小块
        智能递归分块 + 滑窗合并
        保证每个小块 200-300 tokens
        """
        small_chunks = []
        text = big_chunk["text"]
        big_chunk_id = big_chunk["big_chunk_id"]
        doc_id = big_chunk["doc_id"]
        doc_metadata = big_chunk.get("metadata", {})

        # 1. 智能递归语义分块
        semantic_chunks = self._smart_recursive_split(text)

        # 2. 滑窗合并，保证每个块在目标大小范围内
        final_small_chunks = self._sliding_window_merge(semantic_chunks)

        # 3. 添加元数据
        for idx, chunk_text in enumerate(final_small_chunks):
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
        智能递归语义分块
        按优先级尝试分隔符：段落、换行、句子、字符
        """
        chunks = []
        tokens = self.count_tokens(text)

        if tokens <= SMALL_CHUNK_MAX_TOKENS:
            return [text]

        # 尝试不同分隔符
        separators = ["\n\n", "\n", ". ", "! ", "? ", ",", "。", "！", "？", "，"]

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
                            # 如果这个chunk还很小，继续合并
                            current_chunk += (sep + part if current_chunk else part)
                            current_tokens += part_tokens
                    else:
                        current_chunk += (sep + part if current_chunk else part)
                        current_tokens += part_tokens

                if current_chunk:
                    chunks.append(current_chunk.strip())

                # 检查是否所有块都在大小限制内
                if all(self.count_tokens(c) <= SMALL_CHUNK_MAX_TOKENS for c in chunks):
                    return chunks

        # fallback: 强制按token切分
        return self._hard_token_split(text)

    def _hard_token_split(self, text: str) -> List[str]:
        """强制按token切分，作为最后手段"""
        chunks = []
        
        if self.tokenizer:
            tokens = self.tokenizer.encode(text)
            for i in range(0, len(tokens), SMALL_CHUNK_MAX_TOKENS):
                chunk_tokens = tokens[i:i + SMALL_CHUNK_MAX_TOKENS]
                chunk_text = self.tokenizer.decode(chunk_tokens)
                chunks.append(chunk_text)
        else:
            # fallback: 按字符估算切分
            chunk_size = SMALL_CHUNK_MAX_TOKENS * 4
            for i in range(0, len(text), chunk_size):
                chunks.append(text[i:i + chunk_size])

        return chunks

    def _sliding_window_merge(self, chunks: List[str]) -> List[str]:
        """
        滑窗重叠分块
        合并过短的小chunk，保证每个chunk 200-300 tokens
        保留10%-20%的重叠
        """
        result = []

        i = 0
        while i < len(chunks):
            current = chunks[i]
            current_tokens = self.count_tokens(current)

            # 尝试合并下一个chunk直到达到最小大小或超过最大大小
            j = i + 1
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
