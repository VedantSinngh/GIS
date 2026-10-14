"use client";

interface Props {
  days: string[];            // sorted ISO date strings
  currentIndex: number;
  playing: boolean;
  speed: number;             // 1 | 2 | 4
  onChange: (index: number) => void;
  onPlayPause: () => void;
  onSpeedChange: (s: number) => void;
}

export default function TimeSlider({
  days,
  currentIndex,
  playing,
  speed,
  onChange,
  onPlayPause,
  onSpeedChange,
}: Props) {
  if (days.length === 0) return null;

  return (
    <div className="time-slider">
      <button
        id="time-play-btn"
        className="time-slider__play-btn"
        onClick={onPlayPause}
        aria-label={playing ? "Pause" : "Play"}
      >
        {playing ? "⏸" : "▶"}
      </button>

      <div className="time-slider__track-wrap">
        <input
          id="time-range"
          type="range"
          min={0}
          max={days.length - 1}
          value={currentIndex}
          onChange={(e) => onChange(+e.target.value)}
          className="time-slider__range"
        />
        <div className="time-slider__label">{days[currentIndex]}</div>
      </div>

      <div className="time-slider__speed">
        {([1, 2, 4] as const).map((s) => (
          <button
            key={s}
            className={`time-slider__speed-btn ${speed === s ? "active" : ""}`}
            onClick={() => onSpeedChange(s)}
          >
            {s}×
          </button>
        ))}
      </div>
    </div>
  );
}
