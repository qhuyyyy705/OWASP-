from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value):
        normalized = value.strip()
        if not normalized:
            raise ValueError("Project name cannot be blank")
        return normalized

class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str
    created_at: datetime

class TargetCreate(BaseModel):
    origin: str = Field(min_length=8, max_length=500)
    @field_validator("origin")
    @classmethod
    def valid_origin(cls, value):
        from urllib.parse import urlsplit
        parsed = urlsplit(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Target must be an http(s) origin without credentials")
        try:
            _ = parsed.port
        except ValueError as exc:
            raise ValueError("Target port is invalid") from exc
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError("Target must be an origin only, without path, query, or fragment")
        return f"{parsed.scheme}://{parsed.netloc}".lower()

class TargetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    origin: str
    created_at: datetime

class ProxyStart(BaseModel):
    project_id: int = Field(gt=0)
    host: Literal["127.0.0.1"] = "127.0.0.1"
    port: int = Field(default=8080, ge=1024, le=65535)
