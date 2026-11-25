# WebSentinel development plan

This plan is reconstructed from the requested scope because `DEVELOPMENT_PLAN.md` and `TASKS.md` were not present in this checkout. Work is delivered one phase at a time; a phase is complete only after its tests and a practical local verification pass.

## Current baseline

- Phase 1: architecture, SQLite entities, REST API boundaries, and security decisions are documented in `ARCHITECTURE.md`.
- Phase 2: Electron + React + FastAPI shell, persisted projects/targets, backend origin scope check, and database-backed dashboard exist. Tests are in `backend/tests/`.
- The target use case is an explicitly configured local OWASP crAPI instance. WebSentinel must not send test traffic to unconfigured or external targets.

## Delivery phases

### Phase 3 — HTTP/HTTPS Proxy (complete)

- Integrate mitmproxy as the interception engine; do not reimplement TLS interception.
- Start/stop and inspect proxy status through the backend API.
- Bind only to loopback; default to `127.0.0.1:8080`.
- Require a project with at least one configured target before starting.
- Enforce configured target origins in the proxy request hook; return a local 403 for out-of-scope requests before forwarding.
- Store the generated mitmproxy CA under the app data directory and offer explicit PEM download. Never install it into a browser or OS trust store.
- Verify HTTP forwarding, HTTPS CONNECT/TLS (using an explicitly trusted test CA in a local fixture), scope blocking, startup failure, and clean stop.

Outcome: see `docs/phase-3.md`. The proxy was also exercised against the locally running crAPI over HTTP and blocked an unconfigured origin. Traffic persistence is intentionally deferred to Phase 4.

### Phase 4 — Traffic history, inspector, and repeater (in progress)

- [x] Persist bounded request/response metadata and bodies with project/target association and timestamps.
- [x] Add searchable/filterable traffic history and structured request/response views.
- [x] Stream traffic updates through Server-Sent Events; redact sensitive headers and common body fields.
- [ ] Verify full crAPI browser workflow and persisted restart behavior in the desktop app.
- [ ] Add bounded/cancellable request repeater with backend scope enforcement.
- [x] Add body size bounds and redact common credentials/secrets from capture storage and headers.

### Phase 5 — Crawler, scope management, and passive scanner

- Add URL normalization, include/exclude patterns, host policy, and server-side scope enforcement shared by proxy, crawler, and repeater.
- Crawl only explicitly scoped origins with URL/depth caps, delay, timeout, duplicate suppression, cancellation, and same-origin redirect checks.
- Run passive checks only against observed traffic; label evidence as potential/confirmed and store evidence/remediation metadata.
- Verify with local fixtures and crAPI only; no automated external target tests.

### Phase 6 — Active scanner

- Keep disabled by default; require explicit user confirmation per scan.
- Permit only configured scope, bound requests and rate, support immediate cancellation, and use non-destructive checks.
- Never perform exploitation, persistence, destructive actions, or SSRF probes to private destinations outside explicit local-lab authorization.
- Record method, evidence, confidence, and limitations for each result.

### Phase 7 — Reports and release hardening

- Add finding lifecycle and HTML/JSON/CSV/PDF reports.
- Add migrations before deployed schema evolution, packaging, local vulnerable-lab instructions, and full regression/security tests.

## Phase acceptance

Each phase updates `TASKS.md` and this plan with actual outcomes. Tests must use temporary databases and local-only fixtures. No phase is marked complete based on compilation alone; its primary user flow must also be exercised.
