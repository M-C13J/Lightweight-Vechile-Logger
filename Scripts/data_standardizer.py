
# data_standardizer.py
# Standardizes heterogeneous telemetry into a unified schema for cross-platform forensics.
# Supports (examples): Drone JSON/XML and Vehicle (AUTOSAR-like dict) into a common record.

from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, Optional
import json
import xml.etree.ElementTree as ET
import hashlib

# Returns the SHA3-256 hash of the given payload as a hexadecimal string
def sha3_256_hex(payload: bytes) -> str:
    return hashlib.sha3_256(payload).hexdigest()

# Defines a unified telemetry schema for autonomous systems
@dataclass
class StandardRecord:
    timestamp_ns: int
    agent_id: str
    domain: str                    # "drone" | "vehicle" | "sim"
    source_format: str             # e.g., "json", "xml", "autosar", "carla"
    position: Dict[str, float]     # {x,y,z} or {lat,lon,alt}
    velocity: Dict[str, float]     # {vx, vy, vz}
    acceleration: Dict[str, float] # {ax, ay, az}
    orientation: Dict[str, float]  # {yaw, pitch, roll}
    sensor: str                    # e.g., "imu", "gps", "lidar", "fusion"
    extras: Dict[str, Any] = field(default_factory=dict)
    record_hash: Optional[str] = None

    def finalize(self):
        # Compute a deterministic hash for chain-of-custody at the record level
        safe = dict(asdict(self))
        safe["record_hash"] = None
        payload = json.dumps(safe, sort_keys=True).encode()
        self.record_hash = sha3_256_hex(payload)

# Converts various telemetry formats into StandardRecord instances
def from_drone_json(obj: Dict[str, Any], agent_id: str, ts_ns: int) -> StandardRecord:
    pos = obj.get("position", {})
    vel = obj.get("velocity", {})
    acc = obj.get("acceleration", {})
    ori = obj.get("orientation", {})
    rec = StandardRecord(
        timestamp_ns=ts_ns,
        agent_id=agent_id,
        domain="drone",
        source_format="json",
        position={"x": float(pos.get("x", 0.0)), "y": float(pos.get("y", 0.0)), "z": float(pos.get("z", 0.0))},
        velocity={"vx": float(vel.get("x", 0.0)), "vy": float(vel.get("y", 0.0)), "vz": float(vel.get("z", 0.0))},
        acceleration={"ax": float(acc.get("x", 0.0)), "ay": float(acc.get("y", 0.0)), "az": float(acc.get("z", 0.0))},
        orientation={"yaw": float(ori.get("yaw", 0.0)), "pitch": float(ori.get("pitch", 0.0)), "roll": float(ori.get("roll", 0.0))},
        sensor=obj.get("sensor", "fusion"),
        extras={k: v for k, v in obj.items() if k not in {"position","velocity","acceleration","orientation","sensor"}},
    )
    rec.finalize()
    return rec

# Parses a small XML telemetry snippet into a StandardRecord
def from_drone_xml(xml_text: str, agent_id: str, ts_ns: int) -> StandardRecord:
    # Expect a small XML like: <telemetry><position x=".." y=".." z=".."/>...</telemetry>
    root = ET.fromstring(xml_text)
    def _attrs(tag):
        e = root.find(tag)
        return e.attrib if e is not None else {}
    pos = _attrs("position")
    vel = _attrs("velocity")
    acc = _attrs("acceleration")
    ori = _attrs("orientation")
    sensor = root.attrib.get("sensor", "fusion")
    rec = StandardRecord(
        timestamp_ns=ts_ns,
        agent_id=agent_id,
        domain="drone",
        source_format="xml",
        position={"x": float(pos.get("x", 0.0)), "y": float(pos.get("y", 0.0)), "z": float(pos.get("z", 0.0))},
        velocity={"vx": float(vel.get("x", 0.0)), "vy": float(vel.get("y", 0.0)), "vz": float(vel.get("z", 0.0))},
        acceleration={"ax": float(acc.get("x", 0.0)), "ay": float(acc.get("y", 0.0)), "az": float(acc.get("z", 0.0))},
        orientation={"yaw": float(ori.get("yaw", 0.0)), "pitch": float(ori.get("pitch", 0.0)), "roll": float(ori.get("roll", 0.0))},
        sensor=sensor,
        extras={"raw_xml_len": len(xml_text)},
    )
    rec.finalize()
    return rec

# Minimal mapping from an AUTOSAR-like V2X payload to common schema
def from_autosar_like(obj: Dict[str, Any], agent_id: str, ts_ns: int) -> StandardRecord:
    # Minimal mapping from an AUTOSAR-like V2X payload to common schema
    # Example expected keys: pose.{x,y,z, yaw,pitch,roll}, speed.{vx,vy,vz}
    pose = obj.get("pose", {})
    speed = obj.get("speed", {})
    acc = obj.get("acc", {})
    rec = StandardRecord(
        timestamp_ns=ts_ns,
        agent_id=agent_id,
        domain="vehicle",
        source_format="autosar",
        position={"x": float(pose.get("x", 0.0)), "y": float(pose.get("y", 0.0)), "z": float(pose.get("z", 0.0))},
        velocity={"vx": float(speed.get("vx", 0.0)), "vy": float(speed.get("vy", 0.0)), "vz": float(speed.get("vz", 0.0))},
        acceleration={"ax": float(acc.get("ax", 0.0)), "ay": float(acc.get("ay", 0.0)), "az": float(acc.get("az", 0.0))},
        orientation={"yaw": float(pose.get("yaw", 0.0)), "pitch": float(pose.get("pitch", 0.0)), "roll": float(pose.get("roll", 0.0))},
        sensor=obj.get("sensor", "fusion"),
        extras={k: v for k, v in obj.items() if k not in {"pose","speed","acc","sensor"}},
    )
    rec.finalize()
    return rec
