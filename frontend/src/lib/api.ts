/**
 * API client for Wildfire Risk Monitor backend.
 * All functions are strictly typed; no `any`.
 */

import type {
  HotspotsResponse,
  AlertsResponse,
  AnalyticsResponse,
  SpreadResponse,
  ExposureResponse,
  FilterState,
} from "./types";

// Legacy re-export so existing imports of `Hotspot` still work
export type { Hotspot } from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`);
  if (!res.ok) {
    const errorData: { detail?: string } = await res
      .json()
      .catch(() => ({}));
    throw new Error(errorData.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ── Hotspots ──────────────────────────────────────────────────────────────────

export async function fetchHotspots(
  bbox: string,
  filters?: Partial<FilterState>,
  dateStart?: string,
  dateEnd?: string
): Promise<HotspotsResponse> {
  const params = new URLSearchParams({ bbox });
  if (filters?.minRisk && filters.minRisk > 0)
    params.set("min_risk", filters.minRisk.toString());
  if (filters?.confidence?.length)
    params.set("confidence", filters.confidence.join(","));
  if (filters?.state) params.set("state", filters.state);
  if (filters?.landCover) params.set("land_cover", filters.landCover);
  if (filters?.daynight?.length)
    params.set("daynight", filters.daynight[0]); // single value
  if (dateStart ?? filters?.dateStart)
    params.set("start", dateStart ?? filters!.dateStart);
  if (dateEnd ?? filters?.dateEnd)
    params.set("end", dateEnd ?? filters!.dateEnd);
  return apiFetch<HotspotsResponse>(`/hotspots?${params.toString()}`);
}

// ── Spread ellipse ─────────────────────────────────────────────────────────────

export async function fetchSpread(
  hotspotId: string,
  lat: number,
  lon: number,
  windSpeed: number,
  windDirection: number,
  hours?: string
): Promise<SpreadResponse> {
  const params = new URLSearchParams({
    lat: lat.toString(),
    lon: lon.toString(),
    wind_speed: windSpeed.toString(),
    wind_direction: windDirection.toString(),
  });
  if (hours) params.set("hours", hours);
  return apiFetch<SpreadResponse>(`/spread/${hotspotId}?${params.toString()}`);
}

// ── Legacy risk-cone (backwards compat) ───────────────────────────────────────

export async function fetchRiskCone(hotspot: {
  id: string;
  latitude: number;
  longitude: number;
  wind_speed: number | null;
  wind_direction: number | null;
}): Promise<{ type: string; features: unknown[] }> {
  const params = new URLSearchParams({
    lat: hotspot.latitude.toString(),
    lon: hotspot.longitude.toString(),
    wind_speed: (hotspot.wind_speed ?? 10).toString(),
    wind_direction: (hotspot.wind_direction ?? 270).toString(),
  });
  return apiFetch(`/risk-cone/${hotspot.id}?${params.toString()}`);
}

// ── Exposure ──────────────────────────────────────────────────────────────────

export async function fetchExposure(
  hotspotId: string,
  lat: number,
  lon: number,
  windSpeed: number,
  windDirection: number,
  radiusKm?: number
): Promise<ExposureResponse> {
  const params = new URLSearchParams({
    lat: lat.toString(),
    lon: lon.toString(),
    wind_speed: windSpeed.toString(),
    wind_direction: windDirection.toString(),
  });
  if (radiusKm) params.set("radius_km", radiusKm.toString());
  return apiFetch<ExposureResponse>(`/exposure/${hotspotId}?${params.toString()}`);
}

// ── Alerts ────────────────────────────────────────────────────────────────────

export async function fetchAlerts(minRisk?: number): Promise<AlertsResponse> {
  const params = new URLSearchParams();
  if (minRisk !== undefined) params.set("min_risk", minRisk.toString());
  return apiFetch<AlertsResponse>(`/alerts?${params.toString()}`);
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export async function fetchAnalytics(
  dateStart?: string,
  dateEnd?: string
): Promise<AnalyticsResponse> {
  const params = new URLSearchParams();
  if (dateStart) params.set("start", dateStart);
  if (dateEnd) params.set("end", dateEnd);
  return apiFetch<AnalyticsResponse>(`/analytics?${params.toString()}`);
}

// ── Export URLs (direct browser links) ───────────────────────────────────────

export function exportCsvUrl(minRisk?: number): string {
  const params = minRisk ? `?min_risk=${minRisk}` : "";
  return `${API_BASE_URL}/export/csv${params}`;
}

export function exportGeoJsonUrl(minRisk?: number): string {
  const params = minRisk ? `?min_risk=${minRisk}` : "";
  return `${API_BASE_URL}/export/geojson${params}`;
}
