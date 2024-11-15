# tests/conftest.py
import io
import pytest
from pathlib import Path
import sys
from typing import Generator
import pandas as pd
import asyncio
from fastapi.testclient import TestClient

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.settings import Settings
from src.api import app
from src.services.optimization_service import OptimizationService
from src.services.geocoding_service import GeocodingService


@pytest.fixture
def test_data_dir() -> Path:
    return Path(__file__).parent / "data"


@pytest.fixture
def settings() -> Settings:
    return Settings(environment="test", debug=True, max_vehicles=10, max_pallets=26)


@pytest.fixture
def test_client() -> Generator:
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_excel_data() -> bytes:
    df = pd.DataFrame(
        {
            "Shipment ID": ["SHP001", "SHP002"],
            "Origin City": ["Chicago", "Detroit"],
            "Origin State": ["IL", "MI"],
            "Destination City": ["Milwaukee", "Cleveland"],
            "Destination State": ["WI", "OH"],
            "Pallet Count": [10, 15],
        }
    )
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False)
    return excel_buffer.getvalue()
