import serpapi
import pandas as pd
import json
import time
import os
import random
import logging
from pathlib import Path
from datetime import datetime, timedelta
from serpapi import GoogleSearch
from dotenv import load_dotenv

# ------------------------------
# Environment Setup
# ------------------------------

# Load API from .env
load_dotenv()
api = os.environ.get("SERPAPI_KEY")

# ------------------------------
# Search Parameters
# ------------------------------

# Target routes
destinations = ["BKK", "NRT", "LHR", "MEL"]

# Outbound travel dates
today = datetime.now()
outbound_dates = [
    (today + timedelta(days = random.randint(1,30))).strftime("%Y-%m-%d"),
    (today + timedelta(days = random.randint(31,60))).strftime("%Y-%m-%d"),
    (today + timedelta(days = random.randint(61,120))).strftime("%Y-%m-%d"),
    (today + timedelta(days = random.randint(121,180))).strftime("%Y-%m-%d")
]

# Search date / extracted date
extracted_date_str = datetime.now().strftime("%Y-%m-%d")

# ------------------------------
# Logging Setup
# ------------------------------

# NOTE: paths are relative to the repo root - run this script from there
# (e.g. `python pipeline/extract_flight_data.py`), which is how the GitHub Actions
# workflow invokes it.
LOG_DIR = Path("logs/flight_log")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# This module is imported and driven by extraction_process.py, which sets up its own
# logger too - propagate=False stops records from also bubbling up to the root logger,
# which would otherwise duplicate/mix output between modules.
logger.propagate = False

if not logger.handlers:
    _formatter = logging.Formatter('%(asctime)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    _file_handler = logging.FileHandler(LOG_DIR / f"flight_log_{extracted_date_str}.txt", encoding='utf-8')
    _file_handler.setFormatter(_formatter)
    _stream_handler = logging.StreamHandler()
    _stream_handler.setFormatter(_formatter)
    logger.addHandler(_file_handler)
    logger.addHandler(_stream_handler)

# ===============================

def extract_flight_data():
    if not api:
        logger.error("Critical error: API key is not found in environment variables. Check your .env file.")
        return
        
    # Loop through travel dates independently 
    # NOTE: paths are relative to the repo root - run this script from there
    # (e.g. `python pipeline/extract_flight_data.py`), which is how the GitHub Actions
    # workflow invokes it.
    os.makedirs("data/raw", exist_ok=True)

    for outbound_date in outbound_dates:
        date_batch_responses = {}
        filename = os.path.join("data/raw", f"serpapi_response_{outbound_date}_search{extracted_date_str}.json")
    
        # Loop through destinations 
        for dest in destinations:
    
            #Building vice-versa bidirectional segments
            sectors = [
                {"from": "SIN", "to": dest, "direction": "outbound"},
                {"from": dest, "to": "SIN", "direction": "inbound"}
            ]
    
            # Execute outbound followed by return leg
            for sector in sectors:
                dep = sector["from"]
                arr = sector["to"]
                direction_flag = sector["direction"]
                route_label = f"{dep}-{arr}_{outbound_date}"
    
                # Building the parameters
                params = {
                    "engine": "google_flights",
                    "departure_id": dep,
                    "arrival_id": arr,
                    "currency": "SGD",
                    "type": "2",
                    "outbound_date": outbound_date,
                    "gl":"sg",
                    "hl":"en",
                    "sort_by":"2",
                    "stops":"1",
                    "api_key":api
                }
    
                try:
                    search = GoogleSearch(params)
                    results = search.get_dict()
    
                    if "error" in results: 
                        date_batch_responses[route_label] = {"status": "error", "message": results["error"]}
                    else: 
                        best_count = len(results.get("best_flights", []))
                        other_count = len(results.get("other_flights", []))
    
                        # Store results under its route market index key
                        date_batch_responses[route_label] = results
    
                except Exception as e:
                    logger.error(f"Connection breakdown for {route_label}: {e}")
                    date_batch_responses[route_label] = {"status": "failed", "message": str(e)}
    
                # 2-second delay barrier to regulate request volume saefty
                time.sleep(2)

        # Exporting files to JSON
        try:
            with open(filename, "w", encoding="utf-8") as json_file:
                json.dump(date_batch_responses, json_file, indent=4, ensure_ascii=False)
    
        except Exception as file_err:
            logger.error(f"Critical file saving failure on: {file_err}")

def main():
    start_time = time.time()
    try:
        logger.info("=" * 70)
        logger.info("Extraction run started")

        extract_flight_data()

        elapsed = round(time.time() - start_time, 2)
        logger.info(f"Extraction sequence complete. Job closed in {elapsed} seconds. Logs at: {LOG_DIR}")
    except Exception:
        logger.exception("Extraction run failed")
        raise

if __name__ == "__main__":
    main()