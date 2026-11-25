# Phase 2 implementation notes

Implemented: secure Electron window defaults, React/TypeScript dashboard, live API status, SQLite-backed projects and target origins, server-side target-origin scope check, and database-backed project/target/finding counts. The dashboard intentionally shows empty states for traffic, activity, and findings until those capabilities store real records.

Not implemented: authentication, migrations, proxy, request history, crawler, scanner, reports, WebSocket updates, application settings, and installer. The current SQLite schema is initialized with SQLAlchemy `create_all`; add Alembic migrations before changing deployed schemas.

Local scope behavior currently allows URLs sharing the configured target scheme, hostname, and port. It does not perform network requests. Outbound modules must add DNS/IP resolution checks and revalidate scope at execution time to mitigate DNS rebinding and SSRF.
