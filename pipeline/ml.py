import joblib
import shutil
import logging
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, mean_absolute_percentage_error

# ------------------------------
# Environment Setup
# -----------------------------

RUN_TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')

Path('logs').mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(f'logs/training_{RUN_TIMESTAMP}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# NOTE: paths are relative to the repo root - run this script from there
# (e.g. `python pipeline/ml.py`), which is how the GitHub Actions workflow invokes it.
DATASET_PATH = 'data/dataset.csv'
MODEL_PATH = 'src/flight_predictor_rf.joblib'
SCHEMA_PATH = 'src/model_feature_schema.joblib'
# Written every run so README.md's performance section can be regenerated from real numbers
METRICS_PATH = 'data/model_metrics.json'

def import_df():
    return pd.read_csv(DATASET_PATH)

# ------------------------------
# Data Processing
# ------------------------------ 

def process_data(df):
    # Handle date formatting and sorting them chronologically
    df['date'] = pd.to_datetime(df['date'], dayfirst=True, format='mixed', errors='coerce')
    df = df.sort_values('date').reset_index(drop = True)

    # Boolean sanitisation - ensure that all boolean fields are shown as 0 or 1.
    for col in ['is_weekend', 'is_lcc', 'is_holiday_sin', 'is_holiday_other', 'is_sch_holiday']:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.upper().map({'TRUE': 1, 'FALSE': 0, '1': 1, '0': 0})
        else:
            df[col] = df[col].astype(int)

    # Extract departure month from deaprture date for seasonal features
    df['departure_date'] = pd.to_datetime(df['departure_date'], dayfirst=True, format='mixed', errors='coerce')
    df['departure_month'] = df['departure_date'].dt.month

    return df

# ------------------------------
# Feature Selection and Encoding
# ------------------------------ 

def select_features(df):
    # Selecting features and one-hot encoding
    core_features = [
        'booking_window',
        'day_of_week',
        'is_weekend',
        'is_lcc',
        'is_holiday_sin',
        'is_holiday_other',
        'is_sch_holiday',
        'route',
        'departure_month']

    X = pd.get_dummies(df[core_features], columns = ['route','booking_window'], drop_first = True)
    y = df['price']

    return X, y

# ------------------------------
# Model Training and Evaluation
# ------------------------------ 

def split_data(X, y, booking_window, test_frac=0.2):
    """Split based on each bucket in chronological order to guarantee each bucket gets a 
    proportionate coverage"""
    dev_indices = []
    test_indices = []

    for bucket, group in booking_window.groupby(booking_window):
        bucket_split = int(len(group) * (1 - test_frac))
        dev_indices.extend(group.index[:bucket_split])
        test_indices.extend(group.index[bucket_split:])
        logger.info(f"  Booking window [{bucket:>14}]: {len(group)} records -> {bucket_split} dev / {len(group) - bucket_split} test")

    dev_indices = sorted(dev_indices)
    test_indices = sorted(test_indices)

    X_dev, X_test = X.loc[dev_indices], X.loc[test_indices]
    y_dev, y_test = y.loc[dev_indices], y.loc[test_indices]
    bw_dev, bw_test = booking_window.loc[dev_indices], booking_window.loc[test_indices]

    logger.info(f"Total historical matrix depth: {X.shape[0]} records")
    logger.info(f"Development pool: {X_dev.shape[0]} records")
    logger.info(f"Hidden validation pool: {X_test.shape[0]} records")

    return X_dev, X_test, y_dev, y_test, bw_dev, bw_test

def cross_validate_model(X_dev, y_dev):
    tscv = TimeSeriesSplit(n_splits =5)
    cv_mae_scores = []

    for fold, (train_idx, val_idx) in enumerate(tscv.split(X_dev)):
        X_cv_train, X_cv_val = X_dev.iloc[train_idx], X_dev.iloc[val_idx]
        y_cv_train, y_cv_val = y_dev.iloc[train_idx], y_dev.iloc[val_idx]

        # Train localised fold trees to evaluate feature stability
        fold_rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        fold_rf.fit(X_cv_train, y_cv_train)
        fold_pred = fold_rf.predict(X_cv_val)
        cv_mae_scores.append(mean_absolute_error(y_cv_val, fold_pred))

        logger.info(f"  Fold {fold+1} Validation MAE: {cv_mae_scores[-1]:.2f} SGD")

    logger.info(f"Mean Inner CV MAE: {np.mean(cv_mae_scores):.2f} SGD")

    return cv_mae_scores

def train_final_model(X_dev, y_dev, X_test):
    rf_master = RandomForestRegressor(
        n_estimators=250,
        max_depth=18,
        min_samples_split=3,
        random_state=42,
        n_jobs=-1
    )

    # Fit on full 80% development pool history
    rf_master.fit(X_dev, y_dev)

    # Generate blind guesses for the hidden 20% future pool
    holdout_predictions = rf_master.predict(X_test)

    return rf_master, holdout_predictions

def _bucket_sort_key(label):
    """Sorts booking_window labels ("1-14 days", "43-56 days", ...) by their lower bound,
    so log/README output reads earliest-lead-time-first instead of alphabetically."""
    try:
        return int(str(label).split('-')[0].split(' ')[0])
    except (ValueError, IndexError):
        return 0

def evaluate_bucket_mape(y_test, holdout_predictions, booking_window_test):
    """Break the holdout MAPE down by booking_window bucket, so a well-covered bucket can't
    hide a poorly-covered one behind one blended aggregate score."""
    results_df = pd.DataFrame({
        'booking_window': booking_window_test.reset_index(drop=True),
        'y_true': pd.Series(y_test).reset_index(drop=True),
        'y_pred': holdout_predictions
    })

    bucket_mape = {}
    for bucket in sorted(results_df['booking_window'].unique(), key=_bucket_sort_key):
        group = results_df[results_df['booking_window'] == bucket]
        mape = mean_absolute_percentage_error(group['y_true'], group['y_pred'])
        bucket_mape[bucket] = {
            'mape_pct': round(float(mape) * 100, 1),
            'n_test_records': int(len(group))
        }
        logger.info(f"  Holdout MAPE [{bucket:>14}]: {mape*100:5.1f}% (n={len(group)})")

    return bucket_mape

# ------------------------------
# Model Archiving
# ------------------------------

def archive_existing_file(filepath, archive_dir='archive'):
    """Move an existing file into an archive folder, tagging it with the date it was last run/saved."""
    path = Path(filepath)
    if not path.exists():
        return  # nothing to archive on a first run

    Path(archive_dir).mkdir(exist_ok=True)
    run_date = datetime.fromtimestamp(path.stat().st_mtime).strftime('%Y%m%d_%H%M%S')
    archived_path = Path(archive_dir) / f"{path.stem}_{run_date}{path.suffix}"
    shutil.move(str(path), archived_path)
    logger.info(f"Archived previous file: {path.name} -> {archived_path}")

def export_model(rf_master, X):
    """Archive any previous model artifacts, then save the newly trained model and its feature schema."""
    archive_existing_file(MODEL_PATH, archive_dir='data/model_archive')
    archive_existing_file(SCHEMA_PATH, archive_dir='data/model_archive')

    joblib.dump(rf_master, MODEL_PATH)

    model_columns = list(X.columns)
    joblib.dump(model_columns, SCHEMA_PATH)

    logger.info("Trained model and feature schema saved.")

def export_metrics(n_records, n_dev, n_test, cv_mae_scores, holdout_mae, holdout_rmse, holdout_r2, holdout_mape, bucket_mape, missing_from_holdout):
    """Write this run's evaluation numbers to METRICS_PATH so README.md's performance
    section can be regenerated from real, current results - see pipeline/update_readme.py."""
    metrics = {
        "run_timestamp_utc": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        "n_records": int(n_records),
        "n_dev_records": int(n_dev),
        "n_test_records": int(n_test),
        "mean_cv_mae_sgd": round(float(np.mean(cv_mae_scores)), 2),
        "holdout_mae_sgd": round(float(holdout_mae), 2),
        "holdout_rmse_sgd": round(float(holdout_rmse), 2),
        "holdout_r2": round(float(holdout_r2), 4),
        "holdout_mape_pct": round(float(holdout_mape) * 100, 1),
        "bucket_mape": bucket_mape,
        "buckets_missing_from_holdout": list(missing_from_holdout),
    }
    Path(METRICS_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(METRICS_PATH, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Model metrics written to {METRICS_PATH}")

def main():
    # Import the dataset
    df = import_df()

    # Process the data
    df_processed = process_data(df)

    # Select features and target variable
    X, y = select_features(df_processed)

    # Split the data into development and test sets
    X_dev, X_test, y_dev, y_test, bw_dev, bw_test = split_data(X, y, df_processed['booking_window'])

    # Cross-validate the model on the development set
    cv_mae_scores = cross_validate_model(X_dev, y_dev)

    # Train the final model on the full development set and make predictions on the test set
    rf_master, holdout_predictions = train_final_model(X_dev, y_dev, X_test)

    # Evaluate the model on the test set
    holdout_mae = mean_absolute_error(y_test, holdout_predictions)
    holdout_rmse = np.sqrt(mean_squared_error(y_test, holdout_predictions))
    holdout_r2 = r2_score(y_test, holdout_predictions)
    holdout_mape = mean_absolute_percentage_error(y_test, holdout_predictions)

    logger.info(f"Holdout Mean Absolute Error (MAE):   {holdout_mae:.2f} SGD")
    logger.info(f"Holdout Root Mean Squared Error (RMSE): {holdout_rmse:.2f} SGD")
    logger.info(f"Holdout Variance Coverage (R² Score):   {holdout_r2:.4f} ({holdout_r2*100:.2f}%)")
    logger.info(f"Holdout Mean Absolute Percentage Error (MAPE): {holdout_mape*100:.2f}%")

    # Break the same holdout down per booking_window bucket, so a well-covered bucket can't
    # mask a poorly-covered one behind the blended aggregate above.
    logger.info("Holdout MAPE by booking window:")
    bucket_mape = evaluate_bucket_mape(y_test, holdout_predictions, bw_test)

    # The chronological 80/20 split can leave some buckets with zero holdout rows entirely
    # (e.g. a bucket only ever collected before the split point) - flag those explicitly
    # rather than letting their absence from the table above go unnoticed.
    missing_from_holdout = sorted(set(bw_dev.unique()) - set(bw_test.unique()), key=_bucket_sort_key)
    if missing_from_holdout:
        logger.warning(f"Buckets present in training but absent from the holdout split (no error estimate available): {missing_from_holdout}")

    # Record this run's evaluation numbers before the final refit below folds test-set
    # rows back into training - these are what README.md's performance section is built from.
    export_metrics(X.shape[0], X_dev.shape[0], X_test.shape[0], cv_mae_scores,
                    holdout_mae, holdout_rmse, holdout_r2, holdout_mape, bucket_mape,
                    missing_from_holdout)

    # Re-train final model
    rf_master.fit(X, y)

    # Save the model and feature schema (archiving any previous versions first)
    export_model(rf_master, X)

if __name__ == "__main__":
    main()