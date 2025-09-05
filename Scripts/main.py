# main.py — runner with built-in exporter (no separate exporter module needed)

import os, json, time, statistics
import numpy as np
from pathlib import Path

from sha3_logger import log_event as log_record_sha3          # append-only log + SHA-3 per record
from blockchain_logger import Blockchain                       # is_chain_valid() for report
from anomaly_detector import train_anomaly_detector, predict_anomalies
from carla_telemetery import get_telemetry

from time_sync import TimeSynchronizer, TimeSyncConfig
from data_standardizer import from_drone_json, StandardRecord
from evidence_correlator import correlate
from lidar_integration import load_point_cloud, voxel_downsample, compute_stats, pointcloud_digest
from multi_agent import MultiAgentManager
from geo_transform import latlon_to_utm

# ------------------------------
# Feature Toggles
# ------------------------------
ENABLE_TIME_SYNC       = True
ENABLE_STANDARDIZATION = True
ENABLE_CORRELATION     = False
ENABLE_LIDAR           = False
ENABLE_MULTI_AGENT     = True
ENABLE_GEO             = False
ENABLE_ML              = True

# ------------------------------
# Config values
# ------------------------------
TIME_MODE = "TSN"          # "NTP" or "TSN"
NTP_OFFSET_MS = 0.0
TSN_PRECISION_US = 1

LIDAR_PATH = "data/scan.npy"
LIDAR_VOXEL = 0.25
CORR_WINDOW_MS = 50
MODEL_PATH = "anomaly_model.pkl"

SAMPLES = 200
SLEEP_MS = 20

# ------------------------------
# Built-in Export helpers
# ------------------------------
EXPORT_DIR = Path("exports")
EXPORT_DIR.mkdir(exist_ok=True)


def export_json(obj, filename):
    p = EXPORT_DIR / filename
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
    return str(p)

def export_csv_row(row_dict, filename):
    # single-row CSV for perf metrics; avoids csv module to keep it tiny
    p = EXPORT_DIR / filename
    if not p.exists():
        with open(p, "w", encoding="utf-8") as f:
            f.write(",".join(row_dict.keys()) + "\n")
    with open(p, "a", encoding="utf-8") as f:
        f.write(",".join(str(row_dict[k]) for k in row_dict.keys()) + "\n")
    return str(p)

# ------------------------------

def ns_now(ts: float) -> int:
    return int(ts * 1_000_000_000)

def to_dict(rec: StandardRecord) -> dict:
    return json.loads(json.dumps(rec, default=lambda o: getattr(o, '__dict__', str(o))))

