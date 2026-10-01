import pytest
from app.models.analytics import Filters


def test_totals(analytics):
    s = analytics.get_overall_summary()
    df = analytics.df
    assert s["shipment_count"] == 2000
    assert s["actual_spend"] == pytest.approx(df.actual_paid.sum())
    assert s["optimized_spend"] == pytest.approx(df.optimized_cost.sum())
    assert s["potential_saving"] == pytest.approx(df.potential_saving.sum())
    assert s["average_saving_per_flagged"] == pytest.approx(
        df.potential_saving.sum() / df.potential_saving.gt(0).sum(), abs=0.01
    )


@pytest.mark.parametrize(
    "filters",
    [
        Filters(lane="KUL-DEL"),
        Filters(carrier="MASkargo"),
        Filters(start_date="2026-06-01", end_date="2026-06-30"),
        Filters(origin="BOM"),
        Filters(destination="SIN"),
        Filters(rate_type="Spot"),
        Filters(min_saving=500),
        Filters(recommended_carrier="MASkargo"),
    ],
)
def test_filtering(analytics, filters):
    df = analytics.filtered(filters)
    assert 0 < len(df) < len(analytics.df)
    if filters.lane:
        assert set(df.lane) == {filters.lane}
    if filters.carrier:
        assert set(df.actual_carrier) == {filters.carrier}
    if filters.start_date:
        assert df.shipment_date.min().strftime("%Y-%m-%d") >= str(filters.start_date)
    if filters.end_date:
        assert df.shipment_date.max().strftime("%Y-%m-%d") <= str(filters.end_date)
    if filters.min_saving:
        assert df.potential_saving.min() >= filters.min_saving
    if filters.recommended_carrier:
        assert set(df.recommended_carrier) == {filters.recommended_carrier}


def test_top_n(analytics):
    rows = analytics.get_top_saving_shipments(limit=10)
    assert len(rows) == 10
    assert rows[0]["potential_saving"] >= rows[-1]["potential_saving"]
    lanes = analytics.get_top_lanes(limit=5)
    assert len(lanes) == 5
    assert lanes[0]["potential_saving"] >= lanes[-1]["potential_saving"]


def test_lookup(analytics):
    d = analytics.get_shipment_analysis("TP-88213")
    assert d["shipment"]["shipment_id"] == "TP-88213"
    assert d["candidates"]
    assert analytics.get_shipment_analysis("TP-1") is None


def test_mix(analytics):
    rows = analytics.get_rate_mix()
    assert sum(r["actual_count"] for r in rows) == 2000
    assert sum(r["recommended_count"] for r in rows) == 2000
    assert sum(r["recommended_percent"] for r in rows) == pytest.approx(100)


def test_trend_totals(analytics):
    rows = analytics.get_monthly_trend()
    assert len(rows) == 6
    assert sum(r["potential_saving"] for r in rows) == pytest.approx(
        analytics.df.potential_saving.sum()
    )
    cumulative = analytics.get_monthly_trend(cumulative=True)
    assert cumulative[-1]["actual_spend"] == pytest.approx(
        analytics.df.actual_paid.sum()
    )


def test_empty(analytics):
    f = Filters(lane="AAA-BBB")
    assert analytics.get_overall_summary(f)["shipment_count"] == 0
    assert analytics.get_rate_mix(f)[0]["actual_percent"] == 0
    assert analytics.get_top_lanes(f) == []


def test_recommendations_valid(analytics):
    for sid in analytics.df[analytics.df.feasible_count.gt(0)].shipment_id.sample(
        20, random_state=42
    ):
        d = analytics.get_shipment_analysis(sid)
        chosen = d["recommended_option"]
        assert chosen["feasible"]
        assert chosen["total_landed_cost"] == min(
            r["total_landed_cost"] for r in d["candidates"] if r["feasible"]
        )


def test_demo_savings_calibration(analytics):
    # Generator-only expectation; no clamp belongs in analytics or the UI.
    assert 5 <= analytics.get_overall_summary()["saving_percent"] <= 10


def test_already_optimal_backend_definition(analytics):
    s = analytics.get_overall_summary()
    assert s["already_optimal_percent"] == pytest.approx(
        (analytics.df.potential_saving.eq(0).sum() / len(analytics.df)) * 100
    )
    assert (
        analytics.get_overall_summary(Filters(lane="MISSING"))[
            "already_optimal_percent"
        ]
        == 0
    )


def test_lane_heatmap_aggregates_and_scope(analytics):
    rows = analytics.get_lane_heatmap()
    assert len(rows) == len({(r["lane"], r["month"]) for r in rows})
    assert sum(r["potential_saving"] for r in rows) == pytest.approx(
        analytics.get_overall_summary()["potential_saving"]
    )
    assert sum(r["shipment_count"] for r in rows) == len(analytics.df)
    assert all(0 <= r["intensity"] <= 1 for r in rows)
    f = Filters(
        lane="KUL-DEL", start_date="2026-06-01", end_date="2026-06-30", min_saving=300
    )
    cells = analytics.get_lane_heatmap(f)
    assert cells and all(
        r["lane"] == "KUL-DEL" and r["month"] == "2026-06" for r in cells
    )
    assert sum(r["potential_saving"] for r in cells) == pytest.approx(
        analytics.get_overall_summary(f)["potential_saving"]
    )
    assert analytics.get_lane_heatmap(Filters(lane="MISSING")) == []


def test_real_metrics_are_not_capped(analytics):
    from app.services.analytics_service import AnalyticsService

    instance = object.__new__(AnalyticsService)
    instance.df = analytics.df.head(10).copy()
    instance.df["actual_paid"] = 1000.0
    instance.df["optimized_cost"] = 500.0
    instance.df["potential_saving"] = 500.0
    assert instance.get_overall_summary()["saving_percent"] == 50
