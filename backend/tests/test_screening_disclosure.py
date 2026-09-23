"""
Tests for screening.py scientific disclosure fields.

Verifies that screen_object() always returns the required transparency fields
and never exposes fields that would misrepresent the computation as Pc.
"""

from __future__ import annotations

import sys
import os
import pytest

# ---------------------------------------------------------------------------
# Ensure the backend directory is on sys.path so we can import screening
# ---------------------------------------------------------------------------
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from screening import screen_object  # noqa: E402


# ---------------------------------------------------------------------------
# Synthetic TLE fixtures — real-format ISS and a second satellite
# These TLEs may be epoch-stale for propagation but their format is valid,
# which is all that is needed for disclosure-field tests that do not require
# a successful propagation result.
# ---------------------------------------------------------------------------

ISS_TLE1 = "1 25544U 98067A   24001.50000000  .00002182  00000-0  40768-4 0  9997"
ISS_TLE2 = "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.50377579435580"

SAT2_TLE1 = "1 20580U 90037B   24001.50000000  .00000034  00000-0  28299-4 0  9993"
SAT2_TLE2 = "2 20580  28.4696 281.3960 0003636 172.0719 188.0379 15.09197837180310"

CATALOG_ROW_ISS = {
    "id": "25544",
    "name": "ISS (ZARYA)",
    "type": "PAYLOAD",
    "tle_line1": ISS_TLE1,
    "tle_line2": ISS_TLE2,
}

CATALOG_ROW_SAT2 = {
    "id": "20580",
    "name": "HUBBLE SPACE TELESCOPE",
    "type": "PAYLOAD",
    "tle_line1": SAT2_TLE1,
    "tle_line2": SAT2_TLE2,
}


