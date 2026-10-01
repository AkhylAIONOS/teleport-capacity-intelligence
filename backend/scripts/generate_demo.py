"""Reproducible simulated USD costs; never real Teleport rates."""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

rng = random.Random(42)
DATA = Path(__file__).resolve().parents[1] / "data"
DATA.mkdir(exist_ok=True)
carriers = [
    "MASkargo",
    "Emirates SkyCargo",
    "Turkish Cargo",
    "Partner Air A",
    "Partner Air B",
    "Own Freighter 1",
    "Own Freighter 2",
    "Own Freighter 3",
]
lanes = [
    ("KUL", d) for d in ["DEL", "BOM", "SIN", "BKK", "MNL", "CGK", "MAA", "BLR"]
] + [("BOM", "SIN"), ("DEL", "BKK"), ("SIN", "CGK"), ("BKK", "MNL")]
shipments, options = [], []
for i in range(2000):
    sid = f"TP-{88000+i}"
    origin, destination = rng.choice(lanes)
    dt = date(2026, 1, 1) + timedelta(days=rng.randrange(181))
    weight = round(rng.uniform(150, 4800), 2)
    # Candidates share the same shipment market baseline. Historical choices
    # are often optimal or close to feasible alternatives, rather than drawing
    # unrelated prices for each airline. This calibration is demo generation only.
    market_base = (
        weight * rng.uniform(1.5, 3.2) * (1.18 if destination in ["DEL", "BOM"] else 1)
    )
    market_fuel = market_base * rng.uniform(0.14, 0.22)
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
    for j, carrier in enumerate(rng.sample(carriers, rng.randrange(4, 9))):
        rate = (
            "Owned" if carrier.startswith("Own") else rng.choice(["Contract", "Spot"])
        )
        multiplier = (
            1.0 if j == 0 else 1 - discount + (0 if j == 1 else rng.uniform(0.01, 0.12))
        )
        base = round(market_base * multiplier, 2)
        fuel = round(market_fuel * multiplier, 2)
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
            fuel_surcharge=fuel,
            other_cost=other,
            total_landed_cost=round(base + fuel + other, 2),
            available=available,
            sla_feasible=sla,
        )
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
fuel = [
    dict(
        date=(date(2026, 1, 1) + timedelta(days=i)).isoformat(),
        fuel_index=round(100 + 10 * rng.random(), 2),
        fuel_price_usd=round(0.8 + 0.2 * rng.random(), 3),
    )
    for i in range(181)
]
for name, rows in [
    ("shipments", shipments),
    ("carrier_options", options),
    ("fuel_index", fuel),
]:
    with (DATA / f"{name}.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
print(
    f"Generated DEMO data: {len(shipments)} shipments, {len(options)} options, {len(fuel)} fuel rows"
)
