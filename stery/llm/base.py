import os
from typing import Any, Iterator, Optional, cast

import openai
from openai import OpenAI, Stream
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam, ChatCompletionChunk

from stery.llm.errors import LLMConfigError, LLMResponseError, LLMError, LLMAuthenticationError, LLMRateLimitError, \
    LLMTimeoutError, LLMProviderError


class LLMClient:
    """
    OpenAI-compatible LLM client.

    当前定位：
    - 负责 OpenAI-compatible Chat Completions 调用
    - 支持非流式 think()
    - 支持流式 think_stream()
    - 统一将底层 SDK 异常转换为框架异常

    当前不负责：
    - PromptTemplate
    - OutputParser
    - Tool Calling
    - RAG
    - Memory
    - Agent Loop
    """

    def __init__(
            self,
            provider: Optional[str] = None,
            model: Optional[str] = None,
            api_key: Optional[str] = None,
            base_url: Optional[str] = None,
            temperature: float = 0.7,
            max_tokens: Optional[int] = None,
            timeout: Optional[int] = None,
            **kwargs: Any,
    ):
        """
        :param provider: LLM 供应商标签
        :param model: 模型名称
        :param api_key: API 密钥
        :param base_url: OpenAI-compatible base_url
        :param temperature: 模型温度
        :param max_tokens: 最大输出 token
        :param timeout: 超时时间，单位秒
        :param kwargs: 扩展参数
        """
        self._api_key = (
                api_key
                or os.getenv("LLM_API_KEY")
                or os.getenv("API_KEY")
        )
        self.base_url = (
                base_url
                or os.getenv("LLM_BASE_URL")
                or os.getenv("BASE_URL")
        )

        env_timeout = os.getenv("LLM_TIMEOUT") or os.getenv("TIMEOUT") or "60"
        self.timeout = timeout if timeout is not None else int(env_timeout)

        self.temperature = temperature
        self.max_tokens = max_tokens
        self.kwargs = kwargs
        self.provider = (
                provider
                or os.getenv("LLM_PROVIDER")
                or os.getenv("PROVIDER")
                or None
        )
        if not self._api_key:
            raise LLMConfigError("LLM API key is required. Please set LLM_API_KEY or API_KEY.")

        if not self.base_url:
            raise LLMConfigError("LLM base_url is required. Please set LLM_BASE_URL or BASE_URL.")
        self.model = (
                model
                or os.getenv("LLM_MODEL")
                or os.getenv("DEFAULT_MODEL")
        )

        if not self.model or not self.model.strip():
            raise LLMConfigError("LLM model is required. Please set model, LLM_MODEL or MODEL.")

        self._client = self._create_client()

    def _create_client(self) -> OpenAI:
        return OpenAI(
            api_key=self._api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

    def think_stream(
            self,
            messages: list[ChatCompletionMessageParam],
            temperature: Optional[float] = None,
    ) -> Iterator[str]:
        try:
            request_params: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature if temperature is not None else self.temperature,
                "stream": True,
            }

            if self.max_tokens is not None:
                request_params["max_tokens"] = self.max_tokens

            response = cast(
                Stream[ChatCompletionChunk],
                self._client.chat.completions.create(**request_params),
            )

            has_content = False

            for chunk in response:
                if not chunk.choices:
                    continue

                choice = chunk.choices[0]
                content = choice.delta.content

                if not isinstance(content, str) or not content:
                    continue

                has_content = True
                yield content

            if not has_content:
                raise LLMResponseError("LLM stream response contains no valid content.")

        except LLMError:
            raise
        except Exception as exc:
            raise self.__map_provider_exception(exc) from exc

    def think(self, messages: list[ChatCompletionMessageParam], **kwargs: Any) -> str:
        """
        非流式调用 LLM，返回完整文本。

        失败时不返回 None，而是抛出明确的 LLM 异常。
        """
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)

        try:
            extra_params = {
                key: value
                for key, value in kwargs.items()
                if key not in {"temperature", "max_tokens", "stream"} and value is not None
            }

            request_params: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature if temperature is not None else self.temperature,
                "stream": False,
                **extra_params,
            }

            actual_max_tokens = max_tokens if max_tokens is not None else self.max_tokens
            if actual_max_tokens is not None:
                request_params["max_tokens"] = actual_max_tokens

            response = cast(
                ChatCompletion,
                self._client.chat.completions.create(**request_params),
            )

            if not response.choices:
                raise LLMResponseError("LLM response contains no choices.")

            content = response.choices[0].message.content

            if not isinstance(content, str) or not content.strip():
                raise LLMResponseError("LLM response content is empty.")

            return content

        except LLMError:
            raise
        except Exception as exc:
            raise self.__map_provider_exception(exc) from exc

    def __map_provider_exception(self, exc: Exception) -> LLMError:
        """
        将 OpenAI SDK / OpenAI-compatible SDK 异常转换为框架异常。

        注意：
        - 这里不直接 raise，而是返回异常对象
        - 调用方使用 raise ... from exc 保留原始异常链
        """
        detail = self.__build_error_detail(exc)

        if self.__is_openai_error(exc, "APITimeoutError"):
            return LLMTimeoutError(f"LLM request timeout. {detail}")

        if self.__is_openai_error(exc, "AuthenticationError"):
            return LLMAuthenticationError(f"LLM authentication failed. {detail}")

        if self.__is_openai_error(exc, "RateLimitError"):
            return LLMRateLimitError(f"LLM rate limit exceeded. {detail}")

        if self.__is_openai_error(exc, "APIConnectionError"):
            return LLMProviderError(f"LLM provider connection error. {detail}")

        if self.__is_openai_error(exc, "APIStatusError"):
            status_code = getattr(exc, "status_code", None)
            return LLMProviderError(
                f"LLM provider status error, status_code={status_code}. {detail}"
            )

        if self.__is_openai_error(exc, "APIError"):
            return LLMProviderError(f"LLM provider API error. {detail}")

        return LLMProviderError(f"Unexpected LLM provider error. {detail}")

    @staticmethod
    def __is_openai_error(exc: Exception, error_name: str) -> bool:
        error_type = getattr(openai, error_name, None)
        return isinstance(error_type, type) and isinstance(exc, error_type)

    def __build_error_detail(self, exc: Exception) -> str:
        status_code = getattr(exc, "status_code", None)
        request_id = getattr(exc, "request_id", None)

        parts = [
            f"provider={self.__normalize_provider() or 'unknown'}",
            f"model={self.model}",
        ]

        if status_code is not None:
            parts.append(f"status_code={status_code}")

        if request_id:
            parts.append(f"request_id={request_id}")

        message = str(exc)
        if message:
            parts.append(f"message={message}")

        return ", ".join(parts)

    def __normalize_provider(self) -> str:
        return (self.provider or "").strip().lower()
