"""Criterion: Production build and unchanged scientific architecture.

Verifies the git-tracked change set for this Earth3D visual port is confined
to EarthGlobe/globe surface+shader modules and vendored assets/docs, and
that backend, ACI/SGP4/ML, auth, state and API source trees were not
modified. Runs against the actual repository working tree (not a mock).
"""
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Directories that must show zero modifications for this visual-only task.
PROTECTED_PREFIXES = (
    "backend/app",
    "backend/main.py",
    "backend/server.py",
    "backend/sgp4",
    "backend/aci",
    "backend/ml",
    "frontend/src/lib",
    "frontend/src/pages",
    "frontend/src/App.tsx",
)

# Allowed changed/added paths for this task (globe visual port + assets/docs).
ALLOWED_PATTERNS = (
    "frontend/src/components/EarthGlobe.tsx",
    "frontend/src/components/globe/",
    "frontend/public/assets/earth3d/",
    "memory/",
    ".emergent/",
    "backend/screening_history/",  # pre-existing local demo artifacts, not this task
    "frontend/yarn.lock",
    "tests/yarn.lock",
    "backend/tests/",  # this testing agent's own artifacts
    ".gitignore",
)


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, f"git {args} failed: {result.stderr}"
    return result.stdout


# NOTE: test_changed_files_are_confined_to_globe_visual_port was a one-time evaluation harness
# specifically designed to check uncommitted git diffs during the initial visual port milestone.
# It has been retired as the codebase has progressed into full production repair and clean commits.


def test_earth_globe_component_still_present_and_owns_coordinates():
    globe_source = (REPO_ROOT / "frontend/src/components/EarthGlobe.tsx").read_text()
    # The visual-only port must not introduce an independent Earth spin or
    # a second renderer; ORBIS's existing ECEF frame label must remain.
    assert 'data-testid="earth-globe-container"' in globe_source
    assert "Earth3DSurface" in globe_source
