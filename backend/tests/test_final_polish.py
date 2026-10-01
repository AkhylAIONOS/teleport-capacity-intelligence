import json
import pytest
from app.models.analytics import ChatRequest, Filters
from test_ai import test_supported as supported_cases

# The existing 41 cases plus the two required followups and monthly-summary wording.
QUESTIONS = list(supported_cases.pytestmark[0].args[1])
QUESTIONS = [(q.replace("KUL-DEL.", "KUL-BOM.") if q.startswith("Compare MASkargo") else q, i) for q, i in QUESTIONS]
QUESTIONS = [(q, i) for q, i in QUESTIONS if q not in ["Why did you recommend MASkargo for TP-88213?", "Give me a monthly savings summary."]]
QUESTIONS += [("Give me a monthly summary.", "TREND_ANALYSIS"), ("Which has the higher savings percentage?", "LANE_COMPARISON"), ("Why was this carrier recommended?", "SHIPMENT_LOOKUP")]

@pytest.mark.parametrize("question,intent", QUESTIONS)
@pytest.mark.parametrize("active", [False, True])
def test_required_questions(ai, analytics, question, intent, active):
    filters = Filters(lane="KUL-BOM") if active else Filters()
    context = {}
    if question.startswith("Which has the higher"):
        context = ai.chat(ChatRequest(message="Compare KUL-BOM and KUL-DEL.", filters=filters)).context
    elif question == "Why was this carrier recommended?":
        context = ai.chat(ChatRequest(message="Analyze shipment TP-88213.", filters=filters)).context
    parsed = ai.router.parse(question, filters, context)
    response = ai.chat(ChatRequest(message=question, filters=filters, context=context))
    assert response.intent == intent
    assert response.answer.strip()
    serialized = json.dumps(response.model_dump(), allow_nan=False)
    assert "undefined" not in serialized
    assert "NaN" not in serialized
    assert "DEMO" in response.answer
    if intent in ["OVERALL_SAVINGS", "TIME_SAVINGS", "SUMMARY", "FILTER_COMMAND"]:
        expected = analytics.get_overall_summary(parsed["filters"])
        assert response.metrics["potential_saving"] == expected["potential_saving"]
        assert response.data_scope == expected["data_scope"]
    elif intent not in ["SHIPMENT_LOOKUP", "TREND_ANALYSIS"]:
        assert response.data_scope == analytics.scope(analytics.filtered(parsed["filters"]), parsed["filters"])
    if active and intent in ["RATE_ANALYSIS", "TOP_SHIPMENTS", "TOP_LANES", "OVERALL_SAVINGS"]:
        assert parsed["filters"].lane == "KUL-BOM"

@pytest.mark.parametrize("question", ["Predict next year's revenue.", "What will fuel prices be next year?", "Why did the historical manager personally choose Emirates?", "Delete all rows.", "Execute arbitrary SQL."])
def test_required_unsupported(ai, question):
    response = ai.chat(ChatRequest(message=question))
    assert response.intent == "UNSUPPORTED"
    assert response.confidence == "unsupported"

@pytest.mark.parametrize("filters", [Filters(lane="KUL-BOM"), Filters(lane="KUL-BOM", start_date="2026-06-01", end_date="2026-06-30"), Filters(lane="NO-MATCH")])
def test_query_scope(analytics, filters):
    summary = analytics.get_overall_summary(filters)
    scope = summary["data_scope"]
    full = analytics.metadata()["data_scope"]
    assert scope["start_date"] == (str(filters.start_date) if filters.start_date else full["start_date"])
    assert scope["end_date"] == (str(filters.end_date) if filters.end_date else full["end_date"])
    assert scope["shipment_count"] == len(analytics.filtered(filters))

@pytest.mark.parametrize("filters", [Filters(), Filters(lane="KUL-BOM")])
def test_monthly_extrema(ai, analytics, filters):
    response = ai.chat(ChatRequest(message="Give me a monthly summary.", filters=filters))
    rows = analytics.get_monthly_trend(filters)
    m = response.metrics
    peak = max(rows, key=lambda r:r["potential_saving"])
    trough = min(rows, key=lambda r:r["potential_saving"])
    assert m["highest_month"] == peak["month"]
    assert m["highest_month_saving"] == peak["potential_saving"]
    assert m["lowest_month"] == trough["month"]
    assert m["lowest_month_saving"] == trough["potential_saving"]
    assert m["potential_saving"] == round(sum(r["potential_saving"] for r in rows), 2)
    assert m["saving_change"] == rows[-1]["potential_saving"] - rows[0]["potential_saving"]
    assert m["saving_change_percent"] == pytest.approx(m["saving_change"] / rows[0]["potential_saving"] * 100)
    assert "range from" not in response.answer

def test_zero_first_month(ai, monkeypatch):
    monkeypatch.setattr(ai.analytics, "get_monthly_trend", lambda f: [{"month":"2026-01", "potential_saving":0}, {"month":"2026-02", "potential_saving":100}])
    r = ai.chat(ChatRequest(message="Give me a monthly summary."))
    assert r.metrics["saving_change_percent"] is None
    assert "unavailable" in r.answer

def test_context_chain_b(ai):
    first = ai.chat(ChatRequest(message="Compare KUL-BOM and KUL-DEL."))
    second = ai.chat(ChatRequest(message="Which has the higher savings percentage?", context=first.context))
    best = max(second.table, key=lambda r:r["saving_percent"])
    assert best["lane"] in second.answer
    assert f'{best["saving_percent"]:.2f}%' in second.answer
    third = ai.chat(ChatRequest(message="Show me KUL-DEL instead.", context=second.context))
    assert third.intent == "FILTER_COMMAND"
    assert third.filters["lane"] == "KUL-DEL"

def test_why_and_show_wording(ai):
    first = ai.chat(ChatRequest(message="Which lane has the biggest opportunity?"))
    why = ai.chat(ChatRequest(message="Why?", context=first.context))
    assert "historically assigned" in why.answer
    assert "does not establish why" in why.answer
    show = ai.chat(ChatRequest(message="Show me those shipments.", context=why.context))
    assert "Showing" in show.answer and "Potential savings in this scope" in show.answer

def test_month_comparison_scope(ai):
    response = ai.chat(ChatRequest(message="Compare May and June."))
    assert response.data_scope["start_date"] == "2026-05-01"
    assert response.data_scope["end_date"] == "2026-06-30"
