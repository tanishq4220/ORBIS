# Probability of Collision (Pc) — Future Implementation Requirements

## Current State

ORBIS currently implements **geometric conjunction screening only**. The system:

- Propagates object positions using SGP4/TLE at discrete time steps
- Computes 3D Euclidean minimum separation distance between catalog objects
- Flags objects closer than a configurable threshold (default 50 km) as `POTENTIAL_CONJUNCTION`
- Returns the minimum separation distance in km

**This is NOT a validated probability-of-collision calculation.**

The `minimum_separation_km` field represents geometric proximity, not collision likelihood.

---

## Why Geometric Distance ≠ Collision Probability

Probability of collision depends on:
1. **Position uncertainty** — the actual object positions are uncertain; TLE-derived positions have typical errors of hundreds of metres to several kilometres depending on object type, data age, and orbit altitude.
2. **Covariance matrices** — a proper Pc calculation requires a 6×6 state covariance matrix for both objects at the TCA, representing uncertainty in position and velocity.
3. **Combined uncertainty** — the relative encounter geometry determines whether the probability is meaningful.
4. **Miss-distance relative to uncertainty** — a 10 km miss with 20 km position uncertainty is very different from a 10 km miss with 0.1 km uncertainty.

---

## What Would Be Required for a Scientifically Defensible Pc

### Data Requirements

1. **State covariance matrices** for each object, propagated to the TCA.
   - Source: conjunction data messages (CDMs) from LeoLabs, 18th Space Control Squadron, or commercial SSA providers.
   - Current TLE data does NOT include covariance.

2. **Validated propagation** — SGP4 accuracy is limited, especially for debris objects. High-fidelity propagators (e.g., numerical integration with atmospheric drag models) improve position estimates.

3. **TLE-derived position uncertainty estimates** — if formal covariance is unavailable, empirical uncertainty models based on object type, orbit regime, and TLE age can be used as a proxy (less accurate).

### Methodology

The standard approach is the **Foster-Estes 2D covariance method** (as used by the US Space Force's SOCRATES):

1. Transform state covariance matrices to the encounter reference frame (RTN or NTW)
2. Project both covariances onto the encounter plane perpendicular to relative velocity
3. Combine the projected covariances
4. Compute the probability that the miss-distance vector falls within the combined hard-body radius (HBR)
5. HBR is determined by object physical size estimates

Alternative methods include:
- Monte Carlo sampling across uncertainty envelope
- Analytical methods (Chan's method, Patera's method)

### Implementation Steps

To implement Pc in ORBIS:

1. Integrate a CDM data source (e.g., Space-Track.org CDM feeds, commercial operators)
2. Parse and store covariance data alongside TLE epochs
3. Implement TCA refinement (see existing `TCA_REFINEMENT.md`)
4. Implement covariance propagation to TCA
5. Apply encounter-frame projection
6. Compute Pc using Foster-Estes or equivalent validated method
7. Validate against published CDM Pc values
8. Display Pc with explicit methodology disclosure and uncertainty bounds

### Disclosure Requirements

Any Pc implementation MUST:
- Clearly state the methodology used
- State the input covariance source
- State the propagation model
- Disclose known limitations
- NOT be mistaken for a definitive risk assessment

---

## References

- Foster, J.L., Estes, H.S. (1992). "A Standardized Method for Evaluating Satellite Conjunction Probabilities"
- Chan, F.K. (2008). "Spacecraft Collision Probability." AIAA.
- Alfano, S. (2005). "A Numerical Implementation of Spherical Object Conjunction Analysis"
- NASA JSC: "Probability of Collision Calculation" (JSC-66756)
- 18th Space Control Squadron CDM format: Space-Track.org
