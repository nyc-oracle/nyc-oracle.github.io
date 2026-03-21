#!/usr/bin/env python3
"""
nyc_seasonal_finder.py

Searches NYC Open Data for datasets with strong annual seasonal patterns.
Prescreens aggressively, prioritizes interesting/surprising datasets,
and stops after finding 30-50 keepers.

Usage:
    python nyc_seasonal_finder.py

Set SOCRATA_TOKEN env var or let it fall back to the default token.
"""

import os
import time
import requests
import numpy as np
import pandas as pd
from pathlib import Path
from statsmodels.tsa.seasonal import STL

# ── Config ────────────────────────────────────────────────────────────────────
TOKEN        = os.environ.get("SOCRATA_TOKEN", "")  # optional; works without one
DOMAIN       = "data.cityofnewyork.us"
CATALOG_URL  = "https://api.us.socrata.com/api/catalog/v1"
DATA_BASE    = f"https://{DOMAIN}/resource"

TARGET_MIN         = 30
TARGET_MAX         = 50
MIN_MONTHS         = 30      # need at least this many monthly buckets
MIN_YEARS          = 3
MAX_MISSING_PCT    = 0.20    # skip if >20% of months are zero/missing
FLAT_THRESHOLD     = 0.05    # skip if std < 5% of mean
SEASONAL_THRESHOLD = 0.40

OUTPUT_DIR = Path("output")
PLOTS_DIR  = OUTPUT_DIR / "plots"
CSV_PATH   = OUTPUT_DIR / "seasonal_datasets.csv"

# ── Priority tiers ─────────────────────────────────────────────────────────────
TIER1 = [
    "rat", "rodent", "mosquito", "bird", "tree", "beach", "swim", "pool",
    "skating", "ice", "heat", "flood", "snow", "animal", "dog", "cat", "fish",
    "death", "birth", "lead", "air quality", "water quality", "noise", "park",
    "garden", "film permit", "art", "nature", "weather", "temperature",
    "precipitation", "emergency", "fire", "ambulance", "flu", "asthma", "health",
]
TIER2 = ["complaint", "311", "violation", "request", "inspection", "permit"]

SKIP_CATEGORIES = {"Reference & Lists", "Geographic Data", "City Government"}
SKIP_NAME_WORDS = ["census", "crosswalk", "lookup", "dictionary", "codebook",
                   "index", "static", "shapefile", "boundary", "borough boundary"]

INTERESTING_WORDS = [
    "rat", "rodent", "mosquito", "bird", "tree", "beach", "ice", "death",
    "birth", "lead", "heat", "flood", "noise", "dog", "cat", "film", "art",
    "garden", "owl", "firefly", "tide", "plant", "flower", "swim",
]
INTERESTING_AGENCIES = ["parks", "health", "cultural", "environment", "wildlife"]


# ── Helpers ───────────────────────────────────────────────────────────────────
def tier(name: str, desc: str) -> int:
    t = (name + " " + desc).lower()
    if any(kw in t for kw in TIER1):
        return 1
    if any(kw in t for kw in TIER2):
        return 2
    return 3


def meta_skip_reason(resource: dict, category: str) -> str | None:
    name = resource.get("name", "").lower()
    if category in SKIP_CATEGORIES:
        return f"category={category!r}"
    if any(w in name for w in SKIP_NAME_WORDS):
        return f"name pattern"
    return None


def date_col_from_meta(resource: dict) -> str | None:
    """Pick a date column using catalog metadata — returns the API field name."""
    fields = resource.get("columns_field_name", [])
    dtypes = resource.get("columns_datatype", [])
    date_cols = [f for f, dt in zip(fields, dtypes)
                 if dt in ("Calendar date", "Date")]
    if not date_cols:
        return None
    # Prefer a column whose field name contains 'date' or 'time'
    for col in date_cols:
        if any(kw in col.lower() for kw in ("date", "time", "created", "opened", "closed")):
            return col
    return date_cols[0]


