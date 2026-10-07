const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Hotspot {
  id: string;
  latitude: number;
  longitude: number;
  brightness: number;
  confidence: string;
  acq_date: string;
  acq_time: string;
  wind_speed: number;
  wind_direction: number;
  ndvi: number | null;
  risk_score: number;
}

export const fetchHotspots = async (bbox: string): Promise<Hotspot[]> => {
  const res = await fetch(`${API_BASE_URL}/hotspots?bbox=${bbox}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to fetch hotspots");
  }
  return res.json();
};

export const fetchRiskCone = async (hotspot: Hotspot): Promise<any> => {
  const params = new URLSearchParams({
    lat: hotspot.latitude.toString(),
    lon: hotspot.longitude.toString(),
    wind_speed: hotspot.wind_speed.toString(),
    wind_direction: hotspot.wind_direction.toString(),
  });
  const res = await fetch(`${API_BASE_URL}/risk-cone/${hotspot.id}?${params.toString()}`);
  if (!res.ok) {
    throw new Error("Failed to fetch risk cone");
  }
  return res.json();
};
