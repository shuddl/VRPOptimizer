from fastapi import FastAPI
from src.api.routes import router as api_router
from src.services.optimization_service import OptimizationService
from src.services.data_service import DataService
from src.services.geocoding_service import GeocodingService
from src.services.visualization_service import VisualizationService
from src.core.settings import Settings
from src.database.database import DatabaseConnection
from src.monitoring.monitoring import MonitoringSystem
from src.services.business_intelligence_service import BusinessIntelligenceService

__all__ = [
    "Settings",
    "DatabaseConnection",
    "DataService",
    "GeocodingService",
    "OptimizationService",
    "VisualizationService",
    "BusinessIntelligenceService",
    "MonitoringSystem",
]


app = FastAPI(title="VRP Optimizer API")
app.include_router(api_router)

__all__ = ["app"]


async def initialize_services(settings: Settings, database: DatabaseConnection):
    """Initialize all required services with database connection."""
    data_service = DataService(settings, database)
    geocoding_service = GeocodingService(settings, database)
    optimization_service = OptimizationService(settings, database)
    visualization_service = VisualizationService(settings)
    monitoring = MonitoringSystem(settings)

    return (
        data_service,
        geocoding_service,
        optimization_service,
        visualization_service,
        monitoring,
    )
