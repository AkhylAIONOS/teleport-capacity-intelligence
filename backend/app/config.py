import json
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
if not DATA_DIR.is_absolute():
    DATA_DIR = BASE_DIR / DATA_DIR
DATA_MODE = os.getenv("DATA_MODE", "demo")
AI_PROVIDER = os.getenv("AI_PROVIDER", "mock")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")
SHIPMENT_COLUMNS = "shipment_id shipment_date origin destination weight_kg volume_cbm actual_carrier actual_rate_type actual_departure_date actual_base_cost actual_fuel_surcharge actual_other_cost actual_paid".split()
OPTION_COLUMNS = "option_id shipment_id carrier mode departure_date rate_type capacity_available_kg required_capacity_kg base_cost fuel_surcharge other_cost total_landed_cost available sla_feasible".split()
FUEL_COLUMNS = "date fuel_index fuel_price_usd".split()
COLUMN_MAP = {
    name: {c: c for c in cols}
    for name, cols in [
        ("shipments", SHIPMENT_COLUMNS),
        ("carrier_options", OPTION_COLUMNS),
        ("fuel_index", FUEL_COLUMNS),
    ]
}
map_file = os.getenv("COLUMN_MAP_FILE")
if map_file:
    map_path = Path(map_file)
    if not map_path.is_absolute():
        map_path = BASE_DIR / map_path
    for dataset, mapping in json.loads(map_path.read_text()).items():
        COLUMN_MAP[dataset].update(mapping)
