# Workstation upgrade

Preserve scientific sources, values and algorithms. Existing full_results persistence is already correct.

## Dependency batches
1. Backend: lib/auth.py, lib/db.py, lib/upstream.py; models/workstation.py; routers/auth.py, connection.py, visualization.py; server.py ingress; history.py immutable storage hardening. Matching frontend types in lib/orbis.ts and routing in lib/api.ts. Auth cookies retained.
2. Assets: scripts/prepare_visual_assets.py; static NASA surface, night/cloud composites, verified Hubble photo; Natural Earth country/admin/city data. Credits in Settings and memory/SPEC.md.
3. Frontend core: lib/data.ts, lib/store.ts; ConsolePrimitives.tsx, AppShell.tsx, EarthGlobe.tsx, GeographyLayer.tsx, ObjectVisual.tsx, ObjectIntelligence.tsx, TelemetryConsole.tsx. index.css, index.html.
4. Pages: Dashboard.tsx, CatalogPage.tsx, ObjectDetail.tsx, Conjunctions.tsx, ConjunctionHistory.tsx, AciInsights.tsx, Analytics.tsx, RiskAnalysis.tsx, Settings.tsx, Register.tsx; App.tsx stays routed. Existing login repair preserved.
5. Verification: public API smoke + typecheck + public browser journey. Escalate any failure for full acceptance verification. Update memory/SPEC.md and test_credentials.md.