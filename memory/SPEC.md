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

## SIH workstation upgrade
- Routed UI now uses WorkstationShell and CommandDashboard, CatalogWorkspace, ObjectWorkspace, ScreeningWorkspace, HistoryWorkspace, AciWorkspace, AnalyticsWorkspace, RiskWorkspace, SettingsWorkspace and RegisterWorkspace. Previous screens remain unrouted source, not an alternative data source.
- All scientific client paths pass through the typed `/api/data/*` gateway; local mode dispatches the EXISTING `/api/*` scientific handlers, never a second implementation. `/api/summary` is canonical across dashboard, catalog totals, ACI and analytics. Impossible count reconciliation raises an explicit integrity error; error states withhold stale data.
- Per-operator connection settings are stored in Mongo. Local/hosted backend is default. Remote ORBIS-compatible public HTTP/HTTPS origins support test/save/reset via `/api/connection`. Proxy validates all DNS answers, pins TCP to a validated public address retaining TLS SNI, disallows redirects/private/reserved hosts and nonstandard ports, limits body/response sizes, and never forwards local cookies/authentication. Local auth/geography/image provenance remain local. Private laptop localhost requires a public tunnel, not direct server-side access.
- Persistent local operator accounts use unique email/id indexes and individual salts with PBKDF2 hashes; name/email are also signed into the existing HTTP-only session. Registered name survives refresh and later login. Forgot-password remains an honest administrator-assisted local recovery page (no email delivery claim).
- Earth surface is the visual-only Earth3D port documented below, with static day/night/cloud maps and atmosphere. Surface UVs, Natural Earth labels and backend globe_xyz share the ECEF axis convention; camera auto-orbit rotates the VIEW, not Earth independently of the catalog. Solar lighting is approximate server-provided visual context, not a propagated orbit.
- Catalog rendering is one buffer point cloud of valid backend samples with camera distance attenuation, satellite/debris layers, hover, selection and a real trajectory line. No per-object DOM nodes. Geography draws generalized country/admin borders; labels are culled by horizon, zoom and screen overlap, capped at 12. Natural Earth 50m admin coverage is limited by the source.
- Renderer lifecycle fix: texture Suspense is inside the persistent Canvas rather than unmounting its WebGL context; demand rendering and vertex-derived texture UVs reduce idle GPU load. Context interruption has a visible restore action rather than a blank surface.
- Selection is in Zustand and shared by globe, intelligence tabs, state, telemetry and screening target. Every object detail uses the route ID. Global search is debounced and queries the backend, as do catalog filters/sorting (40 rows/page).
- Telemetry replays actual returned UTC samples at 1x/10x/100x/1000x with play/pause/steps/scrub/live. At sparse sampling rates the marker holds until the next actual sample; no interpolated science values. Other catalog points are explicitly hidden during selected-object replay to avoid mixing epochs. The line uses the existing trajectory endpoint, anchored to telemetry start.
- Object visuals: Hubble ID 20580 plus a matching mission name maps to verified NASA/ESA archival photograph heic0908c (19 May 2009). All unverified identities use an explicit REPRESENTATIVE OBJECT MODEL; image failures fall back rather than imply identity. No generated art is labeled as photography.
- Configurable SGP4 screening retains defaults 10min/60min/50km/top10. Full original results were already persisted and remain intact; storage now rejects overwrites and uses a locked atomic history index. Empty secondary propagation is ERROR, never CLEAR. History opening is GET-only, pages original rows and can download the complete original JSON.
- Reliability UI displays real model confidence, ML class, age, consistency, ACI and decision with calibrated-prototype/independent-validation caveats. Null prediction error says N/A / No valid live/reference comparison available. No frontend ACI, ML, SGP4 or separation calculations.

### Earth3D visual-only integration
- `components/globe/Earth3DSurface.tsx` and `earth3dShaders.ts` port the day/night blending, cloud mask, Fresnel atmosphere and transparent atmospheric shell from mitchcamza/Earth3D revision `1d151516f8041e5bec91aee83f7d8261e9f6604d`; ocean specular reflection uses the upstream packed mask. Three image assets are served locally from `public/assets/earth3d/`, not third-party runtime URLs. Surface is radius 1; atmosphere is radius 1.025. Antialiasing is enabled with DPR capped at 1.5, and the existing demand-rendered Canvas is retained.
- `EarthGlobe.tsx` swaps the visual surface, enables bounded renderer quality, exposes texture attribution, and explicitly requests frames while camera auto-rotation is active. This fixes the existing auto-rotation freeze under demand rendering; paused views retain demand rendering. No backend/API/model/auth/database/layout/timeline/store changes. Real bulk catalog GPU points, IDs, satellite/debris colors, screening highlights, selection, actual trajectories, and zoom-dependent geography are unchanged.
- ECEF registration remains `x = r cos(lat) cos(lon)`, `y = r sin(lat)`, `z = r cos(lat) sin(lon)`. Only sphere texture U is mirrored (`1 - uv.x`). No frontend propagation, scientific recomputation, object-coordinate rotation, random science values, standalone 23.5-degree tilt or artificial Earth spin. Existing camera auto-rotation provides motion without slipping the map under tracked objects.
- Existing `/environment` supplies solar illumination at the selected live/replay epoch. Clouds/night lights are explicitly archival visual context, not live weather. Replay still renders only real returned samples, hides the other catalog points, and returns to live using the unchanged existing store/data hooks.

### Visual source provenance
- Active Earth3D surface/cloud/night/specular textures: https://github.com/mitchcamza/Earth3D (pinned revision above). Solar System Scope CC BY 4.0 textures and James Hastings-Trew specular mapping are credited in `/assets/earth3d/ATTRIBUTION.txt`, linked from the globe legend; shader techniques credited upstream to Bruno Simon's Three.js Journey.
- Previous NASA Blue Marble/three-globe/Three.js texture files remain preserved on disk, but the active globe uses the Earth3D assets.
- Natural Earth public-domain `ne_110m_admin_0_countries`, `ne_50m_admin_1_states_provinces`, `ne_110m_populated_places`.
- Verified Hubble photograph: https://esahubble.org/images/heic0908c/ (NASA/ESA).