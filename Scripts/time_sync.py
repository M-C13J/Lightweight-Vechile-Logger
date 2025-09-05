
# time_sync.py
# Lightweight time synchronization helpers for NTP-like (ms) and TSN-like (us) precision.
# Note: This is a simulation/helper layer; for true TSN/PTP use system/hardware stacks.

from __future__ import annotations
import time
from dataclasses import dataclass

@dataclass
class TimeSyncConfig:
    mode: str = "NTP"            # "NTP" or "TSN"
    ntp_offset_ms: float = 0.0   # simulated NTP offset to apply (can be ±)
    tsn_precision_us: int = 1    # rounding precision for TSN microseconds (e.g., 1, 10)

# Simple time synchronizer supporting NTP-like and TSN-like modes
class TimeSynchronizer:
    # Initialize with a TimeSyncConfig
    def __init__(self, cfg: TimeSyncConfig = TimeSyncConfig()):
        mode = (cfg.mode or "NTP").upper()
        if mode not in {"NTP", "TSN"}:
            raise ValueError("TimeSynchronizer.mode must be 'NTP' or 'TSN'")
        self.cfg = TimeSyncConfig(mode=mode, ntp_offset_ms=cfg.ntp_offset_ms, tsn_precision_us=cfg.tsn_precision_us)

    # Return synchronized epoch time (seconds as float)
    def now(self) -> float:
        """Return synchronized epoch time (seconds as float)."""
        t = time.time()
        return self.align(t)

    # Align a given epoch time (seconds) according to the configured mode
    def align(self, t_seconds: float) -> float:
        if self.cfg.mode == "NTP":
            # Apply an offset (ms) to simulate offset-corrected time.
            return t_seconds + (self.cfg.ntp_offset_ms / 1000.0)
        # TSN-like: quantize to microsecond grid to simulate sub-ms precision.
        us = int(round(t_seconds * 1_000_000))
        grid = max(1, int(self.cfg.tsn_precision_us))
        us_quant = (us // grid) * grid
        return us_quant / 1_000_000.0
