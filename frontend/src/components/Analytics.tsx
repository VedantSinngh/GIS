"use client";

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, ScatterChart, Scatter, LineChart, Line,
  CartesianGrid, Legend,
} from "recharts";
import type { AnalyticsResponse } from "../lib/types";

interface Props {
  data: AnalyticsResponse | null;
  loading: boolean;
}

const RISK_COLORS: Record<string, string> = {
  Extreme: "#ff2200",
  High: "#ff6600",
  Moderate: "#ffaa00",
  Low: "#00fa9a",
};

const CHART_COLORS = ["#ff6600", "#ff2200", "#ffaa00", "#4da6ff", "#00fa9a", "#cc44ff"];

export default function Analytics({ data, loading }: Props) {
  if (loading) return <div className="analytics-loading">Loading analytics…</div>;
  if (!data) return null;

  return (
    <div className="analytics-panel">
      <h2 className="analytics-title">Analytics Dashboard</h2>

      {/* Fires per day line chart */}
      <div className="chart-card">
        <h3 className="chart-title">Fires per Day</h3>
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={data.fires_per_day}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10, fill: "#999" }}
              tickFormatter={(d: string) => d.slice(5)}
            />
            <YAxis tick={{ fontSize: 10, fill: "#999" }} />
            <Tooltip
              contentStyle={{ background: "#1e1e1e", border: "1px solid #444", color: "#fff" }}
            />
            <Line
              type="monotone"
              dataKey="count"
              stroke="#ff6600"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Risk level pie */}
      <div className="chart-card">
        <h3 className="chart-title">Risk Level Distribution</h3>
        <ResponsiveContainer width="100%" height={160}>
          <PieChart>
            <Pie
              data={data.risk_distribution}
              dataKey="count"
              nameKey="level"
              cx="50%"
              cy="50%"
              outerRadius={60}
              label={({ level, count }) => `${level}: ${count}`}
              labelLine={false}
            >
              {data.risk_distribution.map((entry) => (
                <Cell
                  key={entry.level}
                  fill={RISK_COLORS[entry.level] ?? "#888"}
                />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ background: "#1e1e1e", border: "1px solid #444", color: "#fff" }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* State counts bar chart */}
      <div className="chart-card">
        <h3 className="chart-title">Top States (fire count)</h3>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={data.state_counts} layout="vertical">
            <XAxis type="number" tick={{ fontSize: 9, fill: "#999" }} />
            <YAxis
              dataKey="state"
              type="category"
              width={90}
              tick={{ fontSize: 9, fill: "#ccc" }}
            />
            <Tooltip
              contentStyle={{ background: "#1e1e1e", border: "1px solid #444", color: "#fff" }}
            />
            <Bar dataKey="count" fill="#ff6600" radius={[0, 3, 3, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Top 10 riskiest */}
      <div className="chart-card">
        <h3 className="chart-title">Top 10 Riskiest Hotspots</h3>
        <div className="top-hotspots-list">
          {data.top_hotspots.map((h, i) => (
            <div key={h.id} className="top-hotspot-row">
              <span className="top-rank">#{i + 1}</span>
              <span className="top-score" style={{ color: h.risk_score >= 75 ? "#ff2200" : "#ff6600" }}>
                {h.risk_score.toFixed(0)}
              </span>
              <span className="top-meta">
                {h.state ?? "—"} · {h.acq_date}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
