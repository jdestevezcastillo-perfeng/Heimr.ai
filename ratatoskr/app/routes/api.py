"""Main API endpoints affected by chaos injection."""
import hashlib
from typing import Optional

from fastapi import APIRouter, Body
from pydantic import BaseModel

from app.chaos.state import chaos_state

router = APIRouter()


class WorkRequest(BaseModel):
    """Request body for work endpoints."""
    data: Optional[str] = None
    iterations: Optional[int] = None


class WorkResponse(BaseModel):
    """Response from work endpoints."""
    message: str
    operation: Optional[str] = None
    result: Optional[str] = None
    payload: str


@router.get("/api/work")
async def get_work():
    """Simple GET work endpoint affected by chaos.
    
    Returns:
        Work response with configured payload size
    """
    config = await chaos_state.get_config()
    payload = "x" * config.resources.response_size_bytes
    
    return WorkResponse(
        message="Work completed successfully",
        operation="get",
        payload=payload
    )


@router.post("/api/work")
async def post_work(request: WorkRequest = Body(...)):
    """Simple POST work endpoint affected by chaos.
    
    Args:
        request: Work request body
        
    Returns:
        Work response with configured payload size
    """
    config = await chaos_state.get_config()
    payload = "x" * config.resources.response_size_bytes
    
    # Optionally process the request data
    result = None
    if request.data:
        result = hashlib.sha256(request.data.encode()).hexdigest()[:16]
    
    return WorkResponse(
        message="Work completed successfully",
        operation="post",
        result=result,
        payload=payload
    )


@router.get("/api/work/{operation}")
async def get_work_operation(operation: str):
    """Parameterized GET work endpoint affected by chaos.
    
    Args:
        operation: Operation identifier
        
    Returns:
        Work response with operation info
    """
    config = await chaos_state.get_config()
    payload = "x" * config.resources.response_size_bytes
    
    return WorkResponse(
        message=f"Work completed successfully for operation: {operation}",
        operation=operation,
        payload=payload
    )


@router.post("/api/work/{operation}")
async def post_work_operation(operation: str, request: WorkRequest = Body(...)):
    """Parameterized POST work endpoint affected by chaos.
    
    Args:
        operation: Operation identifier
        request: Work request body
        
    Returns:
        Work response with operation info
    """
    config = await chaos_state.get_config()
    payload = "x" * config.resources.response_size_bytes
    
    # Optionally process the request data
    result = None
    if request.data:
        result = hashlib.sha256(request.data.encode()).hexdigest()[:16]
    
    return WorkResponse(
        message=f"Work completed successfully for operation: {operation}",
        operation=operation,
        result=result,
        payload=payload
    )
