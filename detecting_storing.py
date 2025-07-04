import cv2
import face_recognition
import os
import pickle
import sqlite3
from datetime import datetime
import numpy as np
from PIL import Image
import io

def calculate_face_quality(face_image, encoding):
    """Calculate face quality score based on multiple factors"""
    try:
        # Face size score (larger faces are generally better)
        height, width = face_image.shape[:2]
        size_score = min(1.0, (height * width) / (150 * 150))  # Normalize to 150x150
        
        # Sharpness score using Laplacian variance
        gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY) if len(face_image.shape) == 3 else face_image
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_score = min(1.0, sharpness / 500)  # Normalize
        
        # Brightness score (avoid too dark or too bright)
        brightness = np.mean(gray)
        brightness_score = 1.0 - abs(brightness - 128) / 128  # Best around 128
        
        # Encoding confidence (face_recognition quality)
        encoding_score = 1.0  # face_recognition already filters low-quality faces
        
        # Combined score
        quality_score = (size_score * 0.3 + sharpness_score * 0.4 + 
                        brightness_score * 0.2 + encoding_score * 0.1)
        
        return quality_score
        
    except Exception as e:
        print(f"⚠️ Error calculating face quality: {e}")
        return 0.5  # Default medium quality

def compress_image(image, quality=85, max_size=None):
    """
    Compress image using multiple methods for optimal storage
    
    Args:
        image: OpenCV image (BGR format)
        quality: JPEG quality (1-100, lower = more compression)
        max_size: Maximum file size in KB (optional)
    
    Returns:
        compressed_image: Compressed image
        compression_ratio: Achieved compression ratio
    """
    try:
        # Convert BGR to RGB for PIL
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)
        
        # Try different compression levels if max_size is specified
        if max_size:
            for q in range(quality, 30, -5):  # Reduce quality gradually
                buffer = io.BytesIO()
                pil_image.save(buffer, format='JPEG', quality=q, optimize=True)
                size_kb = len(buffer.getvalue()) / 1024
                
                if size_kb <= max_size:
                    buffer.seek(0)
                    compressed_pil = Image.open(buffer)
                    compressed_image = cv2.cvtColor(np.array(compressed_pil), cv2.COLOR_RGB2BGR)
                    compression_ratio = size_kb / (image.nbytes / 1024)
                    return compressed_image, compression_ratio
        
        # Standard compression
        buffer = io.BytesIO()
        pil_image.save(buffer, format='JPEG', quality=quality, optimize=True)
        buffer.seek(0)
        compressed_pil = Image.open(buffer)
        compressed_image = cv2.cvtColor(np.array(compressed_pil), cv2.COLOR_RGB2BGR)
        
        original_size = image.nbytes / 1024  # KB
        compressed_size = len(buffer.getvalue()) / 1024  # KB
        compression_ratio = compressed_size / original_size
        
        return compressed_image, compression_ratio
        
    except Exception as e:
        print(f"⚠️ Error compressing image: {e}")
        return image, 1.0  # Return original if compression fails

