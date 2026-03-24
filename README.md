# NYC Oracle

A prophecy lookup interface for NYC seasonal patterns. Enter a prophecy number to discover what the city's data portends.

## About the Prophecies

The prophecies are generated from seasonal patterns in NYC Open Data using statistical decomposition. Datasets from the Department of Environmental Protection, DOHMH, and 311 service request data are analyzed to identify strong, recurring cycles throughout the year.

**Prophecies are generated and maintained in a separate repository:** [`oracle-prophecy-creation`](https://github.com/nyc-oracle/oracle-prophecy-creation)

When new prophecies are generated, the `prophecies_all.csv` file is updated and deployed here.

## Local Preview

Preview the website locally without needing to push to GitHub.

### Using Python (Recommended)

```bash
cd /path/to/nyc-oracle.github.io
python3 -m http.server 8000