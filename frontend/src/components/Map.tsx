"use client";

import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, GeoJSON, useMap } from "react-leaflet";
import L from "leaflet";
import { Hotspot, fetchRiskCone } from "../lib/api";

// Fix for default Leaflet icon in React
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

// Custom markers based on risk score
const createIcon = (color: string) => {
  return new L.Icon({
    iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${color}.png`,
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
  });
};

const iconHigh = createIcon("red");
const iconMedium = createIcon("orange");
const iconLow = createIcon("green");

export default function Map({ hotspots, selectedHotspot, setSelectedHotspot }: { hotspots: Hotspot[], selectedHotspot: Hotspot | null, setSelectedHotspot: (h: Hotspot | null) => void }) {
  const [riskCone, setRiskCone] = useState<any>(null);

  useEffect(() => {
    if (selectedHotspot) {
      fetchRiskCone(selectedHotspot)
        .then(data => setRiskCone(data))
        .catch(err => console.error(err));
    } else {
      setRiskCone(null);
    }
  }, [selectedHotspot]);

  // Default to India
  const center: [number, number] = [20.5937, 78.9629]; 
  const zoom = 5;

  return (
    <MapContainer center={center} zoom={zoom} style={{ height: "100%", width: "100%" }}>
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      />
      
      {hotspots.map(hotspot => {
        let icon = iconLow;
        if (hotspot.risk_score > 70) icon = iconHigh;
        else if (hotspot.risk_score > 40) icon = iconMedium;

        return (
          <Marker 
            key={hotspot.id} 
            position={[hotspot.latitude, hotspot.longitude]} 
            icon={icon}
            eventHandlers={{
              click: () => setSelectedHotspot(hotspot),
            }}
          >
            <Popup className="custom-popup">
              <div>
                <strong>Risk Score: {hotspot.risk_score}</strong>
                <br/>
                Detected: {hotspot.acq_date} {hotspot.acq_time}
              </div>
            </Popup>
          </Marker>
        );
      })}

      {riskCone && (
        <GeoJSON 
          key={selectedHotspot?.id} 
          data={riskCone} 
          style={{ color: "#ff4500", weight: 2, opacity: 0.8, fillColor: "#ff4500", fillOpacity: 0.3 }} 
        />
      )}
    </MapContainer>
  );
}
