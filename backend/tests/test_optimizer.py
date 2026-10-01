import pandas as pd
import pytest
from app.services.optimizer import optimize_shipment


def sample():
    shipment = pd.Series(
        dict(
            shipment_id="T1",
            actual_paid=100,
            actual_carrier="Historical",
            actual_rate_type="Contract",
            actual_departure_date=pd.Timestamp("2026-01-02"),
            shipment_date=pd.Timestamp("2026-01-01"),
            weight_kg=100,
        )
    )
    options = pd.DataFrame(
        [
            dict(
                option_id="A",
                carrier="Alpha",
                rate_type="Spot",
                departure_date=pd.Timestamp("2026-01-02"),
                total_landed_cost=70,
                available=True,
                sla_feasible=True,
                capacity_available_kg=120,
                required_capacity_kg=100,
            ),
            dict(
                option_id="B",
                carrier="Beta",
                rate_type="Contract",
                departure_date=pd.Timestamp("2026-01-03"),
                total_landed_cost=80,
                available=True,
                sla_feasible=True,
                capacity_available_kg=120,
                required_capacity_kg=100,
            ),
        ]
    )
    return shipment, options


def test_cheapest_feasible():
    s, o = sample()
    r = optimize_shipment(s, o)
    assert r["recommended_carrier"] == "Alpha"
    assert r["potential_saving"] == 30


@pytest.mark.parametrize(
    "column,value",
    [
        ("available", False),
        ("sla_feasible", False),
        ("capacity_available_kg", 50),
        ("total_landed_cost", float("nan")),
        ("total_landed_cost", -1),
        ("departure_date", pd.Timestamp("2025-01-01")),
    ],
)
def test_rejected_options(column, value):
    s, o = sample()
    o.loc[0, column] = value
    assert optimize_shipment(s, o)["recommended_carrier"] == "Beta"


def test_never_negative():
    s, o = sample()
    s.actual_paid = 20
    r = optimize_shipment(s, o)
    assert r["potential_saving"] == 0
    assert r["optimized_cost"] == 70


def test_no_feasible():
    s, o = sample()
    o.available = False
    r = optimize_shipment(s, o)
    assert r["status"] == "NO_FEASIBLE_ALTERNATIVE"
    assert r["optimized_cost"] == 100
    assert r["potential_saving"] == 0


def test_capacity_cannot_understate_shipment():
    s, o = sample()
    o.loc[0, "required_capacity_kg"] = 10
    o.loc[0, "capacity_available_kg"] = 20
    assert optimize_shipment(s, o)["recommended_carrier"] == "Beta"


def test_ties():
    s, o = sample()
    o.total_landed_cost = 70
    o.loc[1, "departure_date"] = pd.Timestamp("2026-01-01")
    assert optimize_shipment(s, o)["recommended_carrier"] == "Beta"
    o.departure_date = pd.Timestamp("2026-01-02")
    assert optimize_shipment(s, o)["recommended_carrier"] == "Alpha"


def test_determinism():
    s, o = sample()
    assert optimize_shipment(s, o) == optimize_shipment(s, o.iloc[::-1])


def test_infinite_cost_rejected():
    s, o = sample()
    o["total_landed_cost"] = o["total_landed_cost"].astype(float)
    o.loc[0, "total_landed_cost"] = float("inf")
    assert optimize_shipment(s, o)["recommended_carrier"] == "Beta"
