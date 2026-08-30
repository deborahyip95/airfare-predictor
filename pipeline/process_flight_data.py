import json
import os
import shutil
import time
import logging
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

try:
    import holidays
except ImportError:
    raise ImportError("The 'holidays' package is missing. Please run 'pip install holidays' before executing.")

# ------------------------------
# Environment Setup
# ------------------------------

source_dir = 'data/raw'
serpapi_csv = 'data/serpapi_response.csv'
feature_csv = 'data/feature_batch.csv'
dataset_csv = 'data/dataset.csv'
LCC_xlsx = 'data/LCC List.xlsx'

# Only support up till 182 days out
MAX_SUPPORTED_BOOKING_WINDOW_DAYS = 182

today_str = datetime.now().strftime('%Y-%m-%d')

# Archiving schema paths
processed_json_dir = 'data/serpapi_response/Processed serpapi_response'
serpapi_archive_dir = 'data/serpapi_response/serpapi_response_archive'
feature_archive_dir = 'data/feature_archive'
dataset_archive_dir = 'data/dataset_archive'

# ------------------------------
# Logging Setup
# ------------------------------

LOG_DIR = Path("logs/process_log")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# This module is imported and driven by extraction_process.py, which sets up its own
# logger too - propagate=False stops records from also bubbling up to the root logger,
# which would otherwise duplicate/mix output between modules.
logger.propagate = False

