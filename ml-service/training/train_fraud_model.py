import os
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

os.makedirs("models", exist_ok=True)
np.random.seed(42)
n_samples = 2500

# Features: [submission_time_gap_seconds, similar_recent_applications, device_change_flag]
X_fraud = np.column_stack([
    np.random.normal(120, 40, n_samples).clip(1, 600),
    np.random.poisson(0.5, n_samples),
    np.random.binomial(1, 0.05, n_samples)
])

fraud_model = IsolationForest(contamination=0.08, random_state=42)
fraud_model.fit(X_fraud)
joblib.dump(fraud_model, "models/fraud_model.pkl")
print("Saved models/fraud_model.pkl")