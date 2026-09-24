# 🛰️ ORBIS — Hackathon Project Submission

> **Orbital Risk & Behaviour Intelligence System (ORBIS)**  
> *Production-Grade Space Domain Awareness (SDA) & Orbital Traffic Management Platform*

---

## 1. Working Prototype / Product

* **Live Deployment URL**: [https://orbis-sda-3wrw.onrender.com](https://orbis-sda-3wrw.onrender.com)
* **Status**: Fully Operational & Publicly Accessible (HTTPS/TLS)
* **Operator Credentials**:
  * **Email**: `operator@orbis.local`
  * **Password**: `ORBIS-DEMO-2026`
* **Core Interactive Capabilities**:
  1. **Global 3D Orbital Surveillance Cockpit**: Real-time Earth-Centered, Earth-Fixed (ECEF) globe rendering 18,588 validated SGP4 orbital states.
  2. **Authoritative 18,693-Object Catalog**: Server-side pagination, search, classification (Satellites vs. Orbital Debris), and health metrics.
  3. **High-Speed Geometric Conjunction Screening**: Evaluates full catalog conjunctions against target spacecraft in <1.5s with golden-section Time of Closest Approach (TCA) refinement.
  4. **Adaptive Confidence Index (ACI) Workspace**: Transparent four-factor orbital reliability scoring with dynamic factor re-normalization.
  5. **Machine Learning Risk Assessment**: Calibrated Random Forest model evaluating orbital decay and data degradation.
  6. **Interactive Telemetry Replay**: Replays propagated orbital states with altitude profiles and orbit visibility toggles.

---

## 2. Project Description

### Executive Summary
With over 45,000 tracked objects in Low Earth Orbit (LEO) and millions of untracked fragments, orbital congestion poses an existential threat to space infrastructure. Traditional Space Situational Awareness (SSA) tools often suffer from stale two-line element (TLE) sets, unquantified propagation uncertainties, and slow conjunction analysis pipelines.

**ORBIS** is a production-grade Space Domain Awareness workstation that bridges real-time astrodynamics with calibrated machine learning and transparent uncertainty quantification.

### The Problem
* **Uncertainty Blindness**: Operators frequently make critical collision avoidance maneuver decisions using outdated orbital observations without knowing the error bounds.
* **Fabricated Metrics**: Prototype systems often report uncalibrated "Collision Probability ($P_c$)" without true covariance matrices, leading to dangerous false confidence.
* **Computational Bottlenecks**: Full-catalog pairwise proximity screening traditionally takes minutes or hours, limiting agility during time-critical conjunction events.

### The ORBIS Solution
1. **Adaptive Confidence Index (ACI)**: Evaluates evidence quality across four independent scientific dimensions:
   * **Data Age**: Models TLE epoch temporal decay.
   * **Trajectory Consistency**: Measures SGP4 orbital arc stability and curvature consistency.
   * **SP3 Reference Ephemeris Validation**: Ground-truth validation against high-precision IGS GPS ephemeris.
   * **Calibrated Machine Learning**: An ensemble Random Forest model producing well-calibrated reliability probabilities.
2. **Dynamic Factor Re-normalization**: Unlike naive systems that fabricate missing data or fail silently, ORBIS mathematically re-weights remaining valid factors when reference ephemerides are legitimately unavailable (e.g., non-GPS objects).
3. **Optimized Spatial Conjunction Screening**: Propagates and screens the entire 18,693-object catalog in under 1.5 seconds, refining closest approach timestamps with golden-section search while explicitly disclosing geometric proximity limitations.

---

## 3. Source Code & Repository

* **GitHub Repository**: [https://github.com/tanishq4220/ORBIS](https://github.com/tanishq4220/ORBIS)
* **Production Branches**: `main` and `repair/production` (fully synchronized)
* **Submission Archive**: `ORBIS_Hackathon_Submission.zip` (clean 26.68 MB archive containing complete source code, models, and assets).

### Repository Directory Structure
```
ORBIS/
├── ACI/                          # Adaptive Confidence Index Pipeline
│   ├── run.py                    # ACI calculation engine & data pipeline
│   ├── engine.py                 # Factor aggregation & re-normalization
│   ├── factors.py                # Mathematical formulation of factors
│   ├── sp3_integration.py        # SP3 ephemeris temporal interpolation
│   └── aci_output.csv            # Pre-computed 18,693-object confidence dataset
├── backend/                      # FastAPI Python Web Backend
│   ├── server.py                 # ASGI entrypoint & route handlers
│   ├── catalog.py                # Thread-safe in-memory catalog store
│   ├── screening.py              # Geometric conjunction engine & TCA search
│   ├── propagate.py              # SGP4, TEME, GMST, ECEF astrodynamics
│   ├── history.py                # Screening history persistence
│   ├── lib/                      # Auth, session cookies, database adapters
│   ├── models/                   # Pydantic schemas
│   └── tests/                    # Backend automated test suite
├── frontend/                     # React 19 + TypeScript SPA
│   ├── src/
│   │   ├── pages/                # Mission Control, Catalog, Screening, ACI
│   │   ├── components/           # 3D Globe, Navigation, Primitives
│   │   └── lib/                  # API client, state stores, math utilities
│   └── dist/                     # Optimized production bundle
├── ml/                           # Machine Learning Reliability Model
│   ├── features.py               # 6-dimensional orbital feature extractor
│   ├── predict_model.py          # Calibrated inference engine
│   └── random_forest_calibrated.joblib  # 400-tree isotonic calibrated model
├── Dockerfile                    # Single-stage container definition
├── render.yaml                   # Render Cloud deployment blueprint
└── SUBMISSION.md                 # Hackathon submission documentation
```

---

## 4. Project Documentation

### Scientific & Astrodynamic Methodology
1. **Coordinate Frame Transformations**:
   * TLE orbital elements $\rightarrow$ SGP4 propagation $\rightarrow$ **TEME** (True Equator, Mean Equinox).
   * **TEME $\rightarrow$ ECEF**: Computed via Greenwich Mean Sidereal Time (GMST) rotation $\theta_{GMST}$:
     $$\begin{pmatrix} X_{ECEF} \\ Y_{ECEF} \\ Z_{ECEF} \end{pmatrix} = \begin{pmatrix} \cos\theta & \sin\theta & 0 \\ -\sin\theta & \cos\theta & 0 \\ 0 & 0 & 1 \end{pmatrix} \begin{pmatrix} X_{TEME} \\ Y_{TEME} \\ Z_{TEME} \end{pmatrix}$$
   * **ECEF $\rightarrow$ Geodetic**: WGS-84 reference ellipsoid ($a = 6378.137\text{ km}, f = 1/298.257223563$).
2. **TCA Golden-Section Optimization**:
   * Initial coarse step interval of 10 minutes identifies candidate encounter windows.
   * Golden-section interval contraction:
     $$\Delta t_{n+1} = \frac{\sqrt{5}-1}{2} \Delta t_n \approx 0.618034 \Delta t_n$$
   * Converges to sub-second closest approach timestamp and minimum separation distance.
3. **Rigorous Test Suite**:
   * **61 Automated Tests**: Covers SP3 interpolation, regression bounds (<50 km magnitude guards), cryptographic tokens, SSRF protection, and catalog reconciliation.
   * Run command: `python -m pytest tests/ backend/tests/ -v --tb=short` (100% pass rate).

---

## 5. Demonstration Video

* **Video Walkthrough Guide**:
  1. **0:00 - 0:45**: Introduction to Space Domain Awareness challenges & ORBIS architecture.
  2. **0:45 - 1:45**: Mission Control Dashboard — Live 3D Earth, real-time SGP4 propagation of 18,693 cataloged objects.
  3. **1:45 - 2:45**: Conjunction Screening Engine — Live screening of the International Space Station (NORAD 25544) against the full catalog with sub-second TCA refinement.
  4. **2:45 - 3:45**: Scientific Transparency — ACI Insights, dynamic uncertainty re-normalization, and calibrated Random Forest predictions.
  5. **3:45 - 4:30**: Production Security & Conclusion.
* **Video Link**: *(Add your recorded YouTube / Loom / Google Drive link here)*

---

## 6. Presentation / Pitch Deck

* **Slide 1**: Title & Mission — ORBIS: Autonomous Space Domain Awareness & Orbital Intelligence
* **Slide 2**: The Orbital Crisis — The Kessler syndrome risk and astronomical growth of LEO debris
* **Slide 3**: The Core Bottleneck — Stale observations, fake $P_c$ calculations, and computational delays
* **Slide 4**: Scientific Innovation 1 — SGP4 to ECEF Astrodynamics with Golden-Section TCA refinement
* **Slide 5**: Scientific Innovation 2 — The Adaptive Confidence Index (ACI) with dynamic factor re-normalization
* **Slide 6**: Scientific Innovation 3 — Calibrated ML reliability prediction using 400-tree Random Forest
* **Slide 7**: Live Product Demonstration — Walkthrough of the operational cloud platform
* **Slide 8**: System Architecture & Security — Single-origin FastAPI + React 19, zero-trust SSRF guards
* **Slide 9**: Roadmap & Future Expansion — Covariance ingestion from Space-Track, optical sensor integration
* **Slide 10**: Team & Summary — Conclusion and Q&A

---

## 7. Technology Stack

| Layer | Technologies |
|---|---|
| **Astrodynamics & Physics** | SGP4, WGS-84 Geodetics, TEME/ECEF Matrix Transformations, IGS SP3 Precise Ephemeris |
| **Backend API** | Python 3.11, FastAPI, Uvicorn, Pydantic v2, Starlette Concurrency Threadpool |
| **Machine Learning** | Scikit-Learn, Random Forest (400 estimators), Isotonic Regression Calibration, NumPy, Pandas |
| **Frontend UI** | React 19, TypeScript, Vite, Tailwind CSS, Three.js 3D WebGL, Lucide Icons, TanStack Query |
| **Security & Auth** | CSPRNG Password Resets (SHA-256), Cookie-based PBKDF2/bcrypt, SSRF Private IP Guards |
| **Deployment & Ops** | Docker, Render Cloud Web Services, Cloudflare TLS Ingress, Pytest Automated Testing |

---

## 8. Demo & Deployment Links

* **Live Cloud Application**: [https://orbis-sda-3wrw.onrender.com](https://orbis-sda-3wrw.onrender.com)
* **GitHub Repository**: [https://github.com/tanishq4220/ORBIS](https://github.com/tanishq4220/ORBIS)
* **Demo Operator Login**:
  * **Email**: `operator@orbis.local`
  * **Password**: `ORBIS-DEMO-2026`
* **Local Submission Archive**: `ORBIS_Hackathon_Submission.zip` in repository root
