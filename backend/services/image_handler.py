# from ..database.config import supabase,SUPABASE_BUCKET1,SUPABASE_BUCKET2
# import cv2
# import numpy as np
# from fastapi import HTTPException
# from fastapi.responses import StreamingResponse
# import io


# def get_images_from_supabase():
#     try:
#         # List all files in the Supabase bucket
#         result = supabase.storage.from_(SUPABASE_BUCKET1).list()

#         print(f"Files in bucket  {result}")
#         if not result:
#             raise HTTPException(status_code=404, detail="No images found in the bucket")

#         # Get the first file from the list
#         file = result[0]
#         file_name = file["name"]

#         image_bytes = supabase.storage.from_(SUPABASE_BUCKET1).download(file_name)


#         return StreamingResponse(io.BytesIO(image_bytes), media_type="image/jpeg")

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error fetching images: {str(e)}")
    
# def upload_image_to_supabase(image: np.ndarray, filename: str, bucket: str = "faces"):

#     success, buffer = cv2.imencode('.jpg', image)
#     if not success:
#         raise Exception("Image encoding failed.")
    
#     image_bytes = io.BytesIO(buffer)

#     response = supabase.storage.from_(bucket).upload(file=image_bytes, path=filename, file_options={"content-type": "image/jpeg"}, upsert=True)
#     return response