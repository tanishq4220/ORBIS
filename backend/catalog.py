"""Cached ORBIS catalog loader — single source of truth for API responses."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
ACI_OUTPUT = BASE_DIR / "ACI" / "aci_output.csv"
SP3_FILE = BASE_DIR / "IGS0OPSFIN_20260910000_01D_15M_ORB.SP3"
ML_MODEL_DIR = BASE_DIR / "ml"


class CatalogStore:
    def __init__(self) -> None:
        self.df: Optional[pd.DataFrame] = None
        self.loaded = False
        self.error: Optional[str] = None
        self._by_id: dict[str, int] = {}

    def load(self) -> None:
        if not ACI_OUTPUT.exists():
            self.loaded = False
            self.error = (
                "ACI output file not found. Run python .\\ACI\\run.py first."
            )
            raise FileNotFoundError(self.error)

        try:
            df = pd.read_csv(ACI_OUTPUT)
            # Normalize expected columns
            for col in (
                "ID",
                "Name",
                "Type",
                "TLE Line 1",
                "TLE Line 2",
                "Epoch",
                "Data_Age_days",
                "Data_Age_Confidence",
                "Trajectory_Consistency",
                "Track_Confidence",
                "Prediction_Error_km",
                "Prediction_Confidence",
                "Prediction_Horizon_hours",
                "Model_Confidence",
                "ML_Prediction",
                "ACI",
                "Decision",
            ):
                if col not in df.columns:
                    df[col] = pd.NA

            df["ID"] = df["ID"].astype(str)
            self.df = df
            self._by_id = {
                str(oid): i for i, oid in enumerate(df["ID"].tolist())
            }
            self.loaded = True
            self.error = None
        except Exception as exc:  # noqa: BLE001
            self.loaded = False
            self.error = f"Could not read ACI output: {exc}"
            raise

    def require(self) -> pd.DataFrame:
        if self.df is None or not self.loaded:
            self.load()
        assert self.df is not None
        return self.df

    def get_row(self, object_id: str) -> Optional[pd.Series]:
        df = self.require()
        idx = self._by_id.get(str(object_id))
        if idx is None:
            matches = df[df["ID"].astype(str) == str(object_id)]
            if matches.empty:
                return None
            return matches.iloc[0]
        return df.iloc[idx]


store = CatalogStore()


def clean_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    try:
        if hasattr(value, "item"):
            value = value.item()
    except Exception:  # noqa: BLE001
        pass

    if isinstance(value, str):
        text = value.strip()
        return text if text else None

    return value


def row_to_object(row: pd.Series, include_tle: bool = True) -> dict[str, Any]:
    obj: dict[str, Any] = {
        "id": clean_value(row.get("ID")),
        "name": clean_value(row.get("Name")),
        "type": clean_value(row.get("Type")),
        "epoch": clean_value(row.get("Epoch")),
        "data_age_days": clean_value(row.get("Data_Age_days")),
        "data_age_confidence": clean_value(row.get("Data_Age_Confidence")),
        "trajectory_consistency": clean_value(
            row.get("Trajectory_Consistency")
        ),
        "track_confidence": clean_value(row.get("Track_Confidence")),
        "prediction_error_km": clean_value(row.get("Prediction_Error_km")),
        "prediction_confidence": clean_value(
            row.get("Prediction_Confidence")
        ),
        "prediction_horizon_hours": clean_value(
            row.get("Prediction_Horizon_hours")
        ),
        "model_confidence": clean_value(row.get("Model_Confidence")),
        "ml_prediction": clean_value(row.get("ML_Prediction")),
        "aci": clean_value(row.get("ACI")),
        "decision": clean_value(row.get("Decision")),
    }

    if include_tle:
        obj["tle_line1"] = clean_value(row.get("TLE Line 1"))
        obj["tle_line2"] = clean_value(row.get("TLE Line 2"))

    return obj


def subsystem_status() -> dict[str, str]:
    statuses = {
        "backend": "OPERATIONAL",
        "dataset": "OFFLINE",
        "sgp4": "AVAILABLE",
        "aci": "OFFLINE",
        "sp3": "NOT CONNECTED",
        "ml": "NOT CONNECTED",
    }

    if store.loaded and store.df is not None and len(store.df) > 0:
        statuses["dataset"] = "OPERATIONAL"
        if "ACI" in store.df.columns and store.df["ACI"].notna().any():
            statuses["aci"] = "OPERATIONAL"
        if (
            "Model_Confidence" in store.df.columns
            and store.df["Model_Confidence"].notna().any()
        ):
            statuses["ml"] = "OPERATIONAL"
        elif (ML_MODEL_DIR / "models").exists() or list(
            ML_MODEL_DIR.glob("*.pkl")
        ) or list(ML_MODEL_DIR.glob("**/*model*")):
            statuses["ml"] = "AVAILABLE"

    if SP3_FILE.exists() or list(BASE_DIR.glob("*.SP3")) or list(
        BASE_DIR.glob("*.sp3")
    ):
        statuses["sp3"] = "AVAILABLE"

    return statuses
