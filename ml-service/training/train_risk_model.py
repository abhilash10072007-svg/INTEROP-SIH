import os
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

os.makedirs("models", exist_ok=True)
np.random.seed(42)
n_samples = 2500

# Features: [age, income, existing_loans, avg_monthly_txn, txn_stability_score]
X_risk = np.column_stack([
    np.random.randint(18, 70, n_samples),
    np.random.normal(30000, 15000, n_samples).clip(5000, 200000),
    np.random.randint(0, 5, n_samples),
    np.random.normal(25000, 12000, n_samples).clip(4000, 180000),
    np.random.uniform(0.1, 1.0, n_samples)
])

# Synthetic risk rule
risk_prob = (X_risk[:, 2] * 0.25) + ((50000 - X_risk[:, 1]) / 100000) + (1.0 - X_risk[:, 4]) * 0.4
y_risk = (risk_prob + np.random.normal(0, 0.1, n_samples) > 0.6).astype(int)

risk_model = RandomForestClassifier(n_estimators=50, random_state=42)
risk_model.fit(X_risk, y_risk)
joblib.dump(risk_model, "models/risk_model.pkl")
print("Saved models/risk_model.pkl")