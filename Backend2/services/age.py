import numpy as np
import cv2
import asyncio

async def predict_age(img_bytes):
    image_path = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)



    net = cv2.dnn.readNetFromCaffe('Backend2/ml_models/age_prediction.prototxt', 'Backend2/ml_models/model.caffemodel')

    blob = cv2.dnn.blobFromImage(image_path, scalefactor=1.0, size=(224, 224), mean=(104, 117, 123))
    net.setInput(blob)
    output = net.forward()
    bucket_idx = output[0].argmax()

    age = bucket_idx
    age_range = age
    if 0<age<10:
        age_range = "0-10"
    elif 10<age<20:
        age_range = "10-20"
    elif 20<age<30:
        age_range = "20-30"
    elif 30<age<40:
        age_range = "30-40"
    elif 40<age<50:
        age_range = "40-50"
    elif 50<age<60:
        age_range = "50-60"
    elif 60<age<70:
        age_range = "60-70"
    elif 70<age<80:
        age_range = "70-80"
    elif 80<age<90:
        age_range = "80-90"
    else:
        age_range = "90+"
    
    return age_range 


