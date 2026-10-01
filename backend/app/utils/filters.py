import json
from fastapi import Request, HTTPException
from pydantic import ValidationError
from app.models.analytics import Filters


def apply_filters(df, filters: Filters):
    result = df
    if filters.start_date:
        result = result[result.shipment_date >= str(filters.start_date)]
    if filters.end_date:
        result = result[result.shipment_date <= str(filters.end_date)]
    for key in ["origin", "destination", "lane", "rate_type", "recommended_rate_type"]:
        value = getattr(filters, key)
        if value:
            result = result[
                result["actual_rate_type" if key == "rate_type" else key].str.casefold()
                == value.casefold()
            ]
    for key, col in [
        ("carrier", "actual_carrier"),
        ("recommended_carrier", "recommended_carrier"),
    ]:
        value = getattr(filters, key)
        if value:
            result = result[result[col].str.casefold() == value.casefold()]
    if filters.min_saving:
        result = result[result.potential_saving >= filters.min_saving]
    if filters.shipment_ids is not None:
        result = result[result.shipment_id.isin(filters.shipment_ids)]
    if filters.search:
        mask = (
            result[["shipment_id", "lane", "actual_carrier", "recommended_carrier"]]
            .fillna("")
            .apply(lambda c: c.str.contains(filters.search, case=False, regex=False))
            .any(axis=1)
        )
        result = result[mask]
    return result.copy()


def parse_filters(request: Request):
    values = {
        key: value
        for key, value in request.query_params.items()
        if key in Filters.model_fields
    }
    try:
        if "shipment_ids" in values:
            values["shipment_ids"] = json.loads(values["shipment_ids"])
        return Filters.model_validate(values)
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
