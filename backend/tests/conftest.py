import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.data_loader import DataLoader
from app.services.analytics_service import AnalyticsService
from app.services.ai_service import AIService


@pytest.fixture(scope="session")
def analytics():
    return AnalyticsService(DataLoader())


@pytest.fixture(scope="session")
def ai(analytics):
    return AIService(analytics)


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as client:
        yield client
