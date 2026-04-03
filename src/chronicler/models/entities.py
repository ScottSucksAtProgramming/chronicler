"""Pydantic data models for D&D campaign entities."""

from enum import Enum

from pydantic import BaseModel, Field


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
    first_appeared: str
    status: EntityStatus = EntityStatus.UNKNOWN
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)
    affiliations: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    key_interactions: list[str] = Field(default_factory=list)


class Location(BaseModel):
    """A location in the campaign world."""

    name: str
    first_appeared: str
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)
    connected_to: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class Faction(BaseModel):
    """A faction or organization in the campaign."""

    name: str
    first_appeared: str
    description: str | None = None
    known_members: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class LootItem(BaseModel):
    """A notable item or piece of loot."""

    name: str
    found_in: str
    description: str | None = None
    held_by: str | None = None
    tags: list[str] = Field(default_factory=list)


class PlotThread(BaseModel):
    """A plot thread or story hook in the campaign."""

    title: str
    status: ThreadStatus
    introduced_in: str
    summary: str
    resolved_in: str | None = None
    related_entities: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
