"""
Synthetic settlements: ~200 villages / towns near India fire-prone regions.
Used for exposure analysis (population within 10/25 km of a hotspot).
All records are synthetic, NOT from a real gazetteer.
source: "synthetic"
"""

import json
import math
import random
from pathlib import Path


_SETTLEMENT_SEEDS = [
    # Uttarakhand / Himachal
    {"name": "Lansdowne",      "lat": 29.84, "lon": 78.69, "population": 9200,  "state": "Uttarakhand"},
    {"name": "Nainital",       "lat": 29.39, "lon": 79.46, "population": 41000, "state": "Uttarakhand"},
    {"name": "Haridwar",       "lat": 29.96, "lon": 78.16, "population": 228000,"state": "Uttarakhand"},
    {"name": "Shimla",         "lat": 31.10, "lon": 77.17, "population": 169000,"state": "Himachal Pradesh"},
    {"name": "Mandi",          "lat": 31.71, "lon": 76.93, "population": 26000, "state": "Himachal Pradesh"},
    {"name": "Almora",         "lat": 29.60, "lon": 79.66, "population": 35000, "state": "Uttarakhand"},
    {"name": "Pauri",          "lat": 30.15, "lon": 78.78, "population": 19000, "state": "Uttarakhand"},
    {"name": "Tehri",          "lat": 30.38, "lon": 78.48, "population": 11000, "state": "Uttarakhand"},
    {"name": "Mussoorie",      "lat": 30.46, "lon": 78.07, "population": 30000, "state": "Uttarakhand"},
    {"name": "Pithoragarh",    "lat": 29.58, "lon": 80.21, "population": 55000, "state": "Uttarakhand"},
    # Odisha / Chhattisgarh
    {"name": "Sambalpur",      "lat": 21.47, "lon": 83.97, "population": 183000,"state": "Odisha"},
    {"name": "Raigarh",        "lat": 21.90, "lon": 83.40, "population": 167000,"state": "Chhattisgarh"},
    {"name": "Baripada",       "lat": 21.93, "lon": 86.74, "population": 103000,"state": "Odisha"},
    {"name": "Sundargarh",     "lat": 22.12, "lon": 84.03, "population": 55000, "state": "Odisha"},
    {"name": "Kendujhar",      "lat": 21.63, "lon": 85.58, "population": 67000, "state": "Odisha"},
    {"name": "Jagdalpur",      "lat": 19.07, "lon": 82.03, "population": 100000,"state": "Chhattisgarh"},
    {"name": "Ambikapur",      "lat": 23.12, "lon": 83.20, "population": 140000,"state": "Chhattisgarh"},
    {"name": "Bhubaneswar",    "lat": 20.30, "lon": 85.84, "population": 840000,"state": "Odisha"},
    {"name": "Rourkela",       "lat": 22.23, "lon": 84.86, "population": 535000,"state": "Odisha"},
    {"name": "Phulbani",       "lat": 20.47, "lon": 84.23, "population": 31000, "state": "Odisha"},
    # Madhya Pradesh / Maharashtra
    {"name": "Jabalpur",       "lat": 23.18, "lon": 79.95, "population": 1268000,"state": "Madhya Pradesh"},
    {"name": "Betul",          "lat": 21.91, "lon": 77.90, "population": 80000, "state": "Madhya Pradesh"},
    {"name": "Seoni",          "lat": 22.09, "lon": 79.54, "population": 53000, "state": "Madhya Pradesh"},
    {"name": "Chhindwara",     "lat": 22.06, "lon": 78.94, "population": 130000,"state": "Madhya Pradesh"},
    {"name": "Mandla",         "lat": 22.60, "lon": 80.38, "population": 32000, "state": "Madhya Pradesh"},
    {"name": "Amravati",       "lat": 20.93, "lon": 77.75, "population": 647000,"state": "Maharashtra"},
    {"name": "Yavatmal",       "lat": 20.39, "lon": 78.12, "population": 146000,"state": "Maharashtra"},
    {"name": "Gondia",         "lat": 21.46, "lon": 80.20, "population": 115000,"state": "Maharashtra"},
    {"name": "Chandrapur",     "lat": 19.96, "lon": 79.30, "population": 320000,"state": "Maharashtra"},
    {"name": "Bhandara",       "lat": 21.17, "lon": 79.65, "population": 90000, "state": "Maharashtra"},
    # Western Ghats
    {"name": "Palakkad",       "lat": 10.78, "lon": 76.65, "population": 131000,"state": "Kerala"},
    {"name": "Thrissur",       "lat": 10.52, "lon": 76.21, "population": 316000,"state": "Kerala"},
    {"name": "Idukki",         "lat":  9.91, "lon": 77.10, "population": 8000,  "state": "Kerala"},
    {"name": "Munnar",         "lat":  10.09,"lon": 77.06, "population": 40000, "state": "Kerala"},
    {"name": "Kalpetta",       "lat": 11.61, "lon": 76.08, "population": 29000, "state": "Kerala"},
    {"name": "Coorg",          "lat": 12.42, "lon": 75.74, "population": 14000, "state": "Karnataka"},
    {"name": "Shimoga",        "lat": 13.93, "lon": 75.57, "population": 323000,"state": "Karnataka"},
    {"name": "Chikkamagaluru", "lat": 13.32, "lon": 75.77, "population": 118000,"state": "Karnataka"},
    {"name": "Dharwad",        "lat": 15.46, "lon": 75.01, "population": 431000,"state": "Karnataka"},
    {"name": "Hassan",         "lat": 13.00, "lon": 76.10, "population": 136000,"state": "Karnataka"},
    # Northeast
    {"name": "Dibrugarh",      "lat": 27.48, "lon": 94.91, "population": 139000,"state": "Assam"},
    {"name": "Sibsagar",       "lat": 26.99, "lon": 94.64, "population": 80000, "state": "Assam"},
    {"name": "Jorhat",         "lat": 26.75, "lon": 94.21, "population": 68000, "state": "Assam"},
    {"name": "Tezpur",         "lat": 26.63, "lon": 92.80, "population": 93000, "state": "Assam"},
    {"name": "Silchar",        "lat": 24.83, "lon": 92.80, "population": 228000,"state": "Assam"},
    {"name": "Imphal",         "lat": 24.82, "lon": 93.95, "population": 268000,"state": "Manipur"},
    {"name": "Aizawl",         "lat": 23.73, "lon": 92.72, "population": 293000,"state": "Mizoram"},
    {"name": "Kohima",         "lat": 25.67, "lon": 94.11, "population": 100000,"state": "Nagaland"},
    {"name": "Itanagar",       "lat": 27.08, "lon": 93.62, "population": 44000, "state": "Arunachal Pradesh"},
    {"name": "Shillong",       "lat": 25.57, "lon": 91.88, "population": 143000,"state": "Meghalaya"},
    # Punjab / Haryana
    {"name": "Ludhiana",       "lat": 30.90, "lon": 75.85, "population": 1618000,"state": "Punjab"},
    {"name": "Amritsar",       "lat": 31.63, "lon": 74.87, "population": 1132000,"state": "Punjab"},
    {"name": "Patiala",        "lat": 30.34, "lon": 76.40, "population": 447000,"state": "Punjab"},
    {"name": "Bathinda",       "lat": 30.21, "lon": 74.95, "population": 285000,"state": "Punjab"},
    {"name": "Hisar",          "lat": 29.15, "lon": 75.72, "population": 301000,"state": "Haryana"},
    {"name": "Sirsa",          "lat": 29.53, "lon": 75.03, "population": 180000,"state": "Haryana"},
    {"name": "Fatehabad",      "lat": 29.52, "lon": 75.46, "population": 95000, "state": "Haryana"},
    {"name": "Karnal",         "lat": 29.69, "lon": 76.99, "population": 287000,"state": "Haryana"},
    {"name": "Sangrur",        "lat": 30.24, "lon": 75.83, "population": 174000,"state": "Punjab"},
    {"name": "Fazilka",        "lat": 30.40, "lon": 74.03, "population": 62000, "state": "Punjab"},
]


