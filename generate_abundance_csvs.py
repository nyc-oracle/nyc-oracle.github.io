#!/usr/bin/env python3
"""
generate_abundance_csvs.py

Fetches 2024 daily counts from NYC Open Data and writes
prophecy-source-data/*_abundance.csv files.

Each output CSV has one row per day for all 366 days of 2024:
    date, mmdd, month, day, weekday, [count|bite_count], abundance

Abundance is assigned by quintile breaks relative to each dataset's own 2024
distribution — see assign_abundance() for the exact logic (copied from
analyze_cyclical.py so both scripts stay in sync).

Datasets generated
------------------
311 Service Requests (erm2-nwe9, data.cityofnewyork.us):
    311_noise_street_2024_abundance.csv   complaint_type = "Noise - Street/Sidewalk"
    311_heat_hotwater_2024_abundance.csv  complaint_type = "HEAT/HOT WATER"
    311_unsanitary_2024_abundance.csv     complaint_type = "Unsanitary Condition"
    311_street_condition_2024_abundance.csv complaint_type = "Street Condition"
    311_dhs_2024_abundance.csv            agency = "DHS"

DOHMH Dog Bite Data (rsgh-akpg, data.cityofnewyork.us):
    dog_bites_2024_abundance.csv          count column: bite_count

NYC Ferry Ridership (t5n6-gx8c, data.cityofnewyork.us):
    ferry_ridership_2024_abundance.csv    sum(boardings) per day

NYPD Arrest Data YTD (uip8-fykc, data.cityofnewyork.us):
    arrests_2024_abundance.csv

Rodent Inspection (p937-wjvj, data.cityofnewyork.us):
    rodent_inspections_2024_abundance.csv

NYC Watershed Water Quality / Limnology (3y4p-uusw, data.cityofnewyork.us):
    watershed_wq_ph_2024_abundance.csv            daily median pH (SU)
    watershed_wq_total_plankton_2024_abundance.csv daily median total plankton (ASU/mL)
    watershed_wq_total_phosphorus_2024_abundance.csv daily median total phosphorus (µg/L)
    watershed_wq_turbidity_2024_abundance.csv     daily median turbidity (NTU)
    watershed_wq_temperature_2024_abundance.csv   daily median water temperature (°C)
    Abundance is computed only over days with actual measurements (sparse data).

Usage:
    python generate_abundance_csvs.py
"""

import argparse
import requests
import pandas as pd
from pathlib import Path

OUT_DIR = Path(__file__).parent / "prophecy-source-data"
NYC_BASE = "https://data.cityofnewyork.us/resource"
WATERSHED_DATASET = "3y4p-uusw"

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def fetch_json(url, params, desc):
    print(f"  Fetching: {desc}")
    try:
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
        print(f"    -> {len(data)} rows")
        return data
    except Exception as e:
        print(f"    -> ERROR: {e}")
        return None


def assign_abundance(daily_counts):
    """
    Classify daily counts into five ordinal abundance levels using quintile breaks.

    Thresholds are computed from the full-year 2024 distribution of the specific
    dataset being classified, so labels are relative within each dataset.

    Bins (quintiles):
        Very Low  : 0th–20th percentile
        Low       : 20th–40th percentile
        Medium    : 40th–60th percentile
        High      : 60th–80th percentile
        Very High : 80th–100th percentile

    Ties at a boundary are assigned to the lower bin.
    Equivalent pandas one-liner:
        pd.qcut(series, q=5, labels=['Very Low','Low','Medium','High','Very High'])
    """
    vals = list(daily_counts)
    n = len(vals)
    s = sorted(vals)
    t = [s[int(n * p / 100)] for p in (20, 40, 60, 80)]  # P20, P40, P60, P80
    bins = ["Very Low", "Low", "Medium", "High", "Very High"]
    return [
        bins[0] if v <= t[0] else
        bins[1] if v <= t[1] else
        bins[2] if v <= t[2] else
        bins[3] if v <= t[3] else
        bins[4]
        for v in vals
    ]


