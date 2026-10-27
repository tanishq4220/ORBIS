"""SP3 prediction-error factor for ORBIS ACI.

Compares SGP4-propagated GPS satellite positions against IGS SP3 precise
ephemeris at the SP3 epoch that is closest in time to each TLE epoch.

Design decisions
----------------
* The SP3 epoch is parsed dynamically from sp3_reference.csv — **no hardcoded date**.
* For each GPS object the TLE is propagated to the nearest SP3 timestamp
  (linear interpolation between the two bracketing 15-min records when both
  are present, or the single nearest otherwise).
* Objects without a GPS PRN mapping → NaN, note: "not in GPS constellation"
* Objects with GPS PRN mapping but no temporal overlap (|gap| > 12 h) →
  NaN, note: "no temporally overlapping precise ephemeris"
* ACI re-normalisation of missing factors is handled by engine.calculate_aci
  (existing behaviour — NaN factors are already excluded from the weighted
  average and remaining weights are re-normalised).
"""

import math
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sgp4.api import Satrec, jday

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GPS PRN ↔ NORAD mapping (32 active GPS satellites)
# ---------------------------------------------------------------------------
GPS_PRN_TO_NORAD: dict[str, str] = {
    "PG01": "62339",  # GPS IIIF SV01
    "PG02": "61741",  # GPS IIIF SV02
    "PG03": "46826",  # GPS III SV01
    "PG04": "48859",  # GPS III SV02
    "PG05": "49705",  # GPS III SV03
    "PG06": "50036",  # GPS III SV04
    "PG07": "52306",  # GPS III SV05
    "PG08": "55268",  # GPS III SV06
    "PG09": "57265",  # GPS IIIF
    "PG10": "62340",  # GPS IIIF
    "PG11": "36585",  # GPS IIF-1 SVN63
    "PG12": "38833",  # GPS IIF-2 SVN65
    "PG13": "39533",  # GPS IIF-3 SVN01
    "PG14": "40534",  # GPS IIF-4 SVN67
    "PG15": "40730",  # GPS IIF-5 SVN03
    "PG16": "41019",  # GPS IIF-6 SVN69
    "PG17": "41328",  # GPS IIF-7 SVN41
    "PG18": "41549",  # GPS IIF-8 SVN43
    "PG19": "41860",  # GPS IIF-9 SVN45
    "PG20": "43873",  # GPS IIF-10 SVN47
    "PG21": "44506",  # GPS IIF-11 SVN49
    "PG22": "44864",  # GPS IIF-12 SVN51
    "PG23": "28874",  # GPS IIR-M SVN60
    "PG24": "28190",  # GPS IIR-M SVN23
    "PG25": "22877",  # GPS IIR SVN43
    "PG26": "28361",  # GPS IIR-M SVN56
    "PG27": "26360",  # GPS IIR SVN27
    "PG28": "26407",  # GPS IIR SVN38
    "PG29": "32711",  # GPS IIR-M SVN57
    "PG30": "39741",  # GPS IIF SVN30
    "PG31": "29486",  # GPS IIR-M SVN52
    "PG32": "27663",  # GPS IIR SVN23
}

NORAD_TO_GPS_PRN: dict[str, str] = {v: k for k, v in GPS_PRN_TO_NORAD.items()}

# Maximum allowed gap between TLE epoch and SP3 coverage boundary before we
# declare "no temporal overlap" and return NaN for that object.
_MAX_TEMPORAL_GAP_HOURS = 12.0


# ---------------------------------------------------------------------------
# GMST helper
# ---------------------------------------------------------------------------

def gmst_rad(dt: datetime) -> float:
    """Greenwich Mean Sidereal Time in radians at UTC datetime *dt*."""
    jd, fr = jday(
        dt.year, dt.month, dt.day,
        dt.hour, dt.minute,
        dt.second + dt.microsecond / 1_000_000.0,
    )
    jd_full = jd + fr
    t = (jd_full - 2_451_545.0) / 36_525.0
    gmst_deg = (
        280.460_618_37
        + 360.985_647_366_29 * (jd_full - 2_451_545.0)
        + 0.000_387_933 * t * t
        - (t * t * t) / 38_710_000.0
    )
    return math.radians(gmst_deg % 360.0)


# ---------------------------------------------------------------------------
# SP3 reference loader
# ---------------------------------------------------------------------------

