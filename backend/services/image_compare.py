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
import uuid as uuid_lib

app = FaceAnalysis(name='buffalo_l')
app.prepare(ctx_id=0, det_size=(640, 640))

threshold = 0.6

async def cosine_similarity(emb1, emb2):
    return dot(emb1, emb2) / (norm(emb1) * norm(emb2))

async def face_extraction(img_bytes: bytes):
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
    similarity = await cosine_similarity(emb1, emb2)
    return similarity > threshold 

async def download_image_from_url(url: str, bucket_name: str):
    try:
        image_byte = supabase.storage.from_(bucket_name).download(url)
        return image_byte  
    except Exception as e:
        print(f"Error downloading image {url}: {e}")
        return None

async def upload_face_to_bucket(face_image: np.ndarray, bucket_name: str) -> str:
    """Upload extracted face to bucket and return the file path"""
    try:
        # Convert face image to bytes
        _, buffer = cv2.imencode('.jpg', face_image)
        face_bytes = buffer.tobytes()
        
        # Generate unique filename
        filename = f"face_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid_lib.uuid4().hex[:8]}.jpg"
        
        # Upload to bucket
        supabase.storage.from_(bucket_name).upload(filename, face_bytes)
        print(f"Uploaded face to {bucket_name}/{filename}")
        return filename
    except Exception as e:
        print(f"Error uploading face to bucket: {e}")
        return None