def build_daily_frame(raw, date_col, count_col, count_rename="count", sparse=False):
    """
    Build a complete 366-row (2024 is a leap year) DataFrame from raw API results.

    For count data (sparse=False): missing days are filled with 0 and abundance
    is assigned across all 366 days.

    For sparse continuous data (sparse=True, e.g. water-quality measurements):
    missing days are filled with NaN and abundance is computed only over days
    that have actual measurements; days without data have an empty abundance.

    Returns None if raw is empty or None.
    """
    if not raw:
        return None

    df = pd.DataFrame(raw)
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce").dt.normalize()
    df[count_col] = pd.to_numeric(df[count_col], errors="coerce")
    if not sparse:
        df[count_col] = df[count_col].fillna(0)
    df = df.dropna(subset=[date_col])
    df = df.groupby(date_col)[count_col].sum().reset_index()

    full_dates = pd.date_range("2024-01-01", "2024-12-31", freq="D")
    fill_value = pd.NA if sparse else 0
    df = df.set_index(date_col).reindex(full_dates, fill_value=fill_value).reset_index()
    df.columns = ["date", count_rename]

    df["mmdd"] = df["date"].dt.strftime("%m-%d")
    df["month"] = df["date"].dt.month.apply(lambda m: MONTH_NAMES[m - 1])
    df["day"] = df["date"].dt.day
    df["weekday"] = df["date"].dt.weekday.apply(lambda w: WEEKDAY_NAMES[w])

    if sparse:
        valid = df[count_rename].notna()
        df["abundance"] = ""
        if valid.sum() > 0:
            df.loc[valid, "abundance"] = assign_abundance(
                df.loc[valid, count_rename].tolist()
            )
    else:
        df["abundance"] = assign_abundance(df[count_rename])

    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df[["date", "mmdd", "month", "day", "weekday", count_rename, "abundance"]]


def save_csv(df, stem):
    path = OUT_DIR / f"{stem}.csv"
    df.to_csv(path, index=False)
    print(f"  Saved -> {path}  ({len(df)} rows)")


# ── Fetch functions ───────────────────────────────────────────────────────────

def fetch_311_daily(complaint_type=None, agency=None):
    """Fetch daily 311 counts for a given complaint_type or agency during 2024."""
    where = "created_date >= '2024-01-01' AND created_date < '2025-01-01'"
    if complaint_type:
        where += f" AND complaint_type = '{complaint_type}'"
    if agency:
        where += f" AND agency = '{agency}'"

    params = {
        "$select": "date_trunc_ymd(created_date) as date, count(*) as count",
        "$group": "date_trunc_ymd(created_date)",
        "$where": where,
        "$limit": 400,
    }
    label = complaint_type or f"agency={agency}"
    return fetch_json(f"{NYC_BASE}/erm2-nwe9.json", params, f"311 {label}")


def fetch_dog_bites_daily():
    """Fetch daily dog bite counts for 2024 (DOHMH Dog Bite Data: rsgh-akpg)."""
    params = {
        "$select": "date_trunc_ymd(dateofbite) as date, count(*) as bite_count",
        "$group": "date_trunc_ymd(dateofbite)",
        "$where": "dateofbite >= '2024-01-01' AND dateofbite < '2025-01-01'",
        "$limit": 400,
    }
    return fetch_json(f"{NYC_BASE}/rsgh-akpg.json", params, "Dog Bites 2024")


def fetch_ferry_daily():
    """Fetch daily ferry boardings for 2024 (NYC Ferry Ridership: t5n6-gx8c)."""
    params = {
        "$select": "date_trunc_ymd(date) as date, sum(boardings) as count",
        "$group": "date_trunc_ymd(date)",
        "$where": "date >= '2024-01-01' AND date < '2025-01-01'",
        "$limit": 400,
    }
    return fetch_json(f"{NYC_BASE}/t5n6-gx8c.json", params, "Ferry Ridership 2024")


def fetch_arrests_daily():
    """Fetch daily arrest counts for 2024 (NYPD Arrest Data Historic: 8h9b-rp9u)."""
    params = {
        "$select": "date_trunc_ymd(arrest_date) as date, count(*) as count",
        "$group": "date_trunc_ymd(arrest_date)",
        "$where": "arrest_date >= '2024-01-01' AND arrest_date < '2025-01-01'",
        "$limit": 400,
    }
    return fetch_json(f"{NYC_BASE}/8h9b-rp9u.json", params, "NYPD Arrests 2024")


def fetch_rodent_inspections_daily():
    """Fetch daily rodent inspection counts for 2024 (Rodent Inspection: p937-wjvj)."""
    params = {
        "$select": "date_trunc_ymd(inspection_date) as date, count(*) as count",
        "$group": "date_trunc_ymd(inspection_date)",
        "$where": "inspection_date >= '2024-01-01' AND inspection_date < '2025-01-01'",
        "$limit": 400,
    }
    return fetch_json(f"{NYC_BASE}/p937-wjvj.json", params, "Rodent Inspections 2024")


