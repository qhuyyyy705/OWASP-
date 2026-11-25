from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
import asyncio, json
import re
import time
import httpx
from urllib.parse import urlsplit, urlunsplit
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.database.session import SessionLocal
from app.models import Finding, Project, Target, TrafficEntry
from app.schemas import ProjectCreate, ProjectOut, ProxyStart, TargetCreate, TargetOut
from app.services.scope import check_scope
from app.services.proxy_manager import proxy_manager
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api")

class RepeaterSend(BaseModel):
    project_id: int = Field(gt=0)
    parent_id: str = Field(min_length=1, max_length=36)
    name: str = Field(default="Repeater", max_length=120)
    method: str = Field(min_length=1, max_length=16)
    url: str = Field(min_length=1, max_length=2048)
    http_version: str = Field(default="HTTP/1.1", max_length=16)
    headers: dict[str, str] = Field(default_factory=dict)
    body: str = Field(default="", max_length=1_048_576)

@router.get("/health")
def health():
    return {"status": "ok"}

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    total_projects = db.scalar(select(func.count(Project.id))) or 0
    total_targets = db.scalar(select(func.count(Target.id))) or 0
    counts = {severity.lower(): db.scalar(select(func.count(Finding.id)).where(Finding.severity == severity)) or 0
              for severity in ("Critical", "High", "Medium", "Low", "Informational")}
    traffic_count = db.scalar(select(func.count(TrafficEntry.id))) or 0
    return {"projects": total_projects, "websites": total_targets, "requests": traffic_count,
            "vulnerabilities": sum(counts.values()), "severity": counts,
            "recent_activity": [], "traffic": [], "implemented": ["projects", "targets", "scope", "dashboard", "proxy-traffic", "traffic-history"]}

