from fastapi import APIRouter, Depends, Request, Query, HTTPException
from app.models.analytics import Filters
from app.utils.filters import parse_filters

router = APIRouter(prefix="/api/shipments", tags=["shipments"])
SORTS = {
    "potential_saving",
    "saving_percent",
    "actual_paid",
    "optimized_cost",
    "shipment_date",
    "shipment_id",
    "lane",
    "actual_carrier",
    "recommended_carrier",
    "actual_rate_type",
    "recommended_rate_type",
}


@router.get("")
def list_shipments(
    request: Request,
    filters: Filters = Depends(parse_filters),
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
    sort_by: str = "potential_saving",
    descending: bool = True,
):
    if sort_by not in SORTS:
        raise HTTPException(422, "Unsupported sort column")
    return request.app.state.analytics.shipments(
        filters, page, page_size, sort_by, descending
    )


@router.get("/{shipment_id}")
def detail(shipment_id: str, request: Request):
    result = request.app.state.analytics.get_shipment_analysis(shipment_id)
    if result is None:
        raise HTTPException(404, "Shipment not found in usable dataset")
    return result
