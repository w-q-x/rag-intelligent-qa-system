import os
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from infrastructure.rag import vector_store
from llm import chat_service
from services.rag_service import rag_service
from utils.auth import get_current_user

router = APIRouter(tags=["RAG"])


class SearchRequest(BaseModel):
    question: str
    enable_rewrite: Optional[bool] = True


class SourceInfo(BaseModel):
    type: str
    file: str
    chunk_id: Optional[str] = None
    doc_id: Optional[str] = None
    chunk_index: Optional[int] = None
    total_chunks: Optional[int] = None
    page_number: Optional[int] = None


class SearchResult(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    text: str
    distance: float
    source: Optional[SourceInfo] = None
    small_chunk_id: Optional[str] = None
    big_chunk_id: Optional[str] = None
    doc_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    original_question: str
    rewritten_query: Optional[str]
    results: List[SearchResult]


class SearchResponseWithSummary(SearchResponse):
    summary: Optional[str] = None
    sources: Optional[List[SourceInfo]] = None


class AddDocumentsRequest(BaseModel):
    documents: List[dict]


class AddDocumentsResponse(BaseModel):
    success: bool
    message: str
    doc_id: Optional[str] = None


class UploadResponse(BaseModel):
    success: bool
    message: str
    doc_id: str
    filename: str
    chunks_count: int
    big_chunks_count: int


def _to_search_result(item: Dict[str, Any]) -> SearchResult:
    text = item.get("text", "")
    source = item.get("source")
    return SearchResult(
        question=item.get("question") or text[:120],
        answer=item.get("answer") or text,
        text=text,
        distance=item.get("distance", 0.0),
        source=SourceInfo(**source) if source else None,
        small_chunk_id=item.get("small_chunk_id"),
        big_chunk_id=item.get("big_chunk_id"),
        doc_id=item.get("doc_id"),
        metadata=item.get("metadata", {}),
    )


def _dedupe_sources(small_chunks: List[Dict[str, Any]]) -> List[SourceInfo]:
    sources = []
    seen = set()
    for chunk in small_chunks:
        source = chunk.get("source")
        if not source:
            continue
        key = (source.get("file"), source.get("doc_id"), source.get("chunk_id"))
        if key in seen:
            continue
        seen.add(key)
        sources.append(SourceInfo(**source))
    return sources


def _build_parent_context(big_chunks: List[Dict[str, Any]], small_chunks: List[Dict[str, Any]]) -> str:
    if big_chunks:
        parts = []
        for index, chunk in enumerate(big_chunks, 1):
            metadata = chunk.get("metadata", {})
            source_file = metadata.get("source_file", "unknown")
            page_number = metadata.get("page_number")
            page_text = f"\nPage: {page_number}" if page_number else ""
            parts.append(
                f"[Reference {index}]\nSource: {source_file}{page_text}\n{chunk.get('text', '')}"
            )
        return "\n\n".join(parts)

    return "\n\n".join(
        f"[Matched child chunk {index}]\nSource: {chunk.get('source', {}).get('file', 'unknown')}\n{chunk.get('text', '')}"
        for index, chunk in enumerate(small_chunks, 1)
    )


@router.get("/search")
async def search_get(q: str = Query(..., description="Search query")):
    try:
        results = vector_store.search(q)
        return SearchResponse(
            original_question=q,
            rewritten_query=None,
            results=[_to_search_result(item) for item in results],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    try:
        results = vector_store.search(request.question)
        return SearchResponse(
            original_question=request.question,
            rewritten_query=None,
            results=[_to_search_result(item) for item in results],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/summary", response_model=SearchResponseWithSummary)
async def search_with_summary_get(q: str = Query(..., description="Search query")):
    return await _search_with_summary(q)


@router.post("/search/summary", response_model=SearchResponseWithSummary)
async def search_with_summary(request: SearchRequest):
    return await _search_with_summary(request.question)


async def _search_with_summary(question: str) -> SearchResponseWithSummary:
    try:
        big_chunks, small_chunks = rag_service.retrieve_parent_context(question)
        sources = _dedupe_sources(small_chunks)

        if small_chunks:
            context = _build_parent_context(big_chunks, small_chunks)
            prompt = f"""Answer the user's question using only the knowledge base context below.

Knowledge base context:
{context}

User question:
{question}

Requirements:
1. If the context is relevant, answer accurately and concisely.
2. If the context is not enough, say that no reliable answer was found in the knowledge base.
3. Mention the source files used at the end.
"""
            summary = chat_service.chat_completion([{"role": "user", "content": prompt}])
        else:
            summary = "No relevant answer was found in the knowledge base."

        return SearchResponseWithSummary(
            original_question=question,
            rewritten_query=None,
            results=[_to_search_result(item) for item in small_chunks],
            summary=summary,
            sources=sources,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...), user_id: str = Depends(get_current_user)):
    temp_path = None
    try:
        file_content = await file.read()
        file_size = len(file_content)
        suffix = os.path.splitext(file.filename or "")[1] or ".txt"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(file_content)
            temp_path = temp_file.name

        result = rag_service.ingest_file(
            temp_path,
            original_filename=file.filename or "uploaded_document",
            file_size=file_size,
            user_id=user_id,
        )

        return UploadResponse(
            success=True,
            message=f"Document '{result['filename']}' uploaded successfully.",
            doc_id=result["doc_id"],
            filename=result["filename"],
            chunks_count=result["small_chunks_count"],
            big_chunks_count=result["big_chunks_count"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


@router.get("/documents")
async def list_documents(user_id: str = Depends(get_current_user)):
    try:
        docs = vector_store.list_documents()
        filtered = [d for d in docs if d.get("user_id") == user_id or user_id == "anonymous"]
        return JSONResponse(content={"documents": filtered}, media_type="application/json; charset=utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    try:
        if doc_id == "faq_collection":
            raise HTTPException(status_code=400, detail="The FAQ collection cannot be deleted.")

        success = rag_service.delete_document(doc_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found.")
        return {"success": True, "message": "Document deleted.", "doc_id": doc_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{doc_id}/status")
async def get_document_status(doc_id: str):
    try:
        return vector_store.get_document_status(doc_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents", response_model=AddDocumentsResponse)
async def add_documents(request: AddDocumentsRequest):
    try:
        result = rag_service.ingest_qa_documents(request.documents)
        return AddDocumentsResponse(
            success=True,
            message=f"Added {len(request.documents)} manual documents.",
            doc_id=result["doc_id"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents")
async def clear_documents():
    try:
        rag_service.clear_documents()
        return {"success": True, "message": "All documents cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/count")
async def count_documents():
    try:
        return {"count": vector_store.count()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
