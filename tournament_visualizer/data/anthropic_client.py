"""Anthropic API client for generating match narratives.

This module provides a simple interface to the Anthropic API for
generating narrative summaries from match event data. Uses API key
authentication and includes retry logic for transient failures.

Example:
    >>> from tournament_visualizer.config import Config
    >>> client = AnthropicClient(api_key=Config.ANTHROPIC_API_KEY)
    >>> response = client.generate_with_tools(
    ...     messages=[{"role": "user", "content": "Extract timeline"}],
    ...     tools=[timeline_tool],
    ...     model="claude-3-5-haiku-20241022"
    ... )
"""

import logging
import time
from typing import Any

import anthropic
from anthropic.types import MessageParam, ToolParam

logger = logging.getLogger(__name__)


class AnthropicClient:
    """Client for calling Anthropic API with retry logic.

    Uses API key authentication. Includes exponential backoff retry
    for rate limits and transient failures.

    Attributes:
        api_key: Anthropic API key
        max_retries: Maximum number of retry attempts (default: 3)
        initial_retry_delay: Initial delay in seconds for exponential backoff (default: 1.0)
    """

    def __init__(
        self,
        api_key: str,
        max_retries: int = 3,
        initial_retry_delay: float = 1.0,
    ) -> None:
        """Initialize Anthropic client.

        Args:
            api_key: Anthropic API key
            max_retries: Maximum number of retry attempts
            initial_retry_delay: Initial delay in seconds for exponential backoff

        Raises:
            ValueError: If api_key is empty
        """
        if not api_key:
            raise ValueError("API key is required")

        self.api_key = api_key
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self._client: anthropic.Anthropic | None = None

    @property
    def client(self) -> anthropic.Anthropic:
        """Lazy-load Anthropic client.

        Returns:
            Anthropic client instance
        """
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def generate_with_tools(
        self,
        messages: list[MessageParam],
        tools: list[ToolParam],
        model: str = "claude-3-5-haiku-20241022",
        max_tokens: int = 4096,
    ) -> anthropic.types.Message:
        """Generate completion using tool calling (structured output).

        Includes retry logic with exponential backoff for rate limits
        and transient failures.

        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: List of tool definitions for structured output
            model: Model name to use (default: Claude 3.5 Haiku)
            max_tokens: Maximum tokens to generate

        Returns:
            Anthropic Message object with tool use in content blocks

        Raises:
            anthropic.APIError: On persistent API errors after retries
        """
        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    f"Calling Anthropic API (attempt {attempt + 1}/{self.max_retries})"
                )
                response = self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    messages=messages,
                    tools=tools,
                )
                logger.debug("API call successful")
                return response

            except anthropic.RateLimitError as e:
                if attempt < self.max_retries - 1:
                    delay = self.initial_retry_delay * (2**attempt)
                    logger.warning(
                        f"Rate limit hit, retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Rate limit exceeded after {self.max_retries} retries")
                    raise

            except anthropic.APIConnectionError as e:
                if attempt < self.max_retries - 1:
                    delay = self.initial_retry_delay * (2**attempt)
                    logger.warning(
                        f"Connection error, retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Connection failed after {self.max_retries} retries"
                    )
                    raise

            except anthropic.APIError as e:
                # Don't retry on client errors (4xx)
                if hasattr(e, "status_code") and 400 <= e.status_code < 500:
                    logger.error(f"Client error (no retry): {e}")
                    raise
                # Retry on server errors (5xx)
                if attempt < self.max_retries - 1:
                    delay = self.initial_retry_delay * (2**attempt)
                    logger.warning(
                        f"Server error, retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Server error after {self.max_retries} retries"
                    )
                    raise

        # Should never reach here due to raises above
        raise RuntimeError("Retry loop exited unexpectedly")

    def generate_text(
        self,
        messages: list[MessageParam],
        model: str = "claude-3-5-haiku-20241022",
        max_tokens: int = 4096,
    ) -> str:
        """Generate text completion (no structured output).

        Includes retry logic with exponential backoff for rate limits
        and transient failures.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name to use (default: Claude 3.5 Haiku)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text content

        Raises:
            anthropic.APIError: On persistent API errors after retries
        """
        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    f"Calling Anthropic API (attempt {attempt + 1}/{self.max_retries})"
                )
                response = self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    messages=messages,
                )
                logger.debug("API call successful")

                # Extract text from content blocks
                text_blocks = [
                    block.text
                    for block in response.content
                    if hasattr(block, "text")
                ]
                return "\n".join(text_blocks)

            except anthropic.RateLimitError as e:
                if attempt < self.max_retries - 1:
                    delay = self.initial_retry_delay * (2**attempt)
                    logger.warning(
                        f"Rate limit hit, retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Rate limit exceeded after {self.max_retries} retries")
                    raise

            except anthropic.APIConnectionError as e:
                if attempt < self.max_retries - 1:
                    delay = self.initial_retry_delay * (2**attempt)
                    logger.warning(
                        f"Connection error, retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Connection failed after {self.max_retries} retries"
                    )
                    raise

            except anthropic.APIError as e:
                # Don't retry on client errors (4xx)
                if hasattr(e, "status_code") and 400 <= e.status_code < 500:
                    logger.error(f"Client error (no retry): {e}")
                    raise
                # Retry on server errors (5xx)
                if attempt < self.max_retries - 1:
                    delay = self.initial_retry_delay * (2**attempt)
                    logger.warning(
                        f"Server error, retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Server error after {self.max_retries} retries"
                    )
                    raise

        # Should never reach here due to raises above
        raise RuntimeError("Retry loop exited unexpectedly")