def load_sp3_reference() -> pd.DataFrame:
    """Load sp3_reference.csv and return a DataFrame with parsed Timestamps."""
    sp3_path = Path(__file__).resolve().parent.parent / "sp3_reference.csv"
    try:
        df = pd.read_csv(sp3_path)
    except Exception as exc:
        logger.error("Failed to load SP3 reference CSV: %s", exc)
        return pd.DataFrame()

    if df.empty:
        return df

    # Parse Timestamp column to UTC-aware datetimes (strip trailing zeros / whitespace)
    try:
        df["_ts"] = pd.to_datetime(df["Timestamp"].str.strip(), utc=True)
    except Exception as exc:
        logger.error("Failed to parse SP3 Timestamp column: %s", exc)
        df["_ts"] = pd.NaT

    return df


def _sp3_epoch_range(sp3_df: pd.DataFrame) -> tuple[datetime, datetime]:
    """Return (first_epoch, last_epoch) as UTC datetimes."""
    ts = sp3_df["_ts"].dropna()
    first = ts.min().to_pydatetime().replace(tzinfo=timezone.utc)
    last = ts.max().to_pydatetime().replace(tzinfo=timezone.utc)
    return first, last


# ---------------------------------------------------------------------------
# Interpolated SP3 position for one PRN at a target datetime
# ---------------------------------------------------------------------------

def _interpolated_sp3_xyz(
    sp3_df: pd.DataFrame,
    prn: str,
    target_dt: datetime,
) -> tuple[float, float, float] | None:
    """Return (X_km, Y_km, Z_km) for *prn* at *target_dt* using linear
    interpolation between the two bracketing SP3 records.

    Returns None if the PRN has no records or target is outside the SP3 window
    by more than _MAX_TEMPORAL_GAP_HOURS.
    """
    prn_rows = sp3_df[sp3_df["PRN"] == prn].copy()
    if prn_rows.empty:
        return None

    prn_rows = prn_rows.sort_values("_ts")
    timestamps = prn_rows["_ts"].values  # numpy datetime64 array

    # Convert target_dt to numpy datetime64 for comparison
    target_np = np.datetime64(target_dt.replace(tzinfo=None), "ns")

    idx = np.searchsorted(timestamps, target_np)

    # Before all records
    if idx == 0:
        gap = abs((target_dt - prn_rows.iloc[0]["_ts"].to_pydatetime().replace(tzinfo=timezone.utc)).total_seconds()) / 3600.0
        if gap > _MAX_TEMPORAL_GAP_HOURS:
            return None
        row = prn_rows.iloc[0]
        return float(row["X_km"]), float(row["Y_km"]), float(row["Z_km"])

    # After all records
    if idx == len(prn_rows):
        gap = abs((target_dt - prn_rows.iloc[-1]["_ts"].to_pydatetime().replace(tzinfo=timezone.utc)).total_seconds()) / 3600.0
        if gap > _MAX_TEMPORAL_GAP_HOURS:
            return None
        row = prn_rows.iloc[-1]
        return float(row["X_km"]), float(row["Y_km"]), float(row["Z_km"])

    # Between two records — linear interpolation
    r_before = prn_rows.iloc[idx - 1]
    r_after = prn_rows.iloc[idx]

    t_before = r_before["_ts"].to_pydatetime().replace(tzinfo=timezone.utc)
    t_after = r_after["_ts"].to_pydatetime().replace(tzinfo=timezone.utc)

    span = (t_after - t_before).total_seconds()
    if span <= 0:
        alpha = 0.0
    else:
        alpha = (target_dt - t_before).total_seconds() / span

    # Check temporal gap from nearest boundary
    gap = min(
        abs((target_dt - t_before).total_seconds()),
        abs((target_dt - t_after).total_seconds()),
    ) / 3600.0
    if gap > _MAX_TEMPORAL_GAP_HOURS:
        return None

    x = float(r_before["X_km"]) + alpha * (float(r_after["X_km"]) - float(r_before["X_km"]))
    y = float(r_before["Y_km"]) + alpha * (float(r_after["Y_km"]) - float(r_before["Y_km"]))
    z = float(r_before["Z_km"]) + alpha * (float(r_after["Z_km"]) - float(r_before["Z_km"]))
    return x, y, z


# ---------------------------------------------------------------------------
# Public API: calculate_sp3_prediction_errors
# ---------------------------------------------------------------------------

