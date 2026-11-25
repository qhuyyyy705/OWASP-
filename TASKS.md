# WebSentinel task board

Status is updated at the end of each phase. Unchecked tasks are not implemented.

## Phase 1 — Architecture

- [x] Document modules, data boundaries, API, and security decisions in `ARCHITECTURE.md`.

## Phase 2 — Core application

- [x] Electron, React/TypeScript, FastAPI, and SQLite foundation.
- [x] Persist projects and target origins; implement backend origin scope check.
- [x] Use stored data in dashboard; show honest empty/not-implemented states.
- [x] Add API integration tests and verify the desktop shell locally.

## Phase 3 — HTTP/HTTPS Proxy (complete)

- [x] Integrate mitmproxy and manage proxy lifecycle through API.
- [x] Bind proxy to loopback and require a configured project target.
- [x] Enforce target-origin scope before proxy forwarding.
- [x] Export generated CA explicitly without installing it.
- [x] Add proxy API, addon, and integration tests.
- [x] Launch the desktop and verify local HTTP forwarding and scope rejection.
- [x] Update docs with observed results and remaining limitations.

## Phase 4 — Traffic history, inspector, repeater (in progress)

- [x] Persist proxy traffic with bounded bodies and project/target association.
- [x] Implement history search/filter and request/response inspector.
- [x] Stream updates and support clear, pause/resume, project/method/status filters.
- [x] Redact sensitive headers and common JSON/form secrets; omit common binary media.
- [ ] Verify full crAPI browser workflow and restart persistence in the desktop app.
- [x] Add tests for stored history endpoints and real proxy capture.
- [ ] Run backend and frontend test/build suites in a functioning Python/Node environment; verify actual crAPI desktop workflow.
- [ ] Implement repeater with backend scope enforcement.

## Phase 5 — Crawler, scope management, passive scanner

- [ ] Add include/exclude patterns and shared backend scope policy.
- [ ] Implement bounded/cancellable same-scope crawler.
- [ ] Implement passive scanner with evidence and confidence.
- [ ] Add local fixture tests for crawl bounds, redirects, scope, and passive rules.

## Phase 6 — Active scanner

- [ ] Default disabled; require explicit confirmation and enforce scope in backend.
- [ ] Add non-destructive bounded modules, rate limits, request caps, and immediate stop.
- [ ] Verify with local lab fixtures only.

## Phase 7 — Reports and release

- [ ] Finding workflow, exports, migrations, packaging, documentation, and full regression suite.
