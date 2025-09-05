import pandas as pd
import numpy as np

# Load dataset
df = pd.read_csv("full_data_carla.csv")

# Drop useless index column
df.drop(columns=["Unnamed: 0"], inplace=True)

# Interpolate missing values
df = df.interpolate(method="linear").fillna(method="bfill").fillna(method="ffill")

# Standardised timestep
dt = 0.1  

# Create telemetry vectors
df["acceleration_x"] = df["accelX"]
df["velocity_x"] = np.cumsum(df["acceleration_x"] * dt)
df["position_x"] = np.cumsum(df["velocity_x"] * dt)

df["acceleration_y"] = df["accelY"]
df["velocity_y"] = np.cumsum(df["acceleration_y"] * dt)
df["position_y"] = np.cumsum(df["velocity_y"] * dt)

# Keep only required columns
telemetry_df = df[["velocity_x", "acceleration_x", "position_x", "position_y", "class"]]

# Split by driver behaviour
for behaviour, subset in telemetry_df.groupby("class"):
    filename = f"telemetry_{behaviour}.csv"
    subset.to_csv(filename, index=False)
    print(f"Saved: {filename}")
