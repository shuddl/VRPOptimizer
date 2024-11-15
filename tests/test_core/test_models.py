# tests/test_core/test_models.py
import pytest
from pydantic import ValidationError
from src.core.models import Location, Shipment, Route, Solution


def test_location_creation():
    """Test Location model validation."""
    location = Location(city="Chicago", state="IL")
    assert location.city == "Chicago"
    assert location.state == "IL"
    assert location.lat is None
    assert location.lng is None

    with pytest.raises(ValidationError):
        Location(city="", state="IL")


def test_shipment_validation():
    """Test Shipment model constraints."""
    origin = Location(city="Chicago", state="IL")
    destination = Location(city="Detroit", state="MI")

    # Valid shipment
    shipment = Shipment(
        id="SHP001", origin=origin, destination=destination, pallet_count=10
    )
    assert shipment.pallet_count == 10

    # Invalid pallet count
    with pytest.raises(ValidationError):
        Shipment(
            id="SHP002",
            origin=origin,
            destination=destination,
            pallet_count=30,  # Exceeds maximum
        )
