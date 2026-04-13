"""Types for LLM Gateway requests and responses."""

from pydantic import BaseModel, computed_field


class LLMUsage(BaseModel):
    """Token usage for an LLM call."""

    prompt_tokens: int
    completion_tokens: int

    @computed_field
    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMRequest(BaseModel):
    """A request to the LLM."""

    messages: list[dict[str, str]]
    model: str
    temperature: float = 0.0
    max_tokens: int | None = None


class LLMResponse(BaseModel):
    """A response from the LLM."""

    content: str
    model: str
    usage: LLMUsage
