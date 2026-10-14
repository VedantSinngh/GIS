"use client";

import { useEffect, useState, useMemo, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";

import {
  fetchHotspots,
  fetchAlerts,
  fetchAnalytics,
} from "../lib/api";
import type {
  Hotspot,
  HotspotsResponse,
  Alert,
  AnalyticsResponse,
  FilterState,
} from "../lib/types";

import SourceBadge from "../components/SourceBadge";
import FilterPanel from "../components/FilterPanel";
import DetailPanel from "../components/DetailPanel";
import AlertsPanel from "../components/AlertsPanel";
import TimeSlider from "../components/TimeSlider";
import Analytics from "../components/Analytics";

// SSR-safe dynamic imports
const Map = dynamic(() => import("../components/Map"), { ssr: false });

const DEFAULT_BBOX = "68.1,6.7,97.4,35.5";

type SidebarTab = "detail" | "alerts" | "analytics";
type Basemap = "dark" | "satellite" | "terrain";

const DEFAULT_FILTERS: FilterState = {
  minRisk: 0,
  confidence: [],
  daynight: [],
  state: "",
  landCover: "",
  dateStart: "",
  dateEnd: "",
};

export default function Home() {
  // ── Data state ───────────────────────────────────────────────────────────
  const [response, setResponse] = useState<HotspotsResponse | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [alertsLoading, setAlertsLoading] = useState(false);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  // ── UI state ─────────────────────────────────────────────────────────────
  const [selectedHotspot, setSelectedHotspot] = useState<Hotspot | null>(null);
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [activeTab, setActiveTab] = useState<SidebarTab>("detail");
  const [basemap, setBasemap] = useState<Basemap>("dark");

  // ── Time slider state ─────────────────────────────────────────────────────
  const [playing, setPlaying] = useState(false);
  const [playSpeed, setPlaySpeed] = useState(1);
  const [dayIndex, setDayIndex] = useState(0);
  const playTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Fetch functions ───────────────────────────────────────────────────────
  const loadHotspots = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchHotspots(DEFAULT_BBOX, filters);
      setResponse(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load data.");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  const loadAlerts = useCallback(async () => {
    setAlertsLoading(true);
    try {
      const data = await fetchAlerts(50);
      setAlerts(data.alerts);
    } catch {
      // non-critical
    } finally {
      setAlertsLoading(false);
    }
  }, []);

  const loadAnalytics = useCallback(async () => {
    setAnalyticsLoading(true);
    try {
      const data = await fetchAnalytics();
      setAnalytics(data);
    } catch {
      // non-critical
    } finally {
      setAnalyticsLoading(false);
    }
  }, []);

  // Initial load + 15-min auto-refresh
  useEffect(() => {
    loadHotspots();
    loadAlerts();
    loadAnalytics();
    const interval = setInterval(() => {
      loadHotspots();
      loadAlerts();
    }, 15 * 60 * 1000);
    return () => clearInterval(interval);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Reload when filters change
  useEffect(() => {
    loadHotspots();
  }, [loadHotspots]);

  // ── Derived data ──────────────────────────────────────────────────────────
  const allHotspots: Hotspot[] = response?.hotspots ?? [];

  const sortedDays = useMemo(() => {
    const days = [...new Set(allHotspots.map((h) => h.acq_date))].sort();
    return days;
  }, [allHotspots]);

  // When time slider is active, show only hotspots from the selected day
  const visibleHotspots = useMemo(() => {
    if (sortedDays.length === 0) return allHotspots;
    const selectedDay = sortedDays[dayIndex] ?? "";
    return allHotspots.filter((h) => h.acq_date === selectedDay);
  }, [allHotspots, sortedDays, dayIndex]);

  // ── Playback ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (playing) {
      playTimerRef.current = setInterval(() => {
        setDayIndex((prev) => {
          if (prev >= sortedDays.length - 1) {
            setPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 800 / playSpeed);
    } else {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
    }
    return () => {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
    };
  }, [playing, playSpeed, sortedDays.length]);

  // ── Select hotspot by ID (from alerts click) ──────────────────────────────
  const selectById = useCallback(
    (id: string) => {
      const h = allHotspots.find((x) => x.id === id);
      if (h) {
        setSelectedHotspot(h);
        setActiveTab("detail");
      }
    },
    [allHotspots]
  );

  // ── Tab change ────────────────────────────────────────────────────────────
  const handleTabChange = (tab: SidebarTab) => {
    setActiveTab(tab);
    if (tab === "detail" && !selectedHotspot) {
      // fine
    }
  };

  return (
    <div className="app-container">
      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <div className="sidebar">
        {/* Header */}
        <div className="sidebar-header">
          <h1 className="sidebar-title">
            🔥 Wildfire Risk Monitor
          </h1>
          <div className="sidebar-subtitle">India · {response?.total ?? 0} hotspots</div>
          <SourceBadge source={response?.data_source ?? null} />
        </div>

        {/* Tab bar */}
        <div className="tab-bar" role="tablist">
          <button
            role="tab"
            aria-selected={activeTab === "detail"}
            className={`tab-btn ${activeTab === "detail" ? "tab-btn--active" : ""}`}
            onClick={() => handleTabChange("detail")}
          >
            Detail
          </button>
          <button
            role="tab"
            aria-selected={activeTab === "alerts"}
            className={`tab-btn ${activeTab === "alerts" ? "tab-btn--active" : ""}`}
            onClick={() => handleTabChange("alerts")}
          >
            Alerts <span className="tab-badge">{alerts.length}</span>
          </button>
          <button
            role="tab"
            aria-selected={activeTab === "analytics"}
            className={`tab-btn ${activeTab === "analytics" ? "tab-btn--active" : ""}`}
            onClick={() => handleTabChange("analytics")}
          >
            Analytics
          </button>
        </div>

        {/* Scrollable panel body */}
        <div className="sidebar-body">
          {error && <div className="error-message">⚠ {error}</div>}

          {activeTab === "detail" && (
            <>
              <FilterPanel
                filters={filters}
                onChange={setFilters}
                dataSource={response?.data_source ?? null}
              />
              {selectedHotspot ? (
                <DetailPanel
                  hotspot={selectedHotspot}
                  onClose={() => setSelectedHotspot(null)}
                />
              ) : (
                <p className="no-selection-hint">
                  Click a hotspot on the map to view details.
                </p>
              )}
            </>
          )}

          {activeTab === "alerts" && (
            <AlertsPanel
              alerts={alerts}
              loading={alertsLoading}
              onSelectHotspot={selectById}
            />
          )}

          {activeTab === "analytics" && (
            <Analytics data={analytics} loading={analyticsLoading} />
          )}
        </div>

        {/* Basemap switcher */}
        <div className="basemap-switcher">
          {(["dark", "satellite", "terrain"] as Basemap[]).map((b) => (
            <button
              key={b}
              className={`basemap-btn ${basemap === b ? "basemap-btn--active" : ""}`}
              onClick={() => setBasemap(b)}
            >
              {b.charAt(0).toUpperCase() + b.slice(1)}
            </button>
          ))}
        </div>

        {/* How it works link */}
        <Link href="/about" className="about-link">
          How it works →
        </Link>
      </div>

      {/* ── Map area ────────────────────────────────────────────────────── */}
      <div className="map-container">
        {loading && (
          <div className="loading-overlay">
            <div className="loading-spinner" />
            <span>Loading hotspots…</span>
          </div>
        )}

        <Map
          hotspots={visibleHotspots}
          selectedHotspot={selectedHotspot}
          setSelectedHotspot={(h) => {
            setSelectedHotspot(h);
            if (h) setActiveTab("detail");
          }}
          basemap={basemap}
        />

        {/* Legend */}
        <div className="map-legend">
          <div className="legend-title">Risk Score</div>
          {[
            { label: "Extreme (≥75)", color: "#ff2200" },
            { label: "High (≥50)", color: "#ff6600" },
            { label: "Moderate (≥25)", color: "#ffaa00" },
            { label: "Low (<25)", color: "#00fa9a" },
          ].map(({ label, color }) => (
            <div key={label} className="legend-item">
              <span className="legend-dot" style={{ background: color }} />
              <span>{label}</span>
            </div>
          ))}
          <div className="legend-title" style={{ marginTop: 8 }}>Spread Rings</div>
          <div className="legend-item">
            <span className="legend-line" />
            <span>1h / 3h / 6h / 12h projection</span>
          </div>
        </div>

        {/* Time slider */}
        {sortedDays.length > 1 && (
          <div className="time-slider-bar">
            <TimeSlider
              days={sortedDays}
              currentIndex={dayIndex}
              playing={playing}
              speed={playSpeed}
              onChange={setDayIndex}
              onPlayPause={() => setPlaying((p) => !p)}
              onSpeedChange={setPlaySpeed}
            />
          </div>
        )}
      </div>
    </div>
  );
}
