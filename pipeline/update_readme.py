"""Regenerates the model-performance block in README.md from the metrics that
pipeline/ml.py writes to data/model_metrics.json after every training run.

NOTE: paths are relative to the repo root - run this script from there
(e.g. `python pipeline/update_readme.py`), which is how the GitHub Actions workflow
invokes it, after pipeline/ml.py and before the commit step.
"""
import json
from pathlib import Path

METRICS_PATH = Path("data/model_metrics.json")
README_PATH = Path("README.md")
START_MARKER = "<!-- MODEL_METRICS_START -->"
END_MARKER = "<!-- MODEL_METRICS_END -->"


def build_bucket_table(bucket_mape: dict, missing_from_holdout: list) -> str:
    """Renders the per-booking-window MAPE breakdown as a markdown table, so a well-covered
    bucket can't hide a poorly-covered one behind one blended aggregate number."""
    if not bucket_mape:
        return ""
    rows = [
        f"| {bucket} | {stats['mape_pct']}% | {stats['n_test_records']} |"
        for bucket, stats in bucket_mape.items()
    ]
    missing_note = ""
    if missing_from_holdout:
        missing_list = ", ".join(missing_from_holdout)
        missing_note = (
            f"\n\n*No holdout data this run for: {missing_list} - these buckets were "
            f"present in training but the chronological 80/20 split happened to leave none "
            f"of their rows in the held-out 20%, so no accuracy estimate exists for them "
            f"here.*"
        )
    return (
        "\n\n<details><summary>Holdout MAPE by booking window</summary>\n\n"
        "| Booking Window | MAPE | Holdout Records |\n"
        "|---|---|---|\n" + "\n".join(rows) + "\n\n"
        "*A bucket with few holdout records is a less reliable estimate of accuracy - "
        "not every 14-day window has accumulated enough data yet.*"
        f"{missing_note}\n"
        "</details>"
    )


def build_metrics_block(metrics: dict) -> str:
    r2_pct = metrics["holdout_r2"] * 100
    return (
        f"{START_MARKER}\n"
        f"Milestones achieved *(auto-updated by the scheduled pipeline - last run: "
        f"{metrics['run_timestamp_utc']} UTC; {metrics['n_dev_records']} records used for "
        f"training/CV, {metrics['n_test_records']} held out for the evaluation below, "
        f"{metrics['n_records']} total)*:\n"
        f"* **Holdout Mean Absolute Percentage Error (MAPE):** {metrics['holdout_mape_pct']}%\n"
        f"* **Holdout Variance Explained (R² Score):** {r2_pct:.1f}%\n"
        f"* **Holdout Root Mean Square Error (RMSE):** ${metrics['holdout_rmse_sgd']:.2f}"
        f"{build_bucket_table(metrics.get('bucket_mape'), metrics.get('buckets_missing_from_holdout', []))}\n"
        f"{END_MARKER}"
    )


def main():
    if not METRICS_PATH.exists():
        print(f"No metrics file at {METRICS_PATH} - run pipeline/ml.py first. Skipping README update.")
        return

    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    readme_text = README_PATH.read_text(encoding="utf-8")

    if START_MARKER not in readme_text or END_MARKER not in readme_text:
        print(f"Could not find {START_MARKER}/{END_MARKER} markers in {README_PATH} - skipping.")
        return

    before, _, rest = readme_text.partition(START_MARKER)
    _, _, after = rest.partition(END_MARKER)
    new_readme = before + build_metrics_block(metrics) + after

    if new_readme != readme_text:
        README_PATH.write_text(new_readme, encoding="utf-8")
        print("README.md model performance section updated.")
    else:
        print("README.md already up to date.")


if __name__ == "__main__":
    main()
