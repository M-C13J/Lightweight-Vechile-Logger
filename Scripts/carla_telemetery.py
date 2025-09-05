# carla_telemetery.py
import csv
import itertools


DATASET_PATH = "../datasets/telemetry_selin.csv" # path to desired dataset CSV file
USE_DATASET = True # if False, connects to CARLA simulator

if USE_DATASET:
    dataset_file = open(DATASET_PATH, newline='', encoding="utf-8")
    reader = csv.DictReader(dataset_file)
    data_iter = itertools.cycle(list(reader)) 

# Fetches telemetry data either from dataset or CARLA simulator
def get_telemetry():
    if USE_DATASET:
        row = next(data_iter)
        return {
            "agent_id": row.get("class", "veh-1"),
            "position_x": float(row.get("position_x", 0.0)),
            "position_y": float(row.get("position_y", 0.0)),
            "velocity_x": float(row.get("velocity_x", 0.0)),
            "velocity_y": float(row.get("velocity_y", 0.0)),  # may not exist in some CSVs
            "acceleration_x": float(row.get("acceleration_x", 0.0)),
            "yaw": float(row.get("yaw", 0.0) if "yaw" in row else 0.0),
            "altitude": float(row.get("altitude", 0.0) if "altitude" in row else 0.0)
        }
    else:
        import carla
        client = carla.Client('localhost', 2000)
        client.set_timeout(10.0)
        world = client.get_world()
        vehicle = world.get_actors().filter('vehicle.*')[0]
        velocity = vehicle.get_velocity()
        accel = vehicle.get_acceleration()
        loc = vehicle.get_location()
        return {
            "agent_id": "veh-live",
            "position_x": loc.x,
            "position_y": loc.y,
            "velocity_x": velocity.x,
            "velocity_y": velocity.y,
            "acceleration_x": accel.x,
            "yaw": getattr(vehicle.get_transform().rotation, "yaw", 0.0),
            "altitude": getattr(loc, "z", 0.0)
        }
