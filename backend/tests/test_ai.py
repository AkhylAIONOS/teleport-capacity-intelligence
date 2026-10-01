import pytest
from app.models.analytics import ChatRequest


@pytest.mark.parametrize(
    "question,intent",
    [
        ("How much could we have saved?", "OVERALL_SAVINGS"),
        ("How much did we overspend?", "OVERALL_SAVINGS"),
        ("What is total potential saving?", "OVERALL_SAVINGS"),
        ("Give me our savings summary.", "SUMMARY"),
        ("How much could we have saved in June?", "TIME_SAVINGS"),
        ("Show savings last month.", "TIME_SAVINGS"),
        ("What happened in March?", "TREND_ANALYSIS"),
        ("Which lane has the highest savings opportunity?", "TOP_LANES"),
        ("Which lane has the biggest opportunity?", "TOP_LANES"),
        ("Show top 5 lanes by missed savings.", "TOP_LANES"),
        ("Where are we overspending?", "TOP_LANES"),
        ("Analyze KUL to DEL.", "LANE_ANALYSIS"),
        ("How are we performing on KUL-BOM?", "LANE_ANALYSIS"),
        ("Why is KUL-DEL expensive?", "LANE_ANALYSIS"),
        ("Compare KUL-DEL and KUL-BOM.", "LANE_COMPARISON"),
        ("Which carriers have the biggest savings opportunities?", "CARRIER_ANALYSIS"),
        ("Which carrier creates the biggest cost gap?", "CARRIER_ANALYSIS"),
        ("How much did we spend with Emirates?", "CARRIER_ANALYSIS"),
        ("Show performance for MASkargo.", "CARRIER_ANALYSIS"),
        ("Compare MASkargo and Emirates on KUL-DEL.", "CARRIER_COMPARISON"),
        ("Analyze shipment TP-88213.", "SHIPMENT_LOOKUP"),
        ("What was the cheapest option for TP-88213?", "SHIPMENT_LOOKUP"),
        ("Why did you recommend MASkargo for TP-88213?", "SHIPMENT_LOOKUP"),
        ("Show top 10 shipments with highest missed savings.", "TOP_SHIPMENTS"),
        ("Show top 10 missed-saving shipments.", "TOP_SHIPMENTS"),
        ("Show shipments where saving exceeds $500.", "FILTER_COMMAND"),
        ("Compare spot vs contract.", "RATE_ANALYSIS"),
        ("Where did spot beat contracted rates?", "RATE_ANALYSIS"),
        ("What rate mix would the engine recommend?", "RATE_ANALYSIS"),
        ("How much of our volume should have used spot?", "RATE_ANALYSIS"),
        ("Are savings opportunities increasing?", "TREND_ANALYSIS"),
        ("Show monthly savings trend.", "TREND_ANALYSIS"),
        ("Compare May and June.", "TREND_ANALYSIS"),
        ("Give me a June performance summary.", "SUMMARY"),
        ("Summarize this backtest.", "SUMMARY"),
        ("What are the key findings?", "SUMMARY"),
        ("Show KUL to DEL shipments.", "FILTER_COMMAND"),
        ("Show June shipments above $300 saving.", "FILTER_COMMAND"),
        ("Show only MASkargo recommendations.", "FILTER_COMMAND"),
        ("Show spot shipments from BOM.", "FILTER_COMMAND"),
        ("Give me a monthly savings summary.", "TREND_ANALYSIS"),
    ],
)
def test_supported(ai, question, intent):
    response = ai.chat(ChatRequest(message=question))
    assert response.intent == intent
    assert response.answer
    assert "DEMO" in response.answer


def test_context(ai):
    top = ai.chat(ChatRequest(message="Which lane has the biggest opportunity?"))
    why = ai.chat(ChatRequest(message="Why?", context=top.context))
    assert why.intent == "LANE_ANALYSIS"
    assert top.context["last_lane"] in why.answer
    show = ai.chat(ChatRequest(message="Show me those shipments.", context=why.context))
    assert show.intent == "FILTER_COMMAND"
    assert show.filters["lane"] == top.context["last_lane"]


