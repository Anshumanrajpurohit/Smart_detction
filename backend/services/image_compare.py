import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis
from numpy import dot
from numpy.linalg import norm
import asyncio
from fastapi import UploadFile, File
import io
from datetime import datetime
from database.config import supabase, SUPABASE_BUCKET1, SUPABASE_BUCKET2
from backend.services.predictor import predict_gender, predict_age
from backend.services.image_handler import get_images_from_supabase,upload_image_to_supabase

app = FaceAnalysis(name='buffalo_l')
app.prepare(ctx_id=0, det_size=(640, 640))

threshold = 0.6

def cosine_similarity(emb1, emb2):
    return dot(emb1, emb2) / (norm(emb1) * norm(emb2))

async def face_extraction(img_bytes: bytes) -> bool:

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

def process_faces_from_supabase():
    print("🔍 Starting Supabase-based face comparison process...")

    # Fetch new faces from `new_faces` table
    new_faces = supabase.table("new_faces").select("*").execute().data

    if not new_faces:
        print("ℹ️ No new faces to process")
        return

    # Fetch old and master faces
    old_faces = supabase.table("old_faces").select("*").execute().data
    master_faces = supabase.table("master_faces").select("*").execute().data

    for new_face in new_faces:
        try:
            new_url = new_face["image_url"]
            new_image_bytes = download_image_from_url(new_url)
            if not new_image_bytes:
                continue

            extracted_faces = await face_extraction(new_image_bytes)
            if not extracted_faces:
                continue

            for cropped_face, embedding in extracted_faces:
                serialized_embedding = encode_embedding(embedding)

                is_duplicate = False
                # --- Step 1: Check with old faces ---
                for old in old_faces:
                    old_embedding = decode_embedding(old["embedding"])
                    match, dist, type_ = compare_faces_strict(old_embedding, embedding)
                    if match and type_ == "exact_match":
                        print(f"❌ Exact duplicate found (dist: {dist:.3f})")
                        supabase.table("new_faces").delete().eq("id", new_face["id"]).execute()
                        is_duplicate = True
                        break

                if is_duplicate:
                    continue

                # --- Step 2: Check with master_faces for similarity ---
                matched_id = None
                for person in master_faces:
                    master_embedding = decode_embedding(person["embedding"])
                    if await face_compare(master_embedding, embedding):
                        matched_id = person["id"]
                        break

                if matched_id:
                    # Update visit count and last seen
                    supabase.table("master_faces").update({
                        "visits": person["visits"] + 1,
                        "last_seen": datetime.now().isoformat()
                    }).eq("id", matched_id).execute()

                    # Add to old_faces
                    supabase.table("old_faces").insert({
                        "image_url": new_url,
                        "embedding": serialized_embedding,
                        "timestamp": datetime.now().isoformat()
                    }).execute()

                    # Remove from new_faces
                    supabase.table("new_faces").delete().eq("id", new_face["id"]).execute()
                    print(f"✅ Matched known person ID {matched_id}, visit count increased")
                else:
                    # --- Step 3: Add new person ---
                    gender = predict_gender(new_url)
                    age = predict_age(new_url)
                    name = f"Person_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                    supabase.table("master_faces").insert({
                        "name": name,
                        "image_url": new_url,
                        "embedding": serialized_embedding,
                        "visits": 1,
                        "age": age,
                        "gender": gender,
                        "first_seen": datetime.now().isoformat(),
                        "last_seen": datetime.now().isoformat()
                    }).execute()

                    # Add to old_faces
                    supabase.table("old_faces").insert({
                        "image_url": new_url,
                        "embedding": serialized_embedding,
                        "timestamp": datetime.now().isoformat()
                    }).execute()

                    # Remove from new_faces
                    supabase.table("new_faces").delete().eq("id", new_face["id"]).execute()
                    print(f"🆕 Added new person '{name}'")

        except Exception as e:
            print(f"❌ Error processing face ID {new_face.get('id')}: {e}")
            continue

    print("✅ Supabase face processing completed.")


