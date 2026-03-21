# Oracle Prophecy Creation

Seasonal patterns in NYC Open Data, used as source material for oracular predictions about the city. Datasets were evaluated using STL decomposition (seasonal strength: 0 = flat, 1 = perfectly seasonal). Those with strong, legible annual cycles become the empirical foundation for prophecy.

---

## Primary Datasets

### 311 Service Requests
**Dataset ID:** `erm2-nwe9` | data.cityofnewyork.us | 2015–present

Rather than the full 311 corpus, specific complaint types are used as seasonal signals. 

| Complaint Type | Seasonal Strength | Peak | Poetic Signal |
|---|---|---|---|
| Noise – Street/Sidewalk | **0.918** | June | the city grows loud with heat |
| HEAT/HOT WATER | **0.912** | December | landlords and cold |
| Water System | 0.883 | July | pipes under pressure |
| Noise – Vehicle | 0.848 | September | windows still open |
| UNSANITARY CONDITION | 0.718 | July | summer and decomposition |
| Street Condition | 0.655 | March | winter's damage revealed |
| Blocked Driveway | 0.075 | — | the city's most constant grievance — never seasonal, never resolved |

**DHS (Dept of Homeless Services)** complaints (strength 0.894, peak August) are tracked separately as an agency-level signal — a quantified measure of summer street homelessness visibility.

---

### DOHMH Dog Bite Data
**Dataset ID:** `rsgh-akpg` | data.cityofnewyork.us | 10 years

**Seasonal strength: 0.65 | Peak: summer**

Dog bites surge every July. Heat, irritability, exposed skin. A clean, legible curve with an obvious narrative. One of the most human-readable seasonal signals in the corpus.

---

### Watershed Water Quality – Limnology
**Dataset ID:** `3y4p-uusw` | data.cityofnewyork.us | 40 years

**Seasonal strength: up to 1.000 | Peak: varies by analyte**

The city's reservoir system has been sampled monthly for four decades. Each analyte follows its own seasonal rhythm — snowmelt, summer stratification, autumn turnover.

| Analyte | Strength | Peak | Signal |
|---|---|---|---|
| Total Phosphorus | 1.000 | October | nutrient pulse after storms |
| Fecal Coliform | 0.991 | May | warm water, human contact |
| Dissolved Oxygen | 0.987 | March | cold water breathes deepest |
| Temperature | 0.973 | August | the reservoir's own summer |
| Chlorophyll a | 0.919 | September | algal blooms, taste and odor events |
| Total Plankton | 0.858 | February | bloom before the thaw |
| Turbidity | 0.791 | January | cloudiest when coldest |

The longest, cleanest record in the corpus. Predictions can speak in the language of the water supply itself.

---

### NYPD Arrests Data (Historic)
**Dataset ID:** `8h9b-rp9u` | data.cityofnewyork.us | 19 years

**Seasonal strength: 0.58 | Peak: summer**

Arrests follow a seasonal arc — more in summer, quieter in winter. Nineteen years of data make this one of the most historically grounded signals in the corpus.

---

### Shootings (2006–Present)
**Dataset ID:** `5ucz-vwe8` | data.cityofnewyork.us | 20 years

**Seasonal strength: 0.69 | Peak: July–August**

Gun violence in NYC follows the heat. The curve is consistent across two decades — rising in May, peaking in July–August, falling with the temperature.

---

### NYC Ferry Ridership
**Dataset ID:** `t5n6-gx8c` | data.cityofnewyork.us | 8.5 years

**Seasonal strength: 0.80 | Peak: July**

The clearest leisure-vs-necessity split in the transit system. Ferry ridership collapses in winter and peaks mid-summer — the city's most purely seasonal transit mode. A fair-weather vessel.

---

### Urban Park Ranger Animal Condition Response
**Dataset ID:** `fuhs-xmg2` | data.cityofnewyork.us | 8 years

**Seasonal strength: 0.44 | Peak: summer**

Rangers respond to injured, sick, or distressed wildlife across the city's parks. Calls surge in spring and summer — baby animals, heat stress, human-wildlife contact. An unexpected window into the city's non-human residents.

