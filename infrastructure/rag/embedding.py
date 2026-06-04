import os
from typing import List
from dotenv import load_dotenv
import dashscope
from dashscope import TextEmbedding
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()

class EmbeddingService:
    def __init__(self):
        self.api_key = os.getenv("EMBEDDING_API_KEY", "your-dashscope-api-key")
        self.model_name = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-v1")
        self.timeout = int(os.getenv("EMBEDDING_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("EMBEDDING_MAX_RETRIES", "3"))
        
        dashscope.api_key = self.api_key

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    def embed(self, texts: List[str]) -> List[List[float]]:
        return self.embed_batch(texts, batch_size=20)

    def embed_batch(self, texts: List[str], batch_size: int = 20) -> List[List[float]]:
        all_embeddings = []
        import time
        total_batches = (len(texts) + batch_size - 1) // batch_size
        for batch_idx in range(0, len(texts), batch_size):
            batch = texts[batch_idx:batch_idx + batch_size]
            embeddings = self._embed_single_batch(batch)
            all_embeddings.extend(embeddings)
            if batch_idx + batch_size < len(texts):
                time.sleep(0.3)
        return all_embeddings

    def _embed_single_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            response = TextEmbedding.call(
                model=self.model_name,
                input=texts
            )
            
            if response.status_code == 200:
                return [embedding["embedding"] for embedding in response.output["embeddings"]]
            else:
                raise EmbeddingAPIError(f"API error: {response.message}")
        except dashscope.exceptions.RateLimitError as e:
            raise EmbeddingRateLimitError(f"Rate limit exceeded: {e}") from e
        except dashscope.exceptions.APIConnectionError as e:
            raise EmbeddingConnectionError(f"Connection error: {e}") from e
        except dashscope.exceptions.TimeoutError as e:
            raise EmbeddingTimeoutError(f"Request timed out: {e}") from e
        except Exception as e:
            raise EmbeddingAPIError(f"API error: {e}") from e

    def embed_single(self, text: str) -> List[float]:
        return self.embed([text])[0]


class EmbeddingError(Exception):
    pass

class EmbeddingRateLimitError(EmbeddingError):
    pass

class EmbeddingConnectionError(EmbeddingError):
    pass

class EmbeddingTimeoutError(EmbeddingError):
    pass

class EmbeddingAPIError(EmbeddingError):
    pass