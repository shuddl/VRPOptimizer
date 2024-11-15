# tests/test_services/test_optimization.py
import pytest
from src.services.optimization_service import OptimizationService
from src.core.models import Location, Shipment


@pytest.fixture
def test_shipments():
    return [
        Shipment(
            id="SHP001",
            origin=Location(city="Chicago", state="IL", lat=41.8781, lng=-87.6298),
            destination=Location(city="Detroit", state="MI", lat=42.3314, lng=-83.0458),
            pallet_count=10,
        ),
        Shipment(
            id="SHP002",
            origin=Location(city="Indianapolis", state="IN", lat=39.7684, lng=-86.1581),
            destination=Location(
                city="Columbus", state="OH", lat=39.9612, lng=-82.9988
            ),
            pallet_count=8,
        ),
    ]


@pytest.mark.asyncio
async def test_optimization(settings, test_shipments):
    service = OptimizationService(settings)
    solution = await service.optimize(test_shipments)

    assert solution is not None
    assert len(solution.routes) > 0
    assert solution.total_distance > 0
    assert len(solution.unassigned_shipments) == 0


def test_lifo_constraints(settings, test_shipments):
    service = OptimizationService(settings)
    solution = await service.optimize(test_shipments)

    # Verify LIFO for each route
    for route in solution.routes:
        active_shipments = []
        for stop_type, shipment in route.stops:
            if stop_type == "pickup":
                active_shipments.append(shipment.id)
            else:
                assert active_shipments.pop() == shipment.id
