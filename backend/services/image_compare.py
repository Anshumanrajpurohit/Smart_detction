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
        # Decode image
        img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            print("❌ Failed to decode image - invalid format or corrupted")
            return []
        
        print(f"📸 Image decoded successfully: {img.shape}")
        
        # Get faces using InsightFace
        faces = app.get(img)
        print(f"🔍 InsightFace detected {len(faces)} faces")
        
        if len(faces) == 0:
            # Try different image preprocessing
            print("🔄 No faces found, trying image enhancements...")
            
            # Convert to grayscale and back to see if it helps
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            enhanced = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            faces = app.get(enhanced)
            print(f"🔍 After enhancement: {len(faces)} faces")
            
            if len(faces) == 0:
                # Try resizing if image is too small/large
                h, w = img.shape[:2]
                if w < 300 or h < 300:
                    resized = cv2.resize(img, (640, 640))
                    faces = app.get(resized)
                    print(f"🔍 After resize: {len(faces)} faces")
                    img = resized  # Use resized image for cropping
        
        results = []
        for i, face in enumerate(faces):
            try:
                box = face.bbox.astype(int)
                print(f"👤 Face {i+1} bbox: {box}")
                
                # Ensure bbox is within image bounds
                h, w = img.shape[:2]
                box[0] = max(0, min(box[0], w-1))  # x1
                box[1] = max(0, min(box[1], h-1))  # y1
                box[2] = max(box[0]+1, min(box[2], w))  # x2
                box[3] = max(box[1]+1, min(box[3], h))  # y2
                
                cropped_face = img[box[1]:box[3], box[0]:box[2]]
                
                if cropped_face.size == 0:
                    print(f"⚠️ Face {i+1} cropping resulted in empty image")
                    continue
                    
                embedding = face.embedding
                print(f"✅ Face {i+1} processed - embedding shape: {embedding.shape}")
                results.append((cropped_face, embedding))
                
            except Exception as e:
                print(f"❌ Error processing face {i+1}: {e}")
                continue
            
        return results
        
    except Exception as e:
        print(f"❌ Error in face extraction: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return []

async def face_compare(emb1, emb2):
    """Compare two face embeddings"""
    try:
        similarity = await cosine_similarity(emb1, emb2)
        return similarity > threshold
    except Exception as e:
        print(f"Error in face comparison: {e}")
        return False

async def download_image_from_url(file_path: str) -> bytes:
    """Download image from Supabase storage - tries multiple buckets"""
    buckets_to_try = ["faces", "android", SUPABASE_BUCKET1, SUPABASE_BUCKET2]
    
    # Remove duplicates while preserving order
    buckets_to_try = list(dict.fromkeys(buckets_to_try))
    
    clean_path = file_path.strip().lstrip('/')
    
    for bucket_name in buckets_to_try:
        try:
            print(f"Trying to download '{clean_path}' from bucket '{bucket_name}'")
            image_bytes = supabase.storage.from_(bucket_name).download(clean_path)
            
            if image_bytes and len(image_bytes) > 0:
                print(f"✅ Successfully downloaded {len(image_bytes)} bytes from '{bucket_name}'")
                return image_bytes
                
        except Exception as e:
            print(f"❌ Failed from bucket '{bucket_name}': {e}")
            continue
    
    print(f"💥 Could not download '{file_path}' from any bucket")
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
        print("📁 Processing images directly from android bucket...")
        
        # Get all images from android bucket
        bucket_images = await get_images_from_bucket(SUPABASE_BUCKET1)
        
        if not bucket_images:
            print("No images found in android bucket")
            return []
        
        print(f"Found {len(bucket_images)} images in android bucket")
        processed_faces = []
        
        for image_file in bucket_images:
            try:
                image_path = image_file['name']
                print(f"🖼️ Processing image: {image_path}")
                
                # Download image
                image_bytes = await download_image_from_url(image_path)
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
                        # Use c_path column (not uuid) to match your database schema
                        supabase.table("new_faces").insert({
                            "c_path": face_filename  # Use the face filename in faces bucket
                        }).execute()
                        
                        processed_faces.append({
                            "original_image": image_path,
                            "face_file": face_filename,
                            "face_index": face_idx
                        })
                        
                        print(f"✅ Added face {face_idx} from {image_path} to processing queue")
                        
                    except Exception as e:
                        print(f"Error processing face {face_idx} from {image_path}: {e}")
                        continue
                        
            except Exception as e:
                print(f"Error processing image {image_file.get('name', 'unknown')}: {e}")
                continue
        
        print(f"🎉 Processed {len(processed_faces)} faces from bucket images")
        return processed_faces
        
    except Exception as e:
        print(f"Error in process_bucket_images: {e}")
        return []

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
        print("🔍 Fetching new faces from database...")
        new_faces_response = supabase.table("new_faces").select("*").execute()
        new_faces = new_faces_response.data
        
        # If new_faces is empty, process images from bucket
        if not new_faces:
            print("📥 No new faces found, checking android bucket for images...")
            bucket_processed = await process_bucket_images()
            
            if not bucket_processed:
                print("⏳ No images processed from bucket, waiting...")
                return []
            
            # After processing bucket images, fetch new_faces again
            new_faces_response = supabase.table("new_faces").select("*").execute()
            new_faces = new_faces_response.data
            if not new_faces:
                print("Still no new faces after bucket processing")
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
                
                # Get the correct path - use c_path (not uuid)
                new_path = new_face.get("c_path")
                face_id = new_face.get("c_id")
                
                if not new_path:
                    print("No c_path found in face data, skipping...")
                    continue
                    
                print(f"Processing face ID {face_id} with path: {new_path}")

                # Download image - will try multiple buckets
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
                            supabase.table("master_faces").insert({
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

    print(f"\n🎉 Processing completed. Total processed: {len(processed)}")
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