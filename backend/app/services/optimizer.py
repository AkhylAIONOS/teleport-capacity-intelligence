import pandas as pd
import math


def evaluate_options(options, shipment):
    rows = options.copy()
    if rows.empty:
        rows["feasible"] = pd.Series(dtype=bool)
        rows["reason"] = pd.Series(dtype=str)
        return rows

    def reasons(o):
        reasons = []
        valid = o.get("data_valid", True)
        if (
            not valid
            or not math.isfinite(float(o.total_landed_cost))
            or o.total_landed_cost < 0
        ):
            reasons.append("Invalid data or cost")
        if not o.available:
            reasons.append("Unavailable")
        if (
            pd.isna(o.capacity_available_kg)
            or pd.isna(o.required_capacity_kg)
            or o.required_capacity_kg <= 0
            or o.capacity_available_kg < max(o.required_capacity_kg, shipment.weight_kg)
        ):
            reasons.append("Insufficient capacity")
        if not o.sla_feasible:
            reasons.append("SLA infeasible")
        if pd.isna(o.departure_date) or o.departure_date < shipment.shipment_date:
            reasons.append("Invalid historical departure")
        return "; ".join(reasons) or "Feasible"

    rows["reason"] = rows.apply(reasons, axis=1)
    rows["feasible"] = rows.reason.eq("Feasible")
    return rows


def optimize_shipment(shipment, options):
    evaluated = evaluate_options(options, shipment)
    feasible = evaluated[evaluated.feasible].sort_values(
        ["total_landed_cost", "departure_date", "carrier", "option_id"], kind="stable"
    )
    rec = feasible.iloc[0] if len(feasible) else None
    cost = (
        float(rec.total_landed_cost) if rec is not None else float(shipment.actual_paid)
    )
    saving = round(max(float(shipment.actual_paid) - cost, 0), 2)
    return dict(
        recommended_option_id=rec.option_id if rec is not None else None,
        recommended_carrier=rec.carrier if rec is not None else shipment.actual_carrier,
        recommended_rate_type=(
            rec.rate_type if rec is not None else shipment.actual_rate_type
        ),
        recommended_departure_date=(
            rec.departure_date if rec is not None else shipment.actual_departure_date
        ),
        optimized_cost=cost,
        potential_saving=saving,
        saving_percent=(
            saving / float(shipment.actual_paid) * 100 if shipment.actual_paid else 0
        ),
        changed_carrier=bool(
            rec is not None and rec.carrier != shipment.actual_carrier
        ),
        changed_rate_type=bool(
            rec is not None and rec.rate_type != shipment.actual_rate_type
        ),
        feasible_count=len(feasible),
        candidate_count=len(evaluated),
        status="OPTIMIZED" if rec is not None else "NO_FEASIBLE_ALTERNATIVE",
    )


def optimize_all(shipments, options):
    groups = {sid: group for sid, group in options.groupby("shipment_id")}
    empty = options.iloc[:0]
    results = [
        optimize_shipment(row, groups.get(row.shipment_id, empty))
        for _, row in shipments.iterrows()
    ]
    names = [
        "recommended_option_id",
        "recommended_carrier",
        "recommended_rate_type",
        "recommended_departure_date",
        "optimized_cost",
        "potential_saving",
        "saving_percent",
        "changed_carrier",
        "changed_rate_type",
        "feasible_count",
        "candidate_count",
        "status",
    ]
    return pd.concat(
        [shipments.reset_index(drop=True), pd.DataFrame(results, columns=names)], axis=1
    )
