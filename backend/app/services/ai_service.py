import calendar
import json
from abc import ABC, abstractmethod
import httpx
from app import config
from app.models.analytics import AIResponse, Filters
from app.services.query_router import QueryRouter, INTENTS

UNSUPPORTED = (
    "The available dataset does not contain enough information to answer this reliably."
)


def money(v):
    return f"${v:,.2f}"


class IntentProvider(ABC):
    @abstractmethod
    def parse(self, message, filters, context):
        pass


class MockProvider(IntentProvider):
    def __init__(self, router):
        self.router = router

    def parse(self, message, filters, context):
        return self.router.parse(message, filters, context)


class OpenAIProvider(IntentProvider):
    """Extracts constrained routing information; never accepts model metrics or SQL."""

    def __init__(self, router):
        self.router = router

    def parse(self, message, filters, context):
        baseline = self.router.parse(message, filters, context)
        if baseline["intent"] != "UNSUPPORTED":
            return baseline
        # Explicitly unsupported topics must never be reclassified by a model.
        import re

        if re.search(
            r"\b(predict|forecast|weather|revenue|profit|next year|next month|future|real|team select|manager|personally|delete|sql)\b",
            message.lower(),
        ):
            return baseline
        metadata = self.router.analytics.metadata()
        prompt = f"""Route an analytics question. Return only JSON with intent, lanes (list), carriers (list), shipment_id (string or null), months (YYYY-MM list), origin (or null), destination (or null), rate_type (or null), recommended_carrier (or null), min_saving (nonnegative number or null), and limit (1..50). Intents: {INTENTS} or UNSUPPORTED. Known carriers: {metadata['carriers']}. Known lanes: {metadata['lanes']}. Dataset dates: {metadata['data_scope']}. Preserve explicitly mentioned unknown entities so the validator can reject them; never drop them to answer a broader question. Questions about predictions, causal business motives beyond recorded candidate constraints, or data absent from the dataset must be UNSUPPORTED. No calculations, answers, SQL, or invented metrics. Use supplied dashboard filters and context for follow-up references."""
        try:
            with httpx.Client(timeout=15) as client:
                response = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                    json={
                        "model": config.OPENAI_MODEL,
                        "temperature": 0,
                        "max_completion_tokens": 600,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": prompt},
                            {
                                "role": "user",
                                "content": json.dumps(
                                    {
                                        "message": message,
                                        "filters": filters.model_dump(mode="json"),
                                        "context": context,
                                    }
                                ),
                            },
                        ],
                    },
                )
                response.raise_for_status()
                route = json.loads(response.json()["choices"][0]["message"]["content"])
            intent = route.get("intent")
            if intent not in INTENTS:
                return baseline
            lanes = route.get("lanes") or []
            carriers = route.get("carriers") or []
            months = route.get("months") or []
            if (
                not isinstance(lanes, list)
                or not isinstance(carriers, list)
                or not isinstance(months, list)
            ):
                return baseline
            if any(l not in metadata["lanes"] for l in lanes) or any(
                c not in metadata["carriers"] for c in carriers
            ):
                return baseline
            if any(
                not isinstance(m, str)
                or not re.fullmatch(r"20\d{2}-(?:0[1-9]|1[0-2])", m)
                for m in months
            ):
                return baseline
            values = filters.model_dump(mode="json")
            for key, allowed in [
                ("origin", metadata["origins"]),
                ("destination", metadata["destinations"]),
                ("rate_type", metadata["rate_types"]),
                ("recommended_carrier", metadata["carriers"]),
            ]:
                value = route.get(key)
                if value:
                    if value not in allowed:
                        return baseline
                    values[key] = value
            if route.get("min_saving") is not None:
                values["min_saving"] = float(route["min_saving"])
            if lanes:
                values["lane"] = lanes[0] if intent != "LANE_COMPARISON" else None
                values["origin"] = None
                values["destination"] = None
            if months:
                year, month = map(int, months[0].split("-"))
                values["start_date"] = months[0] + "-01"
                values["end_date"] = (
                    months[0] + f"-{calendar.monthrange(year,month)[1]}"
                )
            sid = route.get("shipment_id")
            if sid and self.router.analytics.get_shipment_analysis(sid) is None:
                return baseline
            if intent == "SHIPMENT_LOOKUP" and not sid:
                return baseline
            if intent in ["LANE_ANALYSIS", "LANE_COMPARISON"] and len(lanes) < (
                2 if intent == "LANE_COMPARISON" else 1
            ):
                return baseline
            if intent == "CARRIER_COMPARISON" and len(carriers) < 2:
                return baseline
            if (
                intent == "FILTER_COMMAND"
                and carriers
                and not route.get("recommended_carrier")
            ):
                values["carrier"] = carriers[0]
            return {
                "intent": intent,
                "filters": Filters(**values),
                "entities": {
                    "lanes": lanes,
                    "carriers": carriers,
                    "months": months,
                    "shipment_id": sid,
                    "limit": min(max(int(route.get("limit") or 5), 1), 50),
                },
            }
        except (
            httpx.HTTPError,
            ValueError,
            KeyError,
            IndexError,
            TypeError,
            AttributeError,
        ):
            return baseline


