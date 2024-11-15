# models.py

from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


@dataclass
class Location:
    city: str
    state: str
    lat: Optional[float] = None
    lng: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            "city": self.city,
            "state": self.state,
            "lat": self.lat,
            "lng": self.lng,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Location":
        return cls(
            city=data["city"],
            state=data["state"],
            lat=data.get("lat"),
            lng=data.get("lng"),
        )


@dataclass
class Shipment:
    id: str
    origin: Location
    destination: Location
    pallet_count: int
    volume: Optional[float] = None
    weight: Optional[float] = None
    pickup_time: Optional[datetime] = None
    delivery_time: Optional[datetime] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "origin": self.origin.to_dict(),
            "destination": self.destination.to_dict(),
            "pallet_count": self.pallet_count,
            "volume": self.volume,
            "weight": self.weight,
            "pickup_time": self.pickup_time.isoformat() if self.pickup_time else None,
            "delivery_time": self.delivery_time.isoformat()
            if self.delivery_time
            else None,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Shipment":
        return cls(
            id=data["id"],
            origin=Location.from_dict(data["origin"]),
            destination=Location.from_dict(data["destination"]),
            pallet_count=data["pallet_count"],
            volume=data.get("volume"),
            weight=data.get("weight"),
            pickup_time=datetime.fromisoformat(data["pickup_time"])
            if data.get("pickup_time")
            else None,
            delivery_time=datetime.fromisoformat(data["delivery_time"])
            if data.get("delivery_time")
            else None,
        )


@dataclass
class Route:
    id: str
    stops: List[Tuple[str, Shipment]]  # (type: 'pickup'|'delivery', shipment)
    total_distance: float
    total_pallets: int
    vehicle_id: str

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "stops": [
                (stop_type, shipment.to_dict()) for stop_type, shipment in self.stops
            ],
            "total_distance": self.total_distance,
            "total_pallets": self.total_pallets,
            "vehicle_id": self.vehicle_id,
        }


@dataclass
class Solution:
    routes: List[Route]
    total_distance: float
    total_cost: float
    unassigned_shipments: List[Shipment]

    def to_dict(self) -> Dict:
        return {
            "routes": [route.to_dict() for route in self.routes],
            "total_distance": self.total_distance,
            "total_cost": self.total_cost,
            "unassigned_shipments": [s.to_dict() for s in self.unassigned_shipments],
        }


class CacheEntry(Base):
    __tablename__ = "geocoding_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    location_key = Column(String, unique=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