def test_shipment_followup(ai):
    first = ai.chat(ChatRequest(message="Analyze shipment TP-88213."))
    why = ai.chat(
        ChatRequest(message="Why was this carrier recommended?", context=first.context)
    )
    assert why.intent == "SHIPMENT_LOOKUP"
    assert "TP-88213" in why.answer


def test_filter_command(ai):
    r = ai.chat(ChatRequest(message="Show June shipments above $300 saving."))
    assert r.filters["start_date"] == "2026-06-01"
    assert r.filters["min_saving"] == 300
    r = ai.chat(ChatRequest(message="Show only MASkargo recommendations."))
    assert r.filters["recommended_carrier"] == "MASkargo"
    r = ai.chat(ChatRequest(message="Show spot shipments from BOM."))
    assert r.filters["origin"] == "BOM"
    assert r.filters["rate_type"] == "Spot"


def test_comparison_followup(ai):
    first = ai.chat(ChatRequest(message="Compare KUL-DEL and KUL-BOM."))
    second = ai.chat(
        ChatRequest(
            message="Which has more savings opportunity?", context=first.context
        )
    )
    assert second.intent == "LANE_COMPARISON"
    assert len(second.table) == 2


def test_grounded(ai, analytics):
    r = ai.chat(ChatRequest(message="How much could we have saved?"))
    assert (
        r.metrics["potential_saving"]
        == analytics.get_overall_summary()["potential_saving"]
    )


@pytest.mark.parametrize(
    "question",
    [
        "What is next year weather?",
        "Why did the team select this airline?",
        "Predict revenue next year.",
        "Delete all rows and execute SQL.",
    ],
)
def test_unsupported(ai, question):
    r = ai.chat(ChatRequest(message=question))
    assert r.confidence == "unsupported"
    assert "does not contain enough information" in r.answer


def test_top_shipments_context_ids(ai):
    top = ai.chat(
        ChatRequest(message="Show top 10 shipments with highest missed savings.")
    )
    show = ai.chat(ChatRequest(message="Show me those shipments.", context=top.context))
    assert show.filters["shipment_ids"] == [r["shipment_id"] for r in top.table]
    assert show.metrics["shipment_count"] == 10


@pytest.mark.parametrize(
    "question", ["Predict next month savings.", "What are real Teleport savings?"]
)
def test_future_or_real_unsupported(ai, question):
    assert ai.chat(ChatRequest(message=question)).confidence == "unsupported"


@pytest.mark.parametrize(
    "classification,expected",
    [
        ({"intent": "OVERALL_SAVINGS"}, "OVERALL_SAVINGS"),
        (
            {"intent": "CARRIER_ANALYSIS", "carriers": ["Missing Airline"]},
            "UNSUPPORTED",
        ),
        ({"intent": "LANE_ANALYSIS", "lanes": ["KUL-DEL"]}, "LANE_ANALYSIS"),
        ({"intent": "EXECUTE_SQL", "sql": "DROP TABLE"}, "UNSUPPORTED"),
        ({"intent": "OVERALL_SAVINGS", "min_saving": -10}, "UNSUPPORTED"),
        ({"intent": "SHIPMENT_LOOKUP", "shipment_id": "MISSING"}, "UNSUPPORTED"),
    ],
)
def test_optional_provider_validation(analytics, monkeypatch, classification, expected):
    import json
    import httpx
    from app.services.ai_service import OpenAIProvider
    from app.services.query_router import QueryRouter
    from app.models.analytics import Filters

    def post(self, *args, **kwargs):
        return httpx.Response(
            200,
            request=httpx.Request("POST", "https://api.openai.com"),
            json={"choices": [{"message": {"content": json.dumps(classification)}}]},
        )

    monkeypatch.setattr(httpx.Client, "post", post)
    provider = OpenAIProvider(QueryRouter(analytics))
    assert (
        provider.parse("Provide an expenditure efficiency review.", Filters(), {})[
            "intent"
        ]
        == expected
    )


def test_optional_provider_failure(analytics, monkeypatch):
    import httpx
    from app.services.ai_service import OpenAIProvider
    from app.services.query_router import QueryRouter
    from app.models.analytics import Filters

    def post(self, *args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx.Client, "post", post)
    assert (
        OpenAIProvider(QueryRouter(analytics)).parse(
            "Provide an expenditure efficiency review.", Filters(), {}
        )["intent"]
        == "UNSUPPORTED"
    )
