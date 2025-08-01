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
import traceback

app = FaceAnalysis(name='buffalo_l')
app.prepare(ctx_id=0, det_size=(640, 640))

threshold = 0.6

async def cosine_similarity(emb1, emb2):
    """Calculate cosine similarity between two embeddings"""
    return dot(emb1, emb2) / (norm(emb1) * norm(emb2))

async def face_extraction(img_bytes: bytes):
    """Extract faces and embeddings from image bytes"""
    try:
        img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            print("Failed to decode image")
            return []
            
        faces = app.get(img)
        results = []
        
        for face in faces:
            box = face.bbox.astype(int)
            cropped_face = img[box[1]:box[3], box[0]:box[2]]
            embedding = face.embedding
            results.append((cropped_face, embedding))
            
        return results
    except Exception as e:
        print(f"Error in face extraction: {e}")
        return []

async def face_compare(emb1, emb2):
    """Compare two face embeddings"""
    try:
        similarity = await cosine_similarity(emb1, emb2)
        return similarity > threshold
    except Exception as e:
        print(f"Error in face comparison: {e}")
        return False

def determine_bucket_from_path(file_path: str) -> str:
    """Determine which bucket to use based on file path"""
    if "faces/" in file_path or file_path.endswith('.jpg') or file_path.endswith('.png'):
        return "faces"
    elif "android/" in file_path:
        return "android"
    else:
        return SUPABASE_BUCKET1  # Default bucket

async def download_image_from_url(file_path: str) -> bytes:
    """Download image from Supabase storage"""
    try:
        # Determine bucket
        bucket_name = determine_bucket_from_path(file_path)
        
        # Clean the file path
        clean_path = file_path.strip().lstrip('/')
        
        print(f"Downloading '{clean_path}' from bucket '{bucket_name}'")
        image_bytes = supabase.storage.from_(bucket_name).download(clean_path)
        
        if image_bytes:
            print(f"Successfully downloaded {len(image_bytes)} bytes")
            return image_bytes
        else:
            print("No data returned from download")
            return None
            
    except Exception as e:
        print(f"Error downloading image '{file_path}': {e}")
        return None

async def encode_embedding(embedding) -> str:
    """Encode numpy embedding to base64 string"""
    return base64.b64encode(embedding.astype(np.float32).tobytes()).decode('utf-8')

async def decode_embedding(encoded_embedding: str) -> np.ndarray:
    """Decode base64 string to numpy embedding"""
    decode_bytes = base64.b64decode(encoded_embedding.encode('utf-8'))
    return np.frombuffer(decode_bytes, dtype=np.float32)

