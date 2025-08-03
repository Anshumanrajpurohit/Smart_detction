from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/process_image")
async def process_image():
    pass