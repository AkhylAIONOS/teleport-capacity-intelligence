"""Live local API/proxy integration check. Run with both servers started."""

import json
import httpx

with httpx.Client(base_url="http://127.0.0.1:5173", timeout=30) as client:

    def get(path, params=None):
        response = client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    def ask(message, context=None, filters=None):
        response = client.post(
            "/api/ai/chat",
            json={
                "message": message,
                "context": context or {},
                "filters": filters or {},
            },
        )
        response.raise_for_status()
        return response.json()

    health = get("/health")
    overall = get("/api/dashboard/summary")
    filtered = get("/api/dashboard/summary", {"lane": "KUL-DEL"})
    assert 0 < filtered["shipment_count"] < overall["shipment_count"]
    rows = get("/api/shipments", {"lane": "KUL-DEL"})
    assert all(row["lane"] == "KUL-DEL" for row in rows["rows"])
    detail = get("/api/shipments/TP-88213")
    assert detail["candidates"] and detail["explanation"]
    for endpoint in [
        "trends",
        "lanes",
        "lane-heatmap",
        "carriers",
        "rate-mix",
        "quality",
        "metadata",
    ]:
        get("/api/dashboard/" + endpoint)
    savings = ask("How much could we have saved?")
    assert savings["metrics"]["potential_saving"] == overall["potential_saving"]
    top = ask("Which lane has the biggest opportunity?")
    why = ask("Why?", top["context"])
    show = ask("Show me those shipments.", why["context"])
    assert top["context"]["last_lane"] == show["filters"]["lane"]
    assert why["intent"] == "LANE_ANALYSIS" and show["intent"] == "FILTER_COMMAND"
    assert (
        get("/api/dashboard/summary", {"lane": show["filters"]["lane"]})[
            "shipment_count"
        ]
        == show["metrics"]["shipment_count"]
    )
    heatmap = get("/api/dashboard/lane-heatmap")
    assert (
        abs(
            sum(cell["potential_saving"] for cell in heatmap)
            - overall["potential_saving"]
        )
        < 0.01
    )
    scope = {
        "lane": "KUL-DEL",
        "start_date": "2026-06-01",
        "end_date": "2026-06-30",
        "min_saving": 300,
    }
    scope_summary = get("/api/dashboard/summary", scope)
    scoped_answer = ask("How much could we have saved?", filters=scope)
    assert (
        scoped_answer["metrics"]["potential_saving"]
        == scope_summary["potential_saving"]
    )
    scoped_cells = get("/api/dashboard/lane-heatmap", scope)
    assert all(
        cell["lane"] == "KUL-DEL" and cell["month"] == "2026-06"
        for cell in scoped_cells
    )
    june_action = ask("Show June shipments above $300 saving.")
    assert june_action["filters"]["start_date"] == "2026-06-01"
    assert june_action["filters"]["min_saving"] == 300
    june_summary = get(
        "/api/dashboard/summary",
        {k: v for k, v in june_action["filters"].items() if v is not None},
    )
    assert (
        june_summary["potential_saving"] == june_action["metrics"]["potential_saving"]
    )
    print(
        json.dumps(
            {
                "health": health,
                "overall": overall,
                "lane_filter_shipments": filtered["shipment_count"],
                "ai_followup_lane": show["filters"]["lane"],
                "result": "PASS",
            },
            indent=2,
        )
    )
