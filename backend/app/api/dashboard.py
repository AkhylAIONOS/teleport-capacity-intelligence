from fastapi import APIRouter, Depends, Request
from app.models.analytics import Filters
from app.utils.filters import parse_filters

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(request: Request, filters: Filters = Depends(parse_filters)):
    return request.app.state.analytics.get_overall_summary(filters)


@router.get("/trends")
def trends(
    request: Request,
    cumulative: bool = False,
    filters: Filters = Depends(parse_filters),
):
    return request.app.state.analytics.get_monthly_trend(filters, cumulative)


@router.get("/lanes")
def lanes(request: Request, filters: Filters = Depends(parse_filters)):
    return request.app.state.analytics.get_top_lanes(filters)


@router.get("/carriers")
def carriers(request: Request, filters: Filters = Depends(parse_filters)):
    return request.app.state.analytics.get_carrier_analysis(filters)


@router.get("/rate-mix")
def rates(request: Request, filters: Filters = Depends(parse_filters)):
    return request.app.state.analytics.get_rate_mix(filters)


@router.get("/metadata")
def metadata(request: Request):
    return request.app.state.analytics.metadata()


@router.get("/quality")
def quality(request: Request):
    return request.app.state.analytics.loader.quality


@router.get("/lane-heatmap")
def lane_heatmap(request: Request, filters: Filters = Depends(parse_filters)):
    return request.app.state.analytics.get_lane_heatmap(filters)
