from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from src.services.optimization_service import OptimizationService
from src.services.data_service import DataService
from src.models.optimization_response import OptimizationResponse
from src.dependencies import get_optimization_service, get_data_service
from typing import List
import requests

router = APIRouter()

@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_routes(
    file: UploadFile = File(...),
    optimization_service: OptimizationService = Depends(get_optimization_service),
    data_service: DataService = Depends(get_data_service),
    background_tasks: BackgroundTasks,
    webhook_url: str = None
):
    # Validate file size
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    if file.spool_max_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed (10 MB)")

    # Validate content type
    if file.content_type not in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only Excel files are allowed.")

    # Process file
    content = await file.read()
    success, errors, shipments = await data_service.process_excel(content)
    if not success:
        raise HTTPException(status_code=400, detail=errors)

    # Validate data
    valid, validation_errors = await data_service.validate_data(shipments)
    if not valid:
        raise HTTPException(status_code=400, detail=validation_errors)

    # Optimize routes
    solution = await optimization_service.optimize(shipments)
    if not solution:
        raise HTTPException(status_code=500, detail="Optimization failed")

    # Send webhook notification if URL is provided
    if webhook_url:
        background_tasks.add_task(send_webhook_notification, webhook_url, solution)

    return OptimizationResponse(solution=solution)

@router.post("/optimize/json", response_model=OptimizationResponse)
async def optimize_routes_json(
    file: UploadFile = File(...),
    optimization_service: OptimizationService = Depends(get_optimization_service),
    data_service: DataService = Depends(get_data_service),
    background_tasks: BackgroundTasks,
    webhook_url: str = None
):
    # Validate file size
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    if file.spool_max_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed (10 MB)")

    # Validate content type
    if file.content_type != "application/json":
        raise HTTPException(status_code=400, detail="Invalid file type. Only JSON files are allowed.")

    # Process file
    content = await file.read()
    success, errors, shipments = await data_service.process_json(content)
    if not success:
        raise HTTPException(status_code=400, detail=errors)

    # Validate data
    valid, validation_errors = await data_service.validate_data(shipments)
    if not valid:
        raise HTTPException(status_code=400, detail=validation_errors)

    # Optimize routes
    solution = await optimization_service.optimize(shipments)
    if not solution:
        raise HTTPException(status_code=500, detail="Optimization failed")

    # Send webhook notification if URL is provided
    if webhook_url:
        background_tasks.add_task(send_webhook_notification, webhook_url, solution)

    return OptimizationResponse(solution=solution)

@router.post("/optimize/csv", response_model=OptimizationResponse)
async def optimize_routes_csv(
    file: UploadFile = File(...),
    optimization_service: OptimizationService = Depends(get_optimization_service),
    data_service: DataService = Depends(get_data_service),
    background_tasks: BackgroundTasks,
    webhook_url: str = None
):
    # Validate file size
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    if file.spool_max_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed (10 MB)")

    # Validate content type
    if file.content_type != "text/csv":
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV files are allowed.")

    # Process file
    content = await file.read()
    success, errors, shipments = await data_service.process_csv(content)
    if not success:
        raise HTTPException(status_code=400, detail=errors)

    # Validate data
    valid, validation_errors = await data_service.validate_data(shipments)
    if not valid:
        raise HTTPException(status_code=400, detail=validation_errors)

    # Optimize routes
    solution = await optimization_service.optimize(shipments)
    if not solution:
        raise HTTPException(status_code=500, detail="Optimization failed")

    # Send webhook notification if URL is provided
    if webhook_url:
        background_tasks.add_task(send_webhook_notification, webhook_url, solution)

    return OptimizationResponse(solution=solution)

async def send_webhook_notification(webhook_url: str, solution: Solution):
    """Send webhook notification with optimization results."""
    try:
        response = requests.post(webhook_url, json=solution.to_dict())
        response.raise_for_status()
    except Exception as e:
        logging.error(f"Failed to send webhook notification: {str(e)}")