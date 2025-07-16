from migrate_to_firebase import db, storage
import cv2
from PIL import Image
import numpy as np


def get_image_from_firebase(image_path: str) -> bytes:
    bucket = storage.bucket()
    blob = bucket.blob(image_path)
    return blob.download_as_bytes()

def store_prediction_result(image_path: str, age: int, gender: str):
    # Find the document where 'image_path' == image_path
    docs = db.collection('your_collection_name').where("image_path", "==", image_path).get()

    if not docs:
        print(f"No document found with image_path: {image_path}")
        return

    for doc in docs:
        doc.reference.update({
            "age": age,
            "gender": gender
        })
        print(f"Updated document {doc.id} with age: {age}, gender: {gender}")