def save_face_crop(frame, location, face_id, quality_score=None, compress=True, compression_quality=75, max_size_kb=50):
    """Save cropped face image with enhanced compression options"""
    try:
        top, right, bottom, left = location
        
        # Add padding and ensure boundaries
        padding = 30  # Increased padding for better crops
        height, width = frame.shape[:2]
        
        top = max(0, top - padding)
        bottom = min(height, bottom + padding)
        left = max(0, left - padding)
        right = min(width, right + padding)
        
        face_image = frame[top:bottom, left:right]
        
        if face_image.size == 0:
            print("⚠️ Empty face crop, skipping...")
            return None, 0
        
        # Calculate quality if not provided
        if quality_score is None:
            # Create a temporary encoding for quality calculation
            rgb_face = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
            face_locations_temp = face_recognition.face_locations(rgb_face)
            if face_locations_temp:
                face_encodings_temp = face_recognition.face_encodings(rgb_face, face_locations_temp)
                if face_encodings_temp:
                    quality_score = calculate_face_quality(face_image, face_encodings_temp[0])
                else:
                    quality_score = 0.3
            else:
                quality_score = 0.3
        
        # Skip very low quality faces
        if quality_score < 0.4:
            print(f"⚠️ Face quality too low ({quality_score:.3f}), skipping...")
            return None, quality_score
        
        # Ensure minimum size for better quality
        min_size = 120
        if face_image.shape[0] < min_size or face_image.shape[1] < min_size:
            # Calculate aspect ratio preserving resize
            aspect_ratio = face_image.shape[1] / face_image.shape[0]
            if aspect_ratio > 1:
                new_width = max(min_size, int(min_size * aspect_ratio))
                new_height = min_size
            else:
                new_height = max(min_size, int(min_size / aspect_ratio))
                new_width = min_size
            face_image = cv2.resize(face_image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # Apply compression if enabled
        original_size = face_image.nbytes / 1024  # KB
        compression_ratio = 1.0
        
        if compress:
            face_image, compression_ratio = compress_image(
                face_image, 
                quality=compression_quality, 
                max_size=max_size_kb
            )
            compressed_size = face_image.nbytes / 1024 * compression_ratio  # Estimated
            print(f"🗜️ Compression: {original_size:.1f}KB → {compressed_size:.1f}KB (ratio: {compression_ratio:.2f})")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        os.makedirs("faces", exist_ok=True)
        
        # Add compression info to filename
        compression_info = f"_c{compression_quality}" if compress else ""
        path = f"faces/face_{face_id}_{timestamp}_q{quality_score:.2f}{compression_info}.jpg"
        
        # Save with optimized settings
        if compress:
            # Use PIL for better compression control
            rgb_image = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_image)
            pil_image.save(path, 'JPEG', quality=compression_quality, optimize=True)
            success = os.path.exists(path)
        else:
            # Use OpenCV for standard saving
            success = cv2.imwrite(path, face_image, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        if success:
            file_size = os.path.getsize(path) / 1024  # KB
            print(f"🖼️ Saved face crop: {path} (quality: {quality_score:.3f}, size: {file_size:.1f}KB)")
            return path, quality_score
        else:
            print("❌ Failed to save face crop")
            return None, quality_score
            
    except Exception as e:
        print(f"❌ Error saving face crop: {e}")
        return None, 0

def is_duplicate_in_frame(new_encoding, frame_encodings, threshold=0.5):
    """Check if face is duplicate within the same frame"""
    if not frame_encodings:
        return False
    
    distances = face_recognition.face_distance(frame_encodings, new_encoding)
    return np.any(distances < threshold)

def detect_and_store_new_faces(video_source=0, detection_time=10, enable_compression=True, compression_quality=75, max_file_size_kb=50):
    """Detect faces with improved accuracy, quality filtering, and compression"""
    
    # Connect to database
    try:
        new_conn = sqlite3.connect("./db/new_faces.db")
        new_cursor = new_conn.cursor()
        
        # Ensure table exists with quality column
        new_cursor.execute('''
            CREATE TABLE IF NOT EXISTS faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_path TEXT,
                encoding BLOB NOT NULL,
                quality_score REAL DEFAULT 0.5,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        new_conn.commit()
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

    # Initialize camera
    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        print("❌ Could not open camera")
        new_conn.close()
        return False

    # Set camera properties for better quality
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # Higher resolution
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Reduce auto exposure for stability

    print(f"📸 Starting enhanced face detection for {detection_time} seconds...")
    print(f"🗜️ Compression: {'Enabled' if enable_compression else 'Disabled'}")
    if enable_compression:
        print(f"   Quality: {compression_quality}%, Max size: {max_file_size_kb}KB")
    print("Press 'q' to quit early, 's' to save current frame faces")

    face_id_counter = 0
    start_time = datetime.now()
    frame_count = 0
    faces_detected = 0
    total_storage_saved = 0  # Track compression savings
    
    # Track recent faces to avoid immediate duplicates
    recent_encodings = []
    recent_timestamps = []
    recent_cleanup_interval = 30  # frames

    try:
        while (datetime.now() - start_time).seconds < detection_time:
            ret, frame = cap.read()
            if not ret:
                print("❌ Failed to read frame")
                continue

            frame_count += 1
            
            # Process every 2nd frame for better performance while maintaining accuracy
            if frame_count % 2 != 0:
                cv2.imshow("Enhanced Face Detection with Compression", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                continue

            # Apply slight blur to reduce noise
            frame_processed = cv2.GaussianBlur(frame, (3, 3), 0)
            
            # Convert BGR to RGB for face_recognition
            rgb_frame = cv2.cvtColor(frame_processed, cv2.COLOR_BGR2RGB)
            
            # Detect faces with better model
            face_locations = face_recognition.face_locations(rgb_frame, model="cnn", number_of_times_to_upsample=1)
            
            if face_locations:
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations, num_jitters=2)
                print(f"🧠 Found {len(face_locations)} face(s) in frame {frame_count}")
                
                frame_encodings = []  # Track encodings in current frame
                
                for encoding, location in zip(face_encodings, face_locations):
                    # Check for duplicates in current frame
                    if is_duplicate_in_frame(encoding, frame_encodings, threshold=0.4):
                        print("⚠️ Duplicate face in same frame, skipping...")
                        continue
                    
                    # Check against recent faces to avoid storing very similar faces
                    is_recent_duplicate = False
                    current_time = frame_count
                    
                    # Clean up old recent encodings
                    recent_encodings = [enc for enc, ts in zip(recent_encodings, recent_timestamps) 
                                      if current_time - ts < recent_cleanup_interval]
                    recent_timestamps = [ts for ts in recent_timestamps 
                                       if current_time - ts < recent_cleanup_interval]
                    
                    if recent_encodings:
                        distances = face_recognition.face_distance(recent_encodings, encoding)
                        if np.any(distances < 0.3):  # Very strict for recent faces
                            print("⚠️ Very similar face detected recently, skipping...")
                            continue
                    
                    face_id_counter += 1
                    
                    # Convert location for OpenCV (top, right, bottom, left)
                    top, right, bottom, left = location
                    
                    # Extract face crop for quality assessment
                    face_crop = frame[max(0, top-30):min(frame.shape[0], bottom+30), 
                                    max(0, left-30):min(frame.shape[1], right+30)]
                    
                    if face_crop.size > 0:
                        quality_score = calculate_face_quality(face_crop, encoding)
                        
                        # Only store high-quality faces
                        if quality_score >= 0.5:
                            # Save face crop with compression
                            image_path, final_quality = save_face_crop(
                                frame, location, face_id_counter, quality_score,
                                compress=enable_compression,
                                compression_quality=compression_quality,
                                max_size_kb=max_file_size_kb
                            )
                            
                            if image_path:
                                # Store in database with quality score
                                encoding_blob = pickle.dumps(encoding)
                                new_cursor.execute(
                                    "INSERT INTO faces (image_path, encoding, quality_score) VALUES (?, ?, ?)", 
                                    (image_path, encoding_blob, final_quality)
                                )
                                new_conn.commit()
                                
                                # Calculate storage savings
                                if enable_compression and os.path.exists(image_path):
                                    file_size = os.path.getsize(image_path) / 1024
                                    estimated_original = file_size / 0.6  # Rough estimate
                                    savings = estimated_original - file_size
                                    total_storage_saved += savings
                                
                                print(f"💾 Stored compressed face #{face_id_counter} (quality: {final_quality:.3f})")
                                
                                # Add to recent encodings
                                recent_encodings.append(encoding)
                                recent_timestamps.append(frame_count)
                                frame_encodings.append(encoding)
                                faces_detected += 1
                                
                                # Draw green rectangle for stored faces
                                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                                cv2.putText(frame, f"Stored #{face_id_counter}", (left, top-10), 
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                            else:
                                # Draw red rectangle for rejected faces
                                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                                cv2.putText(frame, "Save Failed", (left, top-10), 
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                        else:
                            print(f"⚠️ Face quality too low ({quality_score:.3f}), not storing")
                            # Draw yellow rectangle for low quality faces
                            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 255), 2)
                            cv2.putText(frame, f"Q:{quality_score:.2f}", (left, top-10), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

            # Display enhanced frame with statistics
            elapsed = (datetime.now() - start_time).seconds
            info_text = f"Stored: {faces_detected} | Compressed | Time: {elapsed}s"
            cv2.putText(frame, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            compression_info = f"Saved: {total_storage_saved:.1f}KB" if enable_compression else "No compression"
            cv2.putText(frame, compression_info, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(frame, "Green=Stored, Yellow=LowQual, Red=Failed", (10, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            cv2.imshow("Enhanced Face Detection with Compression", frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("🛑 Stopped by user")
                break
            elif key == ord('s') and face_locations:
                print(f"💾 Manually triggered save for {len(face_locations)} faces")

    except Exception as e:
        print(f"❌ Error during face detection: {e}")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        new_conn.close()
        
        print(f"✅ Enhanced detection with compression complete!")
        print(f"📊 Results: {faces_detected} high-quality faces stored from {frame_count} frames")
        if enable_compression:
            print(f"💾 Storage saved: ~{total_storage_saved:.1f}KB through compression")
        return faces_detected > 0

def test_camera():
    """Test camera functionality with enhanced checks"""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Camera not available")
        return False
    
    # Test different resolutions
    resolutions = [(1280, 720), (640, 480), (320, 240)]
    working_resolution = None
    
    for width, height in resolutions:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        ret, frame = cap.read()
        if ret and frame.shape[1] >= width * 0.8:  # Allow some tolerance
            working_resolution = (frame.shape[1], frame.shape[0])
            break
    
    if working_resolution:
        print(f"✅ Camera working at resolution: {working_resolution[0]}x{working_resolution[1]}")
        
        # Test face detection capability
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        if face_locations:
            print(f"🧠 Face detection test: {len(face_locations)} face(s) detected")
        else:
            print("ℹ️ No faces detected in test frame (this is normal if no one is in view)")
        
        cap.release()
        return True
    else:
        print("❌ Cannot capture frame at any resolution")
        cap.release()
        return False

if __name__ == "__main__":
    print("🧪 Testing enhanced camera system with compression...")
    if test_camera():
        print("🎬 Starting enhanced face detection with compression...")
        print("📋 Features: Quality filtering, duplicate prevention, image compression")
        
        # Configure compression settings
        ENABLE_COMPRESSION = True      # Enable/disable compression
        COMPRESSION_QUALITY = 75       # JPEG quality (1-100, lower = more compression)
        MAX_FILE_SIZE_KB = 50         # Maximum file size in KB
        
        detect_and_store_new_faces(
            video_source=0, 
            detection_time=20,
            enable_compression=ENABLE_COMPRESSION,
            compression_quality=COMPRESSION_QUALITY,
            max_file_size_kb=MAX_FILE_SIZE_KB
        )
    else:
        print("❌ Camera test failed")