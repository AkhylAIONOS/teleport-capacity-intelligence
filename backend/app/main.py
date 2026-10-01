from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import CORS_ORIGINS, DATA_MODE
from app.services.data_loader import DataLoader
from app.services.analytics_service import AnalyticsService
from app.services.ai_service import AIService
from app.api import dashboard, shipments, analytics, ai


@asynccontextmanager
async def lifespan(app):
    app.state.analytics = AnalyticsService(DataLoader())
    app.state.ai = AIService(app.state.analytics)
    yield


app = FastAPI(
    title="Teleport Capacity Intelligence", version="0.1.0", lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
for router in [dashboard.router, shipments.router, analytics.router, ai.router]:
    app.include_router(router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "data_mode": DATA_MODE,
        "usable_shipments": len(app.state.analytics.df),
    }
