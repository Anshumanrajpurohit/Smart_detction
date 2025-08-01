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

async def face_compare(emb1, emb2):
    similarity = await cosine_similarity(emb1, emb2)
    return similarity > threshold 

async def download_image_from_url(url: str):
    try:
        # Auto-detect bucket from URL
        bucket_name = "faces"  # default
        if "/faces/" in url:
            bucket_name = "faces"
        elif "/android/" in url:
            bucket_name = "android"
        
        # Extract file path from URL
        if "/object/public/" in url:
            parts = url.split("/object/public/")
            if len(parts) > 1:
                path_with_bucket = parts[1]
                # Remove bucket name from path
                path_parts = path_with_bucket.split("/", 1)
                if len(path_parts) > 1:
                    file_path = path_parts[1]
                else:
                    file_path = path_with_bucket
            else:
                file_path = url
        else:
            file_path = url
        
        print(f"Downloading from bucket '{bucket_name}' with path: '{file_path}'")
        image_byte = supabase.storage.from_(bucket_name).download(file_path)
        return image_byte
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None

async def encode_embedding(embedding) -> str:
    return base64.b64encode(embedding.astype(np.float32).tobytes()).decode('utf-8')

async def decode_embedding(encoded_embedding: str) -> np.ndarray:
    decode_bytes = base64.b64decode(encoded_embedding.encode('utf-8'))
    return np.frombuffer(decode_bytes, dtype=np.float32)

async def process_faces_from_supabase():
    processed = []
    
    try:
        new_faces = supabase.table("new_faces").select("*").execute().data
        if not new_faces:
            print("No new faces to process")
            return []

        old_faces = supabase.table("old_faces").select("*").execute().data
        master_faces = supabase.table("master_faces").select("*").execute().data

        for new_face in new_faces:
            try:
                new_url = new_face["c_path"]
                print(f"Processing new face: {new_url}")

                new_image_bytes = await download_image_from_url(new_url)
                if not new_image_bytes:
                    print(f"Failed to download image: {new_url}")
                    continue

                extracted_faces = await face_extraction(new_image_bytes)
                if not extracted_faces:
                    print("No faces detected in the image")
                    continue

                for cropped_face, embedding in extracted_faces:
                    is_duplicate = False
                    
                    # Check against old faces for duplicates
                    for old in old_faces:
                        old_embedding = await decode_embedding(old["c_embedding"])
                        match = await face_compare(old_embedding, embedding)
                        if match:
                            print(f"Duplicate face found, removing from new_faces")
                            supabase.table("new_faces").delete().eq("c_id", new_face["c_id"]).execute()
                            is_duplicate = True
                            break

                    if is_duplicate:
                        continue

                    # Check against master faces for known persons
                    matched_id = None
                    matched_person = None
                    for person in master_faces:
                        master_embedding = await decode_embedding(person["c_embedding"])

                        if await face_compare(master_embedding, embedding):
                            matched_id = person["c_id"]
                            matched_person = person
                            break

                    if matched_id and matched_person:
                        # Update visit count for known person
                        supabase.table("master_faces").update({
                            "c_visit": matched_person["c_visit"] + 1
                        }).eq("c_id", matched_id).execute()

                        # Add to old_faces
                        supabase.table("old_faces").insert({
                            "c_path": new_url,
                            "c_embedding": await encode_embedding(embedding)
                        }).execute()

                        processed.append({"status": "matched", "id": matched_id})
                        
                        # Remove from new_faces
                        supabase.table("new_faces").delete().eq("c_id", new_face["c_id"]).execute()
                        print(f"Matched known person ID {matched_id}, visit count increased")
                    else:
                        # New person - predict gender and age
                        gender = await predict_gender(new_image_bytes)
                        age = await predict_age(new_image_bytes)
                        name = f"Person_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                        # Insert into master_faces
                        supabase.table("master_faces").insert({
                            "c_name": name,
                            "c_path": new_url,
                            "c_embedding": await encode_embedding(embedding),
                            "c_visit": 1,
                            "c_age": age,
                            "c_gender": gender
                        }).execute()

                        # Insert into old_faces
                        supabase.table("old_faces").insert({
                            "c_path": new_url,
                            "c_embedding": await encode_embedding(embedding)
                        }).execute()

                        processed.append({"status": "new", "name": name})
                        
                        # Remove from new_faces
                        supabase.table("new_faces").delete().eq("c_id", new_face["c_id"]).execute()
                        print(f"Added new person '{name}'")

            except Exception as e:
                print(f"Error processing face ID {new_face.get('c_id')}: {e}")
                continue

        print("Supabase face processing completed.")
        return processed
        
    except Exception as e:
        print(f"Error in process_faces_from_supabase: {e}")
        raise e