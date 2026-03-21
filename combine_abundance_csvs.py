#!/usr/bin/env python3
"""
combine_abundance_csvs.py

Combines all per-dataset *_abundance.csv files in prophecy-source-data/ into
a single all_combined_abundance.csv, then cleans the result.

Output columns:
    source, date, mmdd, month, day, weekday, value, abundance, description

Cleaning steps applied:
    - date is parsed and re-formatted as YYYY-MM-DD; unparseable rows are dropped.
    - abundance must be one of the five canonical levels; other values are dropped.
    - rows with a missing or blank description are dropped.
    - rows with a missing value are kept (some datasets have sparse days).

Usage:
    python combine_abundance_csvs.py [--data-dir PATH] [--out PATH]
"""

import argparse
import re
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "prophecy-source-data"
OUT_FILE = DATA_DIR / "all_combined_abundance.csv"

VALID_ABUNDANCE = {"Very Low", "Low", "Medium", "High", "Very High"}

# Files to skip — already-combined outputs and non-abundance tables
SKIP_STEMS = re.compile(
    r"^(all_combined|sample_prophecies|prophecies_)", re.IGNORECASE
)


def source_name(path: Path) -> str:
    """Derive a short source label from the filename stem.

    '311_noise_street_2024_abundance' -> '311_noise_street'
    'watershed_wq_ph_2024_abundance'  -> 'watershed_wq_ph'
    """
    stem = path.stem  # e.g. "311_noise_street_2024_abundance"
    stem = re.sub(r"_abundance$", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"_2024$", "", stem, flags=re.IGNORECASE)
    return stem


def load_file(path: Path) -> pd.DataFrame | None:
    """Load one abundance CSV and normalise it to the shared schema."""
    try:
        df = pd.read_csv(path, dtype=str)
    except Exception as e:
        print(f"  WARN: could not read {path.name}: {e}")
        return None

    if df.empty:
        print(f"  WARN: {path.name} is empty — skipping")
        return None

    # Identify the value column (everything that isn't a known shared column)
    shared = {"date", "mmdd", "month", "day", "weekday", "abundance", "description"}
    value_cols = [c for c in df.columns if c not in shared]
    if not value_cols:
        print(f"  WARN: {path.name} has no value column — skipping")
        return None

    value_col = value_cols[0]  # e.g. "count", "bite_count", "temperature_c"
    df = df.rename(columns={value_col: "value"})

    # Add source label
    df.insert(0, "source", source_name(path))

    # Keep only the canonical output columns (drop any extras)
    cols = ["source", "date", "mmdd", "month", "day", "weekday", "value",
            "abundance", "description"]
    for col in cols:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[cols]

    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all cleaning rules and return the cleaned DataFrame."""

    original = len(df)

    # --- date -----------------------------------------------------------
    parsed = pd.to_datetime(df["date"], errors="coerce")
    bad_dates = parsed.isna().sum()
    if bad_dates:
        print(f"  dropping {bad_dates} rows with unparseable date")
    df = df[parsed.notna()].copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")

    # --- abundance ------------------------------------------------------
    bad_abundance = ~df["abundance"].isin(VALID_ABUNDANCE)
    n_bad = bad_abundance.sum()
    if n_bad:
        bad_vals = df.loc[bad_abundance, "abundance"].unique().tolist()
        print(f"  dropping {n_bad} rows with invalid abundance values: {bad_vals}")
    df = df[~bad_abundance].copy()

    # --- description ----------------------------------------------------
    blank_desc = df["description"].isna() | (df["description"].str.strip() == "")
    n_blank = blank_desc.sum()
    if n_blank:
        print(f"  dropping {n_blank} rows with missing/blank description")
    df = df[~blank_desc].copy()

    print(f"  {original} -> {len(df)} rows after cleaning")
    return df


def main():
    global DATA_DIR, OUT_FILE

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir", default=str(DATA_DIR),
        help="Directory containing the per-dataset abundance CSVs",
    )
    parser.add_argument(
        "--out", default=str(OUT_FILE),
        help="Output path for the combined CSV",
    )
    args = parser.parse_args()

    DATA_DIR = Path(args.data_dir)
    OUT_FILE = Path(args.out)

    csv_files = sorted(
        p for p in DATA_DIR.glob("*.csv")
        if not SKIP_STEMS.match(p.stem)
    )

    if not csv_files:
        print(f"No matching CSVs found in {DATA_DIR}")
        return

    print(f"Found {len(csv_files)} file(s) to combine:\n")

    frames = []
    for path in csv_files:
        print(f"[{path.name}]")
        df = load_file(path)
        if df is not None:
            print(f"  loaded {len(df)} rows")
            frames.append(df)

    if not frames:
        print("No data loaded — aborting.")
        return

    combined = pd.concat(frames, ignore_index=True)
    print(f"\nCombined: {len(combined)} rows from {len(frames)} file(s)")

    print("\nCleaning...")
    combined = clean(combined)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUT_FILE, index=False)
    print(f"\nSaved -> {OUT_FILE}  ({len(combined)} rows, {combined['source'].nunique()} sources)")


if __name__ == "__main__":
    main()