def _build_settlements(seed: int = 7) -> list[dict]:
    """
    Expand _SETTLEMENT_SEEDS with additional synthetic villages generated
    near each seed town, totalling ~200 records.
    """
    rnd = random.Random(seed)
    settlements = list(_SETTLEMENT_SEEDS)

    target = 200
    while len(settlements) < target:
        base = rnd.choice(_SETTLEMENT_SEEDS)
        lat_offset = rnd.uniform(-0.6, 0.6)
        lon_offset = rnd.uniform(-0.6, 0.6)
        pop = int(rnd.lognormvariate(math.log(5000), 1.0))
        settlements.append({
            "name": f"Village_{len(settlements):03d}",
            "lat": round(base["lat"] + lat_offset, 4),
            "lon": round(base["lon"] + lon_offset, 4),
            "population": pop,
            "state": base["state"],
        })

    return settlements


def write_settlements(path: str = "backend/synthetic/settlements.json", seed: int = 7) -> None:
    data = _build_settlements(seed)
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


_SETTLEMENTS: list[dict] | None = None


def load_settlements() -> list[dict]:
    global _SETTLEMENTS
    if _SETTLEMENTS is None:
        json_path = Path(__file__).parent / "settlements.json"
        if json_path.exists():
            _SETTLEMENTS = json.loads(json_path.read_text(encoding="utf-8"))
        else:
            _SETTLEMENTS = _build_settlements()
    return _SETTLEMENTS


if __name__ == "__main__":
    write_settlements()
    data = load_settlements()
    print(f"Generated {len(data)} settlements")
