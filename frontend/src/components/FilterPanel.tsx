"use client";

import { useState } from "react";
import type { FilterState } from "../lib/types";
import { exportCsvUrl, exportGeoJsonUrl } from "../lib/api";

interface Props {
  filters: FilterState;
  onChange: (f: FilterState) => void;
  dataSource: string | null;
}

const STATES = [
  "Uttarakhand", "Himachal Pradesh", "Odisha", "Chhattisgarh",
  "Madhya Pradesh", "Maharashtra", "Kerala", "Karnataka",
  "Assam", "Manipur", "Mizoram", "Nagaland", "Arunachal Pradesh",
  "Meghalaya", "Punjab", "Haryana",
];

const LAND_COVERS = [
  "pine_forest", "dry_deciduous", "mixed_forest",
  "tropical_forest", "jhum_agriculture", "cropland",
];

export default function FilterPanel({ filters, onChange, dataSource }: Props) {
  const [open, setOpen] = useState(true);

  const setF = (patch: Partial<FilterState>) =>
    onChange({ ...filters, ...patch });

  const toggleConf = (v: "l" | "n" | "h") => {
    const next = filters.confidence.includes(v)
      ? filters.confidence.filter((c) => c !== v)
      : [...filters.confidence, v];
    setF({ confidence: next });
  };

  const toggleDaynight = (v: "D" | "N") => {
    const next = filters.daynight.includes(v)
      ? filters.daynight.filter((d) => d !== v)
      : [...filters.daynight, v];
    setF({ daynight: next });
  };

  return (
    <div className="filter-panel">
      <button
        className="filter-panel__toggle"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <span>Filters</span>
        <span>{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="filter-panel__body">
          {/* Risk threshold */}
          <div className="filter-row">
            <label className="filter-label">
              Min Risk Score
              <span className="filter-value">{filters.minRisk}</span>
            </label>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={filters.minRisk}
              onChange={(e) => setF({ minRisk: +e.target.value })}
            />
          </div>

          {/* Confidence */}
          <div className="filter-row">
            <span className="filter-label">Confidence</span>
            <div className="filter-chips">
              {(["h", "n", "l"] as const).map((c) => (
                <button
                  key={c}
                  className={`chip ${filters.confidence.includes(c) ? "chip--active" : ""}`}
                  onClick={() => toggleConf(c)}
                >
                  {c === "h" ? "High" : c === "n" ? "Nominal" : "Low"}
                </button>
              ))}
            </div>
          </div>

          {/* Day / Night */}
          <div className="filter-row">
            <span className="filter-label">Day / Night</span>
            <div className="filter-chips">
              {(["D", "N"] as const).map((v) => (
                <button
                  key={v}
                  className={`chip ${filters.daynight.includes(v) ? "chip--active" : ""}`}
                  onClick={() => toggleDaynight(v)}
                >
                  {v === "D" ? "☀ Day" : "🌙 Night"}
                </button>
              ))}
            </div>
          </div>

          {/* State */}
          <div className="filter-row">
            <label className="filter-label" htmlFor="state-select">State</label>
            <select
              id="state-select"
              value={filters.state}
              onChange={(e) => setF({ state: e.target.value })}
              className="filter-select"
            >
              <option value="">All states</option>
              {STATES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {/* Land cover */}
          <div className="filter-row">
            <label className="filter-label" htmlFor="lc-select">Land Cover</label>
            <select
              id="lc-select"
              value={filters.landCover}
              onChange={(e) => setF({ landCover: e.target.value })}
              className="filter-select"
            >
              <option value="">All types</option>
              {LAND_COVERS.map((lc) => (
                <option key={lc} value={lc}>
                  {lc.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </div>

          {/* Date range */}
          <div className="filter-row filter-row--dates">
            <label className="filter-label">Date range</label>
            <div className="filter-dates">
              <input
                type="date"
                value={filters.dateStart}
                onChange={(e) => setF({ dateStart: e.target.value })}
                className="filter-date-input"
              />
              <span>→</span>
              <input
                type="date"
                value={filters.dateEnd}
                onChange={(e) => setF({ dateEnd: e.target.value })}
                className="filter-date-input"
              />
            </div>
          </div>

          {/* Export */}
          <div className="filter-row filter-row--export">
            <span className="filter-label">Export filtered</span>
            <div className="filter-chips">
              <a
                href={exportCsvUrl(filters.minRisk)}
                target="_blank"
                rel="noreferrer"
                className="chip chip--export"
              >
                CSV
              </a>
              <a
                href={exportGeoJsonUrl(filters.minRisk)}
                target="_blank"
                rel="noreferrer"
                className="chip chip--export"
              >
                GeoJSON
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
