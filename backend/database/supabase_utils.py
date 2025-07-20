import requests
from config import supabase,SUPABASE_BUCKET1
from fastapi import HTTPException,FastAPI

app = FastAPI()

@app.get("/images")
def get_images_from_supabase():
    result = supabase.storage.from_(SUPABASE_BUCKET1).list()
    
    try:
        file = result[0]
        file_name = file["name"]
        image = supabase.storage.from_('android').download(file_name)

        return image
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching images: {str(e)}")


    
    
        

        
