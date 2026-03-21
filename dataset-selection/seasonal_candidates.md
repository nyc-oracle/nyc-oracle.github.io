# NYC Seasonal Data: Candidates for Poetic Predictions

Datasets with strong annual cyclical patterns, evaluated for use as source material for season-based oracular predictions. Strength scores use STL decomposition (0 = flat, 1 = perfectly seasonal).

---

## Tier 1: Most Compelling

### Dog Bites
**Strength: 0.65 | Peak: summer | 10 years**
People bite — and get bitten — more in summer. Every July the city's dogs grow restless. A clean, legible curve with an obvious narrative: heat, irritability, exposed skin. Perfect for warm-month predictions.
`data.cityofnewyork.us/d/rsgh-akpg`

### Watershed Water Quality – Limnology
**Strength: 0.94 | Peak: varies by measure | 40 years**
The city's reservoir system has been sampled monthly for four decades. Algae blooms, oxygen levels, turbidity — each follows its own seasonal rhythm tied to snowmelt, summer stratification, and autumn turnover. The longest, cleanest record in the corpus. Predictions could speak in the language of the water supply itself.
`data.cityofnewyork.us/d/3y4p-uusw`

### Shootings
**Strength: 0.69 | Peak: summer | 20 years**
Gun violence in NYC follows the heat. The curve is consistent across two decades — it rises in May, peaks in July–August, falls with the temperature. Somber but one of the most reliable seasonal signals in the city's public record.
`data.cityofnewyork.us/d/5ucz-vwe8`

### Urban Park Ranger Animal Condition Response
**Strength: 0.44 | Peak: summer | 8 years**
Rangers respond to injured, sick, or distressed wildlife across the city's parks. Calls surge in spring and summer — baby animals, heat stress, human-wildlife contact. An unexpected window into the city's non-human residents and their seasonal vulnerabilities.
`data.cityofnewyork.us/d/fuhs-xmg2`

### Urban Park Ranger Engagement Tracker
**Strength: 0.73 | Peak: summer | 5 years**
Tracks ranger-led public programs and encounters. Peaks sharply in summer. The city's wildest civil servants appear and disappear with the seasons.
`data.cityofnewyork.us/d/rcd4-qkns`

### NYC Ferry Ridership
**Strength: 0.80 | Peak: July | 8.5 years**
The clearest leisure-vs-necessity split in the transit system. Ferry ridership collapses in winter and peaks mid-summer — it is the city's most purely seasonal transit mode, a fair-weather vessel.
`data.cityofnewyork.us/d/t5n6-gx8c`

### NYPD Arrests
**Strength: 0.58 | Peak: summer | 19 years**
Arrests follow a seasonal arc — more in summer, quieter in winter. Nineteen years of data make this one of the most historically grounded signals in the corpus.
`data.cityofnewyork.us/d/8h9b-rp9u`

### NYC Pool Inspections
**Strength: 0.72 | Peak: summer | 6 years**
Pools open, pools are inspected, pools close. A tight seasonal window with a near-perfect curve. Speaks to the brief, permitted season of public water.
`data.cityofnewyork.us/d/3kfa-rvez`

---

## Tier 2: Interesting, Worth Considering

### Street Construction Closures
**Strength: 0.74 | Peak: summer | 35 years**
The city tears itself apart on a schedule. Construction closures peak in summer — warmer months when asphalt can be laid and disruption is most visible. 35 years of data.
`data.cityofnewyork.us/d/ezy6-djsf`

### Street Resurfacing
**Strength: 0.83 | Peak: summer | 6 years**
The city repaves itself each summer. The asphalt calendar is highly seasonal — winter cold stops the work, summer heat enables it. Could yield predictions about repair, renewal, disruption.
`data.cityofnewyork.us/d/xnfm-u3k5`

### NYPD Personnel Demographics (Hiring)
**Strength: 0.50 | Peak: varies | 52 years**
Application dates for NYPD go back over 50 years — by far the longest personnel record in the corpus. Police hiring follows a seasonal bureaucratic rhythm. Less poetic but historically deep.
`data.cityofnewyork.us/d/5vr7-5fki`

### 911 End-to-End Data
**Strength: 0.43 | Peak: summer | 12 years**
When people call for help, and how long it takes to arrive, follows a seasonal shape. Summer increases call volume and strains response times.
`data.cityofnewyork.us/d/t7p9-n9dy`

---

## 311 Calls: Deep Dive

**Dataset:** `erm2-nwe9` — 311 Service Requests, 2015–present, 15M+ complaints

Rather than using the full 311 dataset, the best approach for predictions is to **choose a specific complaint type** as a seasonal signal. The contrast between complaint types is itself the story.

| Complaint Type | Strength | Peak | Poetic angle |
|---|---|---|---|
| Noise – Street/Sidewalk | **0.918** | June | the city grows loud with heat |
| HEAT/HOT WATER | **0.912** | December | landlords and cold |
| Water System | 0.883 | July | pipes under pressure |
| Noise – Vehicle | 0.848 | September | windows still open |
| UNSANITARY CONDITION | 0.718 | July | summer and decomposition |
| Street Condition | 0.655 | March | winter's damage revealed |
| Blocked Driveway | 0.075 | — | the city's most constant grievance — never seasonal, never resolved |

**Most useful for predictions:**
- **HEAT/HOT WATER + Noise - Street/Sidewalk** as a pair — they are near-perfect seasonal inverses. Together they tell the full year.
- **DHS (Dept of Homeless Services)** complaints peak in August (strength 0.894) — a quantified signal of summer street homelessness visibility. Less obvious than noise, more unsettling.
- **Blocked Driveway** as a foil: the complaint that never changes. A symbol of permanent urban friction.

---

## Rodent Inspections

**Dataset:** `p937-wjvj`
**Monthly seasonality: 0.139 (LOW)** — inspections are administratively scheduled, not reactive to rat biology. The inspection calendar does not follow the rat.

**But:** a striking weekly cycle exists.

| Day | Relative volume |
|---|---|
| Mon–Fri | ~1.35x average |
| Sat–Sun | ~0.10x average |

Inspectors don't work weekends. The rats do. A 48-hour surveillance gap recurs every week, every year, across the whole city. The most interesting thing about rodent inspections is what they *don't* capture.

**Prediction angle:** not "when are there more rats" but "when is the city looking, and when has it looked away."

---

## MTA Ridership

**Dataset:** `vxuj-8kew` (data.ny.gov), supplemented by Ferry `t5n6-gx8c`
**Note:** 2020–2025 data only; COVID recovery embedded in the signal.

| Mode | Strength | Peak | Character |
|---|---|---|---|
| LIRR | 0.879 | October | suburban commuter + leisure |
| NYC Ferry | 0.803 | July | fair-weather only |
| Subway | 0.787 | October | back-to-school/office |
| Metro-North | 0.678 | October | Hudson Valley + CT |
| Staten Island Railway | 0.542 | October | smallest, most local |
| Bus | 0.442 | October | moderate |
| Bridges & Tunnels | 0.329 | August | road-trip season |
| Access-A-Ride | **0.000** | — | medically driven — no seasonality at all |

**Access-A-Ride** is the most remarkable outlier: the one transit mode that is completely indifferent to season. Medical necessity has no summer. Useful as a counterpoint — a prediction about constancy rather than change.

**Ferry** is the cleanest seasonal signal: it rises and falls with weather alone, unmediated by commuting obligation.
