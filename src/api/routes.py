from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import List
import src.database.database as database
from src.api.schemas import OptimizationResponse, OptimizationRequest
from src.services.optimization_service import OptimizationService
from src.services.data_service import DataService
from src.core.exceptions import VRPOptimizerError
from src.api.dependencies import get_optimization_service, get_data_service
import logging
from sqlalchemy.sql import text

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_routes(
    file: UploadFile = File(...),
    optimization_service: OptimizationService = Depends(get_optimization_service),
    data_service: DataService = Depends(get_data_service),
):
    try:
        # Read file content.
        content = await file.read()

        # Process shipments from file.
        shipments = await data_service.process_excel(content)

        # Perform optimization.
        solution = optimization_service.optimize(shipments)

        return OptimizationResponse(success=True, solution=solution)
    except Exception as error:
        logger.error(f"Unexpected error: {str(error)}")
        raise HTTPException(status_code=500, detail="An internal error occurred.")


@router.get("/health")
async def health_check():
    """Check system health including database connection."""
    try:
        # Test database connection
        async with database.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
