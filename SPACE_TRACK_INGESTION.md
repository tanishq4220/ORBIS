# Space-Track.org TLE Ingestion Guide

This document outlines the architecture, authentication, query protocols, and data pipelines for ingesting ground-truth Two-Line Element (TLE) sets from [Space-Track.org](https://www.space-track.org) into ORBIS.

---

## 1. Overview & Operational Role

ORBIS relies on accurate orbital elements to drive:
1. **SGP4 Ephemeris Propagation** (TEME/ECEF state coordinates)
2. **Awareness and Confidence Index (ACI)** Pipeline (temporal data age decay, trajectory consistency)
3. **Geometric Conjunction Screening** (closest approach distance & TCA)

While the prototype uses a curated Excel snapshot (`satellite_debris_tle (2).xlsx`), a production SDA environment requires continuous, authenticated ingestion from the 18th Space Defense Squadron via Space-Track.org.

---

## 2. Authentication & Security Protocols

Space-Track enforces session-based cookie authentication using HTTPS:

- **Endpoint**: `https://www.space-track.org/ajaxauth/login`
- **Method**: `POST`
- **Payload**: `identity=<USERNAME>&password=<PASSWORD>`
- **Response**: Sets a session cookie (`spacetrack_session`) used for subsequent authenticated REST queries.

### Rules of Engagement & Rate Limiting
- **Concurrent requests**: Maximum **20 requests per minute** per account.
- **Bulk queries**: Always prefer batch endpoints over per-object queries.
- **Bandwidth**: Query compressed endpoints (`/format/json` or `/format/tle`) with gzip compression enabled.
- **Credentials**: Store `SPACE_TRACK_USER` and `SPACE_TRACK_PASSWORD` exclusively in environment variables or a secrets manager. Never commit credentials to source control.

---

## 3. Querying & Filter Specifications

Space-Track uses a RESTful URL structure:
```
https://www.space-track.org/basicspacedata/query/class/{CLASS}/[PREDICATES]/[ORDER]/[LIMIT]/format/{FORMAT}
```

### A. Full Active Catalog Ingestion
Fetches the latest TLE for all active, unclassified objects in Earth orbit:
```bash
https://www.space-track.org/basicspacedata/query/class/gp/EPOCH/>now-7/orderby/NORAD_CAT_ID asc/format/json
```

### B. Specific Catalog Ingestion by NORAD IDs
Fetches latest orbital states for specific objects of interest (e.g. GPS constellation + ISS):
```bash
https://www.space-track.org/basicspacedata/query/class/gp/NORAD_CAT_ID/25544,26407,27663,28190,28361,28874,29486,32711,36585,38833,39533/orderby/NORAD_CAT_ID/format/json
```

### C. Conjunction Screening Zone Filter (Orbital Altitude)
Screening LEO objects only (mean motion > 11.25 revs/day, period < 128 min):
```bash
https://www.space-track.org/basicspacedata/query/class/gp/MEAN_MOTION/>11.25/EPOCH/>now-3/format/json
```

---

## 4. Ingestion Pipeline & Schema Mapping

The JSON output from `class/gp` maps directly into ORBIS catalog fields:

| Space-Track Field | ORBIS Field | Type | Description |
|---|---|---|---|
| `NORAD_CAT_ID` | `ID` | string | 5-digit NORAD identifier |
| `OBJECT_NAME` | `Name` | string | Common satellite/payload name |
| `OBJECT_TYPE` | `Type` | string | `PAYLOAD` -> `Satellite`, `DEBRIS` -> `Debris`, `ROCKET BODY` -> `Debris` |
| `TLE_LINE1` | `TLE Line 1` | string | SGP4 Line 1 (69 chars) |
| `TLE_LINE2` | `TLE Line 2` | string | SGP4 Line 2 (69 chars) |
| `EPOCH` | `Epoch` | string (ISO-8601) | TLE epoch UTC |
| Derived | `Data_Age_days` | float | `(now_utc - epoch_utc).total_seconds() / 86400.0` |
| Derived via ML | `Model_Confidence` | float | Calibrated Random Forest confidence |
| Derived via SGP4 | `Trajectory_Consistency` | float | SGP4 position variance across step intervals |
| Derived via SP3 | `Prediction_Error_km` | float | 3D error against SP3 precise orbit |

---

## 5. Sample Automation Script (`ingest_spacetrack.py`)

```python
"""Sample automated Space-Track ingestion script for ORBIS."""
import os
import requests
import pandas as pd
from datetime import datetime, timezone

LOGIN_URL = "https://www.space-track.org/ajaxauth/login"
QUERY_URL = "https://www.space-track.org/basicspacedata/query/class/gp/EPOCH/>now-3/orderby/NORAD_CAT_ID asc/format/json"

def fetch_latest_tles(username: str, password: str) -> pd.DataFrame:
    session = requests.Session()
    
    # Authenticate
    login_resp = session.post(LOGIN_URL, data={"identity": username, "password": password})
    login_resp.raise_for_status()
    
    # Query GP catalog
    query_resp = session.get(QUERY_URL)
    query_resp.raise_for_status()
    data = query_resp.json()
    
    records = []
    for item in data:
        obj_type = item.get("OBJECT_TYPE", "").upper()
        normalized_type = "Satellite" if "PAYLOAD" in obj_type else "Debris"
        
        records.append({
            "ID": item["NORAD_CAT_ID"],
            "Name": item.get("OBJECT_NAME", f"OBJECT {item['NORAD_CAT_ID']}"),
            "Type": normalized_type,
            "TLE Line 1": item["TLE_LINE1"],
            "TLE Line 2": item["TLE_LINE2"],
            "Epoch": item["EPOCH"],
        })
        
    return pd.DataFrame(records)

if __name__ == "__main__":
    user = os.environ.get("SPACE_TRACK_USER")
    pwd = os.environ.get("SPACE_TRACK_PASS")
    if user and pwd:
        df = fetch_latest_tles(user, pwd)
        df.to_excel("satellite_debris_tle_live.xlsx", index=False)
        print(f"Ingested {len(df)} live TLE records from Space-Track.org")
```

---

## 6. Update Frequency & Cadence Strategy

- **LEO Payloads & Active Satellites**: Re-query every **8 to 12 hours** (atmospheric drag causes orbital decay).
- **MEO / GEO Satellites**: Re-query every **24 to 48 hours** (gravitational perturbations dominate, higher orbit stability).
- **Debris Clouds**: Re-query every **12 hours** to update positional uncertainty bounds.
- **Cache Policy**: Store raw TLEs in a local append-only historical database (`ml/data/historical_tle/raw/sat{id}.csv`) to build training sets for long-term ML reliability calibration.
