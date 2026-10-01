from fastapi import APIRouter, Request
from app.models.analytics import ChatRequest, AIResponse

router = APIRouter(prefix="/api/ai", tags=["AI"])


@router.post("/chat", response_model=AIResponse)
def chat(payload: ChatRequest, request: Request):
    return request.app.state.ai.chat(payload)
