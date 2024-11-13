# src/api/routes.py
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import List
from .schemas import OptimizationResponse, OptimizationRequest
from ..services import OptimizationService, DataService
from ..core.exceptions import VRPOptimizerError

router = APIRouter()

@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_routes(
    file: UploadFile = File(...),
    optimization_service: OptimizationService = Depends(),
    data_service: DataService = Depends()
):
    try:
        content = await file.read()
        shipments = await data_service.process_excel(content)
        solution = await optimization_service.optimize(shipments)
        return OptimizationResponse(
            success=True,
            solution=solution
        )
    except VRPOptimizerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    return {"status": "healthy"}