def fetch_watershed_analyte_daily(analyte_api_name, value_col):
    """
    Fetch daily median for one analyte from the NYC Watershed Water Quality dataset
    (3y4p-uusw). Measurements are sparse (not every day has a sample), so this
    returns only days that have at least one measurement — build_daily_frame with
    sparse=True handles filling the rest with NaN.
    """
    params = {
        "$select": "sample_date, final_result",
        "$where": (
            f"sample_date >= '2024-01-01' AND sample_date < '2025-01-01'"
            f" AND analyte = '{analyte_api_name}'"
        ),
        "$limit": 50000,
        "$order": "sample_date",
    }
    raw = fetch_json(
        f"{NYC_BASE}/{WATERSHED_DATASET}.json", params,
        f"Watershed {analyte_api_name} 2024",
    )
    if not raw:
        return None

    df = pd.DataFrame(raw)
    df["sample_date"] = pd.to_datetime(df["sample_date"], errors="coerce").dt.normalize()
    df["final_result"] = pd.to_numeric(df["final_result"], errors="coerce")
    df = df.dropna(subset=["sample_date", "final_result"])
    df = df[df["final_result"] >= 0]

    daily = df.groupby("sample_date")["final_result"].median().reset_index()
    daily.columns = ["date", value_col]
    daily["date"] = daily["date"].dt.strftime("%Y-%m-%d")
    return daily.to_dict("records")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    global OUT_DIR
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    args = parser.parse_args()
    OUT_DIR = Path(args.out_dir)
    OUT_DIR.mkdir(exist_ok=True)

    datasets = [
        # (output stem, fetch_fn, count_col in API response, count_col in CSV, sparse)
        ("311_noise_street_2024_abundance",
         lambda: fetch_311_daily("Noise - Street/Sidewalk"), "count", "count", False),
        ("311_heat_hotwater_2024_abundance",
         lambda: fetch_311_daily("HEAT/HOT WATER"), "count", "count", False),
        ("311_unsanitary_2024_abundance",
         lambda: fetch_311_daily("UNSANITARY CONDITION"), "count", "count", False),
        ("311_street_condition_2024_abundance",
         lambda: fetch_311_daily("Street Condition"), "count", "count", False),
        ("311_dhs_2024_abundance",
         lambda: fetch_311_daily(agency="DHS"), "count", "count", False),
        ("dog_bites_2024_abundance",
         fetch_dog_bites_daily, "bite_count", "bite_count", False),
        ("ferry_ridership_2024_abundance",
         fetch_ferry_daily, "count", "count", False),
        ("arrests_2024_abundance",
         fetch_arrests_daily, "count", "count", False),
        ("rodent_inspections_2024_abundance",
         fetch_rodent_inspections_daily, "count", "count", False),
        # Watershed water quality — sparse continuous measurements
        ("watershed_wq_ph_2024_abundance",
         lambda: fetch_watershed_analyte_daily("pH", "ph"), "ph", "ph", True),
        ("watershed_wq_total_plankton_2024_abundance",
         lambda: fetch_watershed_analyte_daily("Total Plankton", "total_plankton"),
         "total_plankton", "total_plankton", True),
        ("watershed_wq_total_phosphorus_2024_abundance",
         lambda: fetch_watershed_analyte_daily("Phosphorus, Total (as P)", "total_phosphorus"),
         "total_phosphorus", "total_phosphorus", True),
        ("watershed_wq_turbidity_2024_abundance",
         lambda: fetch_watershed_analyte_daily("Turbidity", "turbidity"),
         "turbidity", "turbidity", True),
        ("watershed_wq_temperature_2024_abundance",
         lambda: fetch_watershed_analyte_daily("Temperature", "temperature_c"),
         "temperature_c", "temperature_c", True),
    ]

    failed = []
    for stem, fetch_fn, count_col, count_rename, sparse in datasets:
        print(f"\n[{stem}]")
        raw = fetch_fn()
        df = build_daily_frame(raw, "date", count_col, count_rename, sparse=sparse)
        if df is not None:
            save_csv(df, stem)
        else:
            print(f"  SKIPPED (no data returned)")
            failed.append(stem)

    print("\n" + "=" * 60)
    if failed:
        print(f"DONE — {len(datasets) - len(failed)}/{len(datasets)} files written.")
        print(f"Failed: {', '.join(failed)}")
    else:
        print(f"DONE — all {len(datasets)} files written to {OUT_DIR}/")


if __name__ == "__main__":
    main()
