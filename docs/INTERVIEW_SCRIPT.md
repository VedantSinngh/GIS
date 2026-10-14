# Wildfire Risk Monitor — Interview Scripts

## 60-Second Pitch (honest version)

"I built a full-stack GIS application that ingests NASA FIRMS satellite fire-detection data, enriches each hotspot with real-time weather from Open-Meteo, and computes a five-factor risk score covering fire intensity, wind, fuel dryness, population exposure, and cluster persistence.

**Because the free FIRMS demo key returns only three hard-coded points**, I built a seeded synthetic data generator that reproduces the exact VIIRS NRT CSV schema and regional Indian fire-season climatology — so I could develop and test the full pipeline end-to-end. The algorithms are the real ones. Swapping `DATA_SOURCE=live` in the environment file switches the app to NASA data with zero code changes.

The UI — Next.js 14 with React-Leaflet — shows spread ellipses using Anderson's 1983 length-to-breadth ratio, a simplified Gaussian smoke-plume AQI estimate, settlement exposure within 10 km, auto-generated alerts, a time-slider playback over 30 days, and a Recharts analytics dashboard. I never hide the 'SIMULATED DATA' banner — honesty is a design constraint, not an afterthought."

---

## 3-Minute Deep Dive

### What the app does
A Wildfire and Air Quality Risk Monitor for India. It renders hundreds of VIIRS satellite fire hotspots on a Leaflet map, colour-coded by a 0–100 risk score. Clicking any hotspot shows risk-breakdown bars (how much each of the five factors contributed), spread-ellipse projections for 1h/3h/6h/12h, a Gaussian smoke plume with Indian AQI category, and the nearest settlements with their estimated fire-front ETAs.

### What is real
- **Architecture**: FastAPI backend → React/Next.js frontend, modular routers, Pydantic validation end-to-end matching TypeScript interfaces.
- **Algorithms**: Anderson 1983 / FARSITE-style length-to-breadth ratio; Gaussian plume dispersion (Ichoku 2003 emission factor); simplified FWI-style fuel-dryness index; haversine distance; Keetch-Byram-inspired temperature/humidity weighting.
- **Schema**: The synthetic data exactly matches the NASA FIRMS VIIRS NRT CSV columns.
- **Weather**: In `hybrid` mode the backend calls Open-Meteo's free API per 0.25° grid cell (cached for 15 min).

### What is simulated
- The hotspot detections themselves — latitude, longitude, brightness, FRP, confidence, acquisition time.
- The NDVI values (regional range, Gaussian noise).
- The wind/temperature/humidity when Open-Meteo is unreachable (neutral fallback, not 0 wind).

### Why a heuristic score, not a physics model
A validated fire-behaviour model (e.g. FlamMap, Phoenix RapidFire) requires fuel-model rasters, terrain DEMs, and per-species ignition thresholds — data pipelines of their own. My score is a transparent, explainable, document-linked decision-support heuristic. Every weight is in a config file; every factor is shown in the UI with its formula.

### How I would validate it
Against NASA FIRMS Archive data (historical NRT CSVs) and MODIS burned-area product MCD64A1. The correlations to check: risk≥75 should predict ≥70% of pixels that later appear in MCD64A1 within 6 hours under similar wind conditions.

---

## 10 Likely Follow-up Questions

**Q1. Why a heuristic and not the Rothermel surface-fire model?**
Rothermel requires per-cell fuel-model parameters (13 Scott-Burgan categories) from a rasterised surface-fuel dataset. For India, ICFRE publishes some fuel data but not at VIIRS 375m resolution. The heuristic lets me demo the full pipeline with transparent, auditable weights without a 40GB fuel raster download.

**Q2. How did you validate the synthetic data is plausible?**
Three checks: (a) the brightness-FRP Pearson correlation is ≥ 0.2 (pytest asserts this); (b) Punjab/Haryana fires peak in October in simulation, matching the ISFR crop-residue burning calendar; (c) all points pass a coarse India land-mask (no ocean points). I also plan a distribution-comparison notebook plotting simulated vs. FIRMS 2023 archive brightness histograms and wind roses.

**Q3. What are the biggest limits of synthetic data?**
Spatial clustering does not reproduce actual ignition topology (road corridors, agricultural edges, lightning patterns). Temporal persistence is random-duration, not driven by suppression or rainfall. The seasonal weight curve is a Gaussian approximation of a complex climatology.

**Q4. How does the spread ellipse differ from real fire modelling?**
Anderson 1983 is purely wind-driven and ignores: slope (fire accelerates uphill at ~doubling per 15° slope), fuel heterogeneity, spotting (embers landing ahead of the front), and suppression. FARSITE uses Rothermel equations through a fuel grid. My ellipse is a first-order geometric approximation useful for demo purposes.

**Q5. How is weather cached?**
Quantize (lat, lon) to the nearest 0.25° grid cell. This means all hotspots within a ~28 km square share one Open-Meteo call. The `cachetools.TTLCache` holds results for 15 minutes. On failure, a neutral value is returned with `weather_ok=false` — never 0 km/h wind.

**Q6. How would you switch to live FIRMS?**
Set `DATA_SOURCE=live` and add a real `FIRMS_MAP_KEY`. The `/hotspots` router calls `fetch_firms_hotspots()`, which parses the VIIRS NRT CSV from `firms.modaps.eosdis.nasa.gov/api/area/csv/`. The CSV schema is identical to the synthetic schema, so zero frontend changes. For `hybrid` mode the backend tries live first and falls back to synthetic.

**Q7. What would you do with Google Earth Engine NDVI?**
Replace the synthetic NDVI field with a GEE JavaScript API call for `MODIS/006/MOD13A2` at each hotspot's coordinates. I'd cache the result in a PostGIS tile table keyed on (h3-index, month) so the per-hotspot lookup is a table scan rather than a live API call.

**Q8. How does the CORS fix work?**
The original code had `allow_origins=["*"]` with `allow_credentials=True` — this is a browser security violation (credentials are silently dropped). The fix: if the allowed-origins list contains `"*"`, set `allow_credentials=False`. Production should list explicit origin URLs in `ALLOWED_ORIGINS` and enable credentials.

**Q9. How scalable is the synthetic generator?**
For 30 days over 6 regions it produces ~5,000–15,000 rows in ~0.4 seconds (pure numpy). It is warmed into memory at startup. For larger windows (90 days), the parquet CLI output (~2MB) can be loaded lazily with polars or dask. The grid-cell weather cache prevents N+1 calls to Open-Meteo.

**Q10. What would make this production-ready?**
Four additions: (1) PostGIS for spatial queries (viewport-bounded fetch, spatial joins for settlements); (2) Celery + Redis for background ingestion of FIRMS data every 3 hours; (3) A validated risk model calibrated against MCD64A1 burn-area history; (4) Auth (API key) on all write endpoints and rate-limiting on the public read endpoints.
