#!/usr/bin/env python3
"""
analyze_watershed_wq.py

Seasonal pattern analysis for NYC Watershed Water Quality / Limnology data
(dataset 3y4p-uusw), restricted to the last 3 years of available data.

Approach:
  - Long-format data (one row per analyte measurement) fetched via Socrata API
  - Aggregated to monthly medians per analyte, city-wide and per key reservoir
  - Seasonal profiles: deviation from 3-year monthly average
  - STL decomposition where data is sufficient (≥24 months)
  - Focus analytes: Temperature, Dissolved Oxygen, pH, Turbidity,
    Chlorophyll a, Total Phosphorus, Fecal Coliform, Total Plankton,
    Microcystins (aggregate)

Output:
  output/watershed_wq_report.md
  output/plots/wq_*.png
"""

import requests
import pandas as pd
import numpy as np
import warnings
from pathlib import Path
from datetime import datetime, date
from statsmodels.tsa.seasonal import STL

warnings.filterwarnings("ignore")

DATASET_ID = "3y4p-uusw"
BASE_URL   = f"https://data.cityofnewyork.us/resource/{DATASET_ID}.json"

# Analytes to analyse (API name → display name, unit)
ANALYTES = {
    "Temperature":                     ("Temperature",            "°C"),
    "Dissolved Oxygen":                ("Dissolved Oxygen",       "mg/L"),
    "pH":                              ("pH",                     "SU"),
    "Turbidity":                       ("Turbidity",              "NTU"),
    "Chlorophyll a":                   ("Chlorophyll a",          "µg/L"),
    "Phosphorus, Total (as P)":        ("Total Phosphorus",       "µg/L"),
    "Coliform, Fecal":                 ("Fecal Coliform",         "CFU/100mL"),
    "Total Plankton":                  ("Total Plankton",         "ASU/mL"),
    "Microcystins":                    ("Microcystins",           "µg/L"),
    "Nitrogen, Total (as N)":          ("Total Nitrogen",         "mg/L"),
    "Organic Carbon, Dissolved":       ("Dissolved Organic Carbon","mg/L"),
}

KEY_RESERVOIRS = ["Kensico", "Ashokan West Basin", "Rondout", "Pepacton", "Cannonsville"]

OUTPUT_DIR  = Path("output")
PLOTS_DIR   = OUTPUT_DIR / "plots"
REPORT_PATH = OUTPUT_DIR / "watershed_wq_report.md"

MONTH_NAMES = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
               7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}


# ── Data fetching ─────────────────────────────────────────────────────────────

def fetch_last_3_years() -> pd.DataFrame:
    """
    Fetch all rows for the focus analytes from the last 3 years of available data.
    We first determine the latest date, then go back 3 years.
    """
    # Get latest date in dataset
    r = requests.get(BASE_URL, params={
        "$select": "max(sample_date) as latest",
    }, timeout=30)
    r.raise_for_status()
    latest_str = r.json()[0]["latest"][:10]
    latest = date.fromisoformat(latest_str)
    cutoff = date(latest.year - 3, latest.month, 1)
    print(f"Latest sample date: {latest}  →  fetching from {cutoff} onward")

    analyte_filter = " OR ".join(f"analyte='{a}'" for a in ANALYTES)
    where = f"sample_date >= '{cutoff}' AND ({analyte_filter})"

    frames = []
    limit, offset = 5000, 0
    while True:
        resp = requests.get(BASE_URL, params={
            "$select": "sample_date,analyte,final_result,reservoir,depth_m",
            "$where":  where,
            "$limit":  limit,
            "$offset": offset,
            "$order":  "sample_date",
        }, timeout=90)
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            break
        frames.append(pd.DataFrame(rows))
        total = offset + len(rows)
        print(f"  fetched {total:,} rows...", end="\r")
        if len(rows) < limit:
            break
        offset += limit

    df = pd.concat(frames, ignore_index=True)
    print(f"  total rows fetched: {len(df):,}            ")
    return df, cutoff, latest


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df["sample_date"] = pd.to_datetime(df["sample_date"], errors="coerce")
    df["final_result"] = pd.to_numeric(df["final_result"], errors="coerce")
    df["depth_m"]      = pd.to_numeric(df["depth_m"],      errors="coerce")
    df = df.dropna(subset=["sample_date", "final_result"])
    df = df[df["final_result"] >= 0]
    df["month"]  = df["sample_date"].dt.to_period("M").dt.to_timestamp()
    df["month_num"] = df["sample_date"].dt.month
    return df


