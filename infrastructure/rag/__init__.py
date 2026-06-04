
from .vector_store import VectorStore
from .embedding import EmbeddingService

vector_store = VectorStore()
embedding_service = EmbeddingService()

__all__ = ["vector_store", "VectorStore", "embedding_service", "EmbeddingService"]

