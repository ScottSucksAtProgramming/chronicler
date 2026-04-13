"""LLM Gateway — single integration point for all LLM calls.

Supports two providers:
- "kimi": Uses Kimi Code CLI (kimi --quiet -p) for LLM calls. No API key needed.
- "nanogpt": Uses nano-gpt.com HTTP API. Requires CHRONICLER_NANOGPT_API_KEY.
"""

import asyncio
import json
import logging
import subprocess
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from chronicler.config.settings import Settings
from chronicler.gateway.types import LLMRequest, LLMResponse, LLMUsage

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMGatewayError(Exception):
    """Raised when an LLM call fails after retries."""


def _resolve_working_directory(settings: Settings):
    """Run external model tools from the configured vault, not the repo."""
    return settings.vault_path


def _raise_for_filtered_content(content: str) -> None:
    lowered = content.lower()
    if "content_filter" in lowered or "considered high risk" in lowered:
        raise LLMGatewayError(
            "LLM provider rejected the prompt as high-risk content, likely due to explicit off-topic banter in the raw transcript."
        )


class LLMGateway:
    """Single integration point for all LLM API calls.

    Routes calls to either Kimi CLI or nano-gpt.com based on settings.llm_provider.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: httpx.AsyncClient | None = None

        if settings.llm_provider == "nanogpt":
            if not settings.nanogpt_api_key:
                raise LLMGatewayError(
                    "CHRONICLER_NANOGPT_API_KEY is required when llm_provider='nanogpt'"
                )
            self._client = httpx.AsyncClient(
                base_url=settings.nanogpt_base_url,
                headers={
                    "Authorization": f"Bearer {settings.nanogpt_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=settings.llm_timeout_seconds,
            )

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send a completion request to the configured LLM provider."""
        if self.settings.llm_provider == "kimi":
            return await self._complete_kimi(request)
        else:
            return await self._complete_nanogpt(request)

    async def _complete_kimi(self, request: LLMRequest) -> LLMResponse:
        """Send a completion request via Kimi Code CLI."""
        # Build the prompt from messages
        prompt_parts = []
        for msg in request.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.append(f"[System instruction]: {content}")
            elif role == "assistant":
                prompt_parts.append(f"[Previous response]: {content}")
            else:
                prompt_parts.append(content)

        full_prompt = "\n\n".join(prompt_parts)

        # Build kimi command
        cmd = ["kimi", "--quiet", "-p", full_prompt]
        if self.settings.kimi_model:
            cmd.extend(["-m", self.settings.kimi_model])

        start = time.monotonic()
        try:
            # Run kimi CLI in a thread to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.settings.llm_timeout_seconds * 4,  # kimi can be slower
                    cwd=_resolve_working_directory(self.settings),
                ),
            )
            latency = time.monotonic() - start

            if result.returncode != 0:
                error_msg = (
                    result.stderr.strip()
                    or f"kimi exited with code {result.returncode}"
                )
                raise LLMGatewayError(f"Kimi CLI error: {error_msg}")

            content = result.stdout.strip()
            if not content:
                raise LLMGatewayError("Kimi CLI returned empty response")
            _raise_for_filtered_content(content)

            response = LLMResponse(
                content=content,
                model=self.settings.kimi_model or "kimi-default",
                usage=LLMUsage(
                    prompt_tokens=0, completion_tokens=0
                ),  # Kimi doesn't report usage
            )

            logger.info(
                "Kimi call: latency=%.2fs, response_len=%d",
                latency,
                len(content),
            )
            return response

        except subprocess.TimeoutExpired:
            raise LLMGatewayError(
                f"Kimi CLI timed out after {self.settings.llm_timeout_seconds * 4}s"
            )
        except FileNotFoundError:
            raise LLMGatewayError(
                "Kimi CLI not found. Install it: https://moonshotai.github.io/kimi-cli/"
            )

    async def _complete_nanogpt(self, request: LLMRequest) -> LLMResponse:
        """Send a completion request to the nano-gpt.com API with retries."""
        assert (
            self._client is not None
        ), "HTTP client not initialized for nanogpt provider"

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
                        **(
                            {"max_tokens": request.max_tokens}
                            if request.max_tokens
                            else {}
                        ),
                    },
                )
                latency = time.monotonic() - start

                response.raise_for_status()
                data = response.json()

                # Parse usage tolerantly — some providers don't include it
                usage_data = data.get("usage", {})
                usage = LLMUsage(
                    prompt_tokens=usage_data.get("prompt_tokens", 0),
                    completion_tokens=usage_data.get("completion_tokens", 0),
                )

                result = LLMResponse(
                    content=data["choices"][0]["message"]["content"],
                    model=data.get("model", request.model),
                    usage=usage,
                )

                logger.info(
                    "LLM call: model=%s tokens=%d latency=%.2fs",
                    result.model,
                    result.usage.total_tokens,
                    latency,
                )
                return result

            except (httpx.HTTPError, KeyError, IndexError) as e:
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

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Remove markdown code fences from LLM output if present."""
        text = text.strip()
        if text.startswith("```"):
            first_newline = text.find("\n")
            if first_newline == -1:
                return text
            text = text[first_newline + 1 :]
            if text.rstrip().endswith("```"):
                text = text.rstrip().rsplit("```", 1)[0].strip()
        return text

    async def complete_structured(
        self,
        request: LLMRequest,
        output_type: type[T],
    ) -> T:
        """Send a completion request and parse the response into a Pydantic model."""
        response = await self.complete(request)

        try:
            content = self._strip_code_fences(response.content)
            parsed = json.loads(content)
            return output_type.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(
                "Structured output parsing failed: %s. Retrying with correction.",
                str(e),
            )

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
                content = self._strip_code_fences(retry_response.content)
                parsed = json.loads(content)
                return output_type.model_validate(parsed)
            except (json.JSONDecodeError, ValidationError) as retry_error:
                raise LLMGatewayError(
                    f"Structured output parsing failed after correction: {retry_error}"
                ) from retry_error

    def complete_sync(self, request: LLMRequest) -> LLMResponse:
        """Synchronous version of complete() for use in threaded contexts.

        For Kimi provider: runs subprocess directly.
        For nanogpt provider: uses sync httpx.
        """
        if self.settings.llm_provider == "kimi":
            return self._complete_kimi_sync(request)
        else:
            return self._complete_nanogpt_sync(request)

    def _complete_kimi_sync(self, request: LLMRequest) -> LLMResponse:
        """Sync Kimi CLI completion."""
        prompt_parts = []
        for msg in request.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.append(f"[System instruction]: {content}")
            elif role == "assistant":
                prompt_parts.append(f"[Previous response]: {content}")
            else:
                prompt_parts.append(content)

        full_prompt = "\n\n".join(prompt_parts)
        cmd = ["kimi", "--quiet", "-p", full_prompt]
        if self.settings.kimi_model:
            cmd.extend(["-m", self.settings.kimi_model])

        start = time.monotonic()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.settings.llm_timeout_seconds * 4,
            cwd=_resolve_working_directory(self.settings),
        )
        latency = time.monotonic() - start

        if result.returncode != 0:
            raise LLMGatewayError(f"Kimi CLI error: {result.stderr.strip()}")

        content = result.stdout.strip()
        if not content:
            raise LLMGatewayError("Kimi CLI returned empty response")
        _raise_for_filtered_content(content)

        logger.info("Kimi sync call: latency=%.2fs", latency)
        return LLMResponse(
            content=content,
            model=self.settings.kimi_model or "kimi-default",
            usage=LLMUsage(prompt_tokens=0, completion_tokens=0),
        )

    def _complete_nanogpt_sync(self, request: LLMRequest) -> LLMResponse:
        """Sync nano-gpt.com completion."""
        response = httpx.post(
            f"{self.settings.nanogpt_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.settings.nanogpt_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": request.model,
                "messages": request.messages,
                "temperature": request.temperature,
            },
            timeout=self.settings.llm_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        usage_data = data.get("usage", {})
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", request.model),
            usage=LLMUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
            ),
        )

    async def close(self) -> None:
        """Close the HTTP client if one was created."""
        if self._client:
            await self._client.aclose()
