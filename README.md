# WebSentinel Security Scanner

A local-first desktop application for authorized website security testing, inspired by OWASP ZAP. It includes a loopback mitmproxy, backend-enforced target scope, persistent bounded traffic history, a live History / HTTP Traffic screen, and request/response inspection. Scanner, crawler, repeater, reports, and installer are not implemented.

## Requirements

- Windows 10/11
- Node.js 20+ and npm
- Python 3.12+

Python is not installed in the current development environment. Install Python 3.12+ and ensure `python` is on `PATH` before starting the backend or desktop app.

## Development setup

1. Backend: `cd backend`, create/activate a virtual environment, then `python -m pip install -r requirements-dev.txt` (includes runtime dependencies and test tools).
2. Install desktop dependencies with `npm install` at the repository root and `npm install` in `frontend/`.
3. From the repository root run `npm run desktop:dev`. This starts Vite; Electron launches the local FastAPI service when it opens.

For browser-only frontend development, start the API manually with `python -m uvicorn app.main:app --host 127.0.0.1 --port 8765` from `backend/`, then run `npm run dev` in `frontend/`.

The API docs are at `http://127.0.0.1:8765/docs`. The SQLite file defaults to `backend/websentinel.db`; set `WEBSENTINEL_DB_PATH` to choose another location. Never expose the local API to an untrusted network.

Run the Phase 2 API checks from `backend/` with `.venv\Scripts\python.exe -m pytest tests` (Windows).

## Current features

- Create and list projects and target origins, persisted in SQLite.
- Backend scope check for target origins.
- Dashboard counts backed by the database (no seeded/demo findings).
- Electron secure-window scaffold and navigation shell.
- HTTP/HTTPS intercepting proxy powered by mitmproxy, bound to loopback and restricted to the selected project's target origins.
- Persisted request and response metadata and bounded bodies, live traffic updates, filters, and an inspector. Authorization, cookie, token, password, and secret values are redacted from captured headers and common JSON/form bodies.
- Explicit download of the mitmproxy CA certificate; WebSentinel never installs it automatically.

## Use the local proxy

1. Create a project and add the exact local target origin (for a common crAPI setup, this may be `http://localhost:8888`; use the address and port configured by your own lab).
2. Open **Proxy**, select that project, and start the listener (default `127.0.0.1:8080`). The backend rejects proxy requests that do not match one of that project's configured origins.
3. Configure a dedicated test browser profile to use `127.0.0.1:8080` for HTTP and HTTPS. WebSentinel does not configure browser profiles or system proxy settings.
4. For HTTPS inspection, download `mitmproxy-ca-cert.pem` from the Proxy screen and trust it manually only in the disposable test profile. Remove that trust when finished. Never install it into the operating system's general trust store for routine browsing.
5. In the Proxy screen, choose the configured target and click **Open Target in test browser**. This opens the URL in the system's default browser; that browser must already have the proxy configured. Stop the proxy when the test is done.

Traffic bodies are limited to 64 KiB by default (`WEBSENTINEL_BODY_LIMIT`, maximum 1 MiB); common binary media is omitted. Out-of-scope HTTP requests and HTTPS CONNECT attempts are rejected before upstream connection. HTTPS inspection requires manual CA trust in the disposable test profile.

The browser launch uses the operating system's default external browser, not a managed disposable profile. Confirm its proxy configuration before browsing; do not use a personal browser profile for HTTPS interception.

## Roadmap

See [ARCHITECTURE.md](ARCHITECTURE.md) for modules, API and phased implementation. Sections marked “Not Implemented” are not operational features.
