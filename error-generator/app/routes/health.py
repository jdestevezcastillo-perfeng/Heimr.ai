"""Health check endpoint."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint that bypasses chaos injection.
    
    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "error-generator"
    }
