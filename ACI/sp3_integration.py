import pandas as pd
import numpy as np
from datetime import datetime, timezone
import math
from sgp4.api import Satrec, jday
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GPS_PRN_TO_NORAD = {
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

NORAD_TO_GPS_PRN = {v: k for k, v in GPS_PRN_TO_NORAD.items()}

def gmst_rad(dt: datetime) -> float:
    jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second + dt.microsecond / 1_000_000.0)
    jd_full = jd + fr
    t = (jd_full - 2451545.0) / 36525.0
    gmst_deg = (
        280.46061837
        + 360.98564736629 * (jd_full - 2451545.0)
        + 0.000387933 * t * t
        - (t * t * t) / 38710000.0
    )
    return math.radians(gmst_deg % 360.0)

def load_sp3_reference() -> pd.DataFrame:
    try:
        sp3_path = Path(__file__).resolve().parent.parent / "sp3_reference.csv"
        sp3_df = pd.read_csv(sp3_path)
        return sp3_df
    except Exception as e:
        logger.error(f"Failed to load SP3 file: {e}")
        return pd.DataFrame()

def calculate_sp3_prediction_errors(df: pd.DataFrame) -> pd.Series:
    sp3_df = load_sp3_reference()

    if sp3_df.empty:
        logger.error("SP3 reference file is empty.")
        return pd.Series(np.nan, index=df.index)

    errors = pd.Series(np.nan, index=df.index)
    
    target_dt = datetime(2026, 4, 1, 0, 0, 0, tzinfo=timezone.utc)
    jd, fr = jday(target_dt.year, target_dt.month, target_dt.day, target_dt.hour, target_dt.minute, target_dt.second)
    gmst = gmst_rad(target_dt)
    
    matched_count = 0
    unmapped_count = 0
    
    for idx, row in df.iterrows():
        norad_id = str(row.get("ID", "")).strip()
        prn = NORAD_TO_GPS_PRN.get(norad_id)
        
        if not prn:
            unmapped_count += 1
            continue

        sp3_rows = sp3_df[sp3_df["PRN"] == prn]
        if sp3_rows.empty:
            logger.info(f"NORAD ID {norad_id} mapped to {prn} but not found in SP3 file.")
            continue
            
        sp3_row = sp3_rows.iloc[0]
        try:
            ref_x = float(sp3_row["X_km"])
            ref_y = float(sp3_row["Y_km"])
            ref_z = float(sp3_row["Z_km"])
            
            if np.isnan(ref_x) or np.isnan(ref_y) or np.isnan(ref_z):
                raise ValueError("NaN in SP3 coordinates")
        except Exception as e:
            raise ValueError(f"Malformed SP3 data for PRN {prn}: {e}")
            
        tle1 = str(row.get("TLE Line 1", "")).strip()
        tle2 = str(row.get("TLE Line 2", "")).strip()
        
        try:
            sat = Satrec.twoline2rv(tle1, tle2)
            err_code, pos_teme, _ = sat.sgp4(jd, fr)
            if err_code != 0:
                logger.info(f"SGP4 propagation failed for {norad_id}")
                continue
                
            x_teme, y_teme, z_teme = pos_teme
            ecef_x = math.cos(gmst) * x_teme + math.sin(gmst) * y_teme
            ecef_y = -math.sin(gmst) * x_teme + math.cos(gmst) * y_teme
            ecef_z = z_teme
            
            error_km = math.sqrt((ecef_x - ref_x)**2 + (ecef_y - ref_y)**2 + (ecef_z - ref_z)**2)
            errors[idx] = error_km
            matched_count += 1
            
        except Exception as e:
            logger.info(f"Error processing {norad_id}: {e}")

    logger.info(f"Matched {matched_count} objects with SP3 data.")
    logger.info(f"Left {unmapped_count} objects as NaN (unmapped to GPS PRN).")
    
    return errors