def calculate_sp3_prediction_errors(df: pd.DataFrame) -> pd.Series:
    """Compute SP3 prediction errors (km) for GPS objects in *df*.

    For each row:
    - If the object is not in the GPS constellation → NaN
      (non-GPS objects are expected; this is correct behaviour)
    - If the object is GPS but its TLE epoch has no temporal overlap with
      the SP3 data (gap > _MAX_TEMPORAL_GAP_HOURS) → NaN,
      note logged as "no temporally overlapping precise ephemeris"
    - Otherwise → propagate TLE via SGP4 to the SP3 epoch nearest the TLE
      epoch, compute ECEF distance to interpolated SP3 position.

    The ACI engine (engine.calculate_aci) already excludes NaN factors and
    re-normalises remaining weights, so no additional handling is needed here.
    """
    sp3_df = load_sp3_reference()
    errors = pd.Series(np.nan, index=df.index)

    if sp3_df.empty or "_ts" not in sp3_df.columns:
        logger.error("SP3 reference not loaded or missing _ts column — all errors NaN.")
        return errors

    # --- Parse actual SP3 epoch range (NO hardcoded date) ---
    sp3_first, sp3_last = _sp3_epoch_range(sp3_df)
    logger.info(
        "SP3 coverage: %s → %s  (%d records, %d PRNs)",
        sp3_first.isoformat(),
        sp3_last.isoformat(),
        len(sp3_df),
        sp3_df["PRN"].nunique(),
    )

    matched_count = 0
    unmapped_count = 0
    no_overlap_count = 0
    sgp4_fail_count = 0

    for idx, row in df.iterrows():
        norad_id = str(row.get("ID", "")).strip()
        prn = NORAD_TO_GPS_PRN.get(norad_id)

        if prn is None:
            unmapped_count += 1
            continue  # Non-GPS object; NaN is correct and expected

        # --- Determine propagation target: nearest SP3 epoch to TLE epoch ---
        # Prefer the SP3 epoch closest to the TLE epoch to minimise
        # extrapolation error.  The TLE epoch is encoded in the TLE itself;
        # clamp to the SP3 window boundaries when outside.
        tle1 = str(row.get("TLE Line 1", "")).strip()
        tle2 = str(row.get("TLE Line 2", "")).strip()

        # Parse TLE epoch → UTC datetime via sgp4
        try:
            sat = Satrec.twoline2rv(tle1, tle2)
            # sat.epoch is Julian date of TLE epoch
            tle_epoch_jd = sat.jdsatepoch + sat.jdsatepochF
            # Convert to datetime
            j2000 = 2_451_545.0
            tle_epoch_dt = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(
                days=(tle_epoch_jd - j2000)
            )
        except Exception as exc:
            logger.debug("Cannot parse TLE epoch for NORAD %s: %s", norad_id, exc)
            no_overlap_count += 1
            continue

        # Clamp to SP3 window
        target_dt = max(sp3_first, min(sp3_last, tle_epoch_dt))

        # Check temporal gap
        gap_hours = abs((tle_epoch_dt - target_dt).total_seconds()) / 3600.0
        if gap_hours > _MAX_TEMPORAL_GAP_HOURS:
            logger.debug(
                "NORAD %s (%s): TLE epoch %s is %.1f h outside SP3 window — no valid overlap.",
                norad_id, prn, tle_epoch_dt.isoformat(), gap_hours,
            )
            no_overlap_count += 1
            continue

        # Get interpolated SP3 reference position
        ref_xyz = _interpolated_sp3_xyz(sp3_df, prn, target_dt)
        if ref_xyz is None:
            logger.debug("NORAD %s (%s): SP3 interpolation returned None.", norad_id, prn)
            no_overlap_count += 1
            continue

        ref_x, ref_y, ref_z = ref_xyz

        # Propagate TLE to target_dt
        try:
            jd, fr = jday(
                target_dt.year, target_dt.month, target_dt.day,
                target_dt.hour, target_dt.minute,
                target_dt.second + target_dt.microsecond / 1_000_000.0,
            )
            err_code, pos_teme, _ = sat.sgp4(jd, fr)
            if err_code != 0:
                logger.debug("SGP4 error code %d for NORAD %s.", err_code, norad_id)
                sgp4_fail_count += 1
                continue

            x_teme, y_teme, z_teme = pos_teme
            theta = gmst_rad(target_dt)
            ecef_x = math.cos(theta) * x_teme + math.sin(theta) * y_teme
            ecef_y = -math.sin(theta) * x_teme + math.cos(theta) * y_teme
            ecef_z = z_teme

            error_km = math.sqrt(
                (ecef_x - ref_x) ** 2
                + (ecef_y - ref_y) ** 2
                + (ecef_z - ref_z) ** 2
            )
            errors[idx] = error_km
            matched_count += 1

        except Exception as exc:
            logger.debug("SGP4/ECEF error for NORAD %s: %s", norad_id, exc)
            sgp4_fail_count += 1

    logger.info(
        "SP3 prediction error summary: matched=%d  no_gps_prn=%d  no_overlap=%d  sgp4_fail=%d",
        matched_count, unmapped_count, no_overlap_count, sgp4_fail_count,
    )
    return errors
