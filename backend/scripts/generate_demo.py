"""Reproducible simulated USD costs; never real Teleport rates."""

import csv
import random
import json
import argparse
import sys
import math
import hashlib
from datetime import date, timedelta
from pathlib import Path

DEMO_RANDOM_SEED = 20261002
rng = random.Random(DEMO_RANDOM_SEED)
DATA = Path(__file__).resolve().parents[1] / "data"
parser = argparse.ArgumentParser()
parser.add_argument("--output-dir", type=Path, default=DATA)
parser.add_argument("--generated-at", help="Optional fixed ISO timestamp for reproducibility checks")
args = parser.parse_args()
SOURCE_DATA = DATA
DATA = args.output_dir
DATA.mkdir(parents=True, exist_ok=True)
snapshots = {p.stem: json.loads(p.read_text()) for p in (SOURCE_DATA / "sources").glob("*.json")}
network = snapshots["teleport_network"]["facts_used"]
benchmark = snapshots["iata_fuel_2026"]["facts_used"]["jet_fuel_average_usd_per_barrel"]
threshold = snapshots["teleport_fsc_reference"]["facts_used"]["benchmark_usd_per_barrel"]
# Weekly synthetic benchmark variation, deliberately not observed IATA prices.
weekly = [round(benchmark + 9 * math.sin(w / 3) + rng.uniform(-4, 4), 2) for w in range(26)]
fuel = [dict(date=(date(2026, 1, 1) + timedelta(days=i)).isoformat(),
             fuel_index=weekly[i // 7], fuel_price_usd=round(weekly[i // 7] / 158.987, 3)) for i in range(181)]
fuel_by_date = {r["date"]: r["fuel_index"] for r in fuel}
lane_metadata = json.loads((SOURCE_DATA / "provenance/lane_provenance.json").read_text())
with (SOURCE_DATA / "sources/airports_reference.csv").open() as f:
    airports = {r["iata_code"]: r for r in csv.DictReader(f)}
carriers = [
    "MASkargo",
    "Emirates SkyCargo",
    "Turkish Cargo",
    "Myanmar Airways International",
    "Synthetic Partner 01",
    "Synthetic Partner 02",
] + [f"Own Freighter {i+1}" for i in range(network["owned_freighters"])]
lanes = [tuple(lane.split("-")) for lane in lane_metadata]
assert all(o in airports and d in airports for o, d in lanes)
shipments, options, cost_inputs = [], [], []
for i in range(2000):
    sid = f"TP-{88000+i}"
    origin, destination = rng.choice(lanes)
    if i == 213:
        origin, destination = "KUL", "BOM"  # TP-88213 deterministic audit fixture
    dt = date(2026, 1, 1) + timedelta(days=rng.randrange(181))
    weight = round(rng.uniform(150, 4800), 2)
    # Candidates share the same shipment market baseline. Historical choices
    # are often optimal or close to feasible alternatives, rather than drawing
    # unrelated prices for each airline. This calibration is demo generation only.
    market_base = (
        weight * rng.uniform(1.5, 3.2) * (1.18 if destination in ["DEL", "BOM"] else 1)
    )
    lane_factor = 1.18 if destination in ["DEL", "BOM", "MAA", "BLR"] else (1.35 if destination in ["SYD", "ICN", "HND"] else 1.0)
    market_fuel = weight * max(fuel_by_date[dt.isoformat()] - threshold, 0) * 0.006 * lane_factor
    market_other = rng.uniform(35, 220)
    opportunity = rng.random()
    if opportunity < 0.25:
        discount = 0.0
    elif opportunity < 0.65:
        discount = rng.uniform(0.025, 0.08)
    elif opportunity < 0.9:
        discount = rng.uniform(0.09, 0.14)
    else:
        discount = rng.uniform(0.16, 0.25)
    candidates = []
    for j, carrier in enumerate(rng.sample(carriers, rng.randrange(4, len(carriers) + 1))):
        rate = (
            "Owned" if carrier.startswith("Own") else rng.choice(["Contract", "Spot"])
        )
        multiplier = (
            1.0 if j == 0 else 1 - discount + (0 if j == 1 else rng.uniform(0.01, 0.12))
        )
        base = round(market_base * multiplier, 2)
        fuel_cost = round(market_fuel * multiplier, 2)
        other = round(market_other * multiplier, 2)
        departure = (dt + timedelta(days=rng.randrange(1, 5))).isoformat()
        # first option guarantees an internally consistent historical choice;
        # some shipments deliberately have no feasible candidate.
        available = j <= 1 or rng.random() > 0.12
        sla = j <= 1 or rng.random() > 0.14
        capacity = round(
            (
                weight * rng.uniform(1.02, 2.0)
                if j <= 1 or rng.random() > 0.15
                else weight * 0.7
            ),
            2,
        )
        if i % 53 == 0:
            available = False
        row = dict(
            option_id=f"{sid}-O{j+1}",
            shipment_id=sid,
            carrier=carrier,
            mode="Freighter" if rate == "Owned" else "Partner",
            departure_date=departure,
            rate_type=rate,
            capacity_available_kg=capacity,
            required_capacity_kg=weight,
            base_cost=base,
            fuel_surcharge=fuel_cost,
            other_cost=other,
            total_landed_cost=round(base + fuel_cost + other, 2),
            available=available,
            sla_feasible=sla,
        )
        cost_inputs.append(dict(option_id=row["option_id"], shipment_id=sid, weight_kg=weight,
            weekly_fuel_index=fuel_by_date[dt.isoformat()], benchmark_usd_per_barrel=threshold,
            synthetic_fuel_coefficient=0.006, synthetic_lane_factor=lane_factor,
            synthetic_candidate_multiplier=multiplier, synthetic_market_base=market_base,
            synthetic_market_other=market_other))
        candidates.append(row)
    actual = candidates[0]
    shipments.append(
        dict(
            shipment_id=sid,
            shipment_date=dt.isoformat(),
            origin=origin,
            destination=destination,
            weight_kg=weight,
            volume_cbm=round(weight / rng.uniform(130, 220), 2),
            actual_carrier=actual["carrier"],
            actual_rate_type=actual["rate_type"],
            actual_departure_date=actual["departure_date"],
            actual_base_cost=actual["base_cost"],
            actual_fuel_surcharge=actual["fuel_surcharge"],
            actual_other_cost=actual["other_cost"],
            actual_paid=actual["total_landed_cost"],
        )
    )
    options.extend(candidates)
for name, rows in [
    ("shipments", shipments),
    ("carrier_options", options),
    ("fuel_index", fuel),
]:
    with (DATA / f"{name}.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
print(
    f"Generated DEMO data: {len(shipments)} shipments, {len(options)} options, {len(fuel)} fuel rows"
)

# Run the unchanged application optimizer, rather than duplicating its rules.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.data_loader import DataLoader
from app.services.analytics_service import AnalyticsService
from datetime import datetime, timezone
summary = AnalyticsService(DataLoader(DATA)).get_overall_summary()
manifest = dict(dataset_name="PUBLIC-SOURCE-CALIBRATED SYNTHETIC DATA", dataset_version="2.0",
    generated_at=args.generated_at or datetime.now(timezone.utc).isoformat(), random_seed=DEMO_RANDOM_SEED,
    demo_period={"start": "2026-01-01", "end": "2026-06-30"}, shipment_count=len(shipments),
    candidate_option_count=len(options), source_ids=[e["source_id"] for e in json.loads((SOURCE_DATA / "provenance/source_registry.json").read_text())],
    generator_version="2.0", summary={k: summary[k] for k in ["actual_spend", "optimized_spend", "potential_saving", "saving_percent"]},
    note="These values are derived from public-source-calibrated synthetic records and are not actual Teleport historical financial results.",
    calibration={"fuel_coefficient": 0.006, "lane_factors": {"South Asia": 1.18, "SYD/ICN/HND": 1.35, "other": 1.0}, "discount_distribution": "25% zero; 40% 2.5–8%; 25% 9–14%; 10% 16–25%", "fuel_series": "weekly USD/barrel around IATA full-year forecast; no observed daily data"},
    carriers={c: {"classification": "PUBLIC_NETWORK_NAME_SYNTHETIC_OPTIONS" if c in snapshots["teleport_1h_2026"]["facts_used"]["partner_names"] else "SYNTHETIC_DEMO_CARRIER", "source_ids": ["teleport_1h_2026"] if c in snapshots["teleport_1h_2026"]["facts_used"]["partner_names"] else ["teleport_network_2026"] if c.startswith("Own Freighter") else [], "fleet_type": network["fleet_type"] if c.startswith("Own Freighter") else None, "note": "Named representative synthetic aircraft" if c.startswith("Own Freighter") else "Emirates retained for tested comparisons; no Teleport relationship claimed" if c == "Emirates SkyCargo" else "All quotes and assignments are synthetic"} for c in carriers})
provenance = DATA / "provenance"
provenance.mkdir(exist_ok=True)
with (provenance / "cost_inputs.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(cost_inputs[0]), lineterminator="\n"); writer.writeheader(); writer.writerows(cost_inputs)
manifest["source_snapshot_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((SOURCE_DATA / "sources").iterdir()) if p.is_file()}
manifest["dataset_sha256"] = {name: hashlib.sha256((DATA / name).read_bytes()).hexdigest() for name in ["shipments.csv", "carrier_options.csv", "fuel_index.csv", "provenance/cost_inputs.csv"]}
(provenance / "demo_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(manifest["summary"], indent=2))
