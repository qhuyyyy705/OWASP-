# WebSentinel architecture and Phase 1–2 plan

## Goals and boundaries

WebSentinel is a local-first desktop application for authorized web security assessment. Phase 2 establishes a working desktop shell, a FastAPI service, persistent SQLite storage, project/target/scope management, and a dashboard based on database data. It does not claim proxy, crawling, or scanning support yet; those features are explicitly reserved for later phases.

## Runtime architecture

```text
Electron main process ── launches local FastAPI child process
        │                    │
  context-isolated       REST API + OpenAPI
  preload bridge              │
        │                 service layer
React + TypeScript ──────── SQLAlchemy ── SQLite
```

The renderer has no Node privileges. Electron uses `contextIsolation`, disables `nodeIntegration`, and exposes only a small typed app-info bridge. The API binds to loopback only. The frontend talks to the API over HTTP; its URL is configured by Vite for development. The backend owns validation and authorization boundaries, including scope checks, so UI controls are never treated as security enforcement.

## Modules

- `frontend/`: React, TypeScript, Vite, Tailwind and Lucide; navigation and dashboard shell.
- `desktop/`: Electron main/preload, secure window defaults, development server integration and backend process lifecycle.
- `backend/app/api/`: versionable REST endpoints and Pydantic contracts.
- `backend/app/core/`: configuration, logging, and URL/scope policy.
- `backend/app/database/`: SQLite engine and session lifecycle.
- `backend/app/models/`: SQLAlchemy persistence entities.
- `backend/app/services/`: application operations separated from HTTP handlers.
- `docs/`: implementation notes and later phase plans.

## Initial data model

Projects own targets. A target has a normalized origin and is the initial allowed scope boundary. Additional include/exclude patterns and explicit allowed/denied hosts can extend this in the scope module. HTTP traffic, scan sessions, findings, crawler results, settings, and logs will be linked to projects in later phases. SQLite database location is configurable via `WEBSENTINEL_DB_PATH`; it is not checked into source control.

## API (Phase 2)

- `GET /api/health`: service status.
- `GET /api/dashboard`: counts from persisted projects, targets, and findings; recent scan activity and charts are empty until those modules exist.
- `GET/POST /api/projects`: list/create projects.
- `GET/POST /api/projects/{id}/targets`: list/add targets.
- `GET /api/scope/check?project_id=…&url=…`: backend scope decision; only the configured target origin is allowed.

FastAPI publishes Swagger/OpenAPI at `/docs`. Inputs are validated with Pydantic, database calls use SQLAlchemy, and unsafe/out-of-scope targets are rejected. The initial API is a local single-user service, not an internet-facing multi-user server.

## Delivery phases

1. **Architecture:** document modules, data model, API and boundaries (this document).
2. **Core application:** establish Electron + React + FastAPI, SQLite persistence, project/target/scope API, database-backed dashboard, navigation and setup instructions.
3. **Proxy:** mitmproxy lifecycle, loopback HTTP/HTTPS interception and project-origin enforcement; CA download remains an explicit user action.
4. **Traffic and Repeater:** persist bounded traffic, request/response inspector and repeater with backend scope checks. Traffic persistence/history is implemented; Repeater remains planned.
5. **Crawler and passive analysis:** managed scope patterns, bounded crawling and passive findings.
6. **Active scanning:** disabled by default; explicit confirmation, strict scope/rate/request limits, cancellation, non-destructive checks.
7. **Management and release:** findings workflow, reports, migrations, regression tests, UI refinement and Windows installer.

Each phase must be implemented and verified before being described as complete. Planned modules are not represented as working features in the UI.

## Key security decisions

- Bind backend to `127.0.0.1`; never expose it on all interfaces by default.
- Scope enforcement is implemented server-side before outbound actions.
- Validate schemes and hostnames; later outbound modules must resolve and reject loopback/private/link-local destinations unless the user explicitly enables a local lab target.
- Never install a proxy CA into the OS/browser automatically; make certificate export an explicit user action.
- Active scanning is disabled by default and must be explicitly confirmed, bounded, non-destructive, and cancellable.
- Do not persist credentials unless required; bound request/response sizes and redact sensitive values in logs.

## Current implementation boundary

The proxy persists allowed requests and responses in `traffic_entries`, scoped to the selected project and matching target. Bodies are size bounded; common binary media is omitted and secret headers plus common JSON/form credential fields are redacted. The History UI reads persisted records and receives updates over Server-Sent Events. HTTPS CONNECT is checked before mitmproxy connects upstream; decrypted HTTP requests then enter the same capture path. Repeater, crawler, passive/active scanners, vulnerability workflow, exports, migrations, and installer are not implemented yet.
