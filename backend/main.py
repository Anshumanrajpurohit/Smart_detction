from fastapi import FastAPI,HTTPException, Depends
from backend.routers.process_image import router as supabase_router

# idhar routs wali file ko load ka and call main funtion
app = FastAPI()

@app.get("/")
def index():
    return {"msg": "Welcome to the Supabase Image API"}

app.include_router(supabase_router, prefix="/supabase", tags=["Supabase Images"])

