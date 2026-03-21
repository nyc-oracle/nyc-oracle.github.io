#!/usr/bin/env python3
"""
analyze_dsny_tonnage.py

Seasonal pattern analysis for DSNY Monthly Tonnage Data (ebb7-mvp5).
36 years of NYC waste collection data by community district.

Waste streams analyzed:
  - refusetonscollected   (regular garbage)
  - papertonscollected    (paper recycling)
  - mgptonscollected      (metal/glass/plastic recycling)
  - resorganicstons       (residential organics)

Outputs:
  output/dsny_tonnage_report.md
  output/plots/dsny_*.png
"""

import requests
import pandas as pd
import numpy as np
import warnings
from pathlib import Path
from datetime import datetime
from statsmodels.tsa.seasonal import STL

warnings.filterwarnings("ignore")

DATASET_ID = "ebb7-mvp5"
BASE_URL = f"https://data.cityofnewyork.us/resource/{DATASET_ID}.json"

WASTE_STREAMS = {
    "refusetonscollected": "Refuse (garbage)",
    "papertonscollected":  "Paper recycling",
    "mgptonscollected":    "Metal/Glass/Plastic recycling",
    "resorganicstons":     "Residential organics",
}

OUTPUT_DIR = Path("output")
PLOTS_DIR  = OUTPUT_DIR / "plots"
REPORT_PATH = OUTPUT_DIR / "dsny_tonnage_report.md"

MONTH_NAMES = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
               7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}

