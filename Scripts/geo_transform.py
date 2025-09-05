
# geo_transform.py
# Minimal WGS84 <-> UTM forward projection (lat/lon to UTM) without external deps.
# For forensic mapping; precision is sufficient for demo/evaluation, not surveying.

from __future__ import annotations
import math
from typing import Tuple

# WGS84 constants
WGS84_A = 6378137.0
WGS84_F = 1 / 298.257223563
WGS84_E2 = WGS84_F * (2 - WGS84_F)

def latlon_to_utm(lat_deg: float, lon_deg: float) -> Tuple[int, float, float, str]:
    # Determine UTM zone
    zone = int((lon_deg + 180) // 6) + 1
    # Hemisphere
    hemisphere = 'N' if lat_deg >= 0 else 'S'

    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    lon0_deg = (zone - 1)*6 - 180 + 3  # central meridian
    lon0 = math.radians(lon0_deg)

    e2 = WGS84_E2
    e_prime2 = e2 / (1 - e2)
    N = WGS84_A / math.sqrt(1 - e2 * math.sin(lat)**2)
    T = math.tan(lat)**2
    C = e_prime2 * math.cos(lat)**2
    A = (lon - lon0) * math.cos(lat)

    # Mercator-like series for UTM (Transverse Mercator)
    k0 = 0.9996
    M = (WGS84_A * ((1 - e2/4 - 3*e2**2/64 - 5*e2**3/256) * lat
        - (3*e2/8 + 3*e2**2/32 + 45*e2**3/1024) * math.sin(2*lat)
        + (15*e2**2/256 + 45*e2**3/1024) * math.sin(4*lat)
        - (35*e2**3/3072) * math.sin(6*lat)))

    easting = k0 * N * (A + (1 - T + C) * A**3 / 6
                + (5 - 18*T + T**2 + 72*C - 58*e_prime2) * A**5 / 120) + 500000.0

    northing = k0 * (M + N * math.tan(lat) * (A**2 / 2
                 + (5 - T + 9*C + 4*C**2) * A**4 / 24
                 + (61 - 58*T + T**2 + 600*C - 330*e_prime2) * A**6 / 720))

    if hemisphere == 'S':
        northing += 10000000.0

    return zone, easting, northing, hemisphere