async def get_images_from_bucket(bucket_name: str):
    """Get all image files from bucket"""
    try:
        files = supabase.storage.from_(bucket_name).list()
        # Filter for image files
        image_files = [f for f in files if f['name'].lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
        return image_files
    except Exception as e:
        print(f"Error listing files from bucket {bucket_name}: {e}")
        return []

async def process_bucket_images():
    """Process images directly from android bucket when new_faces is empty"""
    try:
        print("Processing images directly from android bucket...")
        
        # Get all images from android bucket
        bucket_images = await get_images_from_bucket(SUPABASE_BUCKET1)
        
        if not bucket_images:
            print("No images found in android bucket")
            return []
        
        processed_faces = []
        
        for image_file in bucket_images:
            try:
                image_path = image_file['name']
                print(f"Processing image: {image_path}")
                
                # Download image
                image_bytes = await download_image_from_url(image_path, SUPABASE_BUCKET1)
                if not image_bytes:
                    continue
                
                # Extract faces
                extracted_faces = await face_extraction(image_bytes)
                if not extracted_faces:
                    print(f"No faces found in {image_path}")
                    continue
                
                # Process each face found in the image
                for face_idx, (cropped_face, embedding) in enumerate(extracted_faces):
                    try:
                        # Upload face to faces bucket
                        face_filename = await upload_face_to_bucket(cropped_face, SUPABASE_BUCKET2)
                        if not face_filename:
                            continue
                        
                        # Add to new_faces table for processing
                        supabase.table("new_faces").insert({
                            "uuid": face_filename,  # Use the face filename in faces bucket
                            "c_path": image_path    # Original image path for reference
                        }).execute()
                        
                        processed_faces.append({
                            "original_image": image_path,
                            "face_file": face_filename,
                            "face_index": face_idx
                        })
                        
                        print(f"Added face {face_idx} from {image_path} to processing queue")
                        
                    except Exception as e:
                        print(f"Error processing face {face_idx} from {image_path}: {e}")
                        continue
                        
            except Exception as e:
                print(f"Error processing image {image_file.get('name', 'unknown')}: {e}")
                continue
        
        print(f"Processed {len(processed_faces)} faces from bucket images")
        return processed_faces
        
    except Exception as e:
        print(f"Error in process_bucket_images: {e}")
        return []

async def encode_embedding(embedding) -> str:
    return base64.b64encode(embedding.astype(np.float32).tobytes()).decode('utf-8')

async def decode_embedding(encoded_embedding: str) -> np.ndarray:
    decode_bytes = base64.b64decode(encoded_embedding.encode('utf-8'))
    return np.frombuffer(decode_bytes, dtype=np.float32)

async def process_faces_from_supabase():
    processed = []
    
    try:
        new_faces = supabase.table("new_faces").select("*").execute().data
        
        # If new_faces is empty, process images from bucket
        if not new_faces:
            print("No new faces to process, checking android bucket for images...")
            bucket_processed = await process_bucket_images()
            
            if not bucket_processed:
                print("No images processed from bucket, waiting...")
                await asyncio.sleep(5)
                return []
            
            # After processing bucket images, fetch new_faces again
            new_faces = supabase.table("new_faces").select("*").execute().data
            if not new_faces:
                print("Still no new faces after bucket processing")
                await asyncio.sleep(5)
                return []

        old_faces = supabase.table("old_faces").select("*").execute().data
        master_faces = supabase.table("master_faces").select("*").execute().data

        for new_face in new_faces:
            try:
                new_url = new_face["uuid"]
                print(f"Trying to download: {new_url} from bucket: {SUPABASE_BUCKET2}")  # Changed to BUCKET2 (faces)

                # Download from faces bucket now (since faces are extracted there)
                new_image_bytes = await download_image_from_url(new_url, SUPABASE_BUCKET2)
                if not new_image_bytes:
                    print(f"Failed to download image: {new_url}")
                    # Clean up the entry
                    supabase.table("new_faces").delete().eq("c_id", new_face["c_id"]).execute()
                    continue

                extracted_faces = await face_extraction(new_image_bytes)
                if not extracted_faces:
                    print(f"No faces found in image: {new_url}")
                    # Still delete from new_faces as it's processed
                    supabase.table("new_faces").delete().eq("c_id", new_face["c_id"]).execute()
                    continue

                for cropped_face, embedding in extracted_faces:
                    is_duplicate = False
                    
                    # Check for duplicates in old_faces
                    for old in old_faces:
                        try:
                            old_embedding = await decode_embedding(old["c_embedding"])
                            match = await face_compare(old_embedding, embedding)
                            if match:
                                print(f"Duplicate face found, removing from new_faces")
                                supabase.table("new_faces").delete().eq("c_id", new_face["c_id"]).execute()
                                is_duplicate = True
                                break
                        except Exception as e:
                            print(f"Error comparing with old face: {e}")
                            continue

                    if is_duplicate:
                        continue

                    matched_id = None
                    matched_person = None
                    
                    # Check for matches in master_faces
                    for person in master_faces:
                        try:
                            master_embedding = await decode_embedding(person["c_embedding"])
                            match = await face_compare(master_embedding, embedding)
                            if match:
                                matched_id = person["c_id"]
                                matched_person = person
                                break
                        except Exception as e:
                            print(f"Error comparing with master face: {e}")
                            continue

                    if matched_id and matched_person:
                        # Update visit count for known person
                        try:
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
                            print(f"Matched known person ID {matched_id}, visit count increased to {matched_person['c_visit'] + 1}")
                        except Exception as e:
                            print(f"Error updating matched person: {e}")
                    else:
                        # Create new person entry
                        try:
                            # For gender/age prediction, we need the original full image
                            # Try to get original image path if available
                            original_image_bytes = new_image_bytes  # Use face image for now
                            if "c_path" in new_face and new_face["c_path"]:
                                # Try to get original image for better gender/age prediction
                                original_bytes = await download_image_from_url(new_face["c_path"], SUPABASE_BUCKET1)
                                if original_bytes:
                                    original_image_bytes = original_bytes
                            
                            gender = await predict_gender(original_image_bytes)
                            age = await predict_age(original_image_bytes)
                            name = f"Person_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                            # Insert new master face
                            supabase.table("master_faces").insert({
                                "c_name": name,
                                "c_path": new_url,
                                "c_embedding": await encode_embedding(embedding),
                                "c_visit": 1,
                                "c_age": age,
                                "c_gender": gender
                            }).execute()

                            # Add to old_faces
                            supabase.table("old_faces").insert({
                                "c_path": new_url,
                                "c_embedding": await encode_embedding(embedding)
                            }).execute()

                            processed.append({"status": "new", "name": name})
                            
                            # Remove from new_faces
                            supabase.table("new_faces").delete().eq("c_id", new_face["c_id"]).execute()
                            print(f"Added new person '{name}'")
                        except Exception as e:
                            print(f"Error creating new person: {e}")

            except Exception as e:
                print(f"Error processing face ID {new_face.get('c_id')}: {e}")
                continue

    except Exception as e:
        print(f"Error in process_faces_from_supabase: {e}")
        await asyncio.sleep(10)

    print("Supabase face processing completed.")
    return processed

# Optional: Add a continuous processing function
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

# To run continuous processing:
# asyncio.run(continuous_face_processing())