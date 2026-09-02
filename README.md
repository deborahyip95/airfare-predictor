# Taking Turbulence out of Ticket Pricing for the Singapore Traveller
An end-to-end data pipeline and machine learning implementation designed to decode dynamic fare volatility, optimise international flight purchasing windows, and deliver actionable "Buy vs. Wait" decision support for Singapore-hub air travellers.

## Evolution: From Capstone Analysis to Production Pipeline
This repository is an upgrade of my original bootcamp capstone, [`singapore-aviation-pricing`](https://github.com/deborahyip95/singapore-aviation-pricing) - a one-time, notebook-driven analysis built to prove the concept. This version turns that proof-of-concept into an unattended, continuously-updating system:

| | v1 - `singapore-aviation-pricing` | v2 - `airfare_predictor` (this repo) |
|---|---|---|
| **Data collection** | One-time manual pull (Google Flights + WebPlotDigitizer) plus SerpApi scrape | Continuous SerpApi scraping via a scheduled GitHub Actions job (~2 random days/week, plus manual dispatch) |
| **Codebase** | Jupyter notebooks (`notebooks/`) + standalone scripts (`scripts/`) | Modular `pipeline/` package (extract → process → train) orchestrated end-to-end, decoupled from the `src/` dashboard |
| **Model retraining** | Trained once on a static dataset snapshot | Automatically retrained on every scheduled run as new fare data accrues; model + schema versioned via git history, superseded binaries archived under `data/model_archive/` |
| **Dataset size** | Static snapshot | Growing dataset - currently 2,083 records and counting |
| **Documentation** | Manually written metrics | Model-performance section below is auto-updated by `pipeline/update_readme.py` on every run |
| **Deployment loop** | Manual retrain → manual redeploy | Pipeline commits refreshed data/model back to the repo → Streamlit Community Cloud auto-redeploys |
| **Train/test split** | Single chronological 80/20 split across the whole dataset | Chronological 80/20 split done independently *within each* `booking_window` bucket, so every window gets holdout coverage instead of some buckets landing entirely on one side of the cut |
| **Booking window horizon** | Uncapped (bounded only by whatever data had been collected) | Explicitly capped at 182 days (~half a year) via `MAX_SUPPORTED_BOOKING_WINDOW_DAYS`, later widened from an initial 90-day cap as more data accrued |
| **Holiday ("travel event") window** | Fixed ±2-day buffer around each holiday, plus ad-hoc Sat→Fri / Sun→Mon / Mon→Fri(-3d) adjustments | Day-of-week-aware bridge window computed per weekday the holiday falls on (see `HOLIDAY_DAY_OFFSETS`) |

**A note on model metrics:** the original capstone reported a stronger MAPE (19.3%) and R² (85.3%) - but on a small, static, hand-curated dataset. As this pipeline has scaled up to a larger, continuously-collected sample of live market prices, the honest holdout MAPE has settled closer to the high-20s (see the live metrics below). That's expected: a bigger, noisier, real-world sample is a harder - and more honest - prediction target than a small curated one, and it's the tradeoff this upgrade deliberately makes in exchange for a system that keeps learning instead of going stale.

## The Problem
Every traveller knows the frustration of seeing a ticket price jumping overnight. Currently, there is a fundamental information trap. Booking platforms only show today's price with little context on whether that price is a good deal or a temporary spike. Airlines rely on that ambiguity to trigger panic-buying. Our goal is to break that cycle, allowing travellers to make informative decisions instead of emotional ones. 

## Target Audience
1. **Flexible leisure travellers:**
Users seeking value who possess the flexibility to optimise booking dats
2. **Budget-conscious consumers:**
Individuals who require high-precision data to navigate the dynamic pricing and secure low fares.

## Project Scope
By gathering continuous market indicators and building a dedicated machine learning pipeline, this system isolates predictable timeline behaviors over a half-year booking horizon (critical period where airlines dynamically restrict lower-tier fare classes). 

### Flight Routes
It maps out localised fare trajectories for four vital bidirectional routes originating from or returning to Singapore:
* SIN $\leftrightarrow$ Bangkok (BKK)
* SIN $\leftrightarrow$ Tokyo (NRT)
* SIN $\leftrightarrow$ London (LHR)
* SIN $\leftrightarrow$ Melbourne (MEL)

### Carrier Segmentation
The model tracks and segments data across the full fare distribution spectrum:
* Low-Cost Carriers (LCC)
* Full-Service Carriers (FSC)

## The Solution
The engine trains a robust Random Forest machine learning model on fare prices behind an interactive, user-facing Streamlit web dashboard operating across two high-value modes:
* **Predictive Mode (What will it cost?):** A point-in-time lookup allowing travelers to input a departure date and search window to evaluate if a live flight price matches the expected market baseline.
* **Prescriptive Mode (When should I buy?):** An optimization timeline sweep that programmatically checks future booking windows to recommend the absolute minimum price point on the fare curve.

### Random Forest Model Performance and Justification
<!-- MODEL_METRICS_START -->
Milestones achieved *(auto-updated by the scheduled pipeline - last run: 2026-09-01 23:51:11 UTC; 2129 records used for training/CV, 538 held out for the evaluation below, 2667 total)*:
* **Holdout Mean Absolute Percentage Error (MAPE):** 25.9%
* **Holdout Variance Explained (R² Score):** 70.0%
* **Holdout Root Mean Square Error (RMSE):** $399.89

<details><summary>Holdout MAPE by booking window</summary>

| Booking Window | MAPE | Holdout Records |
|---|---|---|
| 1-14 days | 25.7% | 106 |
| 15-28 days | 22.1% | 62 |
| 29-42 days | 25.3% | 80 |
| 43-56 days | 30.1% | 135 |
| 57-70 days | 16.6% | 44 |
| 71-84 days | 20.9% | 35 |
| 85-98 days | 22.8% | 10 |
| 99-112 days | 24.7% | 11 |
| 113-126 days | 18.3% | 19 |
| 127-140 days | 34.0% | 18 |
| 141-154 days | 55.4% | 8 |
| 169-182 days | 37.9% | 10 |

*A bucket with few holdout records is a less reliable estimate of accuracy - not every 14-day window has accumulated enough data yet.*
</details>
<!-- MODEL_METRICS_END -->

### Modeling Methodology
Three non-obvious design decisions moved between the original capstone (`singapore-aviation-pricing`) and this pipeline - see the [Evolution table](#evolution-from-capstone-analysis-to-production-pipeline) above for a side-by-side summary:
* **Per-window train/test split:** the capstone used one chronological 80/20 cutoff across the whole dataset, which can leave an entire `booking_window` bucket sitting only on the training side (or only on the holdout side) if that window's records happen to cluster early or late in the collection history. This pipeline instead splits chronologically 80/20 *within each bucket independently*, so every window that has accumulated data gets some holdout coverage - which is what makes the per-bucket MAPE table above possible. See `split_data()` in `pipeline/ml.py`.
* **182-day booking horizon:** the capstone had no hard cap on how far out a booking window could extend. This pipeline enforces an explicit cap (`MAX_SUPPORTED_BOOKING_WINDOW_DAYS` in `pipeline/process_flight_data.py`), started at 90 days and since widened to 182 days (~half a year) to capture more of the advance-purchase curve airlines use to progressively restrict lower fare classes as departure approaches.
* **"Travel event" (public holiday) window:** the capstone used a fixed ±2-day buffer around each holiday date, with a few hand-added exceptions for holidays landing on Saturday, Sunday, or Monday. This pipeline replaces that with a day-of-week-aware "bridge day" window: a holiday on Thursday or Friday pulls in the following long weekend, one on Monday or Tuesday pulls in the preceding weekend, and a midweek Wednesday holiday only flags itself. See `HOLIDAY_DAY_OFFSETS` in `pipeline/process_flight_data.py` for the exact per-weekday offsets.

### Feature Dictionary
To shift from raw price collection to predictive modeling, the dataset incorporates engineered categorical and temporal layers:
* **Time-Based Features (Temporal):** 
    * `booking_window`: A timeline interval capturing advance purchase curves
    * `departure_month`: Numeric representation tracking the price snapshot collection day
    * `day_of_week`: Binary flag identifying weekend price fluctuations
    * `is_weekend`: Calendar month capturing broader annual seasonality trends
* **Label Features (Categorical Segments):** 
    * `route`: One-way directional sectors setting baseline pricing coordinates
    * `is_lcc`: Categorical indicator isolating Low-Cost Carriers from Full-Service Carriers
* **Demand drivers (External Overlays):** 
    * `is_holiday_sin`: Bridge-day-aware flag mapping Singapore Public Holiday demand shocks (see [Modeling Methodology](#modeling-methodology))
    * `is_holiday_other`: Bridge-day-aware flag mapping destination-specific holiday waves (see [Modeling Methodology](#modeling-methodology))
    * `is_sch_holiday`: Custom flag isolating major Singapore school vacation blocks (June and December)

## The Data Lineage 
The project uses a reliable, repeatable data pipeline to scale up from manual data collection to automated, production-ready extraction.

1. **Phase 1 - Historical Baseline:** Manual extraction of flight prices from Google Flights and using WebPlotDigitizer to establish baseline price-to-departure curves
2. **Phase 2 - Automated Scaling:** Scaling up programmatically using Python requests to query SerpApi
3. **Phase 3 - Feature Enrichment:** Ingestion of external categorical layers
4. **Phase 4 - Storage and Staging:** Data cleaning scripts that fix text formats, unpack raw API data, and safely remove duplicate records while preserving real flight options.

### Repository Directory Structure
```text
├── .github/workflows/
│   └── data_pipeline.yml           # Scheduled GitHub Actions run: extract -> process -> train -> commit
├── data/
│   ├── dataset.csv                 # Master training dataset
│   ├── LCC List.xlsx               # Low-cost-carrier code mapping used during feature enrichment
│   ├── raw/                        # Incoming SerpApi JSON dumps (gitignored, regenerated each run)
│   ├── serpapi_response/           # Archived raw/processed SerpApi batches (gitignored)
│   ├── feature_archive/            # Dated snapshots of engineered feature batches
│   └── dataset_archive/            # Dated backups of the master dataset
├── pipeline/
│   ├── extract_flight_data.py      # API data extraction (SerpApi)
│   ├── process_flight_data.py      # Data cleaning, feature engineering, dataset integration
│   ├── extraction_process.py       # Orchestrates extraction + processing (pipeline step 1)
│   └── ml.py                       # Model training and export (pipeline step 2)
├── src/
│   ├── app.py                      # Streamlit web application dashboard execution script
│   ├── flight_predictor_rf.joblib  # Trained model, refreshed by pipeline/ml.py
│   ├── model_feature_schema.joblib # Feature schema paired with the trained model
│   ├── airside_background.png
│   └── .streamlit/config.toml
├── logs/                           # Run logs from every pipeline stage (gitignored)
├── requirements.txt                # Project dependencies and environment tracking
├── .gitignore                      # Enforces exclusion of local .env, logs, and raw payload dumps
└── README.md                       # Repository documentation front page
```

### Automated Pipeline (GitHub Actions)
`pipeline/ml.py`, `pipeline/extract_flight_data.py`, and `pipeline/process_flight_data.py` are designed to be run from the repository root (all their internal paths are root-relative), which is how `.github/workflows/data_pipeline.yml` invokes them on a schedule. To enable it on your own fork/repo:
1. Add your SerpApi key as a repository secret named `SERPAPI_KEY` (Settings → Secrets and variables → Actions).
2. The workflow extracts new fares, re-processes `data/dataset.csv`, retrains the model into `src/`, and commits the results back - Streamlit Community Cloud then auto-redeploys on that push.
3. You can also trigger a run manually from the Actions tab (`workflow_dispatch`).
### Setup & Local Deployment Guide

**Environment Setup:** Clone the repository, create a clean virtual environment, and install the tracked project dependencies:
```
1. Navigate into the project folder 
cd airfare_predictor

2. Create an isolated folder named 'pricing_env'
python -m venv pricing_env

3. Activate the folder so your terminal uses it
source pricing_env/bin/activate  # On Windows terminal use: pricing_env\Scripts\activate

4. Install all required data libraries safely into this folder
pip install -r requirements.txt
```

**API Credentials Configuration:** Populate the `.env` file with your secure access token.   
``` bash
SERPAPI_KEY=your_secret_serpapi_key_here
```

**Run the Dashboard:** Launch the interactive Streamlit user application:
```
streamlit run src/app.py
```
Or use the hosted version — no setup required: https://airfare-predictor-singapore.streamlit.app/

**Run the Data Pipeline Locally:** Populate `.env` with `SERPAPI_KEY`, then from the repository root:
```
python pipeline/extraction_process.py   # pulls fresh fares and rebuilds data/dataset.csv
python pipeline/ml.py                   # retrains the model into src/
```