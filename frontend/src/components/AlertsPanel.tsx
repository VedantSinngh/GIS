"use client";

import type { Alert } from "../lib/types";

interface Props {
  alerts: Alert[];
  loading: boolean;
  onSelectHotspot: (id: string) => void;
}

const SEVERITY_COLORS: Record<string, string> = {
  Extreme: "#ff2200",
  Critical: "#ff6600",
  Warning: "#ffaa00",
  Info: "#4da6ff",
};

const SEVERITY_ICON: Record<string, string> = {
  Extreme: "🚨",
  Critical: "🔥",
  Warning: "⚠",
  Info: "ℹ",
};

export default function AlertsPanel({ alerts, loading, onSelectHotspot }: Props) {
  if (loading) {
    return <div className="alerts-panel"><p className="alerts-empty">Loading alerts…</p></div>;
  }

  return (
    <div className="alerts-panel">
      <h3 className="alerts-title">
        🚨 Active Alerts
        <span className="alerts-count">{alerts.length}</span>
      </h3>
      {alerts.length === 0 && (
        <p className="alerts-empty">No alerts above threshold.</p>
      )}
      <div className="alerts-list">
        {alerts.slice(0, 20).map((alert) => (
          <button
            key={alert.id}
            className="alert-card"
            style={{ borderLeftColor: SEVERITY_COLORS[alert.severity] ?? "#aaa" }}
            onClick={() => onSelectHotspot(alert.hotspot_id)}
          >
            <div className="alert-card__header">
              <span className="alert-icon">{SEVERITY_ICON[alert.severity]}</span>
              <span
                className="alert-severity"
                style={{ color: SEVERITY_COLORS[alert.severity] }}
              >
                {alert.severity}
              </span>
              <span className="alert-date">{alert.acq_date}</span>
            </div>
            <p className="alert-message">{alert.message}</p>
            <div className="alert-meta">
              Risk: <strong>{alert.risk_score.toFixed(0)}</strong>
              {alert.settlement_name && ` · Near ${alert.settlement_name}`}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
