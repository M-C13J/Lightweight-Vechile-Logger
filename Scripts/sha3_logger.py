# sha3_logger.py
import hashlib
import json
import time
from pathlib import Path

LOG_FILE = Path("log.jsonl")

def sha3_hash(data: str) -> str:
    return hashlib.sha3_512(data.encode()).hexdigest()

def log_event(event: dict):
    timestamp = time.time()
    event_data = json.dumps({
        "timestamp": timestamp,
        "event": event,
    })
    hash_digest = sha3_hash(event_data)
    
    entry = {
        "data": event_data,
        "sha3": hash_digest
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
