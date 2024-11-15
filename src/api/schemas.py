from pydantic import BaseModel, Field
from typing import List, Optional, Tuple
from datetime import datetime


class LocationSchema(BaseModel):
    city: str
    state: str
    lat: Optional[float] = None
    lng: Optional[float] = None


class ShipmentSchema(BaseModel):
    id: str
    origin: LocationSchema
    destination: LocationSchema
    pallet_count: int = Field(..., gt=0, le=26)
    volume: Optional[float] = None
    weight: Optional[float] = None


class RouteSchema(BaseModel):
    id: str
    stops: List[Tuple[str, ShipmentSchema]]
    total_distance: float
    total_pallets: int
    vehicle_id: str


class SolutionSchema(BaseModel):
    routes: List[RouteSchema]
    total_distance: float
    total_cost: float
    unassigned_shipments: List[ShipmentSchema]


class OptimizationRequest(BaseModel):
    max_vehicles: Optional[int] = 10
    max_distance: Optional[float] = 800.0
    time_limit: Optional[int] = 30


class OptimizationResponse(BaseModel):
    success: bool
    solution: Optional[SolutionSchema] = None
    error: Optional[str] = None