def fetch_monthly(dataset_id: str, date_col: str) -> pd.Series | None:
    """Aggregate dataset to monthly event counts via SODA."""
    url = f"{DATA_BASE}/{dataset_id}.json"

    def _query(where: str | None = None) -> list | None:
        params = {
            "$select": f"date_trunc_ym({date_col}) as month, count(*) as n",
            "$group":  f"date_trunc_ym({date_col})",
            "$order":  f"date_trunc_ym({date_col})",
            "$limit":  "2000",
        }
        if where:
            params["$where"] = where
        if TOKEN:
            params["$$app_token"] = TOKEN
        try:
            r = requests.get(url, params=params, timeout=45)
            r.raise_for_status()
            return r.json()
        except Exception:
            return None

    rows = _query()
    # If timed out / failed, retry with last 7 years only
    if rows is None:
        rows = _query(f"{date_col} >= '2018-01-01'")
    if rows is None:
        return None

    if not rows or not isinstance(rows, list) or "month" not in rows[0]:
        return None

    df = pd.DataFrame(rows)
    df["month"] = pd.to_datetime(df["month"], errors="coerce")
    df["n"]     = pd.to_numeric(df["n"],     errors="coerce")
    df = df.dropna().set_index("month").sort_index()
    if df.empty:
        return None

    # Reindex to fill any missing months with 0
    full_idx = pd.date_range(df.index.min(), df.index.max(), freq="MS")
    return df["n"].reindex(full_idx, fill_value=0)


def prescreen(series: pd.Series) -> str | None:
    n      = len(series)
    years  = n / 12.0
    if n < MIN_MONTHS:
        return f"only {n} months"
    if years < MIN_YEARS:
        return f"only {years:.1f} years"
    missing = (series == 0).mean()
    if missing > MAX_MISSING_PCT:
        return f"{missing:.0%} zero months"
    if series.mean() == 0:
        return "all zeros"
    if series.std() / series.mean() < FLAT_THRESHOLD:
        return "flat signal"
    return None


def score_seasonality(series: pd.Series) -> float:
    """STL seasonal strength, 0–1."""
    if len(series) < 24:
        return 0.0
    try:
        res = STL(series, period=12, robust=True).fit()
        var_r  = np.var(res.resid)
        var_sr = np.var(res.seasonal + res.resid)
        return float(max(0.0, 1 - var_r / var_sr)) if var_sr else 0.0
    except Exception:
        return 0.0


def annual_fft_check(series: pd.Series) -> bool:
    """Confirm dominant FFT frequency is ~annual (1/12 cycles/month)."""
    try:
        vals   = series.values - series.mean()
        fft    = np.abs(np.fft.rfft(vals))
        freqs  = np.fft.rfftfreq(len(vals))
        target = np.argmin(np.abs(freqs - 1 / 12))
        dom    = np.argmax(fft[1:]) + 1
        return abs(dom - target) <= 2
    except Exception:
        return False


def interest_score(name: str, agency: str, years: float) -> int:
    text = (name + " " + agency).lower()
    s = sum(2 for w in INTERESTING_WORDS if w in text)
    s += sum(2 for a in INTERESTING_AGENCIES if a in text)
    s += 3 if years > 10 else (1 if years > 5 else 0)
    return s


def save_sparkline(series: pd.Series, name: str, dataset_id: str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 1.8))
        ax.plot(series.index, series.values, linewidth=1.3, color="#2a6ebb")
        ax.fill_between(series.index, series.values, alpha=0.15, color="#2a6ebb")
        ax.set_title(name[:70], fontsize=7, pad=3)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(labelsize=6)
        plt.tight_layout(pad=0.3)
        safe = "".join(c if c.isalnum() else "_" for c in name[:40])
        fig.savefig(PLOTS_DIR / f"{dataset_id}_{safe}.png", dpi=100)
        plt.close(fig)
    except Exception:
        pass


