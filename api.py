from migrate_to_firebase import db, storage
import cv2
from PIL import Image
import numpy as np
import time
from predictor import predict_gender,predict_age


def get_image_from_firebase(image_path: str) -> bytes:
    bucket = storage.bucket()
    blob = bucket.blob(image_path)
    return blob.download_as_bytes()

def poll_and_predict(interval_seconds=10):
    while True:
        print("Checking Firestore for records with missing age/gender...")

        docs = db.collection("people").where("age", "==", None).stream()

        for doc in docs:
            data = doc.to_dict()
            image_path = data.get("image_path")

            try:
                image_bytes = get_image_from_firebase(image_path)
                age, gender = predict_age,predict_gender(image_path)

                # Take first prediction since it's a cropped face
                age = age if age else "unknown"
                gender = gender if gender else "unknown"

                doc.reference.update({
                    "age": age,
                    "gender": gender
                })

                print(f"✅ Updated: {image_path} with age={age}, gender={gender}")

            except Exception as e:
                print(f"❌ Error processing {image_path}: {e}")
                doc.reference.update({
                    "error": str(e)
                })

        time.sleep(interval_seconds)




