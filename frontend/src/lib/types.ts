/**
 * Shared TypeScript types — mirror backend Pydantic models.
 * No `any` allowed; all optional fields are explicitly typed.
 */

export type Confidence = "l" | "n" | "h";
export type DayNight = "D" | "N";
export type Satellite = "N" | "N20" | "N21";
export type DataSource = "synthetic" | "firms_live";
export type RiskLevel = "Low" | "Moderate" | "High" | "Extreme";
export type AlertSeverity = "Info" | "Warning" | "Critical" | "Extreme";
export type AQICategory =
  | "Good"
  | "Satisfactory"
  | "Moderate"
  | "Poor"
  | "Very Poor"
  | "Severe";

export interface RiskComponent {
  name: string;
  normalized: number;
  weight: number;
  contribution: number;
  label: string;
}

export interface NearSettlement {
  name: string;
  state: string;
  population: number;
  distance_km: number;
  bearing_deg: number;
  eta_hours: number | null;
}

export interface SpreadRing {
  hours: number;
  area_km2: number;
  geojson: GeoJSONFeature;
}

export interface SmokePlume {
  aqi_category: AQICategory;
  pm25_ug_m3: number;
  geojson: GeoJSONFeature;
}

export interface Hotspot {
  id: string;
  latitude: number;
  longitude: number;

  // VIIRS NRT
  brightness: number;
  bright_ti4: number;
  bright_ti5: number | null;
  confidence: Confidence;
  acq_date: string;
  acq_time: string;
  satellite: Satellite | null;
  instrument: string;
  frp: number | null;
  daynight: DayNight | null;
  scan: number | null;
  track: number | null;

  // Weather
  wind_speed: number | null;
  wind_direction: number | null;
  temperature_c: number | null;
  humidity_pct: number | null;
  weather_ok: boolean;
  weather_source: string;

  // Vegetation
  ndvi: number | null;

  // Metadata
  land_cover: string | null;
  state: string | null;
  region: string | null;
  source: DataSource;
  cluster_id: string | null;
  persistence_days: number | null;

  // Risk
  risk_score: number | null;
  risk_level: RiskLevel | null;
  risk_breakdown: RiskComponent[] | null;

  // Optional enrichments
  nearest_settlements: NearSettlement[] | null;
  spread_rings: SpreadRing[] | null;
  smoke_plume: SmokePlume | null;
}

export interface HotspotsResponse {
  data_source: DataSource;
  generated_at: string;
  total: number;
  hotspots: Hotspot[];
}

export interface Alert {
  id: string;
  hotspot_id: string;
  severity: AlertSeverity;
  message: string;
  settlement_name: string | null;
  distance_km: number | null;
  risk_score: number;
  acq_date: string;
}

export interface AlertsResponse {
  total: number;
  alerts: Alert[];
}

export interface DailyCount {
  date: string;
  count: number;
}

export interface RiskLevelCount {
  level: string;
  count: number;
}

export interface StateCount {
  state: string;
  count: number;
}

export interface TopHotspot {
  id: string;
  latitude: number;
  longitude: number;
  risk_score: number;
  state: string | null;
  acq_date: string;
}

export interface AnalyticsResponse {
  fires_per_day: DailyCount[];
  risk_distribution: RiskLevelCount[];
  state_counts: StateCount[];
  top_hotspots: TopHotspot[];
}

export interface SpreadResponse {
  hotspot_id: string;
  wind_speed: number;
  wind_direction: number;
  rings: SpreadRing[];
}

export interface ExposureResponse {
  hotspot_id: string;
  radius_km: number;
  total_population_at_risk: number;
  settlements: NearSettlement[];
}

// ── GeoJSON minimal types (avoids @types/geojson dep) ────────────────────────

export interface GeoJSONFeature {
  type: "Feature";
  geometry: {
    type: string;
    coordinates: number[][][] | number[][] | number[];
  };
  properties: Record<string, unknown>;
}

export interface GeoJSONFeatureCollection {
  type: "FeatureCollection";
  features: GeoJSONFeature[];
}

// ── Filter state ──────────────────────────────────────────────────────────────

export interface FilterState {
  minRisk: number;
  confidence: ("l" | "n" | "h")[];
  daynight: ("D" | "N")[];
  state: string;
  landCover: string;
  dateStart: string;
  dateEnd: string;
}