# ── Statistics ────────────────────────────────────────────────────────────────

def monthly_median(df: pd.DataFrame, analyte: str) -> pd.Series:
    sub = df[df["analyte"] == analyte]
    if sub.empty:
        return pd.Series(dtype=float)
    s = sub.groupby("month")["final_result"].median().sort_index()
    full_idx = pd.date_range(s.index.min(), s.index.max(), freq="MS")
    return s.reindex(full_idx)


def seasonal_profile(s: pd.Series) -> dict[int, float]:
    """Monthly median as % deviation from grand median."""
    by_month = s.groupby(s.index.month).median()
    grand    = by_month.median()
    if grand == 0:
        return {m: 0.0 for m in by_month.index}
    return {int(m): round((v / grand - 1) * 100, 1) for m, v in by_month.items()}


def stl_strength(s: pd.Series) -> float | None:
    s2 = s.dropna()
    if len(s2) < 24:
        return None
    try:
        res    = STL(s2, period=12, robust=True).fit()
        var_r  = np.var(res.resid)
        var_sr = np.var(res.seasonal + res.resid)
        return round(float(max(0.0, 1 - var_r / var_sr)), 4) if var_sr else 0.0
    except Exception:
        return None


def peak_month(s: pd.Series) -> int | None:
    s2 = s.dropna()
    if len(s2) < 24:
        return None
    try:
        res  = STL(s2, period=12, robust=True).fit()
        seas = pd.Series(res.seasonal.values, index=s2.index)
        return int(seas.groupby(seas.index.month).mean().idxmax())
    except Exception:
        return None


def trough_month(s: pd.Series) -> int | None:
    s2 = s.dropna()
    if len(s2) < 24:
        return None
    try:
        res  = STL(s2, period=12, robust=True).fit()
        seas = pd.Series(res.seasonal.values, index=s2.index)
        return int(seas.groupby(seas.index.month).mean().idxmin())
    except Exception:
        return None


def season_name(m: int | None) -> str:
    if m is None:
        return "N/A"
    return {12:"winter",1:"winter",2:"winter",
            3:"spring",4:"spring",5:"spring",
            6:"summer",7:"summer",8:"summer"}.get(m, "fall")


def ml(m: int | None) -> str:
    return MONTH_NAMES.get(m, "N/A") if m else "N/A"


def fmt_strength(s) -> str:
    return f"{s:.3f}" if s is not None else "N/A"


def sparkline(profile: dict) -> str:
    blocks = " ▁▂▃▄▅▆▇█"
    vals   = [profile.get(m, 0) for m in range(1, 13)]
    vals   = [0.0 if (v is None or (isinstance(v, float) and np.isnan(v))) else v for v in vals]
    lo, hi = min(vals), max(vals)
    rng    = hi - lo or 1
    return "".join(blocks[round((v - lo) / rng * 8)] for v in vals)


# ── Plotting ──────────────────────────────────────────────────────────────────

