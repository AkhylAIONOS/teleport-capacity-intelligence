import json
import pandas as pd
from app.config import DATA_MODE
from app.models.analytics import Filters
from app.services.optimizer import optimize_all, evaluate_options
from app.utils.filters import apply_filters


def records(df):
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.strftime("%Y-%m-%d")
    return json.loads(out.to_json(orient="records"))


class AnalyticsService:
    def __init__(self, loader):
        self.loader = loader
        self.df = optimize_all(loader.shipments, loader.options)

    def filtered(self, filters=None):
        return apply_filters(self.df, filters or Filters())

    def scope(self, df, filters=None):
        filters = filters or Filters()
        return dict(
            start_date=str(filters.start_date) if filters.start_date else (self.df.shipment_date.min().strftime("%Y-%m-%d") if len(self.df) else None),
            data_first_date=df.shipment_date.min().strftime("%Y-%m-%d") if len(df) else None,
            end_date=str(filters.end_date) if filters.end_date else (self.df.shipment_date.max().strftime("%Y-%m-%d") if len(self.df) else None),
            data_last_date=df.shipment_date.max().strftime("%Y-%m-%d") if len(df) else None,
            shipment_count=len(df),
            data_mode=DATA_MODE,
            currency="USD",
        )

    def get_overall_summary(self, filters=None):
        df = self.filtered(filters)
        actual = float(df.actual_paid.sum())
        saving = float(df.potential_saving.sum())
        flagged = int(df.potential_saving.gt(0).sum())
        return dict(
            actual_spend=round(actual, 2),
            optimized_spend=round(float(df.optimized_cost.sum()), 2),
            potential_saving=round(saving, 2),
            saving_percent=saving / actual * 100 if actual else 0,
            shipment_count=len(df),
            flagged_shipments=flagged,
            average_saving_per_flagged=round(saving / flagged, 2) if flagged else 0,
            feasible_shipments=int(df.feasible_count.gt(0).sum()),
            unchanged_shipments=len(df) - flagged,
            already_optimal_percent=(
                (len(df) - flagged) / len(df) * 100 if len(df) else 0
            ),
            no_feasible_alternative=int(df.status.eq("NO_FEASIBLE_ALTERNATIVE").sum()),
            data_scope=self.scope(df, filters),
        )

    def get_time_summary(self, filters=None):
        return self.get_overall_summary(filters)

    def grouped(self, key, filters=None):
        df = self.filtered(filters)
        if df.empty:
            return []
        g = (
            df.groupby(key)
            .agg(
                actual_spend=("actual_paid", "sum"),
                optimized_spend=("optimized_cost", "sum"),
                potential_saving=("potential_saving", "sum"),
                shipment_count=("shipment_id", "count"),
                flagged_shipments=("potential_saving", lambda v: int(v.gt(0).sum())),
                weight_kg=("weight_kg", "sum"),
            )
            .reset_index()
        )
        g["saving_percent"] = (
            g.potential_saving / g.actual_spend.replace(0, float("nan")) * 100
        )
        return records(
            g.sort_values(["potential_saving", key], ascending=[False, True])
        )

    def get_top_lanes(self, filters=None, limit=50):
        return self.grouped("lane", filters)[:limit]

    def get_lane_heatmap(self, filters=None):
        """Same dashboard scope, grouped by historical lane and calendar month."""
        df = self.filtered(filters)
        if df.empty:
            return []
        df["month"] = df.shipment_date.dt.strftime("%Y-%m")
        grouped = (
            df.groupby(["lane", "month"])
            .agg(
                actual_spend=("actual_paid", "sum"),
                optimized_spend=("optimized_cost", "sum"),
                potential_saving=("potential_saving", "sum"),
                shipment_count=("shipment_id", "count"),
            )
            .reset_index()
        )
        grouped["saving_percent"] = (
            grouped.potential_saving
            / grouped.actual_spend.replace(0, float("nan"))
            * 100
        )
        maximum = float(grouped.potential_saving.max())
        grouped["intensity"] = grouped.potential_saving / maximum if maximum else 0.0
        from app.services.provenance import load_provenance
        provenance = load_provenance()["lane_provenance"]
        return [{**row, "provenance": provenance.get(row["lane"], {"classification": "UNCLASSIFIED_IMPORTED_LANE", "note": "No public route evidence attached."})} for row in records(grouped.sort_values(["lane", "month"]))]

    def get_lane_analysis(self, lane, filters=None):
        f = (filters or Filters()).model_copy(update={"lane": lane})
        return dict(
            summary=self.get_overall_summary(f),
            drivers=self.get_carrier_analysis(f),
            rate_mix=self.get_rate_mix(f),
        )

    def compare_lanes(self, lanes, filters=None):
        return [
            dict(
                lane=lane,
                **self.get_overall_summary(
                    (filters or Filters()).model_copy(update={"lane": lane})
                ),
            )
            for lane in lanes
        ]

    def get_carrier_analysis(self, filters=None):
        df = self.filtered(filters)
        rows = self.grouped("actual_carrier", filters)
        for r in rows:
            r["carrier"] = r.pop("actual_carrier")
            r["average_cost"] = r["actual_spend"] / r["shipment_count"]
            r["recommended_usage"] = int(df.recommended_carrier.eq(r["carrier"]).sum())
        return rows

    def compare_carriers(self, carriers, filters=None):
        df = self.filtered(filters)
        all_rows = {r["carrier"]: r for r in self.get_carrier_analysis(filters)}
        return [
            all_rows.get(
                c,
                dict(
                    carrier=c,
                    shipment_count=0,
                    actual_spend=0,
                    average_cost=0,
                    recommended_usage=int(df.recommended_carrier.eq(c).sum()),
                    potential_saving=0,
                ),
            )
            for c in carriers
        ]

    def get_monthly_trend(self, filters=None, cumulative=False):
        df = self.filtered(filters)
        if df.empty:
            return []
        df["month"] = df.shipment_date.dt.strftime("%Y-%m")
        grouped = (
            df.groupby("month")
            .agg(
                actual_spend=("actual_paid", "sum"),
                optimized_spend=("optimized_cost", "sum"),
                potential_saving=("potential_saving", "sum"),
                shipment_count=("shipment_id", "count"),
            )
            .reset_index()
        )
        if cumulative:
            grouped[["actual_spend", "optimized_spend", "potential_saving"]] = grouped[
                ["actual_spend", "optimized_spend", "potential_saving"]
            ].cumsum()
        return records(grouped)

    def get_rate_mix(self, filters=None):
        df = self.filtered(filters)
        total = len(df)
        weight = float(df.weight_kg.sum())
        out = []
        for rate in ["Contract", "Spot", "Owned"]:
            a = df.actual_rate_type.eq(rate)
            r = df.recommended_rate_type.eq(rate)
            out.append(
                dict(
                    rate_type=rate,
                    actual_count=int(a.sum()),
                    recommended_count=int(r.sum()),
                    actual_percent=float(a.sum()) / total * 100 if total else 0,
                    recommended_percent=float(r.sum()) / total * 100 if total else 0,
                    actual_weight_kg=float(df.loc[a, "weight_kg"].sum()),
                    recommended_weight_kg=float(df.loc[r, "weight_kg"].sum()),
                    recommended_weight_percent=(
                        float(df.loc[r, "weight_kg"].sum()) / weight * 100
                        if weight
                        else 0
                    ),
                    actual_spend=float(df.loc[a, "actual_paid"].sum()),
                    potential_saving=float(df.loc[a, "potential_saving"].sum()),
                    spot_beats_contract_count=(
                        int(
                            (
                                df.actual_rate_type.eq("Contract")
                                & df.recommended_rate_type.eq("Spot")
                                & df.potential_saving.gt(0)
                            ).sum()
                        )
                        if rate == "Spot"
                        else 0
                    ),
                )
            )
        return out

    def shipments(
        self,
        filters=None,
        page=1,
        page_size=15,
        sort_by="potential_saving",
        descending=True,
    ):
        df = self.filtered(filters).sort_values(
            [sort_by, "shipment_id"], ascending=[not descending, True], kind="stable"
        )
        return dict(
            rows=records(df.iloc[(page - 1) * page_size : page * page_size]),
            total=len(df),
            page=page,
            page_size=page_size,
        )

    def get_top_saving_shipments(self, filters=None, limit=10):
        return self.shipments(filters, page_size=limit)["rows"]

    def get_shipment_analysis(self, sid):
        found = self.df[self.df.shipment_id.eq(sid)]
        if found.empty:
            return None
        row = found.iloc[0]
        evaluated = evaluate_options(
            self.loader.options[self.loader.options.shipment_id.eq(sid)], row
        )
        recommendation = evaluated[evaluated.option_id.eq(row.recommended_option_id)]
        explanation = (
            f"{row.recommended_carrier} was recommended because it meets availability, capacity and SLA requirements and has the lowest total landed cost among {int(row.feasible_count)} feasible candidates. Ties use earlier departure, then carrier name, then option ID."
            if row.feasible_count
            else "No feasible alternative exists. Historical cost and decision are retained; no saving is claimed."
        )
        return dict(
            shipment=records(found)[0],
            recommended_option=(
                records(recommendation)[0] if len(recommendation) else None
            ),
            candidates=records(evaluated.sort_values("total_landed_cost")),
            explanation=explanation,
        )

    def metadata(self):
        df = self.df
        return dict(
            origins=sorted(df.origin.unique().tolist()),
            destinations=sorted(df.destination.unique().tolist()),
            lanes=sorted(df.lane.unique().tolist()),
            carriers=sorted(set(df.actual_carrier) | set(df.recommended_carrier)),
            rate_types=["Contract", "Spot", "Owned"],
            data_scope=self.scope(df),
            quality=self.loader.quality,
        )

    def apply_filters(self, filters):
        return self.get_overall_summary(filters)
