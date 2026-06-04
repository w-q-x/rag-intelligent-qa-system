import json
import os
import sys
import types
import uuid
from typing import Any, Dict, List, Optional

import numpy as np

if not hasattr(np, "float_"):
    np.float_ = np.float64
if not hasattr(np, "int_"):
    np.int_ = np.int64
if not hasattr(np, "uint"):
    np.uint = np.uint64

# Chroma 0.4.x eagerly builds a default ONNX embedding function while importing.
# This project always supplies DashScope embeddings, so avoid loading the local
# onnxruntime binary when it is incompatible with the installed NumPy version.
if "onnxruntime" not in sys.modules:
    onnxruntime_stub = types.ModuleType("onnxruntime")
    onnxruntime_stub.get_available_providers = lambda: []
    sys.modules["onnxruntime"] = onnxruntime_stub

import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from .embedding import EmbeddingService

load_dotenv()


DEFAULT_COLLECTION_NAME = "documents"
VECTOR_DB_PATH = os.getenv("RAG_DB_PATH", "data/vector_db")
os.makedirs(VECTOR_DB_PATH, exist_ok=True)

HNSW_SPACE = os.getenv("HNSW_SPACE", "cosine")
HNSW_M = int(os.getenv("HNSW_M", "16"))
HNSW_CONSTRUCTION_EF = int(os.getenv("HNSW_EF_CONSTRUCTION", os.getenv("HNSW_CONSTRUCTION_EF", "200")))
HNSW_SEARCH_EF = int(os.getenv("HNSW_EF_SEARCH", os.getenv("HNSW_SEARCH_EF", "50")))


