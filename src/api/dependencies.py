from fastapi import Depends
from src.services.optimization_service import OptimizationService
from src.services.data_service import DataService
from src.services.geocoding_service import GeocodingService
from src.services.visualization_service import VisualizationService
from src.core.settings import Settings
from src.monitoring.monitoring import MonitoringSystem


def get_settings() -> Settings:
    return Settings()


def get_monitoring_system(
    settings: Settings = Depends(get_settings),
) -> MonitoringSystem:
    return MonitoringSystem(settings)


def get_optimization_service(
    settings: Settings = Depends(get_settings),
    monitoring: MonitoringSystem = Depends(get_monitoring_system),
) -> OptimizationService:
    return OptimizationService(settings, monitoring)


def get_data_service(
    settings: Settings = Depends(get_settings),
    monitoring: MonitoringSystem = Depends(get_monitoring_system),
) -> DataService:
    return DataService(settings, monitoring)


def get_geocoding_service(
    settings: Settings = Depends(get_settings),
    monitoring: MonitoringSystem = Depends(get_monitoring_system),
) -> GeocodingService:
    return GeocodingService(settings, monitoring)


def get_visualization_service(
    settings: Settings = Depends(get_settings),
) -> VisualizationService:
    return VisualizationService(settings)
