from .client import LLMClient, ModelError, ModelRateLimitError, ModelConnectionError, ModelTimeoutError, ModelAPIError

chat_service = LLMClient()

__all__ = ["chat_service", "LLMClient", "ModelError", "ModelRateLimitError", "ModelConnectionError", "ModelTimeoutError", "ModelAPIError"]