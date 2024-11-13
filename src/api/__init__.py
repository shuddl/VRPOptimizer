# src/api/__init__.py
from fastapi import FastAPI
from .routes import router as api_router
from .schemas import (
    ShipmentSchema,
    RouteSchema,
    SolutionSchema,
    OptimizationRequest,
    OptimizationResponse
)

app = FastAPI(title="VRP Optimizer API")
app.include_router(api_router)

__all__ = [
    'app',
    'ShipmentSchema',
    'RouteSchema',
    'SolutionSchema',
    'OptimizationRequest',
    'OptimizationResponse'
]