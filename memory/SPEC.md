# ORBIS Living Spec

## Purpose
ORBIS is a dark aerospace mission-control console for orbital object confidence, SGP4 state, telemetry replay, analytics, and prototype geometric conjunction screening.

## Authoritative data
- Catalog values come from `ACI/aci_output.csv` through `backend/catalog.py`.
- SGP4 state, positions, trajectory, and telemetry come from `backend/propagate.py` and the real TLE catalog.
- ACI and ML fields are displayed, never recalculated, by the frontend.
- Conjunction screening is geometric SGP4 separation only; no collision probability is claimed.

## Key flows
- Signed HTTP-only cookie-session login with demo operator, registration, logout, protected routes, and session survival across backend reloads.
- Login-cookie repair: HTTPS sessions use host-only `Secure; HttpOnly; SameSite=None; Partitioned` cookies for embedded previews, including Chromium with third-party cookies blocked. HTTP local development uses `SameSite=Lax`. Auth responses/requests bypass caches, and login verifies `/api/auth/me` before entering protected routes. Logout expires both partitioned and legacy cookies and resets the query cache/in-memory UI. Browsers blocking all embedded storage receive a new-tab recovery link; tokens are never stored in browser-accessible storage. Scientific modules are unchanged by this repair.
- Dashboard loads `/api/summary`, `/api/health`, and bulk `/api/positions`, rendering one GPU point cloud plus a textured Earth.
- Catalog pages query paginated `/api/objects`; satellites and debris are backend type filters.
- Object detail loads object identity, state, trajectory, and telemetry; replay controls use returned samples.
- Conjunctions POST the fixed default configuration (10 minute step, 60 minute window, 50 km threshold, top 10) and history replays saved full matrices.
- ACI insights, analytics, risk analysis, and settings consume backend responses.

## Data model / roles
Auth users have `id`, `email`, and `name`; there are no roles beyond local operator access. Scientific objects mirror the catalog response fields and optional propagated state.

## Backend shape
All application routes are registered on `api_router` with `/api` prefix in `backend/server.py`. Scientific modules from the uploaded ORBIS project are preserved in `backend/`, `ACI/`, `SGP4/`, and `ml/`.