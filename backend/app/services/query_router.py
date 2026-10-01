import calendar
import re
from datetime import date, timedelta
from app.models.analytics import Filters

INTENTS = [
    "OVERALL_SAVINGS",
    "TIME_SAVINGS",
    "TOP_LANES",
    "LANE_ANALYSIS",
    "LANE_COMPARISON",
    "CARRIER_ANALYSIS",
    "CARRIER_COMPARISON",
    "SHIPMENT_LOOKUP",
    "TOP_SHIPMENTS",
    "RATE_ANALYSIS",
    "TREND_ANALYSIS",
    "SUMMARY",
    "FILTER_COMMAND",
]


class QueryRouter:
    def __init__(self, analytics):
        self.analytics = analytics

    def parse(self, message, filters, context):
        text = message.strip()
        lower = text.lower()
        upper = text.upper()
        if re.search(
            r"\b(predict|forecast|weather|revenue|profit|next year|next month|future|real|team select|manager|personally|delete|sql)\b",
            lower,
        ):
            return dict(intent="UNSUPPORTED", filters=filters, entities={})
        comparison_followup = bool(re.search(r"which has (?:more|the higher)", lower))
        f = filters.model_dump(mode="json")
        entities = {}
        intent = None
        airports = (
            self.analytics.metadata()["origins"]
            + self.analytics.metadata()["destinations"]
        )
        pattern = r"\b([A-Z]{3})\s*(?:-|→|TO|/)\s*([A-Z]{3})\b"
        lanes = [
            f"{a}-{b}"
            for a, b in re.findall(pattern, upper)
            if a in airports and b in airports
        ]
        if lanes:
            entities["lanes"] = list(dict.fromkeys(lanes))
            f["lane"] = lanes[0]
            f["origin"] = None
            f["destination"] = None
        known = self.analytics.metadata()["carriers"]
        carriers = [
            c
            for c in known
            if c.lower() in lower
            or (c == "Emirates SkyCargo" and "emirates" in lower)
            or (c == "Turkish Cargo" and "turkish" in lower)
        ]
        if carriers:
            entities["carriers"] = carriers
        for rate in ["Contract", "Spot", "Owned"]:
            if (
                re.search(r"\b" + rate.lower() + r"\b", lower)
                and "compare" not in lower
                and "mix" not in lower
                and "beat" not in lower
                and "volume" not in lower
            ):
                f["rate_type"] = rate
        known_ids = {
            str(value).casefold(): str(value) for value in self.analytics.df.shipment_id
        }
        tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9._/-]*", text)
        matched_ids = [
            known_ids[token.casefold().rstrip(".")]
            for token in tokens
            if token.casefold().rstrip(".") in known_ids
        ]
        sid = matched_ids[0] if matched_ids else None
        if sid:
            entities["shipment_id"] = sid
        else:
            demo_id = re.search(r"\bTP-\d+\b", upper)
            if demo_id:
                sid = demo_id.group()
                entities["shipment_id"] = sid
        n = re.search(r"top\s+(\d+)", lower)
        entities["limit"] = min(max(int(n.group(1)), 1), 50) if n else 5
        threshold = re.search(
            r"(?:above|exceeds?|over|greater than|at least)\s*\$?([\d,]+(?:\.\d+)?)",
            lower,
        )
        if threshold:
            f["min_saving"] = float(threshold.group(1).replace(",", ""))
        months = []
        for month in range(1, 13):
            if re.search(r"\b" + calendar.month_name[month].lower() + r"\b", lower):
                months.append(month)
        # Historical dataset year anchors month-only queries; relative dates use today's calendar.
        scope = self.analytics.scope(self.analytics.df)
        year_match = re.search(r"\b(20\d{2})\b", lower)
        year = (
            int(year_match.group(1))
            if year_match
            else int((scope.get("end_date") or date.today().isoformat())[:4])
        )
        if months:
            entities["months"] = [f"{year}-{m:02}" for m in months]
            f["start_date"] = f"{year}-{months[0]:02}-01"
            f["end_date"] = (
                f"{year}-{months[0]:02}-{calendar.monthrange(year,months[0])[1]}"
            )
        if "last month" in lower:
            last = date.today().replace(day=1) - timedelta(days=1)
            f["start_date"] = last.replace(day=1).isoformat()
            f["end_date"] = last.isoformat()
        if (
            "why" in lower
            or "those" in lower
            or "them" in lower
            or "that lane" in lower
            or comparison_followup
            or lower
            in [
                "show me the shipments",
                "show shipments",
                "why was this carrier recommended?",
            ]
        ):
            if not lanes and context.get("last_lane"):
                f["lane"] = context["last_lane"]
                entities["lanes"] = [context["last_lane"]]
            if not sid and context.get("last_shipment"):
                entities["shipment_id"] = context["last_shipment"]
            if not carriers and context.get("last_carrier"):
                entities["carriers"] = [context["last_carrier"]]
            if not months and context.get("last_date_range"):
                f.update(context["last_date_range"])
            if comparison_followup and context.get("last_lanes"):
                entities["lanes"] = context["last_lanes"]
        if "reset" in lower and ("filter" in lower or "dashboard" in lower):
            f = Filters().model_dump(mode="json")
            intent = "FILTER_COMMAND"
            entities["reset"] = True
        elif entities.get("shipment_id"):
            intent = "SHIPMENT_LOOKUP"
        elif ("compare" in lower or comparison_followup) and len(
            entities.get("carriers", [])
        ) >= 2:
            intent = "CARRIER_COMPARISON"
            f["carrier"] = None
            f["recommended_carrier"] = None
        elif ("compare" in lower or comparison_followup) and len(
            entities.get("lanes", [])
        ) >= 2:
            intent = "LANE_COMPARISON"
            f["lane"] = None
        elif ("compare" in lower and len(months) >= 2) or any(
            w in lower for w in ["trend", "increasing", "monthly", "what happened"]
        ):
            intent = "TREND_ANALYSIS"
        elif any(
            w in lower for w in ["spot", "contract", "rate mix", "rate type", "volume"]
        ) and not ("shipment" in lower and "show" in lower):
            intent = "RATE_ANALYSIS"
        elif "shipment" in lower and ("show" in lower or "top" in lower):
            intent = (
                "TOP_SHIPMENTS"
                if "top" in lower or ("highest" in lower and "saving" in lower)
                else "FILTER_COMMAND"
            )
        elif any(w in lower for w in ["summary", "summarize", "key findings"]):
            intent = "SUMMARY"
        elif entities.get("lanes"):
            intent = "LANE_ANALYSIS"
        elif ("lane" in lower or "where" in lower) and any(
            w in lower
            for w in [
                "saving",
                "opportunity",
                "opportunities",
                "overspend",
                "biggest",
                "highest",
                "top",
            ]
        ):
            intent = "TOP_LANES"
        elif entities.get("carriers") or (
            "carrier" in lower
            and any(
                w in lower
                for w in [
                    "saving",
                    "opportunity",
                    "opportunities",
                    "gap",
                    "spend",
                    "performance",
                ]
            )
        ):
            intent = "CARRIER_ANALYSIS"
        elif any(w in lower for w in ["saved", "saving", "overspend", "backtest"]):
            intent = (
                "TIME_SAVINGS" if months or "last month" in lower else "OVERALL_SAVINGS"
            )
        if (
            lower.startswith(("show", "filter"))
            and (
                lanes
                or threshold
                or "recommendations" in lower
                or re.search(r"from\s+[a-z]{3}", lower)
            )
            and "top" not in lower
        ):
            intent = "FILTER_COMMAND"
        if intent == "FILTER_COMMAND":
            if (
                ("those" in lower or "them" in lower)
                and context.get("last_intent") == "TOP_SHIPMENTS"
                and context.get("last_result_ids")
            ):
                f["shipment_ids"] = context["last_result_ids"][:100]
            if carriers:
                key = "recommended_carrier" if "recommend" in lower else "carrier"
                f[key] = carriers[0]
            for rate in ["Contract", "Spot", "Owned"]:
                if re.search(r"\b" + rate.lower() + r"\b", lower):
                    f["rate_type"] = rate
            origin = re.search(r"\bFROM\s+([A-Z]{3})\b", upper)
            if origin and origin.group(1) in airports:
                f["origin"] = origin.group(1)
                f["lane"] = None
        if "savings percentage" in lower:
            entities["comparison_metric"] = "saving_percent"
        return dict(
            intent=intent or "UNSUPPORTED", filters=Filters(**f), entities=entities
        )
