from fastapi import APIRouter, Request
from app.models.analytics import QueryRequest, AIResponse

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.post("/query", response_model=AIResponse)
def query(payload: QueryRequest, request: Request):
    return request.app.state.ai.execute(
        payload.intent, payload.filters, {**payload.entities, "limit": payload.limit}
    )
