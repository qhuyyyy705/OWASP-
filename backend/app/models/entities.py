from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base

def now_utc():
    return datetime.now(timezone.utc)

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    targets: Mapped[list["Target"]] = relationship(back_populates="project", cascade="all, delete-orphan")

class Target(Base):
    __tablename__ = "targets"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    origin: Mapped[str] = mapped_column(String(500), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    project: Mapped[Project] = relationship(back_populates="targets")

class Finding(Base):
    __tablename__ = "vulnerabilities"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    severity: Mapped[str] = mapped_column(String(20), default="Informational", index=True)
    title: Mapped[str] = mapped_column(String(240))
    state: Mapped[str] = mapped_column(String(30), default="Potential")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

class TrafficEntry(Base):
    __tablename__ = "traffic_entries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    target_id: Mapped[int | None] = mapped_column(ForeignKey("targets.id", ondelete="SET NULL"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
    method: Mapped[str] = mapped_column(String(16), index=True)
    url: Mapped[str] = mapped_column(Text)
    hostname: Mapped[str] = mapped_column(String(255), index=True)
    path: Mapped[str] = mapped_column(Text)
    query_params: Mapped[str] = mapped_column(Text, default="{}")
    http_version: Mapped[str] = mapped_column(String(16), default="")
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    request_headers: Mapped[str] = mapped_column(Text, default="{}")
    response_headers: Mapped[str] = mapped_column(Text, default="{}")
    request_body: Mapped[str] = mapped_column(Text, default="")
    response_body: Mapped[str] = mapped_column(Text, default="")
    request_size: Mapped[int] = mapped_column(Integer, default=0)
    response_size: Mapped[int] = mapped_column(Integer, default=0)
    content_type: Mapped[str] = mapped_column(String(255), default="")
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("traffic_entries.id", ondelete="SET NULL"), nullable=True, index=True)
    repeater_name: Mapped[str] = mapped_column(String(120), default="")
