import json
import os
from pathlib import Path
import importlib

# -------------------------------
# Locate modules
# -------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]   # repo root
SCRIPTS_DIR = PROJECT_ROOT / "Scripts"

import sys
sys.path.insert(0, str(SCRIPTS_DIR))

sha3_logger = importlib.import_module("sha3_logger")
blockchain_logger = importlib.import_module("blockchain_logger")

# -------------------------------
# SHA-3 Logger Test
# -------------------------------
events = []
for i in range(5):
    event = {
        "timestamp_ns": 1_700_000_000_000_000_000 + i,
        "agent_id": "veh-test",
        "position": {"x": float(i), "y": float(i*i), "z": 0.0},
        "velocity": {"vx": float(i+0.1), "vy": 0.0, "vz": 0.0},
        "acceleration": {"ax": 0.01*i, "ay": 0.0, "az": 0.0},
        "source": "whitebox"
    }
    sha3_logger.log_event(event)
    events.append(event)

# Verify determinism
bad_lines = []
with open("log.jsonl", "r", encoding="utf-8") as f:
    for idx, line in enumerate(f, start=1):
        obj = json.loads(line)
        if sha3_logger.sha3_hash(obj["data"]) != obj["sha3"]:
            bad_lines.append(idx)

if not bad_lines:
    print("Determinism check: all lines verified OK")
else:
    print("Determinism check FAILED at lines:", bad_lines)

# Tamper detection
with open("log.jsonl", "r", encoding="utf-8") as f:
    lines = f.readlines()

obj = json.loads(lines[2])  # 3rd record
inner = json.loads(obj["data"])
inner["event"]["position"]["x"] += 0.5  # deliberate tamper
obj["data"] = json.dumps(inner, sort_keys=True)
lines[2] = json.dumps(obj) + "\n"

with open("log_tampered.jsonl", "w", encoding="utf-8") as f:
    f.writelines(lines)

mismatches = []
with open("log_tampered.jsonl", "r", encoding="utf-8") as f:
    for idx, line in enumerate(f, start=1):
        obj = json.loads(line)
        if sha3_logger.sha3_hash(obj["data"]) != obj["sha3"]:
            mismatches.append(idx)

print("Tamper verification mismatches:", mismatches)
if mismatches == [3]:
    print("Tamper test: only the modified record failed (as expected)")
else:
    print("Tamper test FAILED:", mismatches)

# -------------------------------
# Blockchain Test
# -------------------------------
chain = blockchain_logger.Blockchain()
for i in range(10):
    payload = json.dumps({"idx": i, "value": i*i}, sort_keys=True)
    chain.add_block(payload)

print("Blockchain valid before tamper:", chain.is_chain_valid())

# Tamper block 5
chain.chain[5].data = json.dumps({"idx": 5, "value": 9999}, sort_keys=True)
print("Blockchain valid after tamper:", chain.is_chain_valid())