import os
import time
from typing import List, Dict, Any, Generator, Optional
from dotenv import load_dotenv
import dashscope
from dashscope import Generation
from dashscope.api_entities.dashscope_response import Message
from dashscope.common.error import DashScopeException

load_dotenv()

class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("MODEL_API_KEY", "your-dashscope-api-key")
        self.model_name = os.getenv("MODEL_MODEL_NAME", "qwen-plus")
        self.timeout = int(os.getenv("MODEL_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("MODEL_MAX_RETRIES", "3"))

        dashscope.api_key = self.api_key

    def chat(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.chat_completion(messages)

    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        last_error = None

        for attempt in range(self.max_retries):
            try:
                dashscope_messages = []
                for msg in messages:
                    role = msg["role"]
                    content = msg["content"]
                    dashscope_messages.append(Message(role=role, content=content))

                response = Generation.call(
                    model=self.model_name,
                    messages=dashscope_messages,
                    **kwargs
                )

                if response.status_code == 200:
                    text = response.output.get('text', '')
                    return text.strip() if text else ''
                else:
                    error_msg = f"API error {response.status_code}: {response.message}"
                    if attempt < self.max_retries - 1:
                        wait_time = min(2 ** attempt, 10)
                        time.sleep(wait_time)
                        continue
                    raise ModelAPIError(error_msg)

            except DashScopeException as e:
                last_error = ModelAPIError(f"DashScope error: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = min(2 ** attempt, 10)
                    time.sleep(wait_time)
                continue
            except Exception as e:
                last_error = ModelAPIError(f"API error: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = min(2 ** attempt, 10)
                    time.sleep(wait_time)
                continue

        raise last_error or ModelAPIError("Unknown error in chat_completion")

    def chat_completion_stream(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        try:
            dashscope_messages = []
            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                dashscope_messages.append(Message(role=role, content=content))

            responses = Generation.call(
                model=self.model_name,
                messages=dashscope_messages,
                stream=True,
                incremental_output=True,
                **kwargs
            )

            prev_text = ''
            for response in responses:
                if response.status_code == 200:
                    text = response.output.get('text', '')
                    if text:
                        if text.startswith(prev_text):
                            delta = text[len(prev_text):]
                            prev_text = text
                            if delta:
                                yield delta
                        else:
                            prev_text = text
                            yield text
                else:
                    raise ModelAPIError(f"Stream error: {response.message}")
        except DashScopeException as e:
            raise ModelAPIError(f"DashScope error: {e}") from e
        except Exception as e:
            raise ModelAPIError(f"API error: {e}") from e

    def generate_with_template(self, template: str, **variables) -> str:
        prompt = template.format(**variables)
        messages = [{"role": "user", "content": prompt}]
        return self.chat_completion(messages)

    def generate_stream_with_template(self, template: str, **variables) -> Generator[str, None, None]:
        prompt = template.format(**variables)
        messages = [{"role": "user", "content": prompt}]
        return self.chat_completion_stream(messages)


class ModelError(Exception):
    pass

class ModelRateLimitError(ModelError):
    pass

class ModelConnectionError(ModelError):
    pass

class ModelTimeoutError(ModelError):
    pass

class ModelAPIError(ModelError):
    pass