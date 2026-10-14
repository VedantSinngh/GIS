"use client";

import type { DataSource } from "../lib/types";

interface Props {
  source: DataSource | null;
}

/**
 * Visible badge displayed whenever synthetic data is active.
 * GOLDEN RULE: never hide this banner when source === "synthetic".
 */
export default function SourceBadge({ source }: Props) {
  if (!source) return null;

  if (source === "synthetic") {
    return (
      <div className="source-badge source-badge--synthetic">
        <span className="source-badge__icon">⚠</span>
        SIMULATED DATA
        <span className="source-badge__sub">
          Algorithms real · Hotspots synthetic
        </span>
      </div>
    );
  }

  return (
    <div className="source-badge source-badge--live">
      <span className="source-badge__icon">●</span>
      LIVE · NASA FIRMS
    </div>
  );
}