async def process_faces_from_supabase():
    """Main function to process faces from Supabase"""
    processed = []
    
    try:
        print("Fetching new faces from database...")
        new_faces_response = supabase.table("new_faces").select("*").execute()
        new_faces = new_faces_response.data
        
        if not new_faces:
            print("No new faces to process")
            return []

        print(f"Found {len(new_faces)} new faces to process")
        
        # Fetch existing data
        old_faces_response = supabase.table("old_faces").select("*").execute()
        old_faces = old_faces_response.data
        
        master_faces_response = supabase.table("master_faces").select("*").execute()
        master_faces = master_faces_response.data
        
        print(f"Database stats - Old faces: {len(old_faces)}, Master faces: {len(master_faces)}")

        for idx, new_face in enumerate(new_faces):
            try:
                print(f"\n--- Processing face {idx + 1}/{len(new_faces)} ---")
                print(f"Face data: {new_face}")
                
                # Get the correct path - use c_path, not uuid
                new_path = new_face.get("c_path")
                face_id = new_face.get("c_id")
                
                if not new_path:
                    print("No c_path found in face data, skipping...")
                    continue
                    
                print(f"Processing face ID {face_id} with path: {new_path}")

                # Download image
                new_image_bytes = await download_image_from_url(new_path)
                if not new_image_bytes:
                    print(f"Failed to download image: {new_path}")
                    # Remove failed download from new_faces
                    supabase.table("new_faces").delete().eq("c_id", face_id).execute()
                    continue

                # Extract faces from image
                extracted_faces = await face_extraction(new_image_bytes)
                if not extracted_faces:
                    print(f"No faces detected in image: {new_path}")
                    # Remove processed (no faces) from new_faces
                    supabase.table("new_faces").delete().eq("c_id", face_id).execute()
                    continue

                print(f"Extracted {len(extracted_faces)} faces from image")

                # Process each detected face
                for face_idx, (cropped_face, embedding) in enumerate(extracted_faces):
                    print(f"Processing face {face_idx + 1}/{len(extracted_faces)}")
                    
                    is_duplicate = False
                    
                    # Check for duplicates in old_faces
                    print("Checking for duplicates in old faces...")
                    for old_idx, old in enumerate(old_faces):
                        try:
                            if not old.get("c_embedding"):
                                continue
                                
                            old_embedding = await decode_embedding(old["c_embedding"])
                            match = await face_compare(old_embedding, embedding)
                            
                            if match:
                                print(f"Duplicate found with old face {old_idx}, removing from new_faces")
                                supabase.table("new_faces").delete().eq("c_id", face_id).execute()
                                is_duplicate = True
                                break
                                
                        except Exception as e:
                            print(f"Error comparing with old face {old_idx}: {e}")
                            continue

                    if is_duplicate:
                        break  # Skip to next new face

                    # Check for matches in master_faces
                    print("Checking for matches in master faces...")
                    matched_person = None
                    
                    for master_idx, person in enumerate(master_faces):
                        try:
                            if not person.get("c_embedding"):
                                continue
                                
                            master_embedding = await decode_embedding(person["c_embedding"])
                            match = await face_compare(master_embedding, embedding)
                            
                            if match:
                                matched_person = person
                                print(f"Match found with master face {master_idx} (ID: {person['c_id']})")
                                break
                                
                        except Exception as e:
                            print(f"Error comparing with master face {master_idx}: {e}")
                            continue

                    if matched_person:
                        # Update existing person
                        try:
                            new_visit_count = matched_person["c_visit"] + 1
                            
                            # Update visit count
                            supabase.table("master_faces").update({
                                "c_visit": new_visit_count
                            }).eq("c_id", matched_person["c_id"]).execute()

                            # Add to old_faces
                            supabase.table("old_faces").insert({
                                "c_path": new_path,
                                "c_embedding": await encode_embedding(embedding)
                            }).execute()

                            processed.append({
                                "status": "matched", 
                                "id": matched_person["c_id"],
                                "name": matched_person.get("c_name", "Unknown"),
                                "visit_count": new_visit_count
                            })
                            
                            print(f"Updated person '{matched_person.get('c_name')}' visit count to {new_visit_count}")
                            
                        except Exception as e:
                            print(f"Error updating matched person: {e}")
                    else:
                        # Create new person
                        try:
                            print("Creating new person entry...")
                            
                            # Predict gender and age
                            gender = await predict_gender(new_image_bytes)
                            age = await predict_age(new_image_bytes)
                            name = f"Person_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{face_idx}"

                            # Insert new master face
                            master_insert_response = supabase.table("master_faces").insert({
                                "c_name": name,
                                "c_path": new_path,
                                "c_embedding": await encode_embedding(embedding),
                                "c_visit": 1,
                                "c_age": age,
                                "c_gender": gender
                            }).execute()

                            # Add to old_faces
                            supabase.table("old_faces").insert({
                                "c_path": new_path,
                                "c_embedding": await encode_embedding(embedding)
                            }).execute()

                            processed.append({
                                "status": "new", 
                                "name": name,
                                "gender": gender,
                                "age": age
                            })
                            
                            print(f"Created new person '{name}' (Gender: {gender}, Age: {age})")
                            
                        except Exception as e:
                            print(f"Error creating new person: {e}")

                # Remove processed face from new_faces
                try:
                    supabase.table("new_faces").delete().eq("c_id", face_id).execute()
                    print(f"Removed processed face {face_id} from new_faces")
                except Exception as e:
                    print(f"Error removing face from new_faces: {e}")

            except Exception as e:
                print(f"Error processing face ID {face_id}: {e}")
                print(f"Traceback: {traceback.format_exc()}")
                continue

    except Exception as e:
        print(f"Error in process_faces_from_supabase: {e}")
        print(f"Traceback: {traceback.format_exc()}")

    print(f"\nProcessing completed. Total processed: {len(processed)}")
    return processed

async def continuous_face_processing():
    """
    Continuously process faces with intelligent waiting
    """
    consecutive_empty_checks = 0
    
    while True:
        try:
            processed = await process_faces_from_supabase()
            
            if not processed:
                consecutive_empty_checks += 1
                # Increase wait time if no faces found repeatedly
                wait_time = min(5 + (consecutive_empty_checks * 2), 30)  # Max 30 seconds
                print(f"No faces processed. Waiting {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                consecutive_empty_checks = 0
                print(f"Processed {len(processed)} faces")
                await asyncio.sleep(1)  # Short wait after processing
                
        except Exception as e:
            print(f"Error in continuous processing: {e}")
            await asyncio.sleep(10)