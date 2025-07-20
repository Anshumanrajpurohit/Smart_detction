# main.py
from fastapi import FastAPI, HTTPException
from api import poll_and_predict


app = FastAPI()

@app.get("/")
def root():
    return {"message": "DL Model API for Age and Gender Classification"}

@app.on_event("startup")
def start_background_task():
    import threading
    threading.Thread(target=poll_and_predict, daemon=True).start()




# from fastapi import FastAPI, HTTPException
# from api import get_image_from_firebase, store_prediction_result
# from predict_age_gender import predict_gender,predict_age

# app = FastAPI()

# @app.get("/")
# def root():
#     return {"message": "DL Model API for Age and Gender Classification"}

# @app.get("/predict/")
# def predict(image_path: str):
#     try:
#         image_bytes = get_image_from_firebase(image_path)

#         age = predict_age(image_bytes)
#         gender = predict_gender(image_bytes)

#         store_prediction_result(image_path, age, gender)

#         return {
#             "image_path": image_path,
#             "age": age,
#             "gender": gender
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

