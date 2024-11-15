# src/database/models.py

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class GeocodingCache(Base):
    """Cache for geocoding results."""

    __tablename__ = "geocoding_cache"

    id = Column(Integer, primary_key=True)
    location_key = Column(String, unique=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class OptimizationResult(Base):
    """Store optimization results."""

    __tablename__ = "optimization_results"

    id = Column(Integer, primary_key=True)
    result_data = Column(Text, nullable=False)  # JSON data
    total_distance = Column(Float)
    total_cost = Column(Float)
    vehicle_count = Column(Integer)
    created_at = Column(DateTime, default=func.now())
    settings_used = Column(Text)  # JSON of settings used


class APIUsage(Base):
    """Track API usage for rate limiting."""

    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True)
    api_name = Column(String, index=True)  # e.g., 'google_geocoding'
    calls_made = Column(Integer, default=0)
    last_call = Column(DateTime)
    daily_limit = Column(Integer)
    reset_at = Column(DateTime)


class TimeStampMixin:
    """Mixin for adding created_at and updated_at timestamps."""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ShipmentStatus(enum.Enum):
    """Enumeration for shipment statuses."""
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    FAILED = "failed"


class OptimizationStatus(enum.Enum):
    """Enumeration for optimization run statuses."""
    SUCCESSFUL = "successful"
    PARTIAL = "partial"
    FAILED = "failed"


class HistoricalOptimization(Base, TimeStampMixin):
    """Model for storing historical optimization runs."""
    __tablename__ = 'historical_optimizations'

    id = Column(Integer, primary_key=True)
    status = Column(Enum(OptimizationStatus), nullable=False)
    total_distance = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    total_duration = Column(Float, nullable=False)
    vehicle_count = Column(Integer, nullable=False)
    total_pallets = Column(Integer, nullable=False)
    average_utilization = Column(Float, nullable=False)
    co2_emissions = Column(Float)
    fuel_consumption = Column(Float)
    optimization_parameters = Column(JSON)
    computation_time = Column(Float)
    error_message = Column(String)
    
    # Relationships
    routes = relationship("HistoricalRoute", back_populates="optimization")
    metrics = relationship("PerformanceMetrics", back_populates="optimization")


class HistoricalRoute(Base, TimeStampMixin):
    """Model for storing historical route data."""
    __tablename__ = 'historical_routes'

    id = Column(Integer, primary_key=True)
    optimization_id = Column(Integer, ForeignKey('historical_optimizations.id'))
    vehicle_id = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    total_distance = Column(Float, nullable=False)
    total_duration = Column(Float, nullable=False)
    total_pallets = Column(Integer, nullable=False)
    stop_count = Column(Integer, nullable=False)
    utilization = Column(Float, nullable=False)
    route_sequence = Column(JSON)  # Stores the sequence of stops
    actual_route = Column(JSON)  # Stores actual route taken if available
    
    # Relationships
    optimization = relationship("HistoricalOptimization", back_populates="routes")
    stops = relationship("RouteStop", back_populates="route")
    metrics = relationship("RouteMetrics", back_populates="route")


class RouteStop(Base, TimeStampMixin):
    """Model for storing individual stop data within routes."""
    __tablename__ = 'route_stops'

    id = Column(Integer, primary_key=True)
    route_id = Column(Integer, ForeignKey('historical_routes.id'))
    sequence_number = Column(Integer, nullable=False)
    location_id = Column(Integer, ForeignKey('locations.id'))
    arrival_time = Column(DateTime)
    departure_time = Column(DateTime)
    pallets = Column(Integer, nullable=False)
    service_time = Column(Float)
    status = Column(Enum(ShipmentStatus), nullable=False)
    delay = Column(Float)  # Deviation from planned time
    
    # Relationships
    route = relationship("HistoricalRoute", back_populates="stops")
    location = relationship("Location")


class Location(Base):
    """Model for storing location data."""
    __tablename__ = 'locations'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    postal_code = Column(String)
    country = Column(String, default='USA')
    latitude = Column(Float)
    longitude = Column(Float)
    zone = Column(String)  # For zone-based analysis
    location_type = Column(String)  # warehouse, customer, depot, etc.


class PerformanceMetrics(Base, TimeStampMixin):
    """Model for storing overall performance metrics."""
    __tablename__ = 'performance_metrics'

    id = Column(Integer, primary_key=True)
    optimization_id = Column(Integer, ForeignKey('historical_optimizations.id'))
    on_time_delivery_rate = Column(Float)
    perfect_delivery_rate = Column(Float)
    average_delay = Column(Float)
    cost_per_mile = Column(Float)
    cost_per_delivery = Column(Float)
    fuel_efficiency = Column(Float)
    carbon_footprint = Column(Float)
    vehicle_utilization = Column(Float)
    service_level = Column(Float)
    customer_satisfaction = Column(Float)
    
    # Relationships
    optimization = relationship("HistoricalOptimization", back_populates="metrics")


class RouteMetrics(Base, TimeStampMixin):
    """Model for storing route-specific metrics."""
    __tablename__ = 'route_metrics'

    id = Column(Integer, primary_key=True)
    route_id = Column(Integer, ForeignKey('historical_routes.id'))
    fuel_consumption = Column(Float)
    idle_time = Column(Float)
    service_time_adherence = Column(Float)
    delivery_accuracy = Column(Float)
    vehicle_utilization = Column(Float)
    cost_efficiency = Column(Float)
    environmental_impact = Column(Float)
    
    # Relationships
    route = relationship("HistoricalRoute", back_populates="metrics")


class DemandHistory(Base, TimeStampMixin):
    """Model for storing historical demand data for forecasting."""
    __tablename__ = 'demand_history'

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    location_id = Column(Integer, ForeignKey('locations.id'))
    actual_demand = Column(Float, nullable=False)
    forecasted_demand = Column(Float)
    forecast_error = Column(Float)
    seasonality_factor = Column(Float)
    trend_factor = Column(Float)
    special_events = Column(JSON)  # Store any special events affecting demand
    
    # Relationships
    location = relationship("Location")


class WeatherData(Base, TimeStampMixin):
    """Model for storing weather data that might affect operations."""
    __tablename__ = 'weather_data'

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    location_id = Column(Integer, ForeignKey('locations.id'))
    temperature = Column(Float)
    precipitation = Column(Float)
    wind_speed = Column(Float)
    weather_condition = Column(String)
    severe_weather_alert = Column(Boolean, default=False)
    impact_level = Column(Integer)  # 1-5 scale of impact on operations
    
    # Relationships
    location = relationship("Location")
