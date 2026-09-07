from typing import Literal
from pydantic import BaseModel, Field


class ConnectionConfig(BaseModel):
    mode: Literal["local", "remote"] = "local"
    url: str | None = None


class ConnectionTest(BaseModel):
    connected: bool
    message: str
    subsystems: dict[str, str] = Field(default_factory=dict)


class EnvironmentState(BaseModel):
    utc: str
    sun_direction: list[float]
    illumination_model: str


class ObjectVisual(BaseModel):
    object_id: str
    kind: Literal["photograph", "technical", "representative"]
    image_url: str | None = None
    source_url: str | None = None
    credit: str | None = None
    caption: str


class GeographyLabel(BaseModel):
    name: str
    latitude: float
    longitude: float
    capital: bool = False


class GeographyData(BaseModel):
    source: str
    lines: list[list[list[float]]]
    labels: list[GeographyLabel]