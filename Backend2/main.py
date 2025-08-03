from fastapi import FastAPI,HTTPException
from routers.image_process import router as imagfe_process_router

app = FastAPI()

@app.get("/")
def index():
    return {"msg": "Welcome to the Supabase Image API"}

@app.include_router(imagfe_process_router,prefix="/process_image", methods=["GET"])