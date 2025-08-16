# anomaly_detector.py
from sklearn.ensemble import IsolationForest
import numpy as np
import joblib

# Train using simulated telemetry data (e.g., speed, acceleration, GPS)
def train_anomaly_detector(data: np.ndarray, model_path="anomaly_model.pkl"):
    clf = IsolationForest(contamination=0.05)
    clf.fit(data)
    joblib.dump(clf, model_path)

def predict_anomalies(data: np.ndarray, model_path="anomaly_model.pkl"):
    clf = joblib.load(model_path)
    return clf.predict(data)  # -1 = anomaly, 1 = normal
