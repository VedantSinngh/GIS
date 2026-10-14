"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  GeoJSON,
  useMap,
  LayersControl,
} from "react-leaflet";
import L from "leaflet";
import type { Hotspot, SpreadRing, GeoJSONFeature } from "../lib/types";
import { fetchSpread } from "../lib/api";

// Fix default icon
delete (L.Icon.Default.prototype as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

// ── Custom circle icons by risk level ─────────────────────────────────────────
function makeCircleIcon(color: string, size: number = 14) {
  return L.divIcon({
    className: "",
    html: `<div style="
      width:${size}px;height:${size}px;
      background:${color};
      border-radius:50%;
      border:2px solid rgba(255,255,255,0.7);
      box-shadow:0 0 6px ${color}88;
    "></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

const iconExtreme = makeCircleIcon("#ff2200", 18);
const iconHigh    = makeCircleIcon("#ff6600", 14);
const iconMed     = makeCircleIcon("#ffaa00", 12);
const iconLow     = makeCircleIcon("#00fa9a", 10);

function riskIcon(score: number | null) {
  if ((score ?? 0) >= 75) return iconExtreme;
  if ((score ?? 0) >= 50) return iconHigh;
  if ((score ?? 0) >= 25) return iconMed;
  return iconLow;
}

// ── Tile configs ──────────────────────────────────────────────────────────────
const TILES = {
  dark: {
    url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attribution: "© CartoDB",
  },
  satellite: {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: "© Esri",
  },
  terrain: {
    url: "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    attribution: "© OpenTopoMap",
  },
};

// ── Spread ring colours ───────────────────────────────────────────────────────
const RING_COLORS = ["#ff990055", "#ff660055", "#ff330055", "#ff000044"];

// ── AQI overlay colour ────────────────────────────────────────────────────────
const AQI_COLORS: Record<string, string> = {
  Good: "#00e40088",
  Satisfactory: "#90e40088",
  Moderate: "#f7d40088",
  Poor: "#ff7e0088",
  "Very Poor": "#ff000088",
  Severe: "#94000d88",
};

// ── Sub-component: auto-fit map bounds when hotspots change ──────────────────
function BoundsFitter({ hotspots }: { hotspots: Hotspot[] }) {
  const map = useMap();
  useEffect(() => {
    if (hotspots.length === 0) return;
    const bounds = L.latLngBounds(
      hotspots.map((h) => [h.latitude, h.longitude] as [number, number])
    );
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 8 });
    }
  }, [hotspots, map]);
  return null;
}

// ── Main Map component ────────────────────────────────────────────────────────

interface Props {
  hotspots: Hotspot[];
  selectedHotspot: Hotspot | null;
  setSelectedHotspot: (h: Hotspot | null) => void;
  basemap?: "dark" | "satellite" | "terrain";
}

export default function Map({
  hotspots,
  selectedHotspot,
  setSelectedHotspot,
  basemap = "dark",
}: Props) {
  const [spreadRings, setSpreadRings] = useState<SpreadRing[]>([]);
  const [loadingSpread, setLoadingSpread] = useState(false);
  const tileRef = useRef(basemap);
  tileRef.current = basemap;

  const tile = TILES[basemap];

  // Fetch spread ellipses for selected hotspot
  useEffect(() => {
    if (!selectedHotspot) {
      setSpreadRings([]);
      return;
    }
    if (
      selectedHotspot.wind_speed === null ||
      selectedHotspot.wind_direction === null
    )
      return;

    setLoadingSpread(true);
    fetchSpread(
      selectedHotspot.id,
      selectedHotspot.latitude,
      selectedHotspot.longitude,
      selectedHotspot.wind_speed,
      selectedHotspot.wind_direction,
      "1,3,6,12"
    )
      .then((res) => setSpreadRings(res.rings))
      .catch(() => setSpreadRings([]))
      .finally(() => setLoadingSpread(false));
  }, [selectedHotspot]);

  const handleMarkerClick = useCallback(
    (h: Hotspot) => setSelectedHotspot(h),
    [setSelectedHotspot]
  );

  return (
    <MapContainer
      center={[20.5937, 78.9629]}
      zoom={5}
      style={{ height: "100%", width: "100%" }}
      zoomControl={true}
    >
      {/* Base tile layer */}
      <TileLayer url={tile.url} attribution={tile.attribution} />

      {/* Auto-fit bounds */}
      <BoundsFitter hotspots={hotspots} />

      {/* Hotspot markers */}
      {hotspots.map((h) => (
        <Marker
          key={h.id}
          position={[h.latitude, h.longitude]}
          icon={riskIcon(h.risk_score)}
          eventHandlers={{ click: () => handleMarkerClick(h) }}
        >
          <Popup className="custom-popup">
            <div className="popup-content">
              <strong>
                {h.risk_level ?? "—"} · {h.risk_score?.toFixed(0) ?? "?"}/100
              </strong>
              <br />
              {h.state ?? "India"} · {h.acq_date}
              <br />
              {h.bright_ti4.toFixed(0)} K ·{" "}
              {h.frp ? `${h.frp.toFixed(1)} MW FRP` : ""}
              <br />
              {h.source === "synthetic" ? "🔬 Simulated" : "📡 FIRMS Live"}
            </div>
          </Popup>
        </Marker>
      ))}

      {/* Spread ellipse rings for selected hotspot */}
      {selectedHotspot &&
        spreadRings.map((ring, i) => (
          <GeoJSON
            key={`${selectedHotspot.id}-ring-${ring.hours}`}
            data={ring.geojson as Parameters<typeof GeoJSON>[0]["data"]}
            style={{
              color: "#ff6600",
              weight: 1.5,
              opacity: 0.9,
              fillColor: RING_COLORS[i] ?? "#ff000033",
              fillOpacity: 0.18,
              dashArray: "4 4",
            }}
          />
        ))}

      {/* Smoke plume for selected hotspot */}
      {selectedHotspot?.smoke_plume && (
        <GeoJSON
          key={`plume-${selectedHotspot.id}`}
          data={
            selectedHotspot.smoke_plume
              .geojson as Parameters<typeof GeoJSON>[0]["data"]
          }
          style={{
            color: "#8888ff",
            weight: 1,
            opacity: 0.6,
            fillColor:
              AQI_COLORS[selectedHotspot.smoke_plume.aqi_category] ??
              "#88888855",
            fillOpacity: 0.35,
          }}
        />
      )}
    </MapContainer>
  );
}