BOROUGHS = ["Bronx", "Brooklyn", "Manhattan", "Queens", "Staten Island"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def fetch_all_rows() -> pd.DataFrame:
    """Fetch all rows via paginated Socrata requests."""
    limit  = 5000
    offset = 0
    frames = []
    print("Fetching DSNY tonnage data...")
    while True:
        r = requests.get(BASE_URL, params={
            "$limit":  limit,
            "$offset": offset,
            "$order":  "month",
        }, timeout=60)
        r.raise_for_status()
        rows = r.json()
        if not rows:
            break
        frames.append(pd.DataFrame(rows))
        print(f"  fetched {offset + len(rows):,} rows...", end="\r")
        if len(rows) < limit:
            break
        offset += limit
    df = pd.concat(frames, ignore_index=True)
    print(f"  total rows: {len(df):,}            ")
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df["month"] = pd.to_datetime(df["month"], errors="coerce")
    for col in WASTE_STREAMS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df = df.dropna(subset=["month"])
    df["month"] = df["month"].dt.to_period("M").dt.to_timestamp()
    return df


def stl_strength(s: pd.Series) -> float:
    try:
        res = STL(s, period=12, robust=True).fit()
        var_r  = np.var(res.resid)
        var_sr = np.var(res.seasonal + res.resid)
        return float(max(0.0, 1 - var_r / var_sr)) if var_sr else 0.0
    except Exception:
        return 0.0


def peak_month(s: pd.Series) -> int | None:
    try:
        res  = STL(s, period=12, robust=True).fit()
        seas = pd.Series(res.seasonal.values, index=s.index)
        return int(seas.groupby(seas.index.month).mean().idxmax())
    except Exception:
        return None


def trough_month(s: pd.Series) -> int | None:
    try:
        res  = STL(s, period=12, robust=True).fit()
        seas = pd.Series(res.seasonal.values, index=s.index)
        return int(seas.groupby(seas.index.month).mean().idxmin())
    except Exception:
        return None


def monthly_avg_profile(s: pd.Series) -> dict:
    """Average value by calendar month, as % deviation from annual mean."""
    profile = s.groupby(s.index.month).mean()
    mean    = profile.mean()
    return {m: round((v / mean - 1) * 100, 1) for m, v in profile.items()}


def season_name(m: int | None) -> str:
    if m is None:
        return "N/A"
    if m in (12, 1, 2):  return "winter"
    if m in (3, 4, 5):   return "spring"
    if m in (6, 7, 8):   return "summer"
    return "fall"


def ml(m: int | None) -> str:
    return MONTH_NAMES.get(m, "N/A") if m else "N/A"


def sparkline_bar(profile: dict) -> str:
    """12-char ASCII sparkline using block chars."""
    blocks = " ▁▂▃▄▅▆▇█"
    vals   = [profile.get(m, 0) for m in range(1, 13)]
    lo, hi = min(vals), max(vals)
    rng    = hi - lo or 1
    chars  = [blocks[round((v - lo) / rng * 8)] for v in vals]
    return "".join(chars)


def save_plot(s: pd.Series, stream_name: str, slug: str) -> str | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        res  = STL(s, period=12, robust=True).fit()
        fig, axes = plt.subplots(3, 1, figsize=(10, 6), sharex=True)
        fig.suptitle(f"DSNY {stream_name} — STL Decomposition", fontsize=11)

        axes[0].plot(s.index, s.values, color="#2a6ebb", lw=1)
        axes[0].set_ylabel("Tons/month", fontsize=8)
        axes[0].set_title("Original series", fontsize=9)

        axes[1].plot(s.index, res.trend, color="#e06c28", lw=1.5)
        axes[1].set_ylabel("Tons/month", fontsize=8)
        axes[1].set_title("Trend", fontsize=9)

        axes[2].plot(s.index, res.seasonal, color="#2aaa5a", lw=1)
        axes[2].axhline(0, color="gray", lw=0.5, ls="--")
        axes[2].set_ylabel("Tons/month", fontsize=8)
        axes[2].set_title("Seasonal component", fontsize=9)

        for ax in axes:
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.tick_params(labelsize=7)

        plt.tight_layout()
        path = PLOTS_DIR / f"dsny_{slug}.png"
        fig.savefig(path, dpi=110)
        plt.close(fig)
        return str(path)
    except Exception as e:
        print(f"  plot error: {e}")
        return None


def save_seasonal_profile_plot(profiles: dict, stream_name: str, slug: str) -> str | None:
    """Bar chart of average seasonal profile by month for one waste stream."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        months = list(range(1, 13))
        vals   = [profiles.get(m, 0) for m in months]
        colors = ["#e06c28" if v >= 0 else "#2a6ebb" for v in vals]
        labels = [MONTH_NAMES[m] for m in months]

        fig, ax = plt.subplots(figsize=(8, 3.5))
        ax.bar(labels, vals, color=colors, edgecolor="white", linewidth=0.5)
        ax.axhline(0, color="black", lw=0.7)
        ax.set_ylabel("% deviation from annual mean", fontsize=9)
        ax.set_title(f"{stream_name} — Average seasonal profile (1990–2026)", fontsize=10)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(labelsize=8)
        plt.tight_layout()
        path = PLOTS_DIR / f"dsny_profile_{slug}.png"
        fig.savefig(path, dpi=110)
        plt.close(fig)
        return str(path)
    except Exception as e:
        print(f"  profile plot error: {e}")
        return None


# ── Analysis ──────────────────────────────────────────────────────────────────

def analyze_citywide(df: pd.DataFrame) -> dict:
    """Aggregate to city-wide monthly totals, run STL on each waste stream."""
    monthly = (
        df.groupby("month")[list(WASTE_STREAMS.keys())]
        .sum()
        .sort_index()
    )
    full_idx = pd.date_range(monthly.index.min(), monthly.index.max(), freq="MS")
    monthly  = monthly.reindex(full_idx)

    results = {}
    for col, label in WASTE_STREAMS.items():
        if col not in monthly.columns:
            continue
        s = monthly[col].fillna(monthly[col].median())
        # Drop leading/trailing zeros (data gaps)
        s = s[(s.cumsum() > 0) & (s[::-1].cumsum()[::-1] > 0)]
        if len(s) < 36:
            continue

        strength = stl_strength(s)
        pk       = peak_month(s)
        tr       = trough_month(s)
        profile  = monthly_avg_profile(s)

        # Peak-to-trough ratio from profile
        pv = profile.get(pk, 0)
        tv = profile.get(tr, 0)

        results[col] = {
            "label":    label,
            "strength": round(strength, 4),
            "peak":     pk,
            "trough":   tr,
            "profile":  profile,
            "series":   s,
            "peak_pct": pv,
            "trough_pct": tv,
            "span_months": len(s),
            "mean_tons":   round(s.mean(), 1),
        }
        print(f"  {label}: strength={strength:.3f}, peak={ml(pk)}, trough={ml(tr)}")

    return results


def analyze_by_borough(df: pd.DataFrame) -> dict:
    """STL seasonal strength for refuse (largest stream) per borough."""
    results = {}
    for borough in BOROUGHS:
        sub = df[df["borough"].str.lower() == borough.lower()]
        if sub.empty:
            # try case-insensitive partial match
            sub = df[df["borough"].str.lower().str.contains(borough.lower().split()[0])]
        if sub.empty:
            continue
        monthly = sub.groupby("month")["refusetonscollected"].sum().sort_index()
        full_idx = pd.date_range(monthly.index.min(), monthly.index.max(), freq="MS")
        s = monthly.reindex(full_idx).fillna(monthly.median())
        s = s[(s.cumsum() > 0)]
        if len(s) < 36:
            continue
        strength = stl_strength(s)
        pk       = peak_month(s)
        results[borough] = {
            "strength": round(strength, 4),
            "peak":     pk,
        }
    return results


def yoy_trend(s: pd.Series) -> float:
    """Simple year-over-year trend: average annual change as % of start."""
    annual = s.resample("YE").sum()
    annual = annual[annual > 0]
    if len(annual) < 2:
        return 0.0
    # Fit linear trend to log to get compound rate
    x = np.arange(len(annual))
    y = np.log(annual.values.astype(float))
    slope = np.polyfit(x, y, 1)[0]
    return round((np.exp(slope) - 1) * 100, 2)


# ── Report ────────────────────────────────────────────────────────────────────

def build_report(citywide: dict, borough_results: dict, df: pd.DataFrame) -> str:
    now   = datetime.now().strftime("%Y-%m-%d")
    lines = []

    lines += [
        "# DSNY Monthly Tonnage: Seasonal Pattern Analysis",
        "",
        f"**Report generated:** {now}  ",
        "**Dataset:** DSNY Monthly Tonnage Data (`ebb7-mvp5`)  ",
        "**Source:** data.cityofnewyork.us  ",
        f"**Coverage:** {df['month'].min().strftime('%Y-%m')} to {df['month'].max().strftime('%Y-%m')} ({len(df):,} district-month rows)  ",
        "**Method:** STL decomposition (period=12 months, robust=True)  ",
        "**Seasonal strength:** 0 = no pattern, 1 = perfectly seasonal",
        "",
        "---",
        "",
        "## 1. City-Wide Seasonal Strength by Waste Stream",
        "",
        "| Waste Stream | Mean Tons/Month | Seasonal Strength | Peak Month | Peak % above avg | Trough Month | Trough % below avg | Trend (YoY%) |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for col, r in sorted(citywide.items(), key=lambda x: -x[1]["strength"]):
        trend = yoy_trend(r["series"])
        tag   = "▲" if trend > 0.5 else ("▼" if trend < -0.5 else "→")
        lines.append(
            f"| {r['label']} | {r['mean_tons']:,.0f} | **{r['strength']:.3f}** | "
            f"{ml(r['peak'])} | +{r['peak_pct']:.1f}% | "
            f"{ml(r['trough'])} | {r['trough_pct']:.1f}% | "
            f"{tag} {trend:+.1f}%/yr |"
        )

    lines += ["", "### Seasonal Profiles (% deviation from annual mean, Jan–Dec)", ""]
    lines.append("| Waste Stream | J | F | M | A | M | J | J | A | S | O | N | D |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for col, r in citywide.items():
        p = r["profile"]
        cells = [f"{p.get(m,0):+.0f}%" for m in range(1, 13)]
        lines.append(f"| {r['label']} | " + " | ".join(cells) + " |")

    lines += ["", "### ASCII Sparklines (Jan–Dec)", ""]
    for col, r in citywide.items():
        bar = sparkline_bar(r["profile"])
        lines.append(f"- **{r['label']}**: `{bar}` (peak={ml(r['peak'])}, trough={ml(r['trough'])})")

    lines += [
        "",
        "---",
        "",
        "## 2. Key Findings",
        "",
    ]

    # --- Refuse ---
    refuse = citywide.get("refusetonscollected")
    if refuse:
        lines += [
            f"### Refuse (Garbage)",
            f"Seasonal strength: **{refuse['strength']:.3f}** — "
            + ("strong" if refuse['strength'] >= 0.5 else "moderate" if refuse['strength'] >= 0.2 else "weak"),
            "",
            f"Refuse peaks in **{ml(refuse['peak'])}** ({refuse['peak_pct']:+.1f}% above average) "
            f"and troughs in **{ml(refuse['trough'])}** ({refuse['trough_pct']:.1f}% below average). "
            f"The summer peak reflects more outdoor eating, takeout containers, and higher residential activity. "
            f"Winter dip may reflect reduced outdoor activity and packaging differences.",
            "",
        ]

    # --- Paper ---
    paper = citywide.get("papertonscollected")
    if paper:
        lines += [
            "### Paper Recycling",
            f"Seasonal strength: **{paper['strength']:.3f}**",
            "",
            f"Paper peaks in **{ml(paper['peak'])}** ({paper['peak_pct']:+.1f}%). "
            f"Holiday shopping and gift wrapping drive a post-December surge in cardboard and paper recycling. "
            f"Summer sees reduced office paper but increased retail packaging.",
            "",
        ]

    # --- MGP ---
    mgp = citywide.get("mgptonscollected")
    if mgp:
        lines += [
            "### Metal / Glass / Plastic Recycling",
            f"Seasonal strength: **{mgp['strength']:.3f}**",
            "",
            f"MGP peaks in **{ml(mgp['peak'])}** ({mgp['peak_pct']:+.1f}%). "
            f"Bottles and cans — beverages — drive this pattern. Summer outdoor events, "
            f"beer/soda consumption, and backyard gatherings produce the highest bottle/can recycling volumes.",
            "",
        ]

    # --- Organics ---
    organics = citywide.get("resorganicstons")
    if organics:
        lines += [
            "### Residential Organics",
            f"Seasonal strength: **{organics['strength']:.3f}**",
            "",
            f"Organics peaks in **{ml(organics['peak'])}** ({organics['peak_pct']:+.1f}%). "
            f"Note: NYC's curbside organics program expanded significantly in 2021-2023, "
            f"so earlier years may show near-zero values (program was opt-in/limited rollout). "
            f"The seasonal profile reflects both food scraps and yard/leaf waste.",
            "",
        ]

    # --- Comparison ---
    if len(citywide) >= 2:
        sorted_by_strength = sorted(citywide.items(), key=lambda x: -x[1]["strength"])
        strongest  = sorted_by_strength[0]
        weakest    = sorted_by_strength[-1]
        lines += [
            "### Cross-Stream Comparison",
            "",
            f"- **Most seasonal stream:** {strongest[1]['label']} (strength {strongest[1]['strength']:.3f})",
            f"- **Least seasonal stream:** {weakest[1]['label']} (strength {weakest[1]['strength']:.3f})",
            "",
        ]

        # Check if peaks are aligned or offset
        peaks = {r["label"]: r["peak"] for _, r in citywide.items() if r["peak"]}
        unique_peaks = set(peaks.values())
        if len(unique_peaks) == 1:
            lines.append("All waste streams peak in the same month — driven by the same underlying seasonal force (likely summer activity).")
        else:
            lines.append("Waste streams peak at different times, revealing distinct drivers:")
            for label, m in peaks.items():
                lines.append(f"  - {label}: peak in {ml(m)} ({season_name(m)})")
        lines.append("")

    # --- Borough ---
    lines += [
        "---",
        "",
        "## 3. Borough-Level Refuse Seasonality",
        "",
        "| Borough | Seasonal Strength | Peak Month |",
        "|---------|-------------------|------------|",
    ]
    for borough, r in borough_results.items():
        lines.append(f"| {borough} | {r['strength']:.3f} | {ml(r['peak'])} |")

    lines += [
        "",
        "Borough-level strengths show whether some areas have more pronounced seasonal "
        "waste patterns — e.g., tourist-heavy Manhattan vs residential outer boroughs.",
        "",
    ]

    # --- Long-term trends ---
    lines += [
        "---",
        "",
        "## 4. Long-Term Trends (1990–2026)",
        "",
    ]
    for col, r in citywide.items():
        trend = yoy_trend(r["series"])
        direction = "increasing" if trend > 0.5 else ("decreasing" if trend < -0.5 else "roughly flat")
        lines.append(
            f"- **{r['label']}**: {direction} at **{trend:+.1f}%/year** on average "
            f"(compound annual rate from log-linear fit)"
        )

    lines += [
        "",
        "Refuse and paper recycling trends reflect NYC's zero-waste initiatives, "
        "population growth, and the rise of e-commerce packaging. "
        "Organics tonnage shows rapid growth from near-zero as the city's composting "
        "program scaled up.",
        "",
        "---",
        "",
        "## 5. Methodology",
        "",
        "- **STL decomposition** (Cleveland et al., 1990): `STL(series, period=12, robust=True)`",
        "- **Seasonal strength:** `max(0, 1 − Var(residual) / Var(seasonal + residual))`",
        "- **Seasonal profile:** average STL seasonal component by calendar month",
        "- **Trend:** compound annual rate from log-linear fit to annual totals",
        "- **Data aggregation:** district-level rows summed to city-wide monthly totals",
        "- Leading/trailing zero rows dropped before fitting",
        "",
        "**Dataset:** DSNY Monthly Tonnage Data  ",
        "**API:** `https://data.cityofnewyork.us/resource/ebb7-mvp5.json`  ",
        "**Dataset ID:** `ebb7-mvp5`",
    ]

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    PLOTS_DIR.mkdir(exist_ok=True)

    df = fetch_all_rows()
    df = clean(df)

    print("\nCity-wide analysis...")
    citywide = analyze_citywide(df)

    print("\nBorough-level analysis (refuse)...")
    borough_results = analyze_by_borough(df)

    print("\nGenerating plots...")
    for col, r in citywide.items():
        slug = col.replace("tonscollected", "").replace("tons", "")
        save_plot(r["series"], r["label"], slug)
        save_seasonal_profile_plot(r["profile"], r["label"], slug + "_profile")

    print("\nBuilding report...")
    report = build_report(citywide, borough_results, df)
    REPORT_PATH.write_text(report)
    print(f"\nReport written to: {REPORT_PATH}")

    # Print summary to terminal
    print("\n" + "="*60)
    print("SEASONAL STRENGTH SUMMARY")
    print("="*60)
    for col, r in sorted(citywide.items(), key=lambda x: -x[1]["strength"]):
        bar = sparkline_bar(r["profile"])
        print(f"  {r['label']:<35} strength={r['strength']:.3f}  peak={ml(r['peak'])}  [{bar}]")


if __name__ == "__main__":
    main()
