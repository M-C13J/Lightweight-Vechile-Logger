
# evidence_correlator.py
# Correlates standardized records across domains/agents using time windows and proximity.

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple
import math
import hashlib
import json

# A correlated event involving multiple agents within a time window and spatial proximity
@dataclass
class CorrelatedEvent:
    t_start_ns: int
    t_end_ns: int
    participants: List[str]     # agent_ids
    records: List[dict]         # underlying standardized records (as dict)
    correlation_hash: str
    
# Returns the SHA3-256 hash of the given payload as a hexadecimal string
def sha3_256_hex(b: bytes) -> str:
    return hashlib.sha3_256(b).hexdigest()

# Computes 2D distance between two records based on their position fields
def _distance_xy(a: dict, b: dict) -> float:
    ax, ay = a.get("position",{}).get("x",0.0), a.get("position",{}).get("y",0.0)
    bx, by = b.get("position",{}).get("x",0.0), b.get("position",{}).get("y",0.0)
    return math.hypot(ax-bx, ay-by)

# Correlates events across multiple agent streams based on time and spatial proximity
def correlate(streams: Dict[str, List[dict]], window_ms: int = 50, max_xy_dist: float = 2.0) -> List[CorrelatedEvent]:
    """Window-join across agent streams by time & proximity.
    streams: {agent_id: [standard_record_dict ... sorted by timestamp_ns]}
    """
    events: List[CorrelatedEvent] = []
    # Flatten with agent tag
    all_rec: List[Tuple[str, dict]] = []
    for aid, recs in streams.items():
        for r in recs:
            all_rec.append((aid, r))
    # Sort by time
    all_rec.sort(key=lambda x: x[1].get("timestamp_ns", 0))
    # Sweep
    W = window_ms * 1_000_000
    i = 0
    while i < len(all_rec):
        aid_i, r_i = all_rec[i]
        t0 = r_i.get("timestamp_ns",0)
        bucket = [(aid_i, r_i)]
        j = i + 1
        while j < len(all_rec):
            aid_j, r_j = all_rec[j]
            t = r_j.get("timestamp_ns",0)
            if t - t0 > W:
                break
            # simple spatial gating
            if _distance_xy(r_i, r_j) <= max_xy_dist:
                bucket.append((aid_j, r_j))
            j += 1
        if len(bucket) > 1:
            t_start = min(r.get("timestamp_ns",0) for _, r in bucket)
            t_end   = max(r.get("timestamp_ns",0) for _, r in bucket)
            participants = sorted({aid for aid, _ in bucket})
            records = [r for _, r in bucket]
            payload = json.dumps({
                "t_start_ns": t_start,
                "t_end_ns": t_end,
                "participants": participants,
                "records_hashes": [r.get("record_hash") for r in records],
            }, sort_keys=True).encode()
            h = sha3_256_hex(payload)
            events.append(CorrelatedEvent(t_start, t_end, participants, records, h))
        i += 1
    return events
