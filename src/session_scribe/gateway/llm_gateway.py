"""LLM Gateway — single integration point for all LLM calls."""

import asyncio
import json
import logging
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from session_scribe.config.settings import Settings
from session_scribe.gateway.types import LLMRequest, LLMResponse, LLMUsage

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMGatewayError(Exception):
    """Raised when an LLM call fails after retries."""


class LLMGateway:
    """Single integration point for all LLM API calls."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.nanogpt_base_url,
            headers={
                "Authorization": f"Bearer {settings.nanogpt_api_key}",
                "Content-Type": "application/json",
            },
            timeout=settings.llm_timeout_seconds,
        )

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send a completion request to the LLM API with retries."""
        last_error: Exception | None = None
        backoff = 1.0

        for attempt in range(self.settings.llm_max_retries + 1):
            try:
                start = time.monotonic()
                response = await self._client.post(
                    "/chat/completions",
                    json={
                        "model": request.model,
                        "messages": request.messages,
                        "temperature": request.temperature,
                        **({"max_tokens": request.max_tokens} if request.max_tokens else {}),
                    },
                )
                latency = time.monotonic() - start

                response.raise_for_status()
                data = response.json()

                result = LLMResponse(
                    content=data["choices"][0]["message"]["content"],
                    model=data.get("model", request.model),
                    usage=LLMUsage(
                        prompt_tokens=data["usage"]["prompt_tokens"],
                        completion_tokens=data["usage"]["completion_tokens"],
                    ),
                )

                logger.info(
                    "LLM call: model=%s tokens=%d latency=%.2fs",
                    result.model,
                    result.usage.total_tokens,
                    latency,
                )
                return result

            except (httpx.HTTPError, KeyError) as e:
                last_error = e
                if attempt < self.settings.llm_max_retries:
                    logger.warning(
                        "LLM call failed (attempt %d/%d): %s. Retrying in %.1fs.",
                        attempt + 1,
                        self.settings.llm_max_retries + 1,
                        str(e),
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2

        raise LLMGatewayError(
            f"LLM call failed after {self.settings.llm_max_retries + 1} attempts: {last_error}"
        )

    async def complete_structured(
        self,
        request: LLMRequest,
        output_type: type[T],
    ) -> T:
        """Send a completion request and parse the response into a Pydantic model."""
        response = await self.complete(request)

        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            parsed = json.loads(content)
            return output_type.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning("Structured output parsing failed: %s. Retrying with correction.", str(e))

            corrective_messages = request.messages + [
                {"role": "assistant", "content": response.content},
                {
                    "role": "user",
                    "content": (
                        f"Your response could not be parsed as valid JSON matching the expected schema. "
                        f"Error: {str(e)}. Please respond with ONLY valid JSON, no markdown formatting."
                    ),
                },
            ]
            corrective_request = LLMRequest(
                messages=corrective_messages,
                model=request.model,
                temperature=request.temperature,
            )
            retry_response = await self.complete(corrective_request)

            try:
                content = retry_response.content.strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                parsed = json.loads(content)
                return output_type.model_validate(parsed)
            except (json.JSONDecodeError, ValidationError) as retry_error:
                raise LLMGatewayError(
                    f"Structured output parsing failed after correction: {retry_error}"
                ) from retry_error

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
