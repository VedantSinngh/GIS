"use client";

import type { Hotspot, RiskComponent } from "../lib/types";

interface Props {
  hotspot: Hotspot | null;
  onClose: () => void;
}

const RISK_COLORS: Record<string, string> = {
  Extreme: "#ff2200",
  High: "#ff6600",
  Moderate: "#ffaa00",
  Low: "#00fa9a",
};

function RiskBar({ component }: { component: RiskComponent }) {
  const pct = Math.round(component.normalized * 100);
  const contPct = Math.round(component.contribution * 100);
  return (
    <div className="risk-bar">
      <div className="risk-bar__header">
        <span className="risk-bar__name">{component.name}</span>
        <span className="risk-bar__pct">{pct}% × {Math.round(component.weight * 100)}%w = {contPct}pts</span>
      </div>
      <div className="risk-bar__track">
        <div
          className="risk-bar__fill"
          style={{ width: `${pct}%`, opacity: 0.85 }}
        />
      </div>
      <div className="risk-bar__label">{component.label}</div>
    </div>
  );
}

export default function DetailPanel({ hotspot, onClose }: Props) {
  if (!hotspot) return null;

  const levelColor = RISK_COLORS[hotspot.risk_level ?? "Low"] ?? "#aaa";

  return (
    <div className="detail-panel">
      <button className="detail-panel__close" onClick={onClose} aria-label="Close detail panel">✕</button>

      {/* Risk header */}
      <div className="detail-panel__risk-header" style={{ borderColor: levelColor }}>
        <div className="detail-risk-score" style={{ color: levelColor }}>
          {hotspot.risk_score ?? "—"}<span>/100</span>
        </div>
        <div className="detail-risk-level" style={{ color: levelColor }}>
          {hotspot.risk_level ?? "Unknown"}
        </div>
        {!hotspot.weather_ok && (
          <div className="detail-warn">⚠ Weather data unavailable — neutral values used</div>
        )}
        <div className="detail-source-tag">
          {hotspot.source === "synthetic" ? "🔬 SIMULATED" : "📡 FIRMS LIVE"}
        </div>
      </div>

      {/* Core info */}
      <div className="detail-section">
        <div className="stat-row">
          <span className="stat-label">Coordinates</span>
          <span className="stat-value">{hotspot.latitude.toFixed(4)}, {hotspot.longitude.toFixed(4)}</span>
        </div>
        <div className="stat-row">
          <span className="stat-label">Brightness (Ti4)</span>
          <span className="stat-value">{hotspot.bright_ti4.toFixed(1)} K</span>
        </div>
        <div className="stat-row">
          <span className="stat-label">FRP</span>
          <span className="stat-value">{hotspot.frp?.toFixed(1) ?? "—"} MW</span>
        </div>
        <div className="stat-row">
          <span className="stat-label">Confidence</span>
          <span className="stat-value">
            {hotspot.confidence === "h" ? "High ✓" : hotspot.confidence === "l" ? "Low" : "Nominal"}
          </span>
        </div>
        <div className="stat-row">
          <span className="stat-label">Detected</span>
          <span className="stat-value">{hotspot.acq_date} {hotspot.acq_time} UTC {hotspot.daynight === "D" ? "☀" : "🌙"}</span>
        </div>
        <div className="stat-row">
          <span className="stat-label">Satellite</span>
          <span className="stat-value">{hotspot.satellite ?? "VIIRS"}</span>
        </div>
      </div>

      {/* Weather */}
      <div className="detail-section">
        <h3 className="detail-section-title">Weather</h3>
        <div className="stat-row">
          <span className="stat-label">Wind</span>
          <span className="stat-value">{hotspot.wind_speed ?? "??"} km/h @ {hotspot.wind_direction ?? "??"}°</span>
        </div>
        <div className="stat-row">
          <span className="stat-label">Temperature</span>
          <span className="stat-value">{hotspot.temperature_c?.toFixed(1) ?? "—"} °C</span>
        </div>
        <div className="stat-row">
          <span className="stat-label">Humidity</span>
          <span className="stat-value">{hotspot.humidity_pct?.toFixed(0) ?? "—"} %</span>
        </div>
        <div className="stat-row">
          <span className="stat-label">NDVI</span>
          <span className="stat-value">{hotspot.ndvi?.toFixed(3) ?? "—"}</span>
        </div>
        <div className="stat-row">
          <span className="stat-label">Land Cover</span>
          <span className="stat-value">{hotspot.land_cover?.replace(/_/g, " ") ?? "—"}</span>
        </div>
      </div>

      {/* Risk breakdown */}
      {hotspot.risk_breakdown && hotspot.risk_breakdown.length > 0 && (
        <div className="detail-section">
          <h3 className="detail-section-title">Risk Breakdown</h3>
          {hotspot.risk_breakdown.map((comp) => (
            <RiskBar key={comp.name} component={comp} />
          ))}
        </div>
      )}

      {/* Nearest settlements */}
      {hotspot.nearest_settlements && hotspot.nearest_settlements.length > 0 && (
        <div className="detail-section">
          <h3 className="detail-section-title">Nearest Settlements</h3>
          {hotspot.nearest_settlements.slice(0, 3).map((s) => (
            <div key={s.name} className="settlement-row">
              <span className="settlement-name">{s.name}</span>
              <span className="settlement-meta">
                {s.distance_km.toFixed(1)} km ·{" "}
                {s.population.toLocaleString()} pop.
                {s.eta_hours !== null && ` · ETA ${s.eta_hours.toFixed(1)}h`}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Smoke plume AQI */}
      {hotspot.smoke_plume && (
        <div className="detail-section">
          <h3 className="detail-section-title">Downwind Air Quality</h3>
          <div className="stat-row">
            <span className="stat-label">PM2.5 estimate</span>
            <span className="stat-value">{hotspot.smoke_plume.pm25_ug_m3.toFixed(1)} µg/m³</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">AQI Category</span>
            <span className={`stat-value aqi-${hotspot.smoke_plume.aqi_category.toLowerCase().replace(" ", "-")}`}>
              {hotspot.smoke_plume.aqi_category}
            </span>
          </div>
        </div>
      )}

      {/* Share link */}
      <button
        className="detail-share-btn"
        onClick={() => {
          const url = `${window.location.origin}?lat=${hotspot.latitude}&lon=${hotspot.longitude}&id=${hotspot.id}`;
          navigator.clipboard.writeText(url);
        }}
      >
        Copy share link
      </button>
    </div>
  );
}
