# Real-Time Wildfire & Air Quality Risk Monitor

A full-stack application that pulls live fire-detection data from NASA FIRMS, correlates it with real-time wind data from Open-Meteo, and computes a heuristic spread risk score.

## Architecture

- **Backend**: FastAPI (Python) - Handles API requests, data fetching from external APIs, caching, and risk score computation.
- **Frontend**: Next.js (TypeScript/React) - Renders an interactive map using Leaflet, allowing users to filter hotspots and view projected spread cones.

## Data Sources

1. **NASA FIRMS Area API**: Active fire hotspots (lat, lon, brightness, confidence). Updates ~3 hours.
2. **Open-Meteo**: Wind speed and direction for a given coordinate.
3. **Google Earth Engine (Planned)**: Sentinel-2 NDVI to approximate vegetation dryness and fuel availability.

## Risk Scoring Methodology

The `risk_score` (0-100) is a heuristic decision-support estimate and **NOT** a certified fire-behavior model.

**Formula Weights:**
- **Fire Intensity (40%)**: Normalized based on FIRMS brightness (typically 295K - 400K) and confidence level (`h`, `n`, `l`).
- **Wind Speed (40%)**: Normalized up to 50 km/h (assumed as highly dangerous).
- **Vegetation Dryness (NDVI) (20%)**: Lower NDVI values (drier vegetation) result in a higher risk contribution. 
  *(Note: For the initial version, NDVI lookup is skipped, defaulting to a neutral contribution of 50%).*

**Risk Cone:**
When a hotspot is selected, a projected spread cone is visualized on the map. The direction is determined by the wind direction (meteorological), and the length of the cone is proportional to the wind speed.

## Setup Instructions

### Backend (FastAPI)

1. Navigate to the `backend` directory.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   Copy `.env.example` to `.env` and add your free NASA FIRMS Map Key.
4. Run the development server:
   ```bash
   python main.py
   ```
   The backend will be available at `http://localhost:8000`.

### Frontend (Next.js)

1. Navigate to the `frontend` directory.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
   The frontend will be available at `http://localhost:3000`.
