from sgp4.api import Satrec, jday
from datetime import datetime, timezone


def propagate_tle(tle_line1, tle_line2, dt=None):
    """
    Propagate a satellite TLE to a specific UTC time.

    Returns:
        position_km: (x, y, z) in km
        velocity_km_s: (vx, vy, vz) in km/s
        error_code: SGP4 error code
    """

    # Create SGP4 satellite object from TLE
    satellite = Satrec.twoline2rv(tle_line1, tle_line2)

    # If no time is provided, use current UTC time
    if dt is None:
        dt = datetime.now(timezone.utc)

    # Convert datetime to Julian Date
    jd, fr = jday(
        dt.year,
        dt.month,
        dt.day,
        dt.hour,
        dt.minute,
        dt.second + dt.microsecond / 1_000_000
    )

    # Propagate
    error_code, position, velocity = satellite.sgp4(jd, fr)

    return position, velocity, error_code

def propagate_multiple(tle_line1, tle_line2, times):
    """
    Propagate one satellite at multiple UTC times.

    Returns:
        positions: list of (x, y, z) positions in km
        velocities: list of (vx, vy, vz) velocities in km/s
        error_codes: list of SGP4 error codes
    """

    satellite = Satrec.twoline2rv(tle_line1, tle_line2)

    positions = []
    velocities = []
    error_codes = []

    for dt in times:

        jd, fr = jday(
            dt.year,
            dt.month,
            dt.day,
            dt.hour,
            dt.minute,
            dt.second + dt.microsecond / 1_000_000
        )

        error_code, position, velocity = satellite.sgp4(jd, fr)

        positions.append(position)
        velocities.append(velocity)
        error_codes.append(error_code)

    return positions, velocities, error_codes