class AIService:
    def __init__(self, analytics):
        self.analytics = analytics
        self.router = QueryRouter(analytics)
        self.provider = (
            OpenAIProvider(self.router)
            if config.AI_PROVIDER == "openai" and config.OPENAI_API_KEY
            else MockProvider(self.router)
        )

    def chat(self, request):
        parsed = self.provider.parse(request.message, request.filters, request.context)
        return self.execute(
            parsed["intent"], parsed["filters"], parsed["entities"], request.context
        )

    def execute(self, intent, filters, entities=None, context=None):
        entities = entities or {}
        context = dict(context or {})
        a = self.analytics
        response = AIResponse(
            answer="",
            intent=intent,
            data_scope=a.scope(a.filtered(filters), filters),
            context=context,
            provider="openai" if isinstance(self.provider, OpenAIProvider) else "mock",
        )
        metrics = {}
        rows = []
        limit = min(max(int(entities.get("limit", 5)), 1), 50)
        if intent in ["OVERALL_SAVINGS", "TIME_SAVINGS", "SUMMARY", "FILTER_COMMAND"]:
            metrics = a.get_overall_summary(filters)
            response.answer = f'Potential savings are {money(metrics["potential_saving"])} ({metrics["saving_percent"]:.2f}% of actual spend). Actual spend: {money(metrics["actual_spend"])}; optimized spend: {money(metrics["optimized_spend"])} across {metrics["shipment_count"]:,} shipments.'
            if intent == "SUMMARY":
                lanes = a.get_top_lanes(filters, 1)
                trend = a.get_monthly_trend(filters)
                response.answer += f' {metrics["flagged_shipments"]:,} shipments have a cheaper feasible option; average saving per flagged shipment: {money(metrics["average_saving_per_flagged"])}. {metrics["no_feasible_alternative"]:,} shipments have no feasible alternative.'
                if lanes:
                    response.answer += f' Largest lane opportunity: {lanes[0]["lane"]} ({money(lanes[0]["potential_saving"])}).'
                rows = trend
                response.chart = {"type": "trend", "rows": trend}
            if intent == "FILTER_COMMAND":
                response.filters = filters.model_dump(mode="json")
                subject = filters.lane.replace("-", " → ") + " " if filters.lane else ""
                response.answer = f'Showing {metrics["shipment_count"]:,} {subject}shipments. Potential savings in this scope are {money(metrics["potential_saving"])} ({metrics["saving_percent"]:.2f}%).'
        elif intent == "TOP_LANES":
            rows = a.get_top_lanes(filters, limit)
            if rows:
                metrics = rows[0]
                context["last_lane"] = rows[0]["lane"]
                response.answer = f'{rows[0]["lane"]} has the largest potential saving: {money(rows[0]["potential_saving"])} ({rows[0]["saving_percent"]:.2f}%). Actual spend: {money(rows[0]["actual_spend"])} across {rows[0]["shipment_count"]:,} shipments; {rows[0]["flagged_shipments"]:,} are flagged.'
        elif intent in ["LANE_ANALYSIS", "LANE_COMPARISON"]:
            lanes = entities.get("lanes", []) or (
                [filters.lane] if filters.lane else []
            )
            if intent == "LANE_COMPARISON" and len(lanes) >= 2:
                rows = a.compare_lanes(lanes, filters)
                context["last_lanes"] = lanes
                best = max(rows, key=lambda x: x[entities.get("comparison_metric", "potential_saving")])
                metrics = {
                    "saving_difference": max(r["potential_saving"] for r in rows)
                    - min(r["potential_saving"] for r in rows)
                }
                response.answer = f'{best["lane"]} has the largest calculated savings opportunity in this comparison: {money(best["potential_saving"])}. Difference between the highest and lowest opportunity: {money(metrics["saving_difference"])}.'
                if entities.get("comparison_metric") == "saving_percent":
                    response.answer = f'{best["lane"]} has the higher savings percentage: {best["saving_percent"]:.2f}% ({money(best["potential_saving"])} potential saving).'
            elif lanes:
                lane = lanes[0]
                analysis = a.get_lane_analysis(lane, filters)
                metrics = analysis["summary"]
                rows = analysis["drivers"]
                context["last_lane"] = lane
                response.answer = f'{lane}: potential savings {money(metrics["potential_saving"])} ({metrics["saving_percent"]:.2f}%) across {metrics["shipment_count"]:,} shipments. The gap is the recorded historical payment versus each cheapest feasible candidate.'
                if rows:
                    response.answer += f' Among shipments historically assigned to {rows[0]["carrier"]}, aggregate potential saving was {money(rows[0]["potential_saving"])}, the largest carrier-level contribution to the {lane} savings gap.'
                response.answer += " The dataset does not establish why the historical team made its original decision."
        elif intent in ["CARRIER_ANALYSIS", "CARRIER_COMPARISON"]:
            carriers = entities.get("carriers", [])
            rows = (
                a.compare_carriers(carriers, filters)
                if carriers
                else a.get_carrier_analysis(filters)[:limit]
            )
            if rows:
                best = max(rows, key=lambda r: r["potential_saving"])
                metrics = best
                context["last_carrier"] = best["carrier"]
                response.answer = f'{best["carrier"]}: actual spend {money(best["actual_spend"])}, {best["shipment_count"]:,} historical shipments, average cost {money(best["average_cost"])}, potential savings {money(best["potential_saving"])}, and {best["recommended_usage"]:,} recommended uses in the filtered scope. Savings are attributed to the historical carrier; they are not a claim about its service quality.'
        elif intent == "SHIPMENT_LOOKUP":
            sid = entities.get("shipment_id")
            detail = a.get_shipment_analysis(sid)
            if detail:
                r = detail["shipment"]
                response.data_scope = a.scope(a.df[a.df.shipment_id.eq(sid)], filters)
                metrics = {
                    k: r[k]
                    for k in [
                        "actual_paid",
                        "optimized_cost",
                        "potential_saving",
                        "saving_percent",
                        "candidate_count",
                        "feasible_count",
                    ]
                }
                rows = detail["candidates"]
                context["last_shipment"] = sid
                response.answer = (
                    f'{sid}: actual {r["actual_carrier"]} / {r["actual_rate_type"]}, {money(r["actual_paid"])}. Recommended {r["recommended_carrier"]} / {r["recommended_rate_type"]}, {money(r["optimized_cost"])}. Potential saving: {money(r["potential_saving"])}. '
                    + detail["explanation"]
                )
        elif intent == "TOP_SHIPMENTS":
            rows = a.get_top_saving_shipments(filters, limit)
            metrics = {"returned_shipments": len(rows)}
            response.answer = f"Here are the {len(rows)} highest-saving shipments in the current scope, ordered by potential saving."
            context["last_result_ids"] = [r["shipment_id"] for r in rows]
            response.filters = filters.model_dump(mode="json")
        elif intent == "RATE_ANALYSIS":
            rows = a.get_rate_mix(filters)
            spot = next(r for r in rows if r["rate_type"] == "Spot")
            metrics = {
                "recommended_spot_weight_percent": spot["recommended_weight_percent"],
                "spot_beats_contract_count": spot["spot_beats_contract_count"],
            }
            response.answer = f'The engine recommends Spot for {spot["recommended_percent"]:.2f}% of shipments and {spot["recommended_weight_percent"]:.2f}% of cargo weight. A feasible Spot option beats the historical Contract choice for {spot["spot_beats_contract_count"]:,} shipments. Actual and recommended mixes include retained historical decisions where no feasible alternative exists.'
        elif intent == "TREND_ANALYSIS":
            months = entities.get("months", [])
            f = filters
            if len(months) >= 2:
                year, month = map(int, max(months).split("-"))
                f = filters.model_copy(update={"start_date": min(months) + "-01", "end_date": max(months) + f"-{calendar.monthrange(year, month)[1]}"})
            rows = a.get_monthly_trend(f)
            if months:
                rows = [r for r in rows if r["month"] in months]
            if rows:
                change = rows[-1]["potential_saving"] - rows[0]["potential_saving"]
                peak = max(rows, key=lambda r: r["potential_saving"])
                trough = min(rows, key=lambda r: r["potential_saving"])
                first, last = rows[0], rows[-1]
                change_percent = change / first["potential_saving"] * 100 if first["potential_saving"] else None
                metrics = {
                    "potential_saving": round(sum(r["potential_saving"] for r in rows), 2),
                    "highest_month": peak["month"], "highest_month_saving": peak["potential_saving"],
                    "lowest_month": trough["month"], "lowest_month_saving": trough["potential_saving"],
                    "first_month": first["month"], "last_month": last["month"],
                    "saving_change": change, "saving_change_percent": change_percent,
                    "first_month_saving": first["potential_saving"], "last_month_saving": last["potential_saving"],
                }
                def month_label(value):
                    year, month = map(int, value.split("-"))
                    return f"{calendar.month_abbr[month]} {year}"
                direction = "increase" if change >= 0 else "decrease"
                percentage = f" ({abs(change_percent):.2f}%)" if change_percent is not None else " (percentage unavailable because first-month saving is zero)"
                response.answer = f'Potential savings totaled {money(metrics["potential_saving"])} across {month_label(first["month"])}–{month_label(last["month"])}. Savings peaked in {month_label(peak["month"])} at {money(peak["potential_saving"])} and were lowest in {month_label(trough["month"])} at {money(trough["potential_saving"])}. From {month_label(first["month"])} to {month_label(last["month"])}, monthly savings changed from {money(first["potential_saving"])} to {money(last["potential_saving"])}, a {direction} of {money(abs(change))}{percentage}. This compares recorded monthly totals and does not predict future savings.'
                response.chart = {"type": "trend", "rows": rows}
                response.data_scope = a.scope(a.filtered(f), f)
        if not response.answer or intent == "UNSUPPORTED":
            response.answer = UNSUPPORTED
            response.confidence = "unsupported"
        elif response.data_scope["shipment_count"] == 0 and intent != "SHIPMENT_LOOKUP":
            response.answer = "No shipments match this scope. " + UNSUPPORTED
            response.confidence = "unsupported"
        response.answer += " " + (
            "DEMO / simulated data; USD."
            if config.DATA_MODE == "demo"
            else "Imported dataset; USD."
        )
        response.metrics = {k: v for k, v in metrics.items() if k != "data_scope"}
        response.table = rows
        if intent in ["TOP_LANES", "LANE_ANALYSIS", "LANE_COMPARISON"]:
            context.pop("last_shipment", None)
            context.pop("last_carrier", None)
        elif intent in ["CARRIER_ANALYSIS", "CARRIER_COMPARISON"]:
            context.pop("last_shipment", None)
        elif intent == "SHIPMENT_LOOKUP":
            context.pop("last_lane", None)
            context.pop("last_carrier", None)
        context["last_intent"] = intent
        if filters.lane:
            context["last_lane"] = filters.lane
        if filters.start_date or filters.end_date:
            context["last_date_range"] = {
                "start_date": str(filters.start_date) if filters.start_date else None,
                "end_date": str(filters.end_date) if filters.end_date else None,
            }
        response.context = context
        return response
