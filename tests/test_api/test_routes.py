# tests/test_api/test_routes.py
import pytest
from fastapi.testclient import TestClient
from src.api.routes import app


def test_health_check(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_optimization_endpoint(test_client, sample_excel_data):
    files = {
        "file": (
            "test.xlsx",
            sample_excel_data,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    response = test_client.post("/optimize", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "solution" in data
    assert len(data["solution"]["routes"]) > 0


# tests/test_ui/test_components.py
import pytest
import streamlit as st
from src.core.models import Solution, Route, Shipment
from ui.components import RouteMap, MetricsPanel, ShipmentTable


@pytest.fixture
def sample_solution():
    # Create test solution with routes
    return Solution(
        routes=[
            Route(
                id="R001",
                stops=[("pickup", test_shipments[0]), ("delivery", test_shipments[0])],
                total_distance=237.1,
                total_pallets=10,
            )
        ],
        total_distance=237.1,
        total_cost=592.75,
        unassigned_shipments=[],
    )


def test_route_map(sample_solution):
    route_map = RouteMap()
    # Test map rendering
    route_map.render(sample_solution)
    # Assert Streamlit components were called
    assert len(st.components.v1._elements) > 0


def test_metrics_panel(sample_solution):
    metrics = MetricsPanel()
    metrics.render(sample_solution)
    # Verify metrics are displayed
    assert len(st.components.v1._elements) > 0