def save_profile_grid(results: dict) -> str | None:
    """One subplot per analyte showing the monthly median profile."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        analytes = [k for k, r in results.items() if r["profile"]]
        ncols = 3
        nrows = -(-len(analytes) // ncols)
        fig, axes = plt.subplots(nrows, ncols, figsize=(14, nrows * 3.2))
        axes = np.array(axes).flatten()

        for i, key in enumerate(analytes):
            r    = results[key]
            ax   = axes[i]
            prof = r["profile"]
            months = list(range(1, 13))
            vals   = [prof.get(m, 0) for m in months]
            colors = ["#e06c28" if v >= 0 else "#2a6ebb" for v in vals]
            labels = [MONTH_NAMES[m] for m in months]

            ax.bar(labels, vals, color=colors, edgecolor="white", lw=0.4)
            ax.axhline(0, color="black", lw=0.6)
            ax.set_title(f"{r['display']} ({r['unit']})", fontsize=8, pad=3)
            ax.set_ylabel("% from median", fontsize=7)
            ax.tick_params(axis="x", labelsize=6, rotation=45)
            ax.tick_params(axis="y", labelsize=7)
            for spine in ax.spines.values():
                spine.set_visible(False)

            # annotate peak/trough
            pk = r.get("peak")
            if pk:
                ax.annotate(f"↑{ml(pk)}", xy=(pk - 1, max(vals)),
                            fontsize=6, color="#c0392b", ha="center")

        # hide unused axes
        for j in range(len(analytes), len(axes)):
            axes[j].set_visible(False)

        fig.suptitle("NYC Watershed Water Quality — Seasonal Profiles (last 3 years)",
                     fontsize=11, y=1.01)
        plt.tight_layout(pad=1.0)
        path = PLOTS_DIR / "wq_seasonal_profiles.png"
        fig.savefig(path, dpi=110, bbox_inches="tight")
        plt.close(fig)
        print(f"  saved: {path}")
        return str(path)
    except Exception as e:
        print(f"  grid plot error: {e}")
        return None


def save_key_analyte_plot(series_dict: dict, title: str, filename: str) -> str | None:
    """Time-series overlay for a few analytes that share units."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(11, 4))
        colors = ["#2a6ebb", "#e06c28", "#2aaa5a", "#9b59b6", "#e74c3c"]
        for i, (label, s) in enumerate(series_dict.items()):
            ax.plot(s.index, s.values, label=label, color=colors[i % len(colors)],
                    lw=1.5, marker="o", markersize=3)
        ax.set_title(title, fontsize=10)
        ax.legend(fontsize=8)
        ax.set_ylabel("Monthly median", fontsize=9)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(labelsize=8)
        plt.tight_layout()
        path = PLOTS_DIR / filename
        fig.savefig(path, dpi=110)
        plt.close(fig)
        print(f"  saved: {path}")
        return str(path)
    except Exception as e:
        print(f"  timeseries plot error: {e}")
        return None


