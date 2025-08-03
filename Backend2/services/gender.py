from deepface import DeepFace
import numpy as np
import os
import cv2
from PIL import Image

async def gender_predictor(img_bytes):
    genders = ['Female', 'Male']
    try:

        image_path = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)

        result = await DeepFace.analyze(img_path=image_path, actions=['gender'], enforce_detection=False)

        gender_scores = result[0]['gender']
        predicted_gender = genders[np.argmax(list(gender_scores.values()))]
        confidence = max(gender_scores.values())

        return predicted_gender

    except Exception as e:
        print(f"Error during prediction: {e}")
        return None
