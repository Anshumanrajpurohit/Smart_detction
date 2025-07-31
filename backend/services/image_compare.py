import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis
from numpy import dot
from numpy.linalg import norm
import asyncio
from fastapi import UploadFile, File, HTTPException
import io
from datetime import datetime
from database.config import supabase, SUPABASE_BUCKET1, SUPABASE_BUCKET2
from services.predictor import predict_gender, predict_age
# from services.image_handler import get_images_from_supabase,upload_image_to_supabase
import base64
import json

app = FaceAnalysis(name='buffalo_l')
app.prepare(ctx_id=0, det_size=(640, 640))

threshold = 0.6

async def cosine_similarity(emb1, emb2):
    return dot(emb1, emb2) / (norm(emb1) * norm(emb2))

async def face_extraction(img_bytes: bytes):

    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    faces = app.get(img)

    results = []
    for face in faces:
        box = face.bbox.astype(int)
        cropped_face = img[box[1]:box[3], box[0]:box[2]]
        embedding = face.embedding
        results.append((cropped_face, embedding))
    return results


async def face_compare(emb1,emb2):
    return cosine_similarity(emb1,emb2) > threshold 

SUPABASE_BUCKET1 = "android"
SUPABASE_BUCKET2 = "faces"

async def download_image_from_url(url: str,SUPABASE_BUCKET1):
    image_byte = supabase.storage.from_(SUPABASE_BUCKET1).download(url)
    return image_byte  

async def encode_embedding(embedding) -> str:
    return base64.b64encode(embedding.astype(np.float32).tobytes()).decode('utf-8')

async def decode_embedding(encoded_embedding: str) -> np.ndarray:
    decode_bytes = base64.b64decode(encoded_embedding.encode('utf-8'))
    return np.frombuffer(decode_bytes, dtype=np.float32)

async def process_faces_from_supabase():
    processed = []
    new_faces = supabase.table("new_faces").select("*").execute().data

    if not new_faces:
        print("No new faces to process")
        return []

    old_faces = supabase.table("old_faces").select("*").execute().data
    master_faces = supabase.table("master_faces").select("*").execute().data

    for new_face in new_faces:
        try:
            new_url = new_face["c_path"]
            print(f"Trying to download: {new_url} from bucket: {SUPABASE_BUCKET1}")

            new_image_bytes = await download_image_from_url(new_url,SUPABASE_BUCKET1)
            if not new_image_bytes:
                continue

            extracted_faces = await face_extraction(new_image_bytes)
            if not extracted_faces:
                continue

            for cropped_face, embedding in extracted_faces:
                # serialized_embedding = encode_embedding(embedding)

                is_duplicate = False
                for old in old_faces:
                    old_embedding = decode_embedding(old["embedding"])
                    match = await face_compare(old_embedding, embedding)
                    if match:
                        supabase.table("new_faces").delete().eq("c_id", new_face["c_id"]).execute()
                        is_duplicate = True
                        break

                if is_duplicate:
                    continue

                matched_id = None
                for person in master_faces:
                    master_embedding = decode_embedding(person["embedding"])

                    if await face_compare(master_embedding, old_embedding):
                        matched_id = person["c_id"]
                        break

                if matched_id:
                    supabase.table("master_faces").update({
                        "c_visit": person["c_visit"] + 1
                        # "last_seen": datetime.now().isoformat()
                    }).eq("c_id", matched_id).execute()

                    supabase.table("old_faces").insert({
                        "c_path": new_url,
                        "c_embedding": encode_embedding(embedding)
                        # "timestamp": datetime.now().isoformat()
                    }).execute()

                    processed.append({"status": "matched", "id": matched_id})
                    # Remove from new_faces
                    supabase.table("new_faces").delete().eq("c_id", new_face["c_id"]).execute()
                    print(f"Matched known person ID {matched_id}, visit count increased")
                else:
                    gender = await predict_gender(new_image_bytes)
                    age = await predict_age(new_image_bytes)
                    name = f"Person_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                    supabase.table("master_faces").insert({
                        "c_name": name,
                        "c_path": new_url,
                        "c_embedding": encode_embedding(embedding),
                        "c_visit": 1,
                        "c_age": age,
                        "c_gender": gender
                        # "first_seen": datetime.now().isoformat(),
                        # "last_seen": datetime.now().isoformat()
                    }).execute()

                    
                    supabase.table("old_faces").insert({
                        "c_path": new_url,
                        "c_embedding": encode_embedding(embedding),
                        # "timestamp": datetime.now().isoformat()
                    }).execute()

                    processed.append({"status": "new", "name": name})
                    supabase.table("new_faces").delete().eq("c_id", new_face["c_id"]).execute()
                    print(f"Added new person '{name}'")

        except Exception as e:
            print(f"Error processing face ID {new_face.get('c_id')}: {e}")
            continue

    print("Supabase face processing completed.")
    return processed


