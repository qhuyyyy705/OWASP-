"""mitmproxy hook that blocks destinations outside configured target origins."""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, parse_qs, parse_qsl, urlencode

from mitmproxy import http


def normalized_origin(url: str) -> str | None:
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return None
        if parsed.username or parsed.password:
            return None
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        return f"{parsed.scheme.lower()}://{parsed.hostname.lower()}:{port}"
    except ValueError:
        return None

_capture_engine = None


class ScopeEnforcementAddon:
    def __init__(self, allowed_origins: list[str] | None = None):
        self.allowed_origins = {origin for item in (allowed_origins or []) if (origin := normalized_origin(item))}

    def request(self, flow: http.HTTPFlow) -> None:
        parent_id = flow.request.headers.pop("X-WebSentinel-Repeater-Parent", "")
        requested_origin = normalized_origin(flow.request.pretty_url)
        if requested_origin not in self.allowed_origins:
            self._block(flow)
            return
        flow.metadata["websentinel_started"] = time.monotonic()
        flow.metadata["websentinel_id"] = str(uuid.uuid4())
        flow.metadata["websentinel_parent_id"] = parent_id
        try:
            self._store_request(flow)
        except Exception:
            # Capture failures must never interrupt authorized proxy forwarding.
            pass

    @staticmethod
    def _safe_headers(headers) -> str:
        output = {}
        used = 0
        for key, value in headers.items(multi=True):
            if len(output) >= 200: break
            safe_value = ("[REDACTED]" if any(secret in key.lower() for secret in ("authorization", "cookie", "token", "secret", "api-key", "api_key", "password")) else str(value)[:4096])
            addition = len(key) + len(safe_value)
            if used + addition > 60000: break
            output[key[:256]] = safe_value
            used += addition
        return json.dumps(output)

    @staticmethod
    def _body(message) -> str:
        try: limit = max(0, min(int(os.getenv("WEBSENTINEL_BODY_LIMIT", "65536")), 1048576))
        except ValueError: limit = 65536
        content_type = message.headers.get("content-type", "").lower()
        if any(kind in content_type for kind in ("image/", "audio/", "video/", "font/", "application/octet-stream", "application/zip", "multipart/")):
            return "[binary body omitted]"
        data = message.raw_content or b""
        try:
            text = data[:limit].decode("utf-8", errors="replace")
            truncated = len(data) > limit
            if "json" in content_type:
                try:
                    def redact(value):
                        if isinstance(value, dict):
                            return {key: ("[REDACTED]" if any(word in key.lower() for word in ("password", "token", "secret", "authorization", "api_key", "apikey")) else redact(item)) for key, item in value.items()}
                        if isinstance(value, list): return [redact(item) for item in value]
                        return value
                    text = json.dumps(redact(json.loads(text)), ensure_ascii=False)
                except (ValueError, TypeError):
                    if truncated: return "[oversized JSON body omitted]"
            elif "application/x-www-form-urlencoded" in content_type:
                text = urlencode([(key, "[REDACTED]" if any(word in key.lower() for word in ("password", "token", "secret", "api_key")) else value) for key, value in parse_qsl(text, keep_blank_values=True)])
            text = re.sub(r'''(?i)(["']?(?:password|access[_-]?token|refresh[_-]?token|token|secret|api[_-]?key|authorization)["']?\s*[:=]\s*["']?)[^"'&,}\s<]+''', r"\1[REDACTED]", text)
            return text + ("\n[body truncated]" if truncated else "")
        except Exception: return "[body unavailable]"

    def _session(self):
        global _capture_engine
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.database.session import Base
        if _capture_engine is None:
            _capture_engine = create_engine(os.environ["WEBSENTINEL_DATABASE_URL"], connect_args={"check_same_thread": False})
            Base.metadata.create_all(_capture_engine)
        return sessionmaker(bind=_capture_engine)()

    def _store_request(self, flow: http.HTTPFlow) -> None:
        from app.models import Project, Target, TrafficEntry
        request = flow.request
        parsed = urlsplit(request.pretty_url)
        db = self._session()
        try:
            project_id = int(os.environ["WEBSENTINEL_PROJECT_ID"])
            target = db.query(Target).filter(Target.project_id == project_id).all()
            target_id = next((item.id for item in target if normalized_origin(item.origin) == normalized_origin(request.pretty_url)), None)
            if db.get(Project, project_id) is None: return
            params = json.dumps(parse_qs(parsed.query))
            entry = TrafficEntry(id=flow.metadata["websentinel_id"], project_id=project_id, target_id=target_id,
                timestamp=datetime.now(timezone.utc), method=request.method, url=request.pretty_url[:16384],
                hostname=request.host[:255], path=(parsed.path or "/")[:8192], query_params=params[:16384],
                http_version=request.http_version, request_headers=self._safe_headers(request.headers),
                request_body=self._body(request), request_size=len(request.raw_content or b""))
            entry.parent_id = flow.metadata.get("websentinel_parent_id") or None
            entry.repeater_name = "Repeater" if entry.parent_id else ""
            db.add(entry); db.commit()
        finally: db.close()

    def response(self, flow: http.HTTPFlow) -> None:
        try: self._finish(flow)
        except Exception: pass

    def error(self, flow: http.HTTPFlow) -> None:
        try: self._finish(flow, str(flow.error) if flow.error else "upstream error")
        except Exception: pass

    def _finish(self, flow: http.HTTPFlow, error: str = "") -> None:
        entry_id = flow.metadata.get("websentinel_id")
        if not entry_id: return
        from app.models import TrafficEntry
        db = self._session()
        try:
            entry = db.get(TrafficEntry, entry_id)
            if entry is None: return
            response = flow.response
            if response:
                entry.status_code = response.status_code
                entry.response_headers = self._safe_headers(response.headers)
                entry.response_body = self._body(response)
                entry.response_size = len(response.raw_content or b"")
                entry.content_type = response.headers.get("content-type", "")[:255]
            entry.duration_ms = round((time.monotonic() - flow.metadata.get("websentinel_started", time.monotonic())) * 1000, 2)
            entry.error = error[:2000]
            db.commit()
        finally: db.close()

    def http_connect(self, flow: http.HTTPFlow) -> None:
        # CONNECT is checked before mitmproxy opens the upstream socket or
        # performs TLS certificate sniffing, so an out-of-scope HTTPS host is
        # never contacted as a side effect of inspecting the tunnel.
        requested_origin = normalized_origin(f"https://{flow.request.host}:{flow.request.port}")
        if requested_origin not in self.allowed_origins:
            self._block(flow)

    @staticmethod
    def _block(flow: http.HTTPFlow) -> None:
        flow.response = http.Response.make(
            403,
            b"WebSentinel proxy blocked this request: destination is outside the configured project scope.\n",
            {"Content-Type": "text/plain; charset=utf-8", "X-WebSentinel-Scope": "blocked"},
        )

    def running(self) -> None:
        # Signal readiness only after mitmproxy has successfully brought its
        # listener up. A successful TCP connect alone can hit another process
        # that already owns the requested port.
        ready_file = os.environ.get("WEBSENTINEL_PROXY_READY_FILE")
        if ready_file:
            Path(ready_file).write_text("ready", encoding="ascii")


try:
    _origins = json.loads(os.environ.get("WEBSENTINEL_PROXY_ALLOWED_ORIGINS", "[]"))
except (TypeError, ValueError):
    _origins = []
addons = [ScopeEnforcementAddon(_origins if isinstance(_origins, list) else [])]
