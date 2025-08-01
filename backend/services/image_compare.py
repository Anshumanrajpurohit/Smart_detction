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

async def encode_embedding(embedding) -> str:
    return base64.b64encode(embedding.astype(np.float32).tobytes()).decode('utf-8')

async def decode_embedding(encoded_embedding: str) -> np.ndarray:
    decode_bytes = base64.b64decode(encoded_embedding.encode('utf-8'))
    return np.frombuffer(decode_bytes, dtype=np.float32)

async def upload_face_to_faces_bucket(cropped_face: np.ndarray) -> str:
    """Upload extracted face to faces bucket and return the file path"""
    try:
        # Convert face image to bytes
        _, buffer = cv2.imencode('.jpg', cropped_face)
        face_bytes = buffer.tobytes()
        
        # Generate unique filename for face
        face_filename = f"face_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
        
        # Upload to faces bucket (SUPABASE_BUCKET2)
        supabase.storage.from_(SUPABASE_BUCKET2).upload(face_filename, face_bytes)
        print(f"Uploaded face to {SUPABASE_BUCKET2}/{face_filename}")
        return face_filename
    except Exception as e:
        print(f"Error uploading face to faces bucket: {e}")
        return None

async def get_images_from_android_bucket():
    """Get all image files from android bucket"""
    try:
        files = supabase.storage.from_(SUPABASE_BUCKET1).list()
        # Filter for image files
        image_files = [f for f in files if f['name'].lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
        print(f"Found {len(image_files)} images in android bucket")
        return image_files
    except Exception as e:
        print(f"Error listing files from android bucket: {e}")
        return []

async def delete_android_image(image_path: str):
    """Delete processed image from android bucket"""
    try:
        supabase.storage.from_(SUPABASE_BUCKET1).remove([image_path])
        print(f"Deleted processed image from android bucket: {image_path}")
        return True
    except Exception as e:
        print(f"Error deleting android image {image_path}: {e}")
        return False

async def process_android_bucket_images():
    """Process images from android bucket when new_faces is empty"""
    try:
        print("new_faces is empty, processing images from android bucket...")
        
        # Get all images from android bucket
        android_images = await get_images_from_android_bucket()
        
        if not android_images:
            print("No images found in android bucket")
            return 0
        
        print(f"Found {len(android_images)} images in android bucket to process")
        processed_count = 0
        
        for image_file in android_images:
            try:
                image_path = image_file['name']
                print(f"Processing android image: {image_path}")
                
                # Download image from android bucket
                image_bytes = await download_image_from_url(image_path, SUPABASE_BUCKET1)
                if not image_bytes:
                    print(f"Failed to download {image_path}")
                    continue
                
                # Extract faces from image
                extracted_faces = await face_extraction(image_bytes)
                if not extracted_faces:
                    print(f"No faces found in {image_path}")
                    # Delete image even if no faces found (processed but no faces)
                    await delete_android_image(image_path)
                    continue
                
                print(f"Found {len(extracted_faces)} faces in {image_path}")
                
                # Process each extracted face
                faces_processed = 0
                for face_idx, (cropped_face, embedding) in enumerate(extracted_faces):
                    try:
                        # Upload face to faces bucket
                        face_filename = await upload_face_to_faces_bucket(cropped_face)
                        if not face_filename:
                            continue
                        
                        # Add face path to new_faces table
                        supabase.table("new_faces").insert({
                            "c_id": face_filename  # Face image path in faces bucket
                        }).execute()
                        
                        faces_processed += 1
                        processed_count += 1
                        print(f"Added face {face_idx+1} from {image_path} to new_faces: {face_filename}")
                        
                    except Exception as e:
                        print(f"Error processing face {face_idx} from {image_path}: {e}")
                        continue
                
                # Delete the android image after processing (regardless of success/failure)
                await delete_android_image(image_path)
                print(f"Processed {faces_processed} faces from {image_path} and deleted original")
                        
            except Exception as e:
                print(f"Error processing android image {image_file.get('name', 'unknown')}: {e}")
                # Try to delete the problematic image to avoid reprocessing
                try:
                    await delete_android_image(image_file.get('name', ''))
                except:
                    pass
                continue
        
        print(f"Processed {processed_count} faces from {len(android_images)} android images (all deleted)")
        return processed_count
        
    except Exception as e:
        print(f"Error in process_android_bucket_images: {e}")
        return 0

async def process_faces_from_supabase():
    processed = []
    
    try:
        # Check new_faces table
        new_faces = supabase.table("new_faces").select("*").execute().data
        
        # If new_faces is empty, process images from android bucket
        if not new_faces:
            print("new_faces table is empty")
            await process_android_bucket_images()
            
            # After processing android bucket, check new_faces again
            new_faces = supabase.table("new_faces").select("*").execute().data
            if not new_faces:
                print("Still no new faces after processing android bucket")
                await asyncio.sleep(5)
                return []

        # Get old_faces and master_faces for comparison
        old_faces = supabase.table("old_faces").select("*").execute().data
        master_faces = supabase.table("master_faces").select("*").execute().data

        print(f"Processing {len(new_faces)} new faces")
        print(f"old_faces count: {len(old_faces)}")
        print(f"master_faces count: {len(master_faces)}")

        for new_face in new_faces:
            try:
                new_url = new_face["c_id"]  # Face image path in faces bucket
                print(f"Processing face: {new_url}")

                # Download face image from faces bucket (SUPABASE_BUCKET2)
                new_image_bytes = await download_image_from_url(new_url, SUPABASE_BUCKET2)
                if not new_image_bytes:
                    print(f"Failed to download face image: {new_url}")
                    # Clean up invalid entry
                    supabase.table("new_faces").delete().eq("c_id", new_face["c_id"]).execute()
                    continue

                # Extract face and embedding from face image
                extracted_faces = await face_extraction(new_image_bytes)
                if not extracted_faces:
                    print(f"No faces found in face image: {new_url}")
                    # Clean up processed entry
                    supabase.table("new_faces").delete().eq("c_id", new_face["c_id"]).execute()
                    continue

                # Process the face (should be only one face in extracted face image)
                cropped_face, embedding = extracted_faces[0]
                
                is_duplicate = False
                
                # Check for duplicates in old_faces
                print("Checking for duplicates in old_faces...")
                for old in old_faces:
                    try:
                        old_embedding = await decode_embedding(old["c_embedding"])
                        match = await face_compare(old_embedding, embedding)
                        if match:
                            print(f"Duplicate face found! Removing from new_faces")
                            supabase.table("new_faces").delete().eq("c_id", new_face["c_id"]).execute()
                            is_duplicate = True
                            break
                    except Exception as e:
                        print(f"Error comparing with old face: {e}")
                        continue

                if is_duplicate:
                    continue

                # Add to old_faces (since it's not a duplicate)
                print("Adding to old_faces...")
                supabase.table("old_faces").insert({
                    "c_path": new_url,
                    "c_embedding": await encode_embedding(embedding)
                }).execute()

                matched_id = None
                matched_person = None
                
                # Check for matches in master_faces
                print("Checking for matches in master_faces...")
                for person in master_faces:
                    try:
                        master_embedding = await decode_embedding(person["c_embedding"])
                        match = await face_compare(master_embedding, embedding)
                        if match:
                            matched_id = person["c_id"]
                            matched_person = person
                            print(f"Found match with existing person ID: {matched_id}")
                            break
                    except Exception as e:
                        print(f"Error comparing with master face: {e}")
                        continue

                if matched_id and matched_person:
                    # Existing person - increment visit count
                    try:
                        new_visit_count = matched_person["c_visit"] + 1
                        supabase.table("master_faces").update({
                            "c_visit": new_visit_count
                        }).eq("c_id", matched_id).execute()

                        processed.append({"status": "matched", "id": matched_id})
                        print(f"Updated person ID {matched_id}, visit count: {new_visit_count}")
                        
                    except Exception as e:
                        print(f"Error updating matched person: {e}")
                else:
                    # New person - create entry in master_faces
                    try:
                        gender = await predict_gender(new_image_bytes)
                        age = await predict_age(new_image_bytes)
                        name = f"Person_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                        # Insert new master face
                        supabase.table("master_faces").insert({
                            "c_name": name,
                            "c_path": new_url,  # Store face path in faces bucket
                            "c_embedding": await encode_embedding(embedding),
                            "c_visit": 1,
                            "c_age": age,
                            "c_gender": gender
                        }).execute()

                        processed.append({"status": "new", "name": name})
                        print(f"Created new person: {name}")
                        
                    except Exception as e:
                        print(f"Error creating new person: {e}")

                # Remove from new_faces (processed successfully)
                supabase.table("new_faces").delete().eq("c_id", new_face["c_id"]).execute()
                print(f"Removed {new_url} from new_faces")

            except Exception as e:
                print(f"Error processing face ID {new_face.get('c_id')}: {e}")
                continue

    except Exception as e:
        print(f"Error in process_faces_from_supabase: {e}")
        await asyncio.sleep(10)

    print(f"Face processing completed. Processed {len(processed)} faces.")
    return processed

# Continuous processing function
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
                # Increase wait time if no faces processed repeatedly
                wait_time = min(5 + (consecutive_empty_checks * 2), 30)  # Max 30 seconds
                print(f"No faces processed. Waiting {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                consecutive_empty_checks = 0
                print(f"Successfully processed {len(processed)} faces")
                await asyncio.sleep(1)  # Short wait after processing
                
        except Exception as e:
            print(f"Error in continuous processing: {e}")
            await asyncio.sleep(10)

# To run continuous processing:
# asyncio.run(continuous_face_processing())