# ── Catalog fetch ──────────────────────────────────────────────────────────────
def fetch_catalog() -> list[dict]:
    datasets, offset, limit = [], 0, 100
    print("Fetching catalog...", flush=True)
    while True:
        headers = {"X-App-Token": TOKEN} if TOKEN else {}
        r = requests.get(CATALOG_URL, params={
            "domains": DOMAIN,
            "only":    "datasets",
            "limit":   limit,
            "offset":  offset,
        }, headers=headers, timeout=30)
        r.raise_for_status()
        data    = r.json()
        results = data.get("results", [])
        if not results:
            break
        for d in results:
            cols = d.get("resource", {}).get("columns_datatype", [])
            if any(dt in ("Calendar date", "Date") for dt in cols):
                datasets.append(d)
        offset += limit
        if offset >= data.get("resultSetSize", 0):
            break
        time.sleep(0.08)
    print(f"  {len(datasets)} datasets have date columns", flush=True)
    return datasets


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    PLOTS_DIR.mkdir(exist_ok=True)

    catalog = fetch_catalog()

    # Sort: Tier 1 first, then 2, then 3
    catalog.sort(key=lambda d: tier(
        d["resource"].get("name", ""),
        " ".join(str(v) for v in d.get("classification", {}).get("domain_tags", [])),
    ))

    keepers  = []
    examined = 0

    for dataset in catalog:
        if len(keepers) >= TARGET_MAX:
            print(f"\nReached {TARGET_MAX} keepers — stopping early.", flush=True)
            break

        resource   = dataset.get("resource", {})
        cls        = dataset.get("classification", {})
        dataset_id = resource.get("id", "")
        name       = resource.get("name", "Unknown")
        category   = cls.get("domain_category", "")
        agency     = category
        permalink  = dataset.get("permalink", f"https://{DOMAIN}/d/{dataset_id}")

        # ── Metadata prescreen ─────────────────────────────────────────────
        reason = meta_skip_reason(resource, category)
        if reason:
            continue

        date_col = date_col_from_meta(resource)
        if not date_col:
            continue

        examined += 1
        print(f"[{examined}] {name[:65]}", flush=True)

        # ── Fetch monthly series ───────────────────────────────────────────
        series = fetch_monthly(dataset_id, date_col)
        if series is None:
            print("  → skip: fetch failed", flush=True)
            continue

        # ── Series prescreen ───────────────────────────────────────────────
        reason = prescreen(series)
        if reason:
            print(f"  → skip: {reason}", flush=True)
            continue

        # ── Seasonality scoring ────────────────────────────────────────────
        strength = score_seasonality(series)
        print(f"  strength={strength:.3f}", flush=True)

        if strength < SEASONAL_THRESHOLD:
            print("  → skip: weak seasonality", flush=True)
            continue

        years    = len(series) / 12.0
        annual   = annual_fft_check(series)  # informational only
        interest = interest_score(name, agency, years)
        save_sparkline(series, name, dataset_id)

        keepers.append({
            "dataset_name":      name,
            "dataset_id":        dataset_id,
            "url":               permalink,
            "date_col":          date_col,
            "seasonal_strength": round(strength, 4),
            "years_of_data":     round(years, 1),
            "months":            len(series),
            "interestingness":   interest,
            "annual_fft":        annual,
            "agency":            agency,
        })
        print(f"  ✓ KEEPER #{len(keepers)}  interest={interest}", flush=True)

        time.sleep(0.25)

    # ── Save results ───────────────────────────────────────────────────────────
    df = (
        pd.DataFrame(keepers)
        .sort_values(["interestingness", "seasonal_strength"], ascending=[False, False])
    )
    df.to_csv(CSV_PATH, index=False)

    print(f"\n{'─'*70}")
    print(f"Examined {examined} datasets → {len(keepers)} keepers → {CSV_PATH}")
    print(df[["dataset_name", "seasonal_strength", "years_of_data", "interestingness"]].to_string())


if __name__ == "__main__":
    main()
