
# lidar_integration.py
# Minimal LiDAR point cloud ingestion + hashing + downsampling (voxel-grid like).

from __future__ import annotations
import os, csv, json, math, hashlib
from typing import Tuple, Optional, List
import numpy as np

# Loads point cloud as Nx3 or Nx4 [x,y,z,(intensity)] from .npy or .csv.
def load_point_cloud(path: str) -> np.ndarray:
    if path.lower().endswith('.npy'):
        arr = np.load(path)
        if arr.ndim != 2 or arr.shape[1] not in (3,4):
            raise ValueError('NPY point cloud must be Nx3 or Nx4')
        return arr.astype(np.float32)
    if path.lower().endswith('.csv'):
        pts: List[List[float]] = []
        with open(path, 'r', newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row: continue
                vals = [float(x) for x in row[:4]]
                pts.append(vals)
        arr = np.array(pts, dtype=np.float32)
        if arr.shape[1] not in (3,4):
            raise ValueError('CSV point cloud must have 3 or 4 columns')
        return arr
    raise ValueError('Unsupported point cloud format (use .npy or .csv)')

# Returns the SHA3-256 hash of the given payload as a hexadecimal string
def sha3_256_hex(data: bytes) -> str:
    return hashlib.sha3_256(data).hexdigest()

# Computes a digest of the point cloud by hashing a strided subset of points
def pointcloud_digest(pc: np.ndarray, stride: int = 10) -> str:
    subset = pc[::max(1,stride)]
    return sha3_256_hex(subset.tobytes())

# Downsamples the point cloud using a voxel grid approach
def voxel_downsample(pc: np.ndarray, voxel_size: float = 0.2) -> np.ndarray:
    if voxel_size <= 0:
        return pc
    grid = np.floor(pc[:,:3] / voxel_size).astype(np.int32)
    # unique rows
    _, idx = np.unique(grid, axis=0, return_index=True)
    return pc[np.sort(idx)]

# Computes basic statistics of the point cloud: count, centroid, bounds
def compute_stats(pc: np.ndarray) -> dict:
    xyz = pc[:,:3]
    centroid = xyz.mean(axis=0).tolist()
    mins = xyz.min(axis=0).tolist()
    maxs = xyz.max(axis=0).tolist()
    n = int(xyz.shape[0])
    return {"points": n, "centroid": centroid, "bounds_min": mins, "bounds_max": maxs}
