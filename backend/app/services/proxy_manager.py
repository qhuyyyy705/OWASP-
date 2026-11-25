from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


class ProxyManager:
    """Owns one local mitmdump subprocess and its per-run scope configuration."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._process: subprocess.Popen | None = None
        self._host = "127.0.0.1"
        self._port = 8080
        self._project_id: int | None = None
        self._started_at: str | None = None

    @property
    def conf_dir(self) -> Path:
        explicit = os.getenv("WEBSENTINEL_DATA_DIR")
        if explicit:
            root = Path(explicit).expanduser()
        elif os.name == "nt":
            root = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming")) / "WebSentinel"
        else:
            root = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "WebSentinel"
        return root / "mitmproxy"

    @property
    def ca_file(self) -> Path:
        return self.conf_dir / "mitmproxy-ca-cert.pem"

    def _running_process(self) -> subprocess.Popen | None:
        if self._process is not None and self._process.poll() is not None:
            self._process = None
            self._project_id = None
            self._started_at = None
        return self._process

    def status(self) -> dict:
        with self._lock:
            process = self._running_process()
            return {
                "running": process is not None,
                "host": self._host,
                "port": self._port,
                "project_id": self._project_id,
                "started_at": self._started_at,
                "ca_available": self.ca_file.is_file(),
            }

    def start(self, project_id: int, allowed_origins: list[str], host: str = "127.0.0.1", port: int = 8080) -> dict:
        if host != "127.0.0.1":
            raise ValueError("The proxy may only bind to 127.0.0.1")
        if not allowed_origins:
            raise ValueError("Configure at least one target origin before starting the proxy")
        with self._lock:
            if self._running_process() is not None:
                raise RuntimeError("The proxy is already running")
            mitmdump = Path(sys.executable).with_name("mitmdump.exe" if os.name == "nt" else "mitmdump")
            addon = Path(__file__).resolve().parent.parent / "proxy" / "addon.py"
            if not mitmdump.is_file():
                raise RuntimeError("mitmproxy is missing from the active Python environment")
            self.conf_dir.mkdir(parents=True, exist_ok=True)
            environment = os.environ.copy()
            environment["WEBSENTINEL_PROXY_ALLOWED_ORIGINS"] = json.dumps(allowed_origins)
            from app.core.config import DATABASE_URL
            environment["WEBSENTINEL_DATABASE_URL"] = DATABASE_URL
            environment["WEBSENTINEL_PROJECT_ID"] = str(project_id)
            environment["WEBSENTINEL_BODY_LIMIT"] = os.getenv("WEBSENTINEL_BODY_LIMIT", "65536")
            ready_file = self.conf_dir / f"proxy-ready-{uuid.uuid4().hex}.tmp"
            environment["WEBSENTINEL_PROXY_READY_FILE"] = str(ready_file)
            command = [
                str(mitmdump), "-q", "--mode", "regular", "--listen-host", host,
                "--listen-port", str(port), "--set", f"confdir={self.conf_dir}", "-s", str(addon),
            ]
            upstream_ca = environment.get("WEBSENTINEL_PROXY_UPSTREAM_CA")
            if upstream_ca:
                ca_path = Path(upstream_ca).expanduser()
                if not ca_path.is_file():
                    raise ValueError("Configured upstream CA file does not exist")
                command.extend(["--set", f"ssl_verify_upstream_trusted_ca={ca_path}"])
            try:
                process = subprocess.Popen(
                    command, cwd=Path(__file__).resolve().parents[2], env=environment,
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
            except OSError as exc:
                raise RuntimeError(f"Could not start mitmproxy: {exc}") from exc
            self._process = process
            self._host, self._port, self._project_id = host, port, project_id
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    self._process = None
                    self._project_id = None
                    ready_file.unlink(missing_ok=True)
                    raise RuntimeError("mitmproxy exited during startup; check the port and proxy configuration")
                if ready_file.is_file():
                    ready_file.unlink(missing_ok=True)
                    self._started_at = datetime.now(timezone.utc).isoformat()
                    return self.status()
                time.sleep(0.05)
            ready_file.unlink(missing_ok=True)
            self.stop()
            raise RuntimeError("Timed out waiting for mitmproxy to listen")

    def stop(self) -> dict:
        with self._lock:
            process = self._running_process()
            if process is not None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
            self._process = None
            self._project_id = None
            self._started_at = None
            return self.status()


proxy_manager = ProxyManager()
