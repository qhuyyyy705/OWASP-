# Phase 3 — HTTP/HTTPS proxy

## Delivered

- Integrated mitmproxy 12.3.x (`mitmdump`) as the proxy engine.
- Added backend start, stop, and status endpoints. The listener binds only to `127.0.0.1`, defaults to port 8080, and refuses ports below 1024.
- Starting requires a project with at least one configured target origin.
- Added mitmproxy `http_connect` scope enforcement so out-of-scope HTTPS destinations are rejected before an upstream connection or TLS certificate lookup. The request hook also rejects out-of-scope HTTP requests.
- CA material is kept in the per-user WebSentinel data directory. The API provides an explicit PEM download; it never installs the certificate into a browser or OS trust store.
- Added Proxy UI for project selection, start/stop, status, listener details, and CA download instructions.

## Verification

- Backend suite: **6 passed**. It includes unit checks for origin normalization and blocking, API validation, occupied-port startup failure, and an integration test that forwards HTTP and HTTPS to local test servers, validates the generated proxy CA, rejects out-of-scope HTTP and HTTPS, and stops the listener.
- Frontend production build: passed (Vite 6.4.6, 1,579 modules); Electron main/preload/launcher syntax checks passed.
- `npm audit`: **0 vulnerabilities**.
- Electron UI displayed the Proxy controls and a live `Running` status.
- Manual localhost crAPI check: `GET http://localhost:8888/` through `127.0.0.1:8080` returned **200**. A request to an unconfigured port was rejected locally with **403**.

## Limits carried forward

- Traffic is not yet stored in WebSentinel's database. There is no History page or Request/Response Inspector in this phase.
- CA download requires the user to import it into a disposable test browser profile; WebSentinel does not alter trust settings.
- Proxy scope currently matches configured scheme, hostname, and port. Include/exclude rules, DNS/IP pinning, crawl/repeater scope policy, and traffic retention limits belong to later phases.
- HTTPS interception was verified with a local CA-signed HTTPS fixture. crAPI in this workspace was accessed over HTTP.
- The backend test client currently emits a Starlette deprecation warning recommending `httpx2`; tests pass, but update the test-client dependency before that integration changes upstream.
