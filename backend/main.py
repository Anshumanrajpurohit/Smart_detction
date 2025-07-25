from fastapi import FastAPI,HTTPException, Depends
from Smart_detction.backend.routers.process_image import router as supabase_router

app = FastAPI()

@app.get("/")
def index():
    return {"msg": "Welcome to the Supabase Image API"}

app.include_router(supabase_router, prefix="/supabase", tags=["Supabase Images"])

