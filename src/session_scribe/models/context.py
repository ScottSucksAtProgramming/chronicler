"""Data models for context bundles and agent memory structures."""

from pydantic import BaseModel, Field


class EntitySummary(BaseModel):
    """Lightweight summary of a known entity for context bundles."""

    name: str
    aliases: list[str] = Field(default_factory=list)
    status: str | None = None


class ThreadSummary(BaseModel):
    """Lightweight summary of an active plot thread."""

    title: str
    summary: str


class PlayerCharacter(BaseModel):
    """Mapping between a player and their character."""

    player_name: str
    character_name: str
    character_class: str | None = None


class ContextBundle(BaseModel):
    """Snapshot of campaign state passed to the extraction module."""

    session_number: int
    known_npcs: list[EntitySummary] = Field(default_factory=list)
    known_locations: list[EntitySummary] = Field(default_factory=list)
    known_factions: list[EntitySummary] = Field(default_factory=list)
    active_threads: list[ThreadSummary] = Field(default_factory=list)
    recent_events: list[str] = Field(default_factory=list)
    entity_aliases: dict[str, str] = Field(default_factory=dict)
    player_characters: list[PlayerCharacter] = Field(default_factory=list)


class AgentMemory(BaseModel):
    """Persistent agent memory stored in the vault."""

    extraction_rules: list[str] = Field(default_factory=list)
    entity_aliases: dict[str, str] = Field(default_factory=dict)
    player_characters: list[PlayerCharacter] = Field(default_factory=list)
    campaign_patterns: list[str] = Field(default_factory=list)
    user_preferences: list[str] = Field(default_factory=list)
