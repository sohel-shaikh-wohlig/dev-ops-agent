"""
API Routes - Dummy/Template File
"""
from fastapi import APIRouter

# Create the router instance - this MUST exist for main.py
router = APIRouter()


# Placeholder route - delete this when adding real routes
@router.get("/status")
async def api_status():
    """
    API status endpoint - placeholder
    """
    return {
        "message": "API routes are ready",
        "routes_loaded": True
    }


# TODO: Add your actual routes below