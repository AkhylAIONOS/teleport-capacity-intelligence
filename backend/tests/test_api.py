import pytest


@pytest.mark.parametrize(
    "path",
    [
        "/health",
        "/api/dashboard/summary",
        "/api/dashboard/trends",
        "/api/dashboard/lanes",
        "/api/dashboard/carriers",
        "/api/dashboard/rate-mix",
        "/api/dashboard/metadata",
        "/api/dashboard/quality",
        "/api/shipments",
        "/api/shipments/TP-88213",
    ],
)
def test_endpoints(client, path):
    assert client.get(path).status_code == 200


def test_api_filters(client):
    total = client.get("/api/dashboard/summary").json()
    part = client.get("/api/dashboard/summary?lane=KUL-DEL").json()
    assert part["shipment_count"] < total["shipment_count"]
    rows = client.get("/api/shipments?lane=KUL-DEL").json()["rows"]
    assert all(r["lane"] == "KUL-DEL" for r in rows)


def test_validation(client):
    assert client.get("/api/shipments?sort_by=DROP").status_code == 422
    assert client.get("/api/shipments?page=-1").status_code == 422
    assert client.get("/api/shipments/TP-1").status_code == 404
    assert client.post("/api/ai/chat", json={"message": ""}).status_code == 422


def test_posts(client):
    assert (
        client.post(
            "/api/ai/chat", json={"message": "How much could we have saved?"}
        ).json()["intent"]
        == "OVERALL_SAVINGS"
    )
    assert (
        client.post("/api/analytics/query", json={"intent": "TOP_LANES", "limit": 3})
        .json()["table"]
        .__len__()
        == 3
    )


def test_dates_and_result_ids(client):
    assert (
        client.get(
            "/api/dashboard/summary?start_date=2026-06-30&end_date=2026-01-01"
        ).status_code
        == 422
    )
    assert client.get("/api/dashboard/summary?min_saving=-1").status_code == 422
    r = client.get("/api/shipments", params={"shipment_ids": '["TP-88213"]'})
    assert r.status_code == 200 and r.json()["total"] == 1


def test_heatmap_endpoint(client):
    cells = client.get(
        "/api/dashboard/lane-heatmap",
        params={
            "lane": "KUL-DEL",
            "start_date": "2026-06-01",
            "end_date": "2026-06-30",
        },
    ).json()
    assert cells and all(
        r["lane"] == "KUL-DEL" and r["month"] == "2026-06" for r in cells
    )