def save_heatmap(df: pd.DataFrame, analyte: str, display: str) -> str | None:
    """Heatmap: reservoir × month-of-year for a single analyte."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        sub = df[df["analyte"] == analyte].copy()
        sub["month_num"] = sub["sample_date"].dt.month
        piv = sub.groupby(["reservoir", "month_num"])["final_result"].median().unstack()
        if piv.empty or piv.shape[0] < 2:
            return None

        fig, ax = plt.subplots(figsize=(10, max(3, piv.shape[0] * 0.55)))
        im = ax.imshow(piv.values, aspect="auto", cmap="YlOrRd")
        ax.set_xticks(range(12))
        ax.set_xticklabels([MONTH_NAMES[m] for m in range(1, 13)], fontsize=8)
        ax.set_yticks(range(len(piv.index)))
        ax.set_yticklabels(piv.index.tolist(), fontsize=8)
        plt.colorbar(im, ax=ax, label=display)
        ax.set_title(f"{display} — Median by Reservoir × Month (last 3 yrs)", fontsize=10)
        plt.tight_layout()
        slug = display.lower().replace(" ", "_").replace("/", "_")
        path = PLOTS_DIR / f"wq_heatmap_{slug}.png"
        fig.savefig(path, dpi=110)
        plt.close(fig)
        print(f"  saved: {path}")
        return str(path)
    except Exception as e:
        print(f"  heatmap error: {e}")
        return None


# ── Main analysis ─────────────────────────────────────────────────────────────

def analyse(df: pd.DataFrame) -> dict:
    results = {}
    for api_name, (display, unit) in ANALYTES.items():
        s = monthly_median(df, api_name)
        if s.dropna().empty:
            print(f"  {display}: no data")
            continue
        prof = seasonal_profile(s)
        str_ = stl_strength(s)
        pk   = peak_month(s)
        tr   = trough_month(s)
        n    = s.dropna().shape[0]
        print(f"  {display:<35} n_months={n:<3} strength={str_ if str_ is not None else 'N/A':<7}  peak={ml(pk)}")
        results[api_name] = {
            "display":  display,
            "unit":     unit,
            "series":   s,
            "profile":  prof,
            "strength": str_,
            "peak":     pk,
            "trough":   tr,
            "n_months": n,
            "median":   round(float(s.dropna().median()), 3),
        }
    return results


# ── Report builder ────────────────────────────────────────────────────────────

def build_report(results: dict, df: pd.DataFrame, cutoff: date, latest: date) -> str:
    now  = datetime.now().strftime("%Y-%m-%d")
    rows_per_analyte = df.groupby("analyte").size().to_dict()
    lines = []

    lines += [
        "# NYC Watershed Water Quality: Seasonal Pattern Analysis",
        "",
        f"**Report generated:** {now}  ",
        "**Dataset:** Watershed Water Quality / Limnology (`3y4p-uusw`)  ",
        "**Source:** data.cityofnewyork.us  ",
        f"**Window:** {cutoff} to {latest} (last 3 years of available data)  ",
        f"**Rows analysed:** {len(df):,}  ",
        "**Method:** Monthly median per analyte → STL decomposition (period=12, robust=True)  ",
        "**Seasonal strength:** 0 = no pattern, 1 = perfectly seasonal  ",
        "",
        "---",
        "",
        "## 1. Seasonal Strength by Analyte",
        "",
        "| Analyte | Unit | Months of Data | 3-yr Median | Seasonal Strength | Peak Month | Trough Month | Jan–Dec Sparkline |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for api_name, r in sorted(results.items(), key=lambda x: -(x[1]["strength"] or 0)):
        s_str = f"**{r['strength']:.3f}**" if r["strength"] is not None else "—"
        bar   = sparkline(r["profile"])
        lines.append(
            f"| {r['display']} | {r['unit']} | {r['n_months']} | {r['median']} "
            f"| {s_str} | {ml(r['peak'])} | {ml(r['trough'])} | `{bar}` |"
        )

    lines += ["", "### Monthly Profile Table (% deviation from 3-year monthly median)", ""]
    lines.append("| Analyte | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for api_name, r in results.items():
        p = r["profile"]
        cells = [f"{p.get(m, 0):+.0f}%" for m in range(1, 13)]
        lines.append(f"| {r['display']} | " + " | ".join(cells) + " |")

    lines += [
        "",
        "---",
        "",
        "## 2. Key Seasonal Findings",
        "",
    ]

    # Temperature
    if "Temperature" in results:
        r = results["Temperature"]
        lines += [
            "### Temperature",
            f"Strength: **{fmt_strength(r['strength'])}** | Peak: **{ml(r['peak'])}** | Trough: **{ml(r['trough'])}**",
            "",
            f"Water temperature follows a textbook seasonal cycle, peaking in {ml(r['peak'])} "
            f"and bottoming in {ml(r['trough'])}. "
            f"3-year median surface temperature: {r['median']} °C. "
            f"This is the benchmark driver — most other analytes are thermally or biologically coupled to it.",
            "",
        ]

    # DO — inverse of temperature
    if "Dissolved Oxygen" in results:
        r  = results["Dissolved Oxygen"]
        tr = r.get("trough")
        pk = r.get("peak")
        lines += [
            "### Dissolved Oxygen",
            f"Strength: **{fmt_strength(r['strength'])}** | Peak: **{ml(pk)}** | Trough: **{ml(tr)}**",
            "",
            f"DO is inversely coupled to temperature (cold water holds more oxygen). "
            f"It troughs in {ml(tr)} when surface water is warmest and algal/microbial O₂ "
            f"demand peaks. Low DO in summer stratified layers is a key stress indicator "
            f"for reservoir health.",
            "",
        ]

    # Chlorophyll a — algae
    if "Chlorophyll a" in results:
        r = results["Chlorophyll a"]
        lines += [
            "### Chlorophyll a (Algal Biomass)",
            f"Strength: **{fmt_strength(r['strength'])}** | Peak: **{ml(r['peak'])}** | Trough: **{ml(r['trough'])}**",
            "",
            f"Chlorophyll a is a direct proxy for phytoplankton / algal biomass. "
            f"It peaks in {ml(r['peak'])} when nutrient loading + warm temperatures + "
            f"long daylight hours drive algal blooms. "
            f"High Chlorophyll a is correlated with taste/odor events and elevated Microcystin risk. "
            "Profile: " + ", ".join(f"{ml(m)}={r['profile'].get(m,0):+.0f}%" for m in [5,6,7,8,9,10]) + ".",
            "",
        ]

    # Phosphorus — nutrient driver
    if "Phosphorus, Total (as P)" in results:
        r = results["Phosphorus, Total (as P)"]
        lines += [
            "### Total Phosphorus",
            f"Strength: **{fmt_strength(r['strength'])}** | Peak: **{ml(r['peak'])}** | Trough: **{ml(r['trough'])}**",
            "",
            f"Phosphorus is the primary limiting nutrient for algal growth in NYC's reservoirs. "
            f"It peaks in {ml(r['peak'])} — likely driven by stormwater runoff during spring melt "
            f"and summer thunderstorms washing agricultural and road-surface phosphorus into watersheds.",
            "",
        ]

    # Turbidity — runoff / clarity
    if "Turbidity" in results:
        r = results["Turbidity"]
        lines += [
            "### Turbidity",
            f"Strength: **{fmt_strength(r['strength'])}** | Peak: **{ml(r['peak'])}** | Trough: **{ml(r['trough'])}**",
            "",
            f"Turbidity (water cloudiness) peaks in {ml(r['peak'])} — indicating the timing of "
            f"peak sediment and particulate loading. Spring snowmelt and early-summer storms "
            f"typically flush the most suspended material into reservoirs. "
            f"High turbidity events trigger treatment challenges at NYC's water filtration plants.",
            "",
        ]

    # Fecal Coliform
    if "Coliform, Fecal" in results:
        r = results["Coliform, Fecal"]
        lines += [
            "### Fecal Coliform",
            f"Strength: **{fmt_strength(r['strength'])}** | Peak: **{ml(r['peak'])}** | Trough: **{ml(r['trough'])}**",
            "",
            f"Fecal coliform peaks in {ml(r['peak'])}. "
            f"This likely reflects increased human/animal recreational activity in watersheds "
            f"and elevated bacterial survival in warm water. "
            f"Coliform peaks are a drinking-water safety trigger for NYC DEP.",
            "",
        ]

    # Microcystins — HAB toxins
    if "Microcystins" in results:
        r = results["Microcystins"]
        lines += [
            "### Microcystins (Cyanotoxins)",
            f"Strength: **{fmt_strength(r['strength'])}** | Peak: **{ml(r['peak'])}** | Trough: **{ml(r['trough'])}**",
            "",
            f"Microcystins — toxins produced by cyanobacteria (blue-green algae) — peak in "
            f"{ml(r['peak'])}. They require warm, nutrient-rich, calm water to bloom. "
            f"The WHO guideline for drinking water is 1 µg/L; recreational thresholds are lower. "
            f"3-year median: {r['median']} µg/L.",
            "",
        ]

    # Plankton
    if "Total Plankton" in results:
        r = results["Total Plankton"]
        lines += [
            "### Total Plankton",
            f"Strength: **{fmt_strength(r['strength'])}** | Peak: **{ml(r['peak'])}** | Trough: **{ml(r['trough'])}**",
            "",
            f"Total plankton follows thermal stratification — blooms in {ml(r['peak'])} "
            f"when warmer surface layers provide ideal growing conditions. "
            f"Plankton succession (diatoms → green algae → cyanobacteria) drives the "
            f"characteristic taste and odor events in NYC's water supply each summer.",
            "",
        ]

    # Cross-analyte coupling note
    temp_r = results.get("Temperature")
    do_r   = results.get("Dissolved Oxygen")
    chl_r  = results.get("Chlorophyll a")
    if temp_r and do_r:
        temp_pk = temp_r.get("peak")
        do_tr   = do_r.get("trough")
        if temp_pk and do_tr and abs(temp_pk - do_tr) <= 1:
            lines += [
                "### Coupled Signal: Temperature ↔ Dissolved Oxygen",
                "",
                f"Temperature peaks in **{ml(temp_pk)}** and DO troughs in **{ml(do_tr)}** — "
                "confirming the classic inverse thermal-oxygen coupling. As surface water warms, "
                "oxygen solubility drops and biological oxygen demand rises, compressing the "
                "oxygenated layer and stressing aquatic organisms in lower strata.",
                "",
            ]

    # --- Reservoir heatmap summary ---
    lines += [
        "---",
        "",
        "## 3. Reservoir-Level Seasonal Patterns (Temperature)",
        "",
    ]

    temp_sub = df[df["analyte"] == "Temperature"].copy()
    temp_sub["month_num"] = temp_sub["sample_date"].dt.month
    piv = temp_sub.groupby(["reservoir", "month_num"])["final_result"].median().unstack()

    if not piv.empty:
        lines.append("Monthly median surface temperature (°C) by reservoir:\n")
        header = "| Reservoir | " + " | ".join(MONTH_NAMES[m] for m in range(1, 13)) + " |"
        sep    = "|---|" + "---|" * 12
        lines += [header, sep]
        for res in piv.index:
            cells = [f"{piv.loc[res, m]:.1f}" if m in piv.columns and not pd.isna(piv.loc[res, m])
                     else "—" for m in range(1, 13)]
            lines.append(f"| {res} | " + " | ".join(cells) + " |")
        lines.append("")

    # Chlorophyll reservoir heatmap summary
    chl_sub = df[df["analyte"] == "Chlorophyll a"].copy()
    if not chl_sub.empty:
        chl_sub["month_num"] = chl_sub["sample_date"].dt.month
        piv_c = chl_sub.groupby(["reservoir", "month_num"])["final_result"].median().unstack()
        if not piv_c.empty:
            lines.append("Monthly median Chlorophyll a (µg/L) by reservoir:\n")
            header = "| Reservoir | " + " | ".join(MONTH_NAMES[m] for m in range(1, 13)) + " |"
            sep    = "|---|" + "---|" * 12
            lines += [header, sep]
            for res in piv_c.index:
                cells = [f"{piv_c.loc[res, m]:.2f}" if m in piv_c.columns and not pd.isna(piv_c.loc[res, m])
                         else "—" for m in range(1, 13)]
                lines.append(f"| {res} | " + " | ".join(cells) + " |")
            lines.append("")

    lines += [
        "---",
        "",
        "## 4. Surprising / Notable Patterns",
        "",
    ]

    surprises = []

    # DO trough — severity
    if do_r and do_r.get("profile"):
        min_do_month = min(do_r["profile"], key=lambda m: do_r["profile"].get(m, 0))
        min_do_pct   = do_r["profile"].get(min_do_month, 0)
        surprises.append(
            f"**Dissolved oxygen drops {abs(min_do_pct):.0f}% below the annual median in "
            f"{ml(min_do_month)}** — a significant summer oxygen deficit that can create "
            f"hypoxic conditions in deeper reservoir layers, stressing fish and other aquatic life."
        )

    # Chlorophyll — summer bloom magnitude
    if chl_r and chl_r.get("profile") and chl_r.get("peak"):
        pk  = chl_r["peak"]
        pct = chl_r["profile"].get(pk, 0)
        surprises.append(
            f"**Chlorophyll a spikes {pct:+.0f}% above average in {ml(pk)}** — "
            f"indicating a pronounced algal bloom season. This is the ecological fingerprint "
            f"of the reservoir's growing season and the primary driver of taste/odor events "
            f"in the drinking water supply."
        )

    # Turbidity timing vs temperature
    turb_r = results.get("Turbidity")
    if turb_r and temp_r and turb_r.get("peak") and temp_r.get("peak"):
        if turb_r["peak"] != temp_r["peak"]:
            surprises.append(
                f"**Turbidity peaks in {ml(turb_r['peak'])} but temperature peaks in "
                f"{ml(temp_r['peak'])}** — sediment loading is driven by early-season runoff "
                f"(snowmelt, rain-on-snow events), not by summer heat. This offset means "
                f"the worst clarity periods and the worst algal periods don't fully overlap."
            )

    # Phosphorus spring flush
    phos_r = results.get("Phosphorus, Total (as P)")
    if phos_r and phos_r.get("peak"):
        surprises.append(
            f"**Total Phosphorus peaks in {ml(phos_r['peak'])}** — watershed nutrient loading "
            f"is concentrated in early-season storm events. This spring phosphorus pulse seeds "
            f"the nutrient reservoir that fuels late-summer algal blooms weeks or months later "
            f"(a lag effect between cause and consequence)."
        )

    # Microcystin vs Chlorophyll lag
    micro_r = results.get("Microcystins")
    if micro_r and chl_r and micro_r.get("peak") and chl_r.get("peak"):
        lag = micro_r["peak"] - chl_r["peak"]
        if lag > 0:
            surprises.append(
                f"**Microcystins peak {lag} month(s) after Chlorophyll a** "
                f"({ml(chl_r['peak'])} vs {ml(micro_r['peak'])}) — "
                f"toxic cyanobacteria bloom slightly later than the general algal community, "
                f"once warm, stratified, low-flushing conditions allow them to outcompete "
                f"other phytoplankton. This lag is an early-warning window for water managers."
            )

    if not surprises:
        surprises.append("No striking cross-analyte surprises detected — data may be insufficient for 3 years.")

    for s in surprises:
        lines.append(f"- {s}\n")

    lines += [
        "---",
        "",
        "## 5. Methodology",
        "",
        "- **Data window:** latest available date − 3 years, filtered to 11 key analytes",
        "- **Aggregation:** monthly median across all sites, depths, and reservoirs (city-wide)",
        "- **STL decomposition:** `STL(series, period=12, robust=True)` — robust to outliers and sampling gaps",
        "- **Seasonal strength:** `max(0, 1 − Var(residual) / Var(seasonal+residual))`",
        "- **Profile:** median by calendar month, expressed as % deviation from the 3-year monthly median",
        "- **Note:** 3 years = ~3 repetitions per season — STL estimates are noisier than longer series;",
        "  treat strength values as indicative rather than definitive",
        "",
        "**Dataset:** Watershed Water Quality Limnology  ",
        "**API:** `https://data.cityofnewyork.us/resource/3y4p-uusw.json`  ",
        "**Dataset ID:** `3y4p-uusw`",
    ]

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    PLOTS_DIR.mkdir(exist_ok=True)

    df, cutoff, latest = fetch_last_3_years()
    df = clean(df)

    print(f"\nAnalysing {len(df):,} measurements across {df['analyte'].nunique()} analytes...")
    results = analyse(df)

    print("\nGenerating plots...")
    save_profile_grid(results)
    # Time-series overlay for thermal/oxygen group
    for_overlay = {}
    for key in ["Temperature", "Dissolved Oxygen"]:
        api = next((k for k, v in ANALYTES.items() if v[0] == key), None)
        if api and api in results:
            for_overlay[key] = results[api]["series"]
    if for_overlay:
        save_key_analyte_plot(for_overlay, "Temperature & Dissolved Oxygen — Monthly Median",
                              "wq_temp_do.png")

    # Nutrient group overlay
    nutrient_overlay = {}
    for api_name, (display, _) in ANALYTES.items():
        if display in ("Total Phosphorus", "Total Nitrogen", "Dissolved Organic Carbon"):
            if api_name in results:
                nutrient_overlay[display] = results[api_name]["series"]
    if nutrient_overlay:
        save_key_analyte_plot(nutrient_overlay, "Nutrients — Monthly Median", "wq_nutrients.png")

    # Heatmaps for temperature and chlorophyll
    save_heatmap(df, "Temperature",   "Temperature (°C)")
    save_heatmap(df, "Chlorophyll a", "Chlorophyll a (µg/L)")

    print("\nBuilding report...")
    report = build_report(results, df, cutoff, latest)
    REPORT_PATH.write_text(report)
    print(f"Report written to: {REPORT_PATH}")

    # Terminal summary
    print("\n" + "=" * 65)
    print("SEASONAL STRENGTH SUMMARY (last 3 years)")
    print("=" * 65)
    for api_name, r in sorted(results.items(), key=lambda x: -(x[1]["strength"] or 0)):
        bar = sparkline(r["profile"])
        s   = r["strength"]
        s_  = f"{s:.3f}" if s is not None else " N/A"
        print(f"  {r['display']:<35} strength={s_}  peak={ml(r['peak']):<4}  [{bar}]")


if __name__ == "__main__":
    main()
