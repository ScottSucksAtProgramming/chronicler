"""Pydantic data models for D&D campaign entities."""

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class EntityStatus(str, Enum):
    """Status of an NPC or other entity."""

    ALIVE = "alive"
    DEAD = "dead"
    UNKNOWN = "unknown"


class ThreadStatus(str, Enum):
    """Status of a plot thread."""

    OPEN = "open"
    CLOSED = "closed"


class NPC(BaseModel):
    """A non-player character in the campaign."""

    name: str
    first_appeared: str | None = None
    source_attribution: str | None = None
    status: EntityStatus = EntityStatus.UNKNOWN
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)
    affiliations: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    key_interactions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_provenance(self) -> "NPC":
        if self.first_appeared is None and self.source_attribution is None:
            raise ValueError("NPC requires first_appeared or source_attribution")
        return self


class Location(BaseModel):
    """A location in the campaign world."""

    name: str
    first_appeared: str | None = None
    source_attribution: str | None = None
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)
    connected_to: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_provenance(self) -> "Location":
        if self.first_appeared is None and self.source_attribution is None:
            raise ValueError("Location requires first_appeared or source_attribution")
        return self


class Faction(BaseModel):
    """A faction or organization in the campaign."""

    name: str
    first_appeared: str | None = None
    source_attribution: str | None = None
    description: str | None = None
    known_members: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_provenance(self) -> "Faction":
        if self.first_appeared is None and self.source_attribution is None:
            raise ValueError("Faction requires first_appeared or source_attribution")
        return self


class LootItem(BaseModel):
    """A notable item or piece of loot."""

    name: str
    found_in: str | None = None
    source_attribution: str | None = None
    description: str | None = None
    held_by: str | None = None
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_provenance(self) -> "LootItem":
        if self.found_in is None and self.source_attribution is None:
            raise ValueError("LootItem requires found_in or source_attribution")
        return self


class PlotThread(BaseModel):
    """A plot thread or story hook in the campaign."""

    title: str
    status: ThreadStatus
    introduced_in: str | None = None
    source_attribution: str | None = None
    summary: str
    resolved_in: str | None = None
    related_entities: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_provenance(self) -> "PlotThread":
        if self.introduced_in is None and self.source_attribution is None:
            raise ValueError("PlotThread requires introduced_in or source_attribution")
        return self
