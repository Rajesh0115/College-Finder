"""
train_ml_model.py — Train a Random Forest Classifier for admission prediction.

This script reads from the SQLite database, generates synthetic admission
outcomes (admitted=1 / not admitted=0) by simulating user percentiles,
and trains a classifier that predicts admission probability via predict_proba().

Output: ml_model.joblib containing model, encoders, scaler, and metadata.
"""

import sqlite3
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, classification_report, confusion_matrix
)
import joblib
import os
import time

# ─── Configuration ───────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_DIR, 'college_data.db')
MODEL_PATH = os.path.join(PROJECT_DIR, 'ml_model.joblib')

RANDOM_STATE = 42
N_ESTIMATORS = 200
MAX_DEPTH = 20
MIN_SAMPLES_SPLIT = 5
TEST_SIZE = 0.2

# Number of synthetic user-percentile samples per real row
SAMPLES_PER_ROW = 5


def load_data():
    """Load cutoff data from SQLite database."""
    print(f"Loading data from {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM cutoffs WHERE Score > 0", conn)
    conn.close()
    print(f"  Loaded {len(df)} rows")
    return df


def generate_training_data(df):
    """
    Generate training dataset with synthetic admission outcomes.

    For each real cutoff row, we simulate multiple 'user scenarios':
    - If user_percentile >= cutoff_score → admitted = 1
    - If user_percentile < cutoff_score  → admitted = 0

    We also compute percentile_diff = user_percentile - cutoff_score
    as a key feature for the model.
    """
    print("Generating training data with synthetic admission outcomes...")

    np.random.seed(RANDOM_STATE)
    rows = []

    for _, row in df.iterrows():
        cutoff = row['Score']

        for _ in range(SAMPLES_PER_ROW):
            # Generate user percentile: mix of near-cutoff and random
            if np.random.random() < 0.6:
                # Near cutoff (within ±10) — most informative region
                user_pct = cutoff + np.random.uniform(-10, 10)
            else:
                # Random across full range
                user_pct = np.random.uniform(0, 100)

            user_pct = np.clip(user_pct, 0, 100)
            admitted = 1 if user_pct >= cutoff else 0
            pct_diff = user_pct - cutoff

            rows.append({
                'College_Name': row['College_Name'],
                'Branch_Group': row['Branch_Group'],
                'Category': row['Category'],
                'City': row['City'],
                'Is_TFWS': row['Is_TFWS'],
                'College_ID': row['College_ID'],
                'Branch_ID': row['Branch_ID'],
                'Score': row['Score'],
                'User_Percentile': user_pct,
                'Percentile_Diff': pct_diff,
                'Admitted': admitted,
            })

    train_df = pd.DataFrame(rows)
    admitted_count = train_df['Admitted'].sum()
    total = len(train_df)
    print(f"  Generated {total} training samples")
    print(f"  Admitted: {admitted_count} ({admitted_count/total*100:.1f}%)")
    print(f"  Not Admitted: {total - admitted_count} ({(total-admitted_count)/total*100:.1f}%)")
    return train_df


def train_model(train_df):
    """Train Random Forest Classifier and return model + artifacts."""
    print("\nEncoding features...")

    # Encode categorical variables
    encoders = {}
    for col in ['Branch_Group', 'Category', 'City']:
        le = LabelEncoder()
        train_df[f'{col}_Encoded'] = le.fit_transform(train_df[col].astype(str))
        encoders[col] = le
        print(f"  {col}: {len(le.classes_)} unique values")

    # Normalize Score and User_Percentile
    scaler = MinMaxScaler()
    train_df[['Score_Norm', 'UserPct_Norm']] = scaler.fit_transform(
        train_df[['Score', 'User_Percentile']]
    )

    # Feature columns
    feature_cols = [
        'Score_Norm', 'UserPct_Norm', 'Percentile_Diff',
        'Branch_Group_Encoded', 'Category_Encoded', 'City_Encoded',
        'Is_TFWS', 'College_ID', 'Branch_ID'
    ]

    X = train_df[feature_cols].fillna(-1)
    y = train_df['Admitted']

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )

    print(f"\nTraining Random Forest Classifier...")
    print(f"  Estimators: {N_ESTIMATORS}, Max Depth: {MAX_DEPTH}")
    print(f"  Train: {len(X_train)}, Test: {len(X_test)}")

    start = time.time()
    model = RandomForestClassifier(
        n_estimators=N_ESTIMATORS,
        max_depth=MAX_DEPTH,
        min_samples_split=MIN_SAMPLES_SPLIT,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        class_weight='balanced'
    )
    model.fit(X_train, y_train)
    elapsed = time.time() - start
    print(f"  Training completed in {elapsed:.1f}s")

    # Evaluate
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)

    print(f"\n{'='*50}")
    print(f"  MODEL EVALUATION RESULTS")
    print(f"{'='*50}")
    print(f"  Accuracy:  {accuracy:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1 Score:  {f1:.4f}")
    print(f"\n  Classification Report:")
    print(classification_report(y_test, y_pred, target_names=['Not Admitted', 'Admitted']))

    # Feature importance
    importances = model.feature_importances_
    feat_imp = sorted(zip(feature_cols, importances), key=lambda x: x[1], reverse=True)
    print("\n  Feature Importance:")
    for feat, imp in feat_imp:
        bar = '#' * int(imp * 50)
        print(f"    {feat:30s} {imp:.4f} {bar}")

    return model, encoders, scaler, feature_cols


def save_model(model, encoders, scaler, feature_cols):
    """Save model artifacts to a single joblib file."""
    save_data = {
        'model': model,
        'encoders': encoders,
        'scaler': scaler,
        'feature_cols': feature_cols,
        'version': '2.0',
        'type': 'classifier',
        'description': 'Random Forest Classifier for MHT-CET admission prediction'
    }
    joblib.dump(save_data, MODEL_PATH, compress=3)
    size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)
    print(f"\n  Model saved to: {MODEL_PATH}")
    print(f"  File size: {size_mb:.1f} MB")


if __name__ == '__main__':
    print("=" * 60)
    print("  MHT-CET ADMISSION PREDICTOR — MODEL TRAINING")
    print("=" * 60)

    df = load_data()
    train_df = generate_training_data(df)
    model, encoders, scaler, feature_cols = train_model(train_df)
    save_model(model, encoders, scaler, feature_cols)

    print("\n  Training complete! Model ready for predictions.")
    print("=" * 60)
