"""Tests for the LLM Gateway."""

import json
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from pydantic import BaseModel

from session_scribe.gateway.types import LLMRequest, LLMResponse, LLMUsage
from session_scribe.gateway.llm_gateway import LLMGateway, LLMGatewayError
from session_scribe.config.settings import Settings


class SampleOutput(BaseModel):
    name: str
    age: int


# Note: `settings` fixture is provided by tests/conftest.py


class TestLLMTypes:
    def test_create_request(self):
        req = LLMRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="test-model",
        )
        assert len(req.messages) == 1
        assert req.temperature == 0.0

    def test_create_response(self):
        resp = LLMResponse(
            content="Hello back",
            model="test-model",
            usage=LLMUsage(prompt_tokens=10, completion_tokens=5),
        )
        assert resp.content == "Hello back"
        assert resp.usage.total_tokens == 15


class TestLLMGateway:
    def test_gateway_init(self, settings):
        gateway = LLMGateway(settings)
        assert gateway.settings.nanogpt_api_key == "test-key-123"

    @pytest.mark.asyncio
    async def test_complete_returns_response(self, settings):
        gateway = LLMGateway(settings)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test response"}}],
            "model": "test-model",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

        with patch.object(gateway, "_client") as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)
            result = await gateway.complete(
                LLMRequest(
                    messages=[{"role": "user", "content": "test"}],
                    model="test-model",
                )
            )
            assert result.content == "test response"
            assert result.usage.total_tokens == 15

    @pytest.mark.asyncio
    async def test_complete_retries_on_http_error(self, settings):
        gateway = LLMGateway(settings)

        fail_response = MagicMock()
        fail_response.status_code = 500
        fail_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=fail_response
        )

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.raise_for_status.return_value = None
        success_response.json.return_value = {
            "choices": [{"message": {"content": "recovered"}}],
            "model": "test-model",
            "usage": {"prompt_tokens": 5, "completion_tokens": 3},
        }

        with patch.object(gateway, "_client") as mock_client:
            mock_client.post = AsyncMock(side_effect=[fail_response, success_response])
            result = await gateway.complete(
                LLMRequest(messages=[{"role": "user", "content": "test"}], model="test-model")
            )
            assert result.content == "recovered"
            assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_complete_raises_after_retries_exhausted(self, settings):
        gateway = LLMGateway(settings)

        fail_response = MagicMock()
        fail_response.status_code = 500
        fail_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=fail_response
        )

        with patch.object(gateway, "_client") as mock_client:
            mock_client.post = AsyncMock(return_value=fail_response)
            with pytest.raises(LLMGatewayError, match="failed after"):
                await gateway.complete(
                    LLMRequest(messages=[{"role": "user", "content": "test"}], model="test-model")
                )

    @pytest.mark.asyncio
    async def test_complete_structured_parses_to_model(self, settings):
        gateway = LLMGateway(settings)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"name": "Bob", "age": 30}'}}],
            "model": "test-model",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

        with patch.object(gateway, "_client") as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)
            result = await gateway.complete_structured(
                LLMRequest(
                    messages=[{"role": "user", "content": "test"}],
                    model="test-model",
                ),
                output_type=SampleOutput,
            )
            assert isinstance(result, SampleOutput)
            assert result.name == "Bob"
            assert result.age == 30

    @pytest.mark.asyncio
    async def test_complete_structured_strips_markdown_code_block(self, settings):
        gateway = LLMGateway(settings)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '```json\n{"name": "Alice", "age": 25}\n```'}}],
            "model": "test-model",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

        with patch.object(gateway, "_client") as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)
            result = await gateway.complete_structured(
                LLMRequest(messages=[{"role": "user", "content": "test"}], model="test-model"),
                output_type=SampleOutput,
            )
            assert result.name == "Alice"
            assert result.age == 25

    @pytest.mark.asyncio
    async def test_complete_structured_invalid_json_retries(self, settings):
        gateway = LLMGateway(settings)

        bad_response = MagicMock()
        bad_response.status_code = 200
        bad_response.raise_for_status.return_value = None
        bad_response.json.return_value = {
            "choices": [{"message": {"content": "not json at all"}}],
            "model": "test-model",
            "usage": {"prompt_tokens": 5, "completion_tokens": 3},
        }

        with patch.object(gateway, "_client") as mock_client:
            mock_client.post = AsyncMock(return_value=bad_response)
            with pytest.raises(LLMGatewayError, match="parsing failed after correction"):
                await gateway.complete_structured(
                    LLMRequest(messages=[{"role": "user", "content": "test"}], model="test-model"),
                    output_type=SampleOutput,
                )
