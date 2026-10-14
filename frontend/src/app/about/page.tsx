import Link from "next/link";

export const metadata = {
  title: "How It Works — Wildfire Risk Monitor",
  description:
    "Honest explanation of the algorithms, data sources, and limitations of the Wildfire Risk Monitor.",
};

export default function AboutPage() {
  return (
    <div className="about-page">
      <nav className="about-nav">
        <Link href="/" className="about-back">← Back to Map</Link>
      </nav>

      <article className="about-content">
        <h1>How It Works</h1>

        <div className="honesty-banner">
          <strong>Honesty First.</strong> This application uses{" "}
          <em>synthetic (simulated)</em> hotspot data when{" "}
          <code>DATA_SOURCE=synthetic</code>. The algorithms, formulas, and
          pipeline architecture are real; the fire detections and weather values
          are generated. The UI always shows a SIMULATED DATA badge when
          synthetic mode is active.
        </div>

        {/* 1. Data Flow */}
        <section className="about-section">
          <h2>1. Data Flow</h2>
          <pre className="mermaid-block">{`
NASA FIRMS (VIIRS NRT CSV)          OR          Synthetic Generator
         │                                              │
         └──────────────── /hotspots API ──────────────┘
                                │
                    Grid-cell weather lookup
                    (Open-Meteo 0.25° cache)
                                │
                    5-Factor Risk Scorer
                    (intensity, wind, fuel, exposure, persistence)
                                │
                    Spread Ellipse (Anderson 1983)
                    Smoke Plume (Gaussian)
                    Exposure (settlements within 10/25 km)
                                │
                    Frontend (Next.js 14 + React-Leaflet)
          `}</pre>
        </section>

        {/* 2. Synthetic Generator */}
        <section className="about-section">
          <h2>2. Synthetic Data Generator</h2>
          <p><strong>What it does:</strong> Produces a seeded, reproducible VIIRS NRT-schema dataset covering 6 fire-prone regions of India for up to 30 simulated days.</p>
          <h3>Algorithm</h3>
          <ol>
            <li>For each region and each day, draw a Poisson number of fire clusters: <code>k ~ Poisson(λ · seasonal_weight)</code></li>
            <li>Cluster centre drawn uniformly from the region bbox. Each cluster has 3–25 hotspots drawn from a 2D Gaussian around the centre.</li>
            <li>Seasonal weight: <code>w = exp(−d²/8)</code> where d = circular-month distance from peak fire season.</li>
            <li>Brightness Ti4 ~ N(region_mean + dryness×20, 6) clipped to [300, 367] K.</li>
            <li>FRP ~ LogNormal(log(mean_frp × (1+dryness)), 0.6) clipped to [0.5, 150] MW.</li>
            <li>Confidence: h if B&gt;0.65 and FRP&gt;15; l if B&lt;0.30 or FRP&lt;3; else n.</li>
          </ol>
          <h3>Real vs Simulated</h3>
          <table className="comparison-table">
            <thead><tr><th>Field</th><th>Real source it mimics</th><th>How simulated</th><th>How to replace</th></tr></thead>
            <tbody>
              <tr><td>bright_ti4</td><td>VIIRS 375m Ti4 band</td><td>Gaussian around regional mean</td><td>Set DATA_SOURCE=live</td></tr>
              <tr><td>frp</td><td>FIRMS FRP (MW)</td><td>Log-normal, correlated with brightness</td><td>Set DATA_SOURCE=live</td></tr>
              <tr><td>ndvi</td><td>MODIS/Sentinel-2 NDVI</td><td>Uniform in regional range</td><td>Google Earth Engine API</td></tr>
              <tr><td>wind_speed_kmh</td><td>Open-Meteo 10m wind</td><td>Gamma-distributed, regional mean</td><td>Already calls Open-Meteo (hybrid mode)</td></tr>
            </tbody>
          </table>
        </section>

        {/* 3. Risk Model */}
        <section className="about-section">
          <h2>3. Risk Score</h2>
          <p><strong>What it does:</strong> Assigns a 0–100 heuristic risk score to each hotspot. NOT a certified fire-behaviour model.</p>
          <h3>Formula</h3>
          <pre className="code-block">{`Score = 30%·Intensity + 25%·Wind + 25%·FuelDryness + 10%·Exposure + 10%·Persistence

Intensity  = clip((B−300)/67, 0,1)·0.5 + clip(log(FRP+1)/log(151), 0,1)·0.5
             × conf_mult  (conf_mult: h=1.2, n=1.0, l=0.7)
Wind       = clip(U/50, 0, 1)          (U in km/h)
FuelDryness= 0.5·(1−ndvi) + 0.3·(1−RH/100) + 0.2·clip((T−20)/30, 0,1)
Exposure   = clip(log(pop+1)/log(500001), 0, 1)
Persistence= clip(days/6, 0, 1)`}</pre>
          <h3>Worked example</h3>
          <pre className="code-block">{`B=345K, FRP=25MW, conf=h, U=18km/h, NDVI=0.3, RH=35%, T=36°C, pop=5000, days=2

Intensity  = (0.672·0.5 + 0.645·0.5) × 1.2 = 0.779
Wind       = 18/50 = 0.360
FuelDryness= 0.5·(1−0.3) + 0.3·(1−0.35) + 0.2·clip(0.533,0,1) = 0.418
Exposure   = log(5001)/log(500001) = 0.489
Persistence= 2/6 = 0.333

Score = 30%·0.779 + 25%·0.360 + 25%·0.418 + 10%·0.489 + 10%·0.333
      = 0.234 + 0.090 + 0.105 + 0.049 + 0.033 = 0.511 → 51.1 → High`}</pre>
        </section>

        {/* 4. Spread Ellipse */}
        <section className="about-section">
          <h2>4. Fire Spread Ellipse</h2>
          <p><strong>What it does:</strong> Projects the fire front as a wind-driven ellipse for 1h/3h/6h/12h.</p>
          <h3>Formula (Anderson 1983 / FARSITE-style)</h3>
          <pre className="code-block">{`LBR = 1 + 0.125 × U         (length-to-breadth ratio; U = wind speed km/h)
ROS = 0.5 × (1 + 0.04 × U)  (rate of spread km/h; base from config)
a   = ROS × hours            (semi-major axis, km)
b   = a / LBR                (semi-minor axis, km)
Area = π × a × b             (km²)

Degree conversion (corrected):
  Δlat_deg = km / 111.32
  Δlon_deg = km / (111.32 × cos(lat_rad))`}</pre>
          <p className="limitation">⚠ Limitations: no terrain slope, no fuel-model variation, no spotting. Real FARSITE uses Rothermel equations. This is a geometric approximation only.</p>
        </section>

        {/* 5. Smoke Plume */}
        <section className="about-section">
          <h2>5. Smoke Plume / AQI Estimate</h2>
          <p><strong>What it does:</strong> Draws a translucent downwind plume and estimates PM2.5 concentration.</p>
          <pre className="code-block">{`Q      = FRP × 0.02        (emission rate g/s, after Ichoku 2003)
σ      = 0.12 × x          (plume width m, grows with downwind distance x)
PM2.5  = Q / (π × σ² × U) × 10⁶   (µg/m³, at centreline)

AQI category (Indian CPCB 2014):
  ≤30: Good, ≤60: Satisfactory, ≤90: Moderate,
  ≤120: Poor, ≤250: Very Poor, >250: Severe`}</pre>
          <p className="limitation">⚠ This is a simplified 2D Gaussian; ignores terrain, atmospheric stability class, aerosol chemistry, and deposition. For real AQI monitoring use SAFAR or CPCB live data.</p>
        </section>

        {/* 6. Migration path */}
        <section className="about-section">
          <h2>6. Migrating to Live Data</h2>
          <ol>
            <li>Set <code>DATA_SOURCE=live</code> in <code>backend/.env</code> and provide a real <code>FIRMS_MAP_KEY</code>.</li>
            <li>For NDVI: replace the synthetic value with a Google Earth Engine NDVI lookup or a cached MODIS MOD13A2 tile.</li>
            <li>For historical validation: compare against FIRMS Archive (firms.modaps.eosdis.nasa.gov/map/) or burned-area products (MCD64A1).</li>
            <li>For risk validation: use historical fire-spread data (NIFC, NWCG) to calibrate the weight coefficients in config.py.</li>
          </ol>
        </section>
      </article>
    </div>
  );
}
