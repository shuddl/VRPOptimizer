# src/api/dependencies.py
from fastapi import Depends
from ..services import (
    OptimizationService,
    DataService,
    GeocodingService,
    VisualizationService
)
from ..core.config import Settings
from ..monitoring import MonitoringSystem

def get_settings():
    return Settings()

def get_monitoring_system(settings: Settings = Depends(get_settings)):
    return MonitoringSystem(settings)

def get_optimization_service(
    settings: Settings = Depends(get_settings),
    monitoring: MonitoringSystem = Depends(get_monitoring_system)
):
    return OptimizationService(settings, monitoring)

def get_data_service(
    settings: Settings = Depends(get_settings),
    monitoring: MonitoringSystem = Depends(get_monitoring_system)
):
    return DataService(settings, monitoring)

def get_geocoding_service(
    settings: Settings = Depends(get_settings),
    monitoring: MonitoringSystem = Depends(get_monitoring_system)
):
    return GeocodingService(settings, monitoring)

def get_visualization_service(
    settings: Settings = Depends(get_settings)
):
    return VisualizationService(settings)