class VectorStore:
    """Chroma vector store for Small-to-Big child chunks."""

    def __init__(self, collection_name=DEFAULT_COLLECTION_NAME):
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(
            path=VECTOR_DB_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=None,
            metadata={
                "hnsw:space": HNSW_SPACE,
                "hnsw:M": HNSW_M,
                "hnsw:construction_ef": HNSW_CONSTRUCTION_EF,
                "hnsw:search_ef": HNSW_SEARCH_EF,
            },
        )
        self.embedding_service = EmbeddingService()

    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            else:
                sanitized[key] = json.dumps(value, ensure_ascii=False)
        return sanitized

    def _active_doc_where(self, doc_id: str) -> Dict[str, Any]:
        return {"$and": [{"doc_id": doc_id}, {"status": "active"}]}

    def _force_flush(self):
        """Force ChromaDB to synchronously process the embeddings_queue.

        ChromaDB PersistentClient uses a background daemon thread to consume
        the embeddings_queue.  On some Windows environments this thread never
        starts or dies silently, leaving vectors stuck in the queue.  We call
        the internal consumer here after every batch so data is immediately
        searchable.
        """
        try:
            sysdb = self.client._server._sysdb
            sysdb._process_queue()
        except Exception:
            pass

    def _search_where(self, metadata_filter: Optional[Dict] = None) -> Dict[str, Any]:
        clauses = [{"status": "active"}]
        if metadata_filter:
            clauses.extend([{key: value} for key, value in metadata_filter.items()])
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def add_small_chunks_batch(self, small_chunks: List[Dict[str, Any]], doc_id: str) -> bool:
        if not small_chunks:
            return True

        existing_ids = set(self._get_existing_chunk_ids(doc_id))
        chunk_ids = []
        texts = []
        metadatas = []

        for chunk in small_chunks:
            text = chunk.get("text", "")
            if not text.strip():
                continue

            chunk_id = chunk.get("small_chunk_id") or str(uuid.uuid4())
            if chunk_id in existing_ids:
                continue

            metadata = {
                "small_chunk_id": chunk_id,
                "big_chunk_id": chunk.get("big_chunk_id", ""),
                "doc_id": doc_id,
                "token_count": chunk.get("token_count", 0),
                "status": "active",
                **chunk.get("metadata", {}),
            }

            chunk_ids.append(chunk_id)
            texts.append(text)
            metadatas.append(self._sanitize_metadata(metadata))

        if not chunk_ids:
            return True

        # Process in sub-batches to avoid embedding API timeout
        sub_batch_size = 20
        for sub_start in range(0, len(texts), sub_batch_size):
            sub_texts = texts[sub_start:sub_start + sub_batch_size]
            sub_ids = chunk_ids[sub_start:sub_start + sub_batch_size]
            sub_metadatas = metadatas[sub_start:sub_start + sub_batch_size]

            embeddings = self.embedding_service.embed(sub_texts)
            self.collection.add(
                ids=sub_ids,
                embeddings=embeddings,
                documents=sub_texts,
                metadatas=sub_metadatas,
            )
            self._force_flush()
        return True

    def _get_existing_chunk_ids(self, doc_id: str) -> List[str]:
        try:
            result = self.collection.get(where=self._active_doc_where(doc_id))
            return list(result.get("ids", [])) if result else []
        except Exception:
            return []

    def add_chunks(self, chunks: List[Dict[str, Any]], doc_id: Optional[str] = None) -> bool:
        if not chunks:
            return True

        if not doc_id:
            doc_id = chunks[0].get("doc_id") or chunks[0].get("metadata", {}).get("doc_id") or str(uuid.uuid4())

        small_chunks = []
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            text = chunk.get("text") or chunk.get("content") or ""
            small_chunks.append(
                {
                    "small_chunk_id": chunk.get("small_chunk_id") or chunk.get("chunk_id") or str(uuid.uuid4()),
                    "big_chunk_id": chunk.get("big_chunk_id") or metadata.get("big_chunk_id") or str(uuid.uuid4()),
                    "doc_id": doc_id,
                    "text": text,
                    "token_count": chunk.get("token_count", len(text)),
                    "metadata": metadata,
                }
            )

        return self.add_small_chunks_batch(small_chunks, doc_id)

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        metadata_filter: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        if top_k is None:
            top_k = int(os.getenv("RETRIEVER_TOP_K", "5"))

        query_embedding = self.embedding_service.embed_single(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=self._search_where(metadata_filter),
        )

        formatted_results = []
        ids = results.get("ids", [[]])[0] if results else []
        docs = results.get("documents", [[]])[0] if results else []
        metadatas = results.get("metadatas", [[]])[0] if results else []
        distances = results.get("distances", [[]])[0] if results else []

        for index, chunk_id in enumerate(ids):
            metadata = metadatas[index] if index < len(metadatas) and metadatas[index] else {}
            text = docs[index] if index < len(docs) else ""
            distance = distances[index] if index < len(distances) else 0.0
            source = {
                "type": "file",
                "file": metadata.get("source_file", "unknown"),
                "chunk_id": chunk_id,
                "doc_id": metadata.get("doc_id", ""),
                "chunk_index": metadata.get("chunk_index", 0),
                "total_chunks": metadata.get("total_chunks", 0),
            }
            if "page_number" in metadata:
                source["page_number"] = metadata["page_number"]

            formatted_results.append(
                {
                    "small_chunk_id": chunk_id,
                    "big_chunk_id": metadata.get("big_chunk_id", ""),
                    "doc_id": metadata.get("doc_id", ""),
                    "text": text,
                    "distance": distance,
                    "metadata": metadata,
                    "source": source,
                }
            )

        return formatted_results

    def list_documents(self) -> List[Dict[str, Any]]:
        docs = self.collection.get()
        documents = {}
        ids = docs.get("ids", []) if docs else []
        metadatas = docs.get("metadatas", []) if docs else []

        for index, metadata in enumerate(metadatas):
            if metadata.get("status") == "deleted":
                continue
            doc_id = metadata.get("doc_id", "")
            if not doc_id:
                continue
            if doc_id not in documents:
                documents[doc_id] = {
                    "doc_id": doc_id,
                    "filename": metadata.get("source_file", metadata.get("file", "unknown")),
                    "file_type": metadata.get("file_type", ""),
                    "file_size": metadata.get("file_size", 0),
                    "chunk_count": 0,
                }
            documents[doc_id]["chunk_count"] += 1

        return list(documents.values())

    def get_all_chunks_by_doc_id(self, doc_id: str) -> List[str]:
        docs = self.collection.get()
        chunk_ids = []
        ids = docs.get("ids", []) if docs else []
        metadatas = docs.get("metadatas", []) if docs else []
        for index, metadata in enumerate(metadatas):
            if metadata.get("doc_id") == doc_id:
                chunk_ids.append(ids[index])
        return chunk_ids

    def soft_delete_document(self, doc_id: str) -> bool:
        chunk_ids = self.get_all_chunks_by_doc_id(doc_id)
        if not chunk_ids:
            return False

        for chunk_id in chunk_ids:
            result = self.collection.get(ids=[chunk_id])
            metadatas = result.get("metadatas", []) if result else []
            if not metadatas:
                continue
            metadata = metadatas[0] or {}
            metadata["status"] = "deleted"
            self.collection.update(ids=[chunk_id], metadatas=[metadata])
        return True

    def delete_vectors_by_ids(self, chunk_ids: List[str]) -> bool:
        if not chunk_ids:
            return True
        self.collection.delete(ids=chunk_ids)
        return True

    def hard_delete_document(self, doc_id: str) -> bool:
        chunk_ids = self.get_all_chunks_by_doc_id(doc_id)
        if not chunk_ids:
            return False
        return self.delete_vectors_by_ids(chunk_ids)

    def get_document_status(self, doc_id: str) -> Dict[str, Any]:
        docs = self.collection.get()
        metadatas = docs.get("metadatas", []) if docs else []
        for metadata in metadatas:
            if metadata.get("doc_id") == doc_id:
                return {
                    "doc_id": doc_id,
                    "status": metadata.get("status", "active"),
                    "filename": metadata.get("source_file", "unknown"),
                }
        return {"doc_id": doc_id, "status": "not_found", "filename": None}

    def clear(self):
        docs = self.collection.get()
        ids = docs.get("ids", []) if docs else []
        if ids:
            self.collection.delete(ids=ids)

    def count(self) -> int:
        return self.collection.count()


vector_store = VectorStore()

__all__ = ["VectorStore", "vector_store"]