@router.get("/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.scalars(select(Project).order_by(Project.created_at.desc())).all()

@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(name=payload.name.strip(), description=payload.description.strip())
    db.add(project)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A project with this name already exists")
    db.refresh(project)
    return project

@router.get("/projects/{project_id}/targets", response_model=list[TargetOut])
def list_targets(project_id: int, db: Session = Depends(get_db)):
    if db.get(Project, project_id) is None:
        raise HTTPException(404, "Project not found")
    return db.scalars(select(Target).where(Target.project_id == project_id)).all()

@router.post("/projects/{project_id}/targets", response_model=TargetOut, status_code=201)
def add_target(project_id: int, payload: TargetCreate, db: Session = Depends(get_db)):
    if db.get(Project, project_id) is None:
        raise HTTPException(404, "Project not found")
    target = Target(project_id=project_id, origin=payload.origin)
    db.add(target)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Target could not be saved")
    db.refresh(target)
    return target

@router.get("/scope/check")
def scope_check(project_id: int = Query(gt=0), url: str = Query(min_length=1, max_length=2048), db: Session = Depends(get_db)):
    allowed, reason = check_scope(db, project_id, url)
    if reason == "Project not found":
        raise HTTPException(404, reason)
    return {"allowed": allowed, "reason": reason}

@router.get("/proxy/status")
def get_proxy_status():
    return proxy_manager.status()

def traffic_dict(entry: TrafficEntry, include_bodies: bool = False):
    from sqlalchemy.inspection import inspect
    result = {column.key: getattr(entry, column.key) for column in inspect(TrafficEntry).mapper.column_attrs}
    result["timestamp"] = entry.timestamp.isoformat() if entry.timestamp else None
    if not include_bodies:
        result.pop("request_body", None); result.pop("response_body", None)
    return result

@router.get("/traffic")
def list_traffic(project_id: int | None = None, target_id: int | None = None, method: str | None = None,
                 status_code: int | None = None, search: str | None = None, limit: int = Query(200, ge=1, le=1000),
                 db: Session = Depends(get_db)):
    query = select(TrafficEntry)
    if project_id: query = query.where(TrafficEntry.project_id == project_id)
    if target_id: query = query.where(TrafficEntry.target_id == target_id)
    if method: query = query.where(TrafficEntry.method == method.upper())
    if status_code: query = query.where(TrafficEntry.status_code == status_code)
    if search: query = query.where(TrafficEntry.url.contains(search) | TrafficEntry.hostname.contains(search))
    rows = db.scalars(query.order_by(TrafficEntry.timestamp.desc()).limit(limit)).all()
    return [traffic_dict(row) for row in rows]

@router.get("/traffic/events")
async def traffic_events(project_id: int | None = None, target_id: int | None = None):
    async def events():
        seen = {}
        while True:
            db = SessionLocal()
            try:
                query = select(TrafficEntry).order_by(TrafficEntry.timestamp.desc()).limit(100)
                if project_id: query = query.where(TrafficEntry.project_id == project_id)
                if target_id: query = query.where(TrafficEntry.target_id == target_id)
                for entry in reversed(db.scalars(query).all()):
                    marker = (entry.status_code, entry.duration_ms, entry.response_size, entry.error)
                    if seen.get(entry.id) == marker: continue
                    seen[entry.id] = marker
                    yield f"data: {json.dumps(traffic_dict(entry))}\n\n"
                if len(seen) > 2000: seen.clear()
            finally: db.close()
            await asyncio.sleep(0.6)
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control":"no-cache", "X-Accel-Buffering":"no"})

@router.get("/traffic/{entry_id}")
def get_traffic(entry_id: str, db: Session = Depends(get_db)):
    entry = db.get(TrafficEntry, entry_id)
    if entry is None: raise HTTPException(404, "Traffic entry not found")
    return traffic_dict(entry, True)

@router.post("/repeater/send")
def repeater_send(payload: RepeaterSend, db: Session = Depends(get_db)):
    original = db.get(TrafficEntry, payload.parent_id)
    if original is None or original.project_id != payload.project_id:
        raise HTTPException(404, "Original request was not found in this project")
    allowed, reason = check_scope(db, payload.project_id, payload.url)
    if not allowed:
        raise HTTPException(403, reason)
    proxy = proxy_manager.status()
    if not proxy["running"] or proxy["project_id"] != payload.project_id:
        raise HTTPException(409, "Start the scoped proxy for this project before sending")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9!#$%&'*+.^_`|~-]{0,15}", payload.method):
        raise HTTPException(422, "Invalid HTTP method")
    headers = {}
    for key, value in payload.headers.items():
        if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", key) or "\r" in value or "\n" in value:
            raise HTTPException(422, f"Invalid header: {key[:80]}")
        if key.lower() not in {"host", "content-length", "connection", "transfer-encoding", "proxy-authorization", "proxy-connection"}:
            headers[key] = value
    headers["X-WebSentinel-Repeater-Parent"] = payload.parent_id
    try:
        started = time.monotonic()
        with httpx.Client(proxy=f"http://{proxy['host']}:{proxy['port']}", trust_env=False, follow_redirects=False, timeout=30) as client:
            with client.stream(payload.method.upper(), payload.url, headers=headers, content=payload.body.encode("utf-8")) as response:
                chunks, size, stored = [], 0, 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if stored < 1_048_576:
                        selected = chunk[:1_048_576 - stored]
                        chunks.append(selected)
                        stored += len(selected)
                body = b"".join(chunks).decode("utf-8", "replace")
                if size > 1_048_576:
                    body += "\n[response body truncated at 1 MiB]"
                return {"status_code": response.status_code, "duration_ms": round((time.monotonic() - started) * 1000, 2), "response_headers": dict(response.headers), "response_body": body, "response_size": size, "content_type": response.headers.get("content-type", ""), "location": response.headers.get("location")}
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Request through scoped proxy failed: {exc}") from exc

@router.delete("/traffic")
def clear_traffic(project_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(TrafficEntry)
    if project_id: query = query.filter(TrafficEntry.project_id == project_id)
    deleted = query.delete(synchronize_session=False); db.commit()
    return {"deleted": deleted}

@router.post("/proxy/start")
def start_proxy(payload: ProxyStart, db: Session = Depends(get_db)):
    project = db.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    origins = [target.origin for target in project.targets]
    try:
        return proxy_manager.start(project.id, origins, payload.host, payload.port)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc

@router.post("/proxy/stop")
def stop_proxy():
    return proxy_manager.stop()

@router.get("/proxy/ca")
def download_proxy_ca():
    if not proxy_manager.ca_file.is_file():
        raise HTTPException(404, "CA certificate is not available; start the proxy first")
    return FileResponse(
        proxy_manager.ca_file,
        media_type="application/x-pem-file",
        filename="mitmproxy-ca-cert.pem",
        headers={"X-Content-Type-Options": "nosniff"},
    )
