# Concept of Operations (CONOPS)

## Mission Summary
- **Mission Type**: Earth Observation using an optical imager
- **Platform**: 3U CubeSat form factor
- **Orbit Type**: Sun-synchronous orbit (SSO)
- **Local Time of Descending Node (LTDN)**: 10:30 AM
- **Primary Tools**: AGI STK for scenario simulation, Python for post-processing

## Revisit Requirement
- **Objective**: Achieve a **global average revisit time of ≤ 24 hours**.
- **Metric Focus**: 
  - **Primary Optimization**: Mean revisit time
  - **Alternative Metric** (if explored): Access gap (time between successive accesses)

## Assumptions

| Parameter                  | Assumption |
|-----------------------------|------------|
| **Sensor Field of Regard**  | ±20° off-nadir (total 40° field of regard) |
| **Minimum Elevation Angle** | 20° above local horizon |
| **Earth Model**             | WGS-84 Ellipsoid |
| **Imaging Duty Cycle**      | Continuous imaging during access windows |

## Notes
- The constellation design will assume a fully functioning optical payload operating continuously within its field of regard during ground passes.
- Future steps (trade studies, optimization) will explicitly reference and refine these assumptions if needed.