"use client";

import { useEffect, useState, useMemo } from "react";
import dynamic from 'next/dynamic';
import { Hotspot, fetchHotspots } from "../lib/api";

// Map must be dynamically imported to avoid SSR issues with Leaflet
const Map = dynamic(() => import("../components/Map"), { ssr: false });

export default function Home() {
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [filteredHotspots, setFilteredHotspots] = useState<Hotspot[]>([]);
  const [selectedHotspot, setSelectedHotspot] = useState<Hotspot | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [riskThreshold, setRiskThreshold] = useState<number>(0);

  // Default bounding box for India (or specific state)
  const defaultBbox = "68.1,6.7,97.4,35.5"; // Approximate India bbox

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchHotspots(defaultBbox);
      setHotspots(data);
    } catch (err: any) {
      setError(err.message || "Failed to load hotspot data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // Auto refresh every 15 minutes
    const interval = setInterval(loadData, 15 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    setFilteredHotspots(hotspots.filter(h => h.risk_score >= riskThreshold));
  }, [hotspots, riskThreshold]);

  return (
    <div className="app-container">
      <div className="sidebar">
        <h1>Wildfire Risk Monitor</h1>
        
        <div className="filter-section">
          <label>
            <span>Min Risk Threshold: {riskThreshold}</span>
          </label>
          <input 
            type="range" 
            min="0" 
            max="100" 
            value={riskThreshold} 
            onChange={(e) => setRiskThreshold(parseInt(e.target.value))} 
          />
        </div>

        {error && <div className="error-message">{error}</div>}

        <div className="info-panel">
          {selectedHotspot ? (
            <>
              <h2>Selected Hotspot</h2>
              <div className="stat-row">
                <span className="stat-label">Risk Score</span>
                <span className={`stat-value ${selectedHotspot.risk_score > 70 ? 'risk-high' : selectedHotspot.risk_score > 40 ? 'risk-medium' : 'risk-low'}`}>
                  {selectedHotspot.risk_score} / 100
                </span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Coordinates</span>
                <span className="stat-value">{selectedHotspot.latitude.toFixed(4)}, {selectedHotspot.longitude.toFixed(4)}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Brightness</span>
                <span className="stat-value">{selectedHotspot.brightness}K</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Confidence</span>
                <span className="stat-value">{selectedHotspot.confidence}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Wind</span>
                <span className="stat-value">{selectedHotspot.wind_speed} km/h @ {selectedHotspot.wind_direction}°</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">NDVI (Dryness proxy)</span>
                <span className="stat-value">{selectedHotspot.ndvi !== null ? selectedHotspot.ndvi.toFixed(2) : 'N/A'}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Detected At</span>
                <span className="stat-value">{selectedHotspot.acq_date} {selectedHotspot.acq_time}</span>
              </div>
            </>
          ) : (
            <p style={{ color: '#aaa', textAlign: 'center', marginTop: '20px' }}>
              Select a hotspot on the map to view details.
            </p>
          )}
        </div>
      </div>
      
      <div className="map-container">
        {loading && <div className="loading-overlay">Loading data...</div>}
        <Map 
          hotspots={filteredHotspots} 
          selectedHotspot={selectedHotspot} 
          setSelectedHotspot={setSelectedHotspot} 
        />
      </div>
    </div>
  );
}
