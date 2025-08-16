# carla_telemetery.py
import numpy as np
import csv
import itertools

# Set this to your dataset path to use pre-recorded data
DATASET_PATH = "dataset.csv"  # CSV with velocity, accel, loc_x, loc_y
USE_DATASET = True

if USE_DATASET:
    dataset_file = open(DATASET_PATH, newline='')
    reader = csv.reader(dataset_file)
    next(reader)  # skip header if exists
    data_iter = itertools.cycle(reader)  # loop forever

def get_telemetry():
    if USE_DATASET:
        row = next(data_iter)
        return np.array([float(row[0]), float(row[1]), float(row[2]), float(row[3])])
    else:
        import carla
        client = carla.Client('localhost', 2000)
        client.set_timeout(10.0)
        world = client.get_world()
        vehicle = world.get_actors().filter('vehicle.*')[0]
        velocity = vehicle.get_velocity()
        accel = vehicle.get_acceleration()
        loc = vehicle.get_location()
        return np.array([velocity.x, accel.x, loc.x, loc.y])
