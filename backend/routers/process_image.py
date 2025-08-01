import requests
# from backend.services.image_handler import get_images_from_supabase
from database.config import supabase, SUPABASE_BUCKET1,SUPABASE_BUCKET2
from fastapi import FastAPI, HTTPException,APIRouter
from fastapi.responses import StreamingResponse
from services.image_compare import continuous_face_processing

## Create a router for the image processing endpoints

router = APIRouter()

@router.get("/")

# async def process_faces():
#     try:
#         final_processed_faces_output = await process_faces_from_supabase()
#         if not final_processed_faces_output:
#             raise HTTPException(status_code=404, detail="No faces found to process")
#         return ({"Faces Compared Successfully": final_processed_faces_output})
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error processing faces: {str(e)}")


async def process_faces():
    try:
        result = await continuous_face_processing()

        if not result:
            raise HTTPException(status_code=404, detail="No faces found to process")

        return {"message": "Faces processed successfully", "data": result}

    except Exception as e:
        print(f"[ERROR] Exception occurred: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing faces: {str(e)}")

#         # Get the first file from the list
#         file = result[0]
#         file_name = file["name"]

#         # Download the image from the same bucket
#         image_bytes = supabase.storage.from_(SUPABASE_BUCKET1).download(file_name)

#         # Return the image as a streaming HTTP response
#         return StreamingResponse(io.BytesIO(image_bytes), media_type="image/jpeg")

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error fetching images: {str(e)}")
    
# @router.post("/images/upload")
# def upload_image_to_supabase(file: bytes):
#     try:
#         file_name = "uploaded_image.jpg" 
#         supabase.storage.from_(SUPABASE_BUCKET2).upload(file_name, file)

#         return {"message": "Image uploaded successfully", "file_name": file_name}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error uploading image: {str(e)}")



# @app.post("/upload")
# def upload_image_to_supabse():
#     try:
#         upload = supabase.storage.from_(SUPABASE_BUCKET2).upload("persion_002.jpg","/Face_Count/H/backend/face_1_20250710_214507_478_q0.81_c75.jpg")
#         if not upload:
#             raise HTTPException(status_code=200, detail="Bhai Upload Hogaya")
#         else:
#             return {"BHai tu haglass ": upload.data}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error uploading image: {str(e)}")