def _run_screen(target_id: str, target_tle1: str, target_tle2: str, catalog: list) -> dict:
    """Helper to invoke screen_object with a minimal 10-min, 1-step window."""
    return screen_object(
        target_id=target_id,
        target_tle1=target_tle1,
        target_tle2=target_tle2,
        catalog_rows=catalog,
        time_step_min=10,
        window_min=10,
        threshold_km=5000.0,
        top_n=10,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDisclosureFields:
    """Verify method, method_description and disclaimer are always present."""

    def test_method_key_present(self):
        """screen_object() must always return a 'method' key."""
        result = _run_screen("25544", ISS_TLE1, ISS_TLE2, [CATALOG_ROW_SAT2])
        assert "method" in result, "'method' key missing from screening result"

    def test_method_value_is_geometric_prototype(self):
        """The method identifier must be exactly 'geometric_prototype'."""
        result = _run_screen("25544", ISS_TLE1, ISS_TLE2, [CATALOG_ROW_SAT2])
        assert result["method"] == "geometric_prototype", (
            f"Expected method='geometric_prototype', got {result['method']!r}"
        )

    def test_method_description_key_present(self):
        """screen_object() must always return a 'method_description' key."""
        result = _run_screen("25544", ISS_TLE1, ISS_TLE2, [CATALOG_ROW_SAT2])
        assert "method_description" in result, "'method_description' key missing"

    def test_method_description_is_non_empty_string(self):
        """method_description must be a non-empty string."""
        result = _run_screen("25544", ISS_TLE1, ISS_TLE2, [CATALOG_ROW_SAT2])
        desc = result["method_description"]
        assert isinstance(desc, str) and len(desc.strip()) > 0, (
            "method_description must be a non-empty string"
        )

    def test_disclaimer_key_present(self):
        """screen_object() must always return a 'disclaimer' key."""
        result = _run_screen("25544", ISS_TLE1, ISS_TLE2, [CATALOG_ROW_SAT2])
        assert "disclaimer" in result, "'disclaimer' key missing from screening result"

    def test_disclaimer_is_non_empty_string(self):
        """disclaimer must be a non-empty string."""
        result = _run_screen("25544", ISS_TLE1, ISS_TLE2, [CATALOG_ROW_SAT2])
        disc = result["disclaimer"]
        assert isinstance(disc, str) and len(disc.strip()) > 0, (
            "disclaimer must be a non-empty string"
        )

    def test_disclaimer_mentions_not_pc(self):
        """disclaimer must explicitly state it is not a Pc calculation."""
        result = _run_screen("25544", ISS_TLE1, ISS_TLE2, [CATALOG_ROW_SAT2])
        disc = result["disclaimer"].upper()
        assert "NOT" in disc, "disclaimer should contain 'NOT' to signal non-Pc nature"

    def test_error_result_still_has_no_forbidden_fields(self):
        """Even an error result (invalid TLE) must not expose collision_probability or pc."""
        result = screen_object(
            target_id="BAD",
            target_tle1="NOT A VALID TLE LINE 1",
            target_tle2="NOT A VALID TLE LINE 2",
            catalog_rows=[],
            time_step_min=10,
            window_min=10,
            threshold_km=50.0,
        )
        assert "collision_probability" not in result, (
            "Field 'collision_probability' must never appear in screening results"
        )
        assert "pc" not in result, (
            "Field 'pc' must never appear in screening results"
        )


class TestForbiddenFields:
    """Verify that Pc-implying fields are never present in any result."""

    def test_no_collision_probability_field_on_success(self):
        """A normal successful result must not contain 'collision_probability'."""
        result = _run_screen("25544", ISS_TLE1, ISS_TLE2, [CATALOG_ROW_SAT2])
        assert "collision_probability" not in result

    def test_no_pc_field_on_success(self):
        """A normal successful result must not contain a field named 'pc'."""
        result = _run_screen("25544", ISS_TLE1, ISS_TLE2, [CATALOG_ROW_SAT2])
        assert "pc" not in result

    def test_no_forbidden_fields_in_result_rows(self):
        """Individual result rows must not contain 'collision_probability' or 'pc'."""
        result = _run_screen("25544", ISS_TLE1, ISS_TLE2, [CATALOG_ROW_SAT2])
        for row in result.get("results", []):
            assert "collision_probability" not in row
            assert "pc" not in row


class TestMinimumSeparation:
    """Verify minimum_separation_km is numeric when results exist."""

    def test_minimum_separation_is_numeric_when_results_exist(self):
        """minimum_separation_km must be a float or int when there are screened objects."""
        result = _run_screen("25544", ISS_TLE1, ISS_TLE2, [CATALOG_ROW_SAT2])
        if result.get("objects_screened", 0) > 0:
            val = result.get("minimum_separation_km")
            assert isinstance(val, (int, float)), (
                f"minimum_separation_km should be numeric, got {type(val)}"
            )

    def test_result_rows_minimum_separation_numeric(self):
        """Each row in results must have a numeric minimum_separation_km."""
        result = _run_screen("25544", ISS_TLE1, ISS_TLE2, [CATALOG_ROW_SAT2])
        for row in result.get("results", []):
            val = row.get("minimum_separation_km")
            assert isinstance(val, (int, float)), (
                f"Row minimum_separation_km should be numeric, got {type(val)} for "
                f"object {row.get('object_id')}"
            )


class TestRequiredTopLevelKeys:
    """Verify essential structural keys are always present."""

    REQUIRED_KEYS = [
        "screening_id",
        "status",
        "target_id",
        "timestamp_utc",
        "method",
        "method_description",
        "disclaimer",
        "results",
    ]

    def test_all_required_keys_present_on_success(self):
        result = _run_screen("25544", ISS_TLE1, ISS_TLE2, [CATALOG_ROW_SAT2])
        for key in self.REQUIRED_KEYS:
            assert key in result, f"Required key '{key}' missing from screening result"

    def test_screening_id_is_string(self):
        result = _run_screen("25544", ISS_TLE1, ISS_TLE2, [CATALOG_ROW_SAT2])
        assert isinstance(result["screening_id"], str)

    def test_results_is_list(self):
        result = _run_screen("25544", ISS_TLE1, ISS_TLE2, [CATALOG_ROW_SAT2])
        assert isinstance(result["results"], list)