def main():
    chain = Blockchain()  # custody chain

    # Time sync
    tsync = TimeSynchronizer(TimeSyncConfig(mode=TIME_MODE, ntp_offset_ms=NTP_OFFSET_MS, tsn_precision_us=TSN_PRECISION_US)) if ENABLE_TIME_SYNC else None

    # ML
    clf = None
    if ENABLE_ML:
        data = np.random.normal(0, 1, (400, 4))
        train_anomaly_detector(data, model_path=MODEL_PATH)
        clf = MODEL_PATH

    mam = MultiAgentManager() if ENABLE_MULTI_AGENT else None
    streams = {}               # for correlation (optional)
    anomaly_flags = []         # collect only anomalies for summary
    latencies = []             # per-iteration latency

    t_run_start = time.perf_counter()

    for i in range(SAMPLES):
        t_iter_start = time.perf_counter()

        raw = get_telemetry()
        t = time.time()
        if tsync:
            t = tsync.align(t)
        ts_ns = ns_now(t)

        # Standardize
        if ENABLE_STANDARDIZATION:
            drone_like = {
                "position": {"x": raw.get("position_x", 0.0), "y": raw.get("position_y", 0.0), "z": float(raw.get("altitude", 0.0))},
                "velocity": {"x": raw.get("velocity_x", 0.0), "y": float(raw.get("velocity_y", 0.0)), "z": 0.0},
                "acceleration": {"x": raw.get("acceleration_x", 0.0), "y": 0.0, "z": 0.0},
                "orientation": {"yaw": float(raw.get("yaw", 0.0)), "pitch": 0.0, "roll": 0.0},
                "sensor": "fusion"
            }
            std = from_drone_json(drone_like, agent_id=str(raw.get("agent_id","veh-1")), ts_ns=ts_ns)
            std_dict = to_dict(std)
        else:
            std_dict = {
                "timestamp_ns": ts_ns,
                "agent_id": str(raw.get("agent_id","veh-1")),
                "position": {"x": raw.get("position_x", 0.0), "y": raw.get("position_y", 0.0)},
                "velocity": {"vx": raw.get("velocity_x", 0.0), "vy": 0.0, "vz": 0.0},
                "acceleration": {"ax": raw.get("acceleration_x", 0.0), "ay": 0.0, "az": 0.0},
                "sensor": "raw",
            }

        # LiDAR
        if ENABLE_LIDAR and os.path.exists(LIDAR_PATH):
            try:
                pc = load_point_cloud(LIDAR_PATH)
                pc_ds = voxel_downsample(pc, voxel_size=LIDAR_VOXEL)
                std_dict["lidar_stats"] = compute_stats(pc_ds)
                std_dict["lidar_digest"] = pointcloud_digest(pc_ds, stride=20)
            except Exception as e:
                std_dict["lidar_error"] = str(e)

        # Geo
        if ENABLE_GEO and "lat" in raw and "lon" in raw:
            try:
                zone, easting, northing, hemi = latlon_to_utm(float(raw["lat"]), float(raw["lon"]))
                std_dict.setdefault("extras", {})["utm"] = {"zone": zone, "easting": easting, "northing": northing, "hemisphere": hemi}
            except Exception as e:
                std_dict.setdefault("extras", {})["utm_error"] = str(e)

        # Multi-agent
        if mam:
            events = mam.update(std_dict)
            if events:
                std_dict.setdefault("multi_agent_events", []).extend(events)

        # ML anomaly detection
        if ENABLE_ML and clf is not None:
            feat = np.array([[
                float(std_dict.get("velocity",{}).get("vx",0.0)),
                float(std_dict.get("acceleration",{}).get("ax",0.0)),
                float(std_dict.get("position",{}).get("x",0.0)),
                float(std_dict.get("position",{}).get("y",0.0)),
            ]], dtype=float)
            pred = predict_anomalies(feat, model_path=clf)
            flag = int(pred[0])                 # usually -1 (anom) or 1 (normal)
            std_dict["anomaly_flag"] = flag
            if flag == -1:
                anomaly_flags.append({
                    "timestamp_ns": ts_ns,
                    "agent_id": std_dict.get("agent_id"),
                    "vx": std_dict.get("velocity",{}).get("vx",0.0),
                    "ax": std_dict.get("acceleration",{}).get("ax",0.0),
                    "x": std_dict.get("position",{}).get("x",0.0),
                    "y": std_dict.get("position",{}).get("y",0.0),
                })
        else:
            std_dict["anomaly_flag"] = 0

        # Log + Blockchain
        log_record_sha3(std_dict)                              # append-only SHA-3 line (custody)  # 
        chain.add_block(json.dumps(std_dict, sort_keys=True))  # add block to local ledger         # 

        # Optional correlation
        if ENABLE_CORRELATION:
            aid = std_dict.get("agent_id","veh-1")
            streams.setdefault(aid, []).append(std_dict)

        # perf timing
        latencies.append(time.perf_counter() - t_iter_start)
        time.sleep(max(0, SLEEP_MS / 1000.0))

    # ------------------------------
    # Built-in Exports (end of run)
    # ------------------------------

    # Chain verification
    chain_ok = chain.is_chain_valid()  # boolean
    export_json({"chain_valid": chain_ok, "blocks": len(chain.chain)}, "chain_verification.json")  # 

    # Anomaly summary
    export_json({"anomalies": anomaly_flags}, "anomaly_summary.json")

    # Correlation bundles (if enabled)
    if ENABLE_CORRELATION:
        corr = correlate(streams, window_ms=CORR_WINDOW_MS)   # 
        export_json({"correlated_events": [ce.__dict__ for ce in corr]}, "correlation_bundles.json")

    # Perf metadata
    total_time = time.perf_counter() - t_run_start
    rps = round(SAMPLES / total_time, 3) if total_time > 0 else 0.0
    lat_sorted = sorted(latencies)
    p50 = round(lat_sorted[int(0.50 * (len(lat_sorted)-1))] * 1000, 3)
    p95 = round(lat_sorted[int(0.95 * (len(lat_sorted)-1))] * 1000, 3)
    export_csv_row({
        "samples": SAMPLES,
        "sleep_ms": SLEEP_MS,
        "total_s": round(total_time, 3),
        "rps": rps,
        "latency_p50_ms": p50,
        "latency_p95_ms": p95,
        "chain_valid": chain_ok
    }, "performance.csv")

if __name__ == "__main__":
    main()