if not logger.handlers:
    _formatter = logging.Formatter('%(asctime)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    _file_handler = logging.FileHandler(LOG_DIR / f"process_log_{today_str}.txt", encoding='utf-8')
    _file_handler.setFormatter(_formatter)
    _stream_handler = logging.StreamHandler()
    _stream_handler.setFormatter(_formatter)
    logger.addHandler(_file_handler)
    logger.addHandler(_stream_handler)

def initialise_environment():
    """Dynamically ensures all operational and archival directories exist."""
    directories = [
        source_dir,
        processed_json_dir,
        serpapi_archive_dir,
        feature_archive_dir,
        dataset_archive_dir
    ]
    for directory in directories: 
        os.makedirs(directory, exist_ok=True) 

# ------------------------------
# SerpApi Batch Processing
# ------------------------------

def process_raw_json_batch():
    json_files = [
        os.path.join(source_dir, file)
        for file in os.listdir(source_dir)
        if file.endswith(".json")
    ] 

    logger.info("Step 1: Processing SerpApi JSON batch")
    logger.info(f"Found {len(json_files)} files to process.")

    if not json_files:
        logger.info("No new raw JSON files found.")
        return []

    # Archive the old SerpApi response, if it exists
    if os.path.exists(serpapi_csv):
        archive_file_name = f"serpapi_response_{today_str}.csv"
        archive_path = os.path.join(serpapi_archive_dir, archive_file_name)
        shutil.move(serpapi_csv, archive_path)
        logger.info(f"Successfully archived SerpApi Response file to: {archive_path}")

    all_flattened_data = []

    for file in json_files: 
        processing_successful = False
        try: 
            with open(file, "r", encoding = "utf-8") as f:
                batch_data = json.load(f)

            for route_label, data in batch_data.items():
                if not isinstance(data, dict):
                    logger.warning(f"Skipping {route_label}: Data is not a dictionary.")
                    continue
                if "search_parameters" not in data:
                    logger.warning(f"Skipping {route_label}: Missing 'search_parameters'.")
                    continue

                search_metadata = data.get("search_metadata", {})
                search_parameters = data.get("search_parameters", {})
        
                date_str = search_metadata.get("processed_at", "")[:10]
                departure_str = search_parameters.get("outbound_date", "")
        
                date = datetime.strptime(date_str, "%Y-%m-%d")
                departure_date = datetime.strptime(departure_str, "%Y-%m-%d")

                # Time-based features
                days_to_departure = (departure_date - date).days
                day_of_week = departure_date.weekday() 
                day_name = departure_date.strftime("%A")
                is_weekend = day_of_week in [4, 5, 6]
        
                # Booking Window logic
                if days_to_departure <= 0:
                    booking_window = "0 days"
                else: 
                    lower_bound = ((days_to_departure - 1) // 14) * 14 + 1
                    upper_bound = lower_bound + 13
                    booking_window = f"{lower_bound}-{upper_bound} days"

                # Label features
                departure_airport = search_parameters.get("departure_id")
                arrival_airport = search_parameters.get("arrival_id")
                other_airport = arrival_airport if departure_airport == "SIN" else departure_airport
        
                all_itineraries = data.get("best_flights", []) + data.get("other_flights", [])
        
                for flight in all_itineraries: 
                    price = flight.get("price")
                    if not price:
                        continue
        
                    flights_segments = flight.get("flights", [])
                    first_segment = flights_segments[0] if flights_segments else {}
                    
                    airline = first_segment.get("airline", "Unknown Airline")
                    raw_flight_num = first_segment.get("flight_number", "")
                    airline_code = raw_flight_num[:2] if raw_flight_num else "NIL"

                    row_record = {
                        "date": date_str,
                        "route": f"{departure_airport}-{arrival_airport}",
                        "departure_date": departure_str,
                        "airline": airline,
                        "airline_code": airline_code,
                        "price": float(price),
                        "days_to_departure": days_to_departure,
                        "day_of_week": day_of_week,
                        "day_name": day_name,
                        "is_weekend": is_weekend,
                        "departure_airport": departure_airport,
                        "out_inbound": 1 if departure_airport == "SIN" else 2,
                        "other_airport": other_airport,
                        "data_source": "api",
                        "booking_window": booking_window
                    }
                    all_flattened_data.append(row_record)
                
                processing_successful = True

        except Exception:
            # logger.exception (rather than logger.error) also captures the full traceback,
            # which is invaluable once this only runs unattended in GitHub Actions.
            logger.exception(f"Error processing file {file}")

        # Archive processed raw JSON file
        if processing_successful:
            file_name = os.path.basename(file)
            dest_path = os.path.join(processed_json_dir, file_name)
            shutil.move(file, dest_path)
            logger.info(f"Moved processed file to archive: {dest_path}")
        else:
            logger.warning(f"{file} left in source directory due to processing failure.")

    if all_flattened_data:
        flat_df = pd.DataFrame(all_flattened_data)
        flat_df.to_csv(serpapi_csv, index=False)
        logger.info(f"Serpapi cleaning complete. New batch saved as: {serpapi_csv}")
        return flat_df
    else:
        logger.info("No new data parsed this execution run.")
        return []

# ------------------------------
# Feature Engineering
# ------------------------------

#   Mon: weekend attaches for free (Sat-Sun-Mon), plus a one-day bridge on the preceding Fri.
#   Tue: a one-day bridge on the preceding Mon reaches the prior weekend (Sat-Sun-Mon-Tue).
#   Wed: no single day reaches either weekend - just the holiday itself.
#   Thu: a one-day bridge on the following Fri reaches the next weekend (Thu-Fri-Sat-Sun).
#   Fri: weekend attaches for free (Fri-Sat-Sun), plus a one-day bridge on the following Mon.
#   Sat/Sun: already a non-work day - no bridge needed or possible.

HOLIDAY_DAY_OFFSETS = {
    0: [-3, -2, -1, 0],   # Monday
    1: [-3, -2, -1, 0],   # Tuesday
    2: [0],               # Wednesday
    3: [0, 1, 2, 3],       # Thursday
    4: [0, 1, 2, 3],       # Friday
    5: [0],               # Saturday
    6: [0],               # Sunday
}

def generate_holiday_lookup_set(country_iso, years_range):
    """Build the set of dates considered "holiday-adjacent" for elevated travel demand -
    see HOLIDAY_DAY_OFFSETS above for the reasoning behind which days get included."""
    country_hols = holidays.country_holidays(country_iso, years=years_range)
    expanded_set = set()

    for h_date in country_hols.keys():
        for offset in HOLIDAY_DAY_OFFSETS[h_date.weekday()]:
            expanded_set.add(h_date + timedelta(days=offset))

    return expanded_set

def apply_feature_enrichment(df):
    logger.info("Step 2: Applying Feature Engineering")
    if isinstance(df, list) or df.empty:
        logger.info("No new batch data available to enrich.")
        return None

    # Archive the old feature batch data, if it exists
    if os.path.exists(feature_csv):
        archive_file_name = f"feature_batch_{today_str}.csv"
        archive_path = os.path.join(feature_archive_dir, archive_file_name)
        shutil.move(feature_csv, archive_path)
        logger.info(f"Successfully archived old feature batch to: {archive_path}")

    df['departure_date'] = pd.to_datetime(df['departure_date'])
    start_year = df['departure_date'].min().year
    end_year = df['departure_date'].max().year 
    years_range = list(range(start_year, end_year + 1))

    # 1. Map Public Holidays
    airport_to_country = {'LHR': 'GB', 'NRT': 'JP', 'BKK': 'TH', 'MEL': 'AU', 'SIN': 'SG'}
    sg_bridged_set = generate_holiday_lookup_set('SG', years_range)
    df['is_holiday_sin'] = df['departure_date'].dt.date.isin(sg_bridged_set).astype(int)

    dest_maps = {code: generate_holiday_lookup_set(iso, years_range) for code, iso in airport_to_country.items() if code != 'SIN'}

    def dest_holiday(row):
        dest = row['other_airport']
        if dest not in dest_maps:
            return 0
        return 1 if row['departure_date'].date() in dest_maps[dest] else 0

    df['is_holiday_other'] = df.apply(dest_holiday, axis=1)
    logger.info("Public holidays feature engineering completed.")

    # 2. Map (Singapore) School Holidays
    def check_school_holiday(row):
        flight_date = row['departure_date'].date()
        current_year = flight_date.year
        month = flight_date.month

        if month in [6, 12]:
            return 1

        for target_month in [6, 12]:
            day1 = datetime(current_year, target_month, 1).date()
            day1_weekday = day1.weekday() # 5 = Sat; 6 = Sun
            if day1_weekday == 5 and flight_date == (day1 - timedelta(days=1)):
                return 1
            if day1_weekday == 6 and flight_date == (day1 - timedelta(days=2)):
                return 1
        return 0

    df['is_sch_holiday'] = df.apply(check_school_holiday, axis=1)
    logger.info("School holidays feature engineering completed.")

    # 3. Carrier Classification (LCC vs FSC)
    if os.path.exists(LCC_xlsx):
        df_lcc = pd.read_excel(LCC_xlsx)
        lcc_col_name = 'airline_code' if 'airline_code' in df_lcc.columns else df_lcc.columns[1]
        lcc_set = set(df_lcc[lcc_col_name].astype(str).str.strip().str.upper())
        df['is_lcc'] = np.where(df['airline_code'].isin(lcc_set), 1, 0)
        logger.info("Carrier classification applied successfully using mapping index.")
    else:
        logger.warning(f"'{LCC_xlsx}' not found. Defaulting 'is_lcc' flags to 0.")
        df['is_lcc'] = 0

    df.to_csv(feature_csv, index=False)
    logger.info(f"Feature enrichment complete. Consolidated batch saved to: {feature_csv}")
    return df

# ------------------------------
# Integration
# ------------------------------

def integrate_and_finalize_dataset(batch_df):
    """Merges processed batch features with historical master data, enforces integrity, and runs automated QA."""
    logger.info("Step 3: Master Dataset Assembly & Validation")
    if batch_df is None or batch_df.empty:
        logger.warning("Pipeline sequence halted: No updated features available for integration.")
        return

    existing_df = pd.DataFrame()

    # Check-archive existing production dataset asset
    if os.path.exists(dataset_csv):
        try:
            existing_df = pd.read_csv(dataset_csv)
            logger.info(f"Loaded {len(existing_df)} existing historical records from {dataset_csv}")

            archive_file_name = f"dataset_{today_str}.csv"
            archive_path = os.path.join(dataset_archive_dir, archive_file_name)
            shutil.copy(dataset_csv, archive_path)
            logger.info(f"Successfully archived master backup copy to: {archive_path}")
        except Exception:
            logger.exception(f"Issue reading existing {dataset_csv}. Starting fresh.")

    # Standardize types before concatenation to avoid warning boundaries
    if not existing_df.empty:
        existing_df['departure_date'] = pd.to_datetime(existing_df['departure_date'], dayfirst=True, format='mixed', errors='coerce')
        batch_df['departure_date'] = pd.to_datetime(batch_df['departure_date'], dayfirst=True, format='mixed', errors='coerce')
        combined_df = pd.concat([existing_df, batch_df], axis=0, ignore_index=True)
    else:
        combined_df = batch_df

    # Deduplication Engine
    dedup_keys = ['date', 'route', 'departure_date', 'airline', 'price']
    available_keys = [key for key in dedup_keys if key in combined_df.columns]

    initial_count = len(combined_df)
    combined_df = combined_df.drop_duplicates(subset=available_keys, keep='first')
    dropped_rows = initial_count - len(combined_df)

    if dropped_rows > 0:
        logger.info(f"Data Integrity Enforcement: Removed {dropped_rows} redundant record variants.")

    # Scope Guard: drop any record beyond the currently-supported booking window (see
    # MAX_SUPPORTED_BOOKING_WINDOW_DAYS above). Runs on the full combined dataset, so this
    # also prunes old out-of-scope rows left over from before the extraction range was
    # narrowed, not just new ones.
    if 'days_to_departure' in combined_df.columns:
        before_scope_count = len(combined_df)
        combined_df = combined_df[combined_df['days_to_departure'] <= MAX_SUPPORTED_BOOKING_WINDOW_DAYS]
        dropped_out_of_scope = before_scope_count - len(combined_df)
        if dropped_out_of_scope > 0:
            logger.info(f"Scope Guard: Removed {dropped_out_of_scope} record(s) beyond the {MAX_SUPPORTED_BOOKING_WINDOW_DAYS}-day supported booking window.")

    # Save finalized output file
    combined_df.to_csv(dataset_csv, index=False)
    logger.info(f"Production Master Database committed successfully at: {dataset_csv}")

    # Audit and Quality Assurance Check
    logger.info("--- Automated Quality Assurance Log ---")
    qa_columns = [
        'route', 'is_weekend', 'departure_airport', 'out_inbound',
        'other_airport', 'data_source', 'booking_window', 'airline',
        'airline_code', 'is_lcc', 'is_holiday_sin', 'is_holiday_other', 'is_sch_holiday'
    ]
    for col in qa_columns:
        if col in combined_df.columns:
            unique_vals = list(combined_df[col].dropna().unique())
            try:
                unique_vals = sorted(unique_vals)
            except TypeError:
                pass
            logger.info(f"  Column [ {col:18} ] -> Distinct Entries ({len(unique_vals)}): {unique_vals}")

# ------------------------------
# Main Run
# ------------------------------

def main():
    start_time = time.time()
    try:
        logger.info("=" * 60)
        logger.info("Starting Automated Flight Data Integration Pipeline")

        # Run the setup steps in sequential dependencies
        initialise_environment()
        raw_cleaned_batch = process_raw_json_batch()
        enriched_feature_batch = apply_feature_enrichment(raw_cleaned_batch)
        integrate_and_finalize_dataset(enriched_feature_batch)

        elapsed = round(time.time() - start_time, 2)
        logger.info(f"Execution Finished Successfully! Master Data Ready. Total Time Elapsed: {elapsed} seconds. Logs at: {LOG_DIR}")

    except Exception:
        # Audit Trail: logger.exception captures the full traceback, not just the message
        logger.exception("Pipeline execution failed")
        raise

if __name__ == "__main__":
    main()