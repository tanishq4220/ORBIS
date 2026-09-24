# 🛰️ ORBIS — Space Domain Awareness (SDA) Platform

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/tanishq4220/ORBIS)

Production-grade Space Domain Awareness platform featuring high-fidelity orbital propagation, geometric conjunction screening, ACI pipeline confidence metrics, machine-learning risk assessment, and an interactive 3D Earth-orbit visualization cockpit.

* **Live Demo**: [https://orbis-sda-3wrw.onrender.com](https://orbis-sda-3wrw.onrender.com)
* **Demo Credentials**: `operator@orbis.local` / `ORBIS-DEMO-2026`
* **Hackathon Submission Brief**: See [SUBMISSION.md](file:///d:/upadated%20orbis/SUBMISSION.md) for complete project documentation, pitch outline, tech stack, and demonstration guides.

---

## 🚀 One-Click Production Deployment

Deploy ORBIS directly to Render with automated TLS/HTTPS and zero configuration:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/tanishq4220/ORBIS)

1. Click the **Deploy to Render** button above (or open `https://render.com/deploy?repo=https://github.com/tanishq4220/ORBIS`).
2. Click **Apply** on the Blueprint page.
3. Render automatically provisions the web service from the included `render.yaml` and `Dockerfile`, runs the health check at `/api/health`, and provides your live permanent HTTPS URL (e.g. `https://orbis-sda.onrender.com`).

---

## 🏛️ Architecture & Verification

* **Backend**: FastAPI 0.141+ with async lifespan, MongoDB driver with in-memory `LocalDB` fallback, and cookie-based PBKDF2/bcrypt authentication.
* **Frontend**: React 19 + TypeScript SPA built with Vite and Tailwind, mounted directly as a unified single-origin application in production.
* **Astrodynamics & Propagation**: SGP4 TEME propagation, GMST rotation to ECEF, geodetic WGS84 conversion, and Three.js visualization coordinate pipeline.
* **SP3 Ground Truth Validation**: Validated against GPS precise ephemerides with sub-millimeter geodetic coordinate transformations (`test_sp3_integration.py`).
* **Conjunction Screening**: Optimized spatial screening completing full catalog evaluation in <1.5s, with explicit geometric method disclosures and zero uncalibrated collision probability claims.
* **Cryptographic Security**: CSPRNG password reset tokens with SHA-256 DB hashing and strict expiration lifecycles; SSRF guard with private IP rejection.
* **Test Suite**: 51 comprehensive tests spanning SP3 integration, authentication security, screening disclosures, catalog reconciliation, and visual ports.

---

## 🛠️ Local Development

### Requirements
* Python 3.11+
* Node.js 20+

### Setup & Run
```bash
# 1. Install frontend dependencies and build SPA
cd frontend
npm install
npm run build
cd ..

# 2. Install backend dependencies and run API server
pip install -r backend/requirements.txt
cd backend
python -m uvicorn server:app --host 127.0.0.1 --port 8001
```

### Running Test Suite
```bash
python -m pytest tests/ backend/tests/ -v --tb=short
```

---

## 📄 License
MIT License — Copyright (c) 2026 Tanishq40
