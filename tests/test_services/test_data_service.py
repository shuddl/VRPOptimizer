# tests/test_services/test_data_service.py
import pytest
import pandas as pd
from io import BytesIO
from src.services.data_service import DataService
from src.core.exceptions import DataValidationError

@pytest.fixture
def sample_excel_data():
    """Create sample Excel data for testing."""
    df = pd.DataFrame({
        'Shipment ID': ['SHP001', 'SHP002'],
        'Origin City': ['Chicago', 'Detroit'],
        'Origin State': ['IL', 'MI'],
        'Destination City': ['Milwaukee', 'Cleveland'],
        'Destination State': ['WI', 'OH'],
        'Pallet Count': [10, 15]
    })
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False)
    return excel_buffer.getvalue()

@pytest.fixture
def invalid_excel_data():
    """Create invalid Excel data for testing."""
    df = pd.DataFrame({
        'Shipment ID': ['SHP001'],
        'Origin City': ['Chicago'],
        # Missing required columns
    })
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False)
    return excel_buffer.getvalue()

@pytest.mark.asyncio
async def test_process_excel(settings, sample_excel_data):
    """Test processing valid Excel data."""
    service = DataService(settings)
    result = await service.process_excel(sample_excel_data)
    
    assert result is not None
    assert len(result) == 2
    assert result[0].origin.city == 'Chicago'
    assert result[1].pallet_count == 15

@pytest.mark.asyncio
async def test_invalid_excel(settings, invalid_excel_data):
    """Test processing invalid Excel data."""
    service = DataService(settings)
    with pytest.raises(DataValidationError):
        await service.process_excel(invalid_excel_data)

@pytest.mark.asyncio
async def test_validate_shipment_data(settings, sample_excel_data):
    """Test shipment data validation."""
    service = DataService(settings)
    shipments = await service.process_excel(sample_excel_data)
    validation_result = await service.validate_data(shipments)
    
    assert validation_result.is_valid
    assert not validation_result.errors

@pytest.mark.asyncio
async def test_export_solution(settings, sample_solution):
    """Test solution export functionality."""
    service = DataService(settings)
    excel_data = await service.export_solution(sample_solution, 'excel')
    
    assert excel_data is not None
    # Verify Excel content
    df = pd.read_excel(BytesIO(excel_data))
    assert 'Route ID' in df.columns
    assert len(df) > 0

@pytest.mark.asyncio
async def test_cache_management(settings, sample_excel_data):
    """Test data caching functionality."""
    service = DataService(settings)
    
    # First process
    result1 = await service.process_excel(sample_excel_data)
    
    # Should use cache
    result2 = await service.process_excel(sample_excel_data)
    
    assert result1 == result2
