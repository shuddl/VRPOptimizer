# tests/test_services/test_visualization_service.py
import pytest
from src.services.visualization_service import VisualizationService
from src.core.models import Solution, Route, Shipment


@pytest.fixture
def sample_solution(test_shipments):
    """Create sample solution for visualization testing."""
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


@pytest.mark.asyncio
async def test_create_route_map(settings, sample_solution):
    """Test route map generation."""
    service = VisualizationService(settings)
    map_data = await service.create_route_map(sample_solution)

    assert map_data is not None
    assert "html" in map_data
    assert "leaflet" in map_data["html"].lower()


@pytest.mark.asyncio
async def test_create_timeline(settings, sample_solution):
    """Test timeline visualization."""
    service = VisualizationService(settings)
    timeline = await service.create_timeline(sample_solution)

    assert timeline is not None
    assert "data" in timeline
    assert len(timeline["data"]) > 0


@pytest.mark.asyncio
async def test_create_analytics_dashboard(settings, sample_solution):
    """Test analytics dashboard generation."""
    service = VisualizationService(settings)
    dashboard = await service.create_analytics_dashboard(sample_solution)

    assert dashboard is not None
    assert "metrics" in dashboard
    assert "charts" in dashboard
