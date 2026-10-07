import os
from dotenv import load_dotenv

load_dotenv()

FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY", "DEMO_KEY")

# Default bounding box for Uttarakhand, India
# Format: W,S,E,N
DEFAULT_BBOX = "77.5,28.7,81.0,31.5"
