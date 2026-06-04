import json
import uuid
from typing import Any, Dict, List, Optional, Tuple

from infrastructure.database import db_manager
from infrastructure.rag import vector_store
from utils.chunker import small_big_chunker
from utils.document_parser import document_parser


class RagService:
    """Coordinates document ingestion and Small-to-Big retrieval."""

    def _row_to_big_chunk(self, row) -> Dict[str, Any]:
        metadata = {}
        if row["metadata"]:
            try:
                metadata = json.loads(row["metadata"])
            except json.JSONDecodeError:
                metadata = {}

        return {
            "big_chunk_id": row["big_chunk_id"],
            "doc_id": row["doc_id"],
            "text": row["text"],
            "token_count": row["token_count"],
            "metadata": metadata,
        }

    def ingest_file(self, file_path: str, original_filename: str, file_size: int, user_id: str = "anonymous") -> Dict[str, Any]:
        doc_id = str(uuid.uuid4())
        elements = document_parser.parse_document(file_path, original_filename, file_size)
        elements = [item for item in elements if item.get("text", "").strip()]
        if not elements:
            raise ValueError("No readable text was extracted from the uploaded document.")

        small_chunks, big_chunks = small_big_chunker.chunk_document(elements, doc_id)
        if not big_chunks or not small_chunks:
            raise ValueError("Document parsing succeeded, but no chunks were produced.")

        for index, big_chunk in enumerate(big_chunks):
            metadata = dict(big_chunk.get("metadata", {}))
            metadata.update(
                {
                    "source_file": original_filename,
                    "file_size": file_size,
                    "user_id": user_id,
                    "big_chunk_index": index,
                    "total_big_chunks": len(big_chunks),
                }
            )
            big_chunk["metadata"] = metadata

        for index, small_chunk in enumerate(small_chunks):
            metadata = dict(small_chunk.get("metadata", {}))
            metadata.update(
                {
                    "source_file": original_filename,
                    "file_size": file_size,
                    "user_id": user_id,
                    "chunk_index": index,
                    "total_chunks": len(small_chunks),
                }
            )
            small_chunk["metadata"] = metadata
            small_chunk["small_chunk_id"] = small_chunk.get("small_chunk_id") or str(uuid.uuid4())
            small_chunk["doc_id"] = doc_id

        db_manager.insert_big_chunks(
            [
                {
                    "big_chunk_id": chunk["big_chunk_id"],
                    "doc_id": chunk["doc_id"],
                    "text": chunk["text"],
                    "token_count": chunk.get("token_count", 0),
                    "metadata": json.dumps(chunk.get("metadata", {}), ensure_ascii=False),
                }
                for chunk in big_chunks
            ]
        )
        try:
            vector_store.add_small_chunks_batch(small_chunks, doc_id)
        except Exception:
            db_manager.delete_big_chunks_by_doc(doc_id)
            raise

        return {
            "doc_id": doc_id,
            "filename": original_filename,
            "file_size": file_size,
            "elements_count": len(elements),
            "big_chunks_count": len(big_chunks),
            "small_chunks_count": len(small_chunks),
            "big_chunks": big_chunks,
            "small_chunks": small_chunks,
        }

    def ingest_qa_documents(self, documents: List[Dict[str, Any]], user_id: str = "anonymous") -> Dict[str, Any]:
        doc_id = str(uuid.uuid4())
        text_parts = []
        for index, doc in enumerate(documents, 1):
            question = doc.get("question", "")
            answer = doc.get("answer", "")
            content = doc.get("text") or doc.get("content") or f"Q: {question}\nA: {answer}"
            if content.strip():
                text_parts.append(f"[{index}]\n{content.strip()}")

        if not text_parts:
            raise ValueError("No valid FAQ content was provided.")

        elements = [
            {
                "element_id": str(uuid.uuid4()),
                "element_type": "faq",
                "text": "\n\n".join(text_parts),
                "metadata": {
                    "source_file": "manual_faq",
                    "user_id": user_id,
                    "file_type": "faq",
                    "file_size": 0,
                },
            }
        ]
        small_chunks, big_chunks = small_big_chunker.chunk_document(elements, doc_id)
        db_manager.insert_big_chunks(
            [
                {
                    "big_chunk_id": chunk["big_chunk_id"],
                    "doc_id": chunk["doc_id"],
                    "text": chunk["text"],
                    "token_count": chunk.get("token_count", 0),
                    "metadata": json.dumps(chunk.get("metadata", {}), ensure_ascii=False),
                }
                for chunk in big_chunks
            ]
        )
        try:
            vector_store.add_small_chunks_batch(small_chunks, doc_id)
        except Exception:
            db_manager.delete_big_chunks_by_doc(doc_id)
            raise
        return {
            "doc_id": doc_id,
            "big_chunks_count": len(big_chunks),
            "small_chunks_count": len(small_chunks),
        }

    def retrieve_parent_context(
        self,
        query: str,
        top_k: Optional[int] = None,
        metadata_filter: Optional[Dict] = None,
        use_hybrid: bool = False,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        if use_hybrid:
            from domain.retrieval.hybrid_search import hybrid_search_engine
            small_chunks = hybrid_search_engine.search(
                query, metadata_filter=metadata_filter
            )
        else:
            small_chunks = vector_store.search(
                query, top_k=top_k, metadata_filter=metadata_filter
            )

        big_chunk_ids = []
        seen = set()
        for chunk in small_chunks:
            big_chunk_id = chunk.get("big_chunk_id")
            if big_chunk_id and big_chunk_id not in seen:
                seen.add(big_chunk_id)
                big_chunk_ids.append(big_chunk_id)

        rows = db_manager.get_big_chunks_by_ids(big_chunk_ids)
        big_chunks = [self._row_to_big_chunk(row) for row in rows]
        return big_chunks, small_chunks

    def delete_document(self, doc_id: str) -> bool:
        vector_deleted = vector_store.hard_delete_document(doc_id)
        db_manager.delete_big_chunks_by_doc(doc_id)
        return vector_deleted

    def clear_documents(self):
        vector_store.clear()
        db_manager.clear_big_chunks()


rag_service = RagService()

__all__ = ["RagService", "rag_service"]
