import requests
from database.config import supabase, SUPABASE_BUCKET1,SUPABASE_BUCKET2
from fastapi import FastAPI, HTTPException,APIRouter
from fastapi.responses import StreamingResponse
import io


router = APIRouter()

@router.get("/images")
def get_images_from_supabase():
    try:
        # List all files in the Supabase bucket
        result = supabase.storage.from_(SUPABASE_BUCKET1).list()

        print(f"Files in bucket  {result}")
        if not result:
            raise HTTPException(status_code=404, detail="No images found in the bucket")

        # Get the first file from the list
        file = result[0]
        file_name = file["name"]

        # Download the image from the same bucket
        image_bytes = supabase.storage.from_(SUPABASE_BUCKET1).download(file_name)

        # Return the image as a streaming HTTP response
        return StreamingResponse(io.BytesIO(image_bytes), media_type="image/jpeg")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching images: {str(e)}")
    
@router.post("/images/upload")
def upload_image_to_supabase(file: bytes):
    try:
        file_name = "uploaded_image.jpg" 
        supabase.storage.from_(SUPABASE_BUCKET2).upload(file_name, file)

        return {"message": "Image uploaded successfully", "file_name": file_name}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading image: {str(e)}")
