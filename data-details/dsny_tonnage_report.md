# DSNY Monthly Tonnage: Seasonal Pattern Analysis

**Report generated:** 2026-03-16  
**Dataset:** DSNY Monthly Tonnage Data (`ebb7-mvp5`)  
**Source:** data.cityofnewyork.us  
**Coverage:** 1990-01 to 2026-02 (24,883 district-month rows)  
**Method:** STL decomposition (period=12 months, robust=True)  
**Seasonal strength:** 0 = no pattern, 1 = perfectly seasonal

---

## 1. City-Wide Seasonal Strength by Waste Stream

| Waste Stream | Mean Tons/Month | Seasonal Strength | Peak Month | Peak % above avg | Trough Month | Trough % below avg | Trend (YoY%) |
|---|---|---|---|---|---|---|---|
| Residential organics | 1,921 | **0.405** | Nov | +73.4% | Feb | -36.6% | ▲ +16.4%/yr |
| Refuse (garbage) | 245,353 | **0.173** | Jun | +6.4% | Feb | -15.2% | → -0.3%/yr |
| Metal/Glass/Plastic recycling | 18,800 | **0.050** | Jun | +8.0% | Feb | -12.1% | ▲ +1.4%/yr |
| Paper recycling | 23,447 | **0.000** | Dec | +13.8% | Feb | -13.4% | → +0.4%/yr |

### Seasonal Profiles (% deviation from annual mean, Jan–Dec)

| Waste Stream | J | F | M | A | M | J | J | A | S | O | N | D |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Refuse (garbage) | -8% | -15% | -1% | +1% | +8% | +6% | +3% | +2% | +2% | +2% | +1% | +0% |
| Paper recycling | -2% | -13% | -0% | -1% | +4% | +6% | -5% | -6% | +1% | +3% | -0% | +14% |
| Metal/Glass/Plastic recycling | +1% | -12% | -1% | +3% | +6% | +8% | +3% | +0% | -2% | -1% | -7% | +2% |
| Residential organics | -13% | -37% | -40% | -1% | +9% | +0% | -5% | -9% | -14% | +12% | +73% | +25% |

### ASCII Sparklines (Jan–Dec)

- **Refuse (garbage)**: `▂ ▅▆██▆▆▆▆▆▅` (peak=Jun, trough=Feb)
- **Paper recycling**: `▃ ▄▄▅▆▃▂▄▅▄█` (peak=Dec, trough=Feb)
- **Metal/Glass/Plastic recycling**: `▅ ▄▆▇█▆▅▄▄▂▆` (peak=Jun, trough=Feb)
- **Residential organics**: `▂  ▃▃▃▂▂▂▄█▅` (peak=Nov, trough=Feb)

---

## 2. Key Findings

### Refuse (Garbage)
Seasonal strength: **0.173** — weak

Refuse peaks in **Jun** (+6.4% above average) and troughs in **Feb** (-15.2% below average). The summer peak reflects more outdoor eating, takeout containers, and higher residential activity. Winter dip may reflect reduced outdoor activity and packaging differences.

### Paper Recycling
Seasonal strength: **0.000**

Paper peaks in **Dec** (+13.8%). Holiday shopping and gift wrapping drive a post-December surge in cardboard and paper recycling. Summer sees reduced office paper but increased retail packaging.

### Metal / Glass / Plastic Recycling
Seasonal strength: **0.050**

MGP peaks in **Jun** (+8.0%). Bottles and cans — beverages — drive this pattern. Summer outdoor events, beer/soda consumption, and backyard gatherings produce the highest bottle/can recycling volumes.

### Residential Organics
Seasonal strength: **0.405**

Organics peaks in **Nov** (+73.4%). Note: NYC's curbside organics program expanded significantly in 2021-2023, so earlier years may show near-zero values (program was opt-in/limited rollout). The seasonal profile reflects both food scraps and yard/leaf waste.

### Cross-Stream Comparison

- **Most seasonal stream:** Residential organics (strength 0.405)
- **Least seasonal stream:** Paper recycling (strength 0.000)

Waste streams peak at different times, revealing distinct drivers:
  - Refuse (garbage): peak in Jun (summer)
  - Paper recycling: peak in Dec (winter)
  - Metal/Glass/Plastic recycling: peak in Jun (summer)
  - Residential organics: peak in Nov (fall)

---

## 3. Borough-Level Refuse Seasonality

| Borough | Seasonal Strength | Peak Month |
|---------|-------------------|------------|
| Bronx | 0.431 | Jun |
| Brooklyn | 0.450 | Jun |
| Manhattan | 0.288 | Jun |
| Queens | 0.534 | Jun |
| Staten Island | 0.751 | May |

Borough-level strengths show whether some areas have more pronounced seasonal waste patterns — e.g., tourist-heavy Manhattan vs residential outer boroughs.

---

## 4. Long-Term Trends (1990–2026)

- **Refuse (garbage)**: roughly flat at **-0.3%/year** on average (compound annual rate from log-linear fit)
- **Paper recycling**: roughly flat at **+0.4%/year** on average (compound annual rate from log-linear fit)
- **Metal/Glass/Plastic recycling**: increasing at **+1.4%/year** on average (compound annual rate from log-linear fit)
- **Residential organics**: increasing at **+16.4%/year** on average (compound annual rate from log-linear fit)

Refuse and paper recycling trends reflect NYC's zero-waste initiatives, population growth, and the rise of e-commerce packaging. Organics tonnage shows rapid growth from near-zero as the city's composting program scaled up.

---

## 5. Methodology

- **STL decomposition** (Cleveland et al., 1990): `STL(series, period=12, robust=True)`
- **Seasonal strength:** `max(0, 1 − Var(residual) / Var(seasonal + residual))`
- **Seasonal profile:** average STL seasonal component by calendar month
- **Trend:** compound annual rate from log-linear fit to annual totals
- **Data aggregation:** district-level rows summed to city-wide monthly totals
- Leading/trailing zero rows dropped before fitting

**Dataset:** DSNY Monthly Tonnage Data  
**API:** `https://data.cityofnewyork.us/resource/ebb7-mvp5.json`  
**Dataset ID:** `ebb7-mvp5`