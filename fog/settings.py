import os
from pathlib import Path


# Project directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


# Fog identity
FOG_ID = os.getenv("FOG_ID", "fog-a")
FOG_ZONE = os.getenv("FOG_ZONE", "university")


# Each Fog has its own database
DEFAULT_DB_NAME = FOG_ID.replace("-", "_") + ".db"

DB_PATH = Path(
    os.getenv(
        "FOG_DB_PATH",
        str(DATA_DIR / DEFAULT_DB_NAME)
    )
)


# Station identifier prefix
STATION_PREFIX = FOG_ID.split("-")[-1].upper()