---

### Urban Park Ranger Engagement Tracker
**Dataset ID:** `rcd4-qkns` | data.cityofnewyork.us | 5 years

**Seasonal strength: 0.73 | Peak: summer**

Tracks ranger-led public programs and encounters. The city's wildest civil servants appear and disappear with the seasons.

---

### NYC Pool Inspections
**Dataset ID:** `3kfa-rvez` | data.cityofnewyork.us | 6 years

**Seasonal strength: 0.72 | Peak: summer**

Pools open, pools are inspected, pools close. A tight seasonal window with a near-perfect curve. The brief, permitted season of public water.

---

## Secondary Datasets

### DSNY Monthly Tonnage
**Dataset ID:** `ebb7-mvp5` | data.cityofnewyork.us | 1990–present

Waste stream seasonality reveals what the city consumes and discards, and when.

| Waste Stream | Strength | Peak | Signal |
|---|---|---|---|
| Residential Organics | 0.405 | November | leaves, scraps, the composting city |
| Refuse (garbage) | 0.173 | June | summer outdoor eating |
| Metal/Glass/Plastic | 0.050 | June | bottles and cans — beverages |
| Paper recycling | 0.000 | December | holiday cardboard, then silence |

---

### MTA Daily Ridership
**Dataset ID:** `vxuj-8kew` | data.ny.gov | 2020–present

Note: COVID-era disruptions are embedded in the signal. Seasonal patterns are more reliable for 2022–2025.

| Mode | Strength | Peak | Signal |
|---|---|---|---|
| LIRR | 0.879 | October | suburban leisure + commute |
| NYC Ferry | 0.803 | July | fair-weather only |
| Subway | 0.787 | October | back-to-school return |
| Metro-North | 0.678 | October | Hudson Valley and CT |
| Bridges & Tunnels | 0.329 | August | road-trip season |
| **Access-A-Ride** | **0.000** | — | **medical necessity has no summer** |

Access-A-Ride is the most remarkable outlier: the one transit mode completely indifferent to season. Useful as a counterpoint — a prediction about constancy rather than change.

---

### Rodent Inspections
**Dataset ID:** `p937-wjvj` | data.cityofnewyork.us

**Monthly seasonal strength: 0.139 (LOW)**

Inspections are administratively scheduled, not reactive to rat biology. The inspection calendar does not follow the rat. But a different pattern emerges:

| Day | Relative volume |
|---|---|
| Mon–Fri | ~1.35x average |
| Sat–Sun | ~0.10x average |

A 48-hour surveillance gap recurs every week, every year, across the whole city. The prophecy here is not "when are there more rats" but "when is the city looking, and when has it looked away."

---

## Methodology

All seasonality scores use **STL (Seasonal-Trend decomposition using LOESS)** with `robust=True` to down-weight outliers.

```
Seasonal Strength = max(0, 1 − Var(residual) / Var(seasonal + residual))
```

Peak month is identified by averaging the STL seasonal component by calendar month across all years. Full methodology: [cyclical_report.md](cyclical_report.md), [dsny_tonnage_report.md](dsny_tonnage_report.md), [watershed_wq_report.md](watershed_wq_report.md).

All NYC data is fetched from public Socrata endpoints at data.cityofnewyork.us. MTA ridership is from data.ny.gov.

### Strength Levels

Seasonal strength scores are binned into three levels, applied consistently across all datasets:

| Threshold | Label |
|---|---|
| strength >= 0.5 | HIGH |
| 0.2 <= strength < 0.5 | MODERATE |
| strength < 0.2 | LOW |

Rodent day-of-week activity uses a separate relative threshold (volume compared to the daily mean):

| Relative to mean | Level |
|---|---|
| > 1.2x | HIGH |
| 0.8x – 1.2x | average |
| 0.5x – 0.8x | low |
| < 0.5x | very low |

### Data Eligibility

Before scoring, each series must pass quality gates:

- **311 agencies:** >= 36 months of data, < 30% missing months
- **STL minimum:** >= 24 non-null observations (2× the 12-month period)
- **MTA:** first and last (partial) months trimmed before scoring
