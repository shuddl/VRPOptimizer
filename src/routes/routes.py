import logging
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from src.services.optimization_service import OptimizationService
from src.services.data_service import DataService
from src.core.models import Solution
from src.api.schemas import OptimizationRequest, OptimizationResponse
from src.api.dependencies import get_optimization_service, get_data_service
from typing import List, Optional, Any
import httpx

router = APIRouter()


@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_routes(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    webhook_url: str = None,
    optimization_service: OptimizationService = Depends(get_optimization_service),
    data_service: DataService = Depends(get_data_service),
):
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, detail="File size exceeds maximum allowed (10 MB)"
        )

    if file.content_type not in (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    ):
        raise HTTPException(
            status_code=400, detail="Invalid file type. Only Excel files are allowed."
        )

    import aiofiles

    content = b""
    async with aiofiles.open(file.file, "rb") as f:
        while chunk := await f.read(1024):
            content += chunk
    success, errors, shipments = await data_service.process_excel(content)
    if not success:
        raise HTTPException(status_code=400, detail=errors)

    valid, validation_errors = await data_service.validate_data(shipments)
    if not valid:
        raise HTTPException(status_code=400, detail=validation_errors)

        background_tasks.add_task(
            await send_webhook_notification, webhook_url, solution
        )
    if not Solution:
        raise HTTPException(status_code=500, detail="Optimization failed")

    if webhook_url:
        background_tasks.add_task(send_webhook_notification, webhook_url, Solution)

    return OptimizationResponse(solution=Solution)


@router.post("/optimize/json", response_model=OptimizationResponse)
async def optimize_routes_json(
    background_tasks: BackgroundTasks,  # Non-default argument moved first
    file: UploadFile = File(...),  # Default argument
    webhook_url: Optional[str] = None,  # Default argument
    optimization_service: OptimizationService = Depends(
        get_optimization_service
    ),  # Default argument
    data_service: DataService = Depends(get_data_service),  # Default argument
):
    """
    Optimize routes based on uploaded JSON data.

    - **background_tasks**: Tasks to run in the background.
    - **file**: The uploaded shipment data file.
    - **webhook_url**: Optional webhook URL for notifications.
    - **optimization_service**: Service to handle optimization logic.
    - **data_service**: Service to handle data processing.
    """
    try:
        # Process the uploaded file
        shipments = await data_service.process_file(file)

        # Perform optimization
        solution = optimization_service.optimize(shipments)

        # Optionally, send a webhook notification in the background
        if webhook_url:
            background_tasks.add_task(send_webhook, webhook_url, solution)

        return OptimizationResponse(success=True, solution=solution)
    except Exception as e:
        return OptimizationResponse(success=False, error=str(e))


async def send_webhook(url: str, solution: Any):
    # Implementation for sending a webhook notification
    pass


@router.post("/optimize/csv", response_model=OptimizationResponse)
async def optimize_routes_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    webhook_url: str = None,
    optimization_service: OptimizationService = Depends(get_optimization_service),
    data_service: DataService = Depends(get_data_service),
):
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    if file.spool_max_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, detail="File size exceeds maximum allowed (10 MB)"
        )

    if file.content_type != "text/csv":
        raise HTTPException(
            status_code=400, detail="Invalid file type. Only CSV files are allowed."
        )

    content = await file.read()
    success, errors, shipments = await data_service.process_csv(content)
    if not success:
        raise HTTPException(status_code=400, detail=errors)

    valid, validation_errors = await data_service.validate_data(shipments)
    if not valid:
        raise HTTPException(status_code=400, detail=validation_errors)

    solution = await optimization_service.optimize(shipments)
    if not solution:
        raise HTTPException(status_code=500, detail="Optimization failed")

    if webhook_url:
        background_tasks.add_task(send_webhook_notification, webhook_url, solution)

    return OptimizationResponse(solution=solution)


@router.post("/your-route", response_model=OptimizationResponse)
async def your_function(
    background_tasks: BackgroundTasks,  # Moved first (non-default)
    file: UploadFile = File(...),  # Default argument
    webhook_url: Optional[str] = None,  # Default argument
    optimization_service: OptimizationService = Depends(get_optimization_service),
    data_service: DataService = Depends(get_data_service),
):
    """
    Optimize routes based on uploaded data.

    - **background_tasks**: Tasks to run in the background.
    - **file**: The uploaded shipment data file.
    - **webhook_url**: Optional webhook URL for notifications.
    - **optimization_service**: Service to handle optimization logic.
    - **data_service**: Service to handle data processing.
    """
    try:
        # Process the uploaded file
        shipments = await data_service.process_file(file)

        # Perform optimization
        solution = optimization_service.optimize(shipments)

        # Optionally, send a webhook notification in the background
        if webhook_url:
            background_tasks.add_task(send_webhook, webhook_url, solution)

        return OptimizationResponse(success=True, solution=solution)
    except Exception as e:
        return OptimizationResponse(success=False, error=str(e))


async def send_webhook_notification(webhook_url: str, solution: Solution):
    """
    Send webhook notification with optimization results.

    Args:
        webhook_url (str): The URL to send the webhook notification to.
        solution (Solution): The optimization solution to include in the notification.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=solution.to_dict())
            response.raise_for_status()
    except Exception as e:
        logging.error(f"Failed to send webhook notification: {str(e)}")
