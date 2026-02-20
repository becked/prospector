"""Groq API client for natural language SQL query generation.

Mirrors the AnthropicClient pattern: lazy client init, exponential backoff
retry for transient errors, and clear error classification.
"""

import logging
import time
from dataclasses import dataclass

import groq
from groq import Groq

logger = logging.getLogger(__name__)


@dataclass
class GroqResponse:
    """Structured response from Groq API."""

    content: str
    model: str
    usage_prompt_tokens: int
    usage_completion_tokens: int


class GroqClient:
    """Client for Groq API with retry logic.

    Attributes:
        api_key: Groq API key
        max_attempts: Maximum number of attempts (including the initial call)
        initial_retry_delay: Initial backoff delay in seconds
    """

    def __init__(
        self,
        api_key: str,
        max_attempts: int = 2,
        initial_retry_delay: float = 2.0,
    ) -> None:
        """Initialize Groq client.

        Args:
            api_key: Groq API key
            max_attempts: Maximum number of attempts (including the initial call)
            initial_retry_delay: Initial backoff delay in seconds

        Raises:
            ValueError: If api_key is empty
        """
        if not api_key:
            raise ValueError("Groq API key is required")

        self.api_key = api_key
        self.max_attempts = max_attempts
        self.initial_retry_delay = initial_retry_delay
        self._client: Groq | None = None

    @property
    def client(self) -> Groq:
        """Lazy-initialize Groq client."""
        if self._client is None:
            self._client = Groq(api_key=self.api_key)
        return self._client

    def generate(
        self,
        messages: list[dict[str, str]],
        model: str = "llama-3.3-70b-versatile",
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> GroqResponse:
        """Generate a chat completion with retry logic.

        Args:
            messages: List of {"role": ..., "content": ...} dicts
            model: Model identifier
            max_tokens: Max tokens to generate
            temperature: Sampling temperature (0.0 for deterministic SQL)

        Returns:
            GroqResponse with content and usage info

        Raises:
            groq.RateLimitError: After all retries exhausted on 429
            groq.AuthenticationError: Immediately on 401 (no retry)
            groq.APIError: On persistent server errors
        """
        for attempt in range(self.max_attempts):
            try:
                logger.debug(
                    f"Calling Groq API (attempt {attempt + 1}/{self.max_attempts})"
                )
                response = self.client.chat.completions.create(
                    messages=messages,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                logger.debug("Groq API call successful")
                return GroqResponse(
                    content=response.choices[0].message.content or "",
                    model=response.model or model,
                    usage_prompt_tokens=(
                        response.usage.prompt_tokens if response.usage else 0
                    ),
                    usage_completion_tokens=(
                        response.usage.completion_tokens if response.usage else 0
                    ),
                )

            except groq.RateLimitError as e:
                if attempt < self.max_attempts - 1:
                    delay = self.initial_retry_delay * (2**attempt)
                    logger.warning(f"Groq rate limit, retry in {delay}s: {e}")
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Groq rate limit exceeded after {self.max_attempts} retries"
                    )
                    raise

            except groq.APIConnectionError as e:
                if attempt < self.max_attempts - 1:
                    delay = self.initial_retry_delay * (2**attempt)
                    logger.warning(f"Groq connection error, retry in {delay}s: {e}")
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Groq connection failed after {self.max_attempts} retries"
                    )
                    raise

            except (groq.AuthenticationError, groq.PermissionDeniedError):
                # Don't retry auth errors
                raise

            except groq.APIError as e:
                # Don't retry client errors (4xx)
                if (
                    hasattr(e, "status_code")
                    and e.status_code
                    and 400 <= e.status_code < 500
                ):
                    logger.error(f"Groq client error (no retry): {e}")
                    raise
                # Retry server errors (5xx)
                if attempt < self.max_attempts - 1:
                    delay = self.initial_retry_delay * (2**attempt)
                    logger.warning(f"Groq server error, retry in {delay}s: {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"Groq server error after {self.max_attempts} retries")
                    raise

        # Should never reach here due to raises above
        raise RuntimeError("Retry loop exited unexpectedly")
