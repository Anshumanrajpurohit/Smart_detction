import sqlite3
import pickle
import face_recognition
import numpy as np
from datetime import datetime
import os

def compare_faces_strict(encoding1, encoding2, strict_threshold=0.45, loose_threshold=0.6):
    """
    Improved face comparison with better thresholds
    strict_threshold: For very confident matches (duplicates)
    loose_threshold: For similar face matches (same person)
    """
    distance = face_recognition.face_distance([encoding1], encoding2)[0]
    
    if distance < strict_threshold:
        return True, distance, "exact_match"
    elif distance < loose_threshold:
        return True, distance, "similar_match"
    else:
        return False, distance, "no_match"

def clear_new_faces_db():
    """Clear all entries from new_faces database and delete associated images"""
    try:
        conn = sqlite3.connect("./db/new_faces.db")
        cursor = conn.cursor()
        
        # Get all image paths before deletion
        cursor.execute("SELECT image_path FROM faces WHERE image_path IS NOT NULL")
        image_paths = [row[0] for row in cursor.fetchall()]
        
        # Delete all records
        cursor.execute("DELETE FROM faces")
        conn.commit()
        conn.close()
        
        # Delete associated images
        deleted_count = 0
        for image_path in image_paths:
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                    deleted_count += 1
                except Exception as e:
                    print(f"⚠️ Could not delete {image_path}: {e}")
        
        print(f"🧹 Cleared new_faces database - removed {deleted_count} images")
        return True
        
    except Exception as e:
        print(f"❌ Error clearing new_faces: {e}")
        return False

def process_interval():
    """
    Enhanced face comparison process with improved logic:
    1. Compare new faces with old faces (remove exact duplicates)
    2. Compare remaining new faces with master database (similar faces = increase visits)
    3. Add truly new faces to master database
    4. Move all processed faces to old_faces for future reference
    """
    print("🔍 Starting enhanced face comparison process...")
    
    try:
        # Connect to all databases
        new_conn = sqlite3.connect("./db/new_faces.db")
        old_conn = sqlite3.connect("./db/old_faces.db")
        master_conn = sqlite3.connect("./db/face_master.db")
        
        new_cursor = new_conn.cursor()
        old_cursor = old_conn.cursor()
        master_cursor = master_conn.cursor()
        
        # Ensure all tables exist with proper schema
        old_cursor.execute('''
            CREATE TABLE IF NOT EXISTS faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_path TEXT,
                encoding BLOB NOT NULL,
                quality_score REAL DEFAULT 0.5,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        master_cursor.execute('''
            CREATE TABLE IF NOT EXISTS people (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL DEFAULT 'Unknown',
                image_path TEXT,
                encoding BLOB NOT NULL,
                quality_score REAL DEFAULT 0.5,
                visits INTEGER DEFAULT 1,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Get all new faces
        new_cursor.execute("SELECT id, image_path, encoding, quality_score, timestamp FROM faces")
        new_faces = new_cursor.fetchall()
        
        if not new_faces:
            print("ℹ️ No new faces to process")
            return True
        
        print(f"📊 Processing {len(new_faces)} new faces...")
        
        # Get all old faces for duplicate checking
        old_cursor.execute("SELECT encoding, quality_score FROM faces")
        old_faces = old_cursor.fetchall()
        
        # Get all master faces for similarity checking
        master_cursor.execute("SELECT id, name, encoding, visits, quality_score FROM people")
        master_people = master_cursor.fetchall()
        
        # Statistics
        processed_count = 0
        duplicate_count = 0
        similar_count = 0
        new_people_count = 0
        faces_to_remove = []
        
        for new_face_id, new_image_path, new_encoding_blob, new_quality, new_timestamp in new_faces:
            try:
                new_encoding = pickle.loads(new_encoding_blob)
                new_quality = new_quality if new_quality else 0.5
                is_processed = False
                
                print(f"🔍 Processing face ID {new_face_id}...")
                
                # STEP 1: Check for exact duplicates in old_faces
                for old_encoding_blob, old_quality in old_faces:
                    try:
                        old_encoding = pickle.loads(old_encoding_blob)
                        is_match, distance, match_type = compare_faces_strict(old_encoding, new_encoding)
                        
                        if is_match and match_type == "exact_match":
                            print(f"❌ Face {new_face_id} is exact duplicate (distance: {distance:.3f}) - removing")
                            faces_to_remove.append(new_face_id)
                            
                            # Delete the duplicate image
                            if new_image_path and os.path.exists(new_image_path):
                                os.remove(new_image_path)
                                print(f"🗑️ Deleted duplicate image: {new_image_path}")
                            
                            duplicate_count += 1
                            is_processed = True
                            break
                            
                    except Exception as e:
                        print(f"⚠️ Error comparing with old face: {e}")
                        continue
                
                # STEP 2: If not a duplicate, check master database for similar faces
                if not is_processed:
                    best_match_id = None
                    best_match_distance = float('inf')
                    best_match_name = None
                    
                    for master_id, master_name, master_encoding_blob, master_visits, master_quality in master_people:
                        try:
                            master_encoding = pickle.loads(master_encoding_blob)
                            is_match, distance, match_type = compare_faces_strict(master_encoding, new_encoding)
                            
                            if is_match and distance < best_match_distance:
                                best_match_id = master_id
                                best_match_distance = distance
                                best_match_name = master_name
                                
                        except Exception as e:
                            print(f"⚠️ Error comparing with master person {master_id}: {e}")
                            continue
                    
                    # If found similar face in master, update visits
                    if best_match_id:
                        print(f"✅ Face {new_face_id} matches person '{best_match_name}' (ID: {best_match_id})")
                        print(f"📊 Distance: {best_match_distance:.3f}, increasing visit count")
                        
                        # Update visits and last_seen
                        master_cursor.execute("""
                            UPDATE people 
                            SET visits = visits + 1, last_seen = CURRENT_TIMESTAMP 
                            WHERE id = ?
                        """, (best_match_id,))
                        
                        # Move to old_faces for future duplicate detection
                        old_cursor.execute("""
                            INSERT INTO faces (image_path, encoding, quality_score, timestamp) 
                            VALUES (?, ?, ?, ?)
                        """, (None, new_encoding_blob, new_quality, new_timestamp))
                        
                        faces_to_remove.append(new_face_id)
                        
                        # Delete the image since it's just a visit, not new person
                        if new_image_path and os.path.exists(new_image_path):
                            os.remove(new_image_path)
                            print(f"🗑️ Deleted visit image: {new_image_path}")
                        
                        similar_count += 1
                        is_processed = True
                    
                    # STEP 3: If no match found, add as new person
                    if not is_processed:
                        print(f"🆕 Face {new_face_id} is a completely new person")
                        
                        # Generate unique name
                        person_name = f"Person_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{new_face_id}"
                        
                        # Add to master database
                        master_cursor.execute("""
                            INSERT INTO people (name, image_path, encoding, quality_score, visits, first_seen, last_seen) 
                            VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """, (person_name, new_image_path, new_encoding_blob, new_quality))
                        
                        new_person_id = master_cursor.lastrowid
                        print(f"👤 Added new person '{person_name}' with ID {new_person_id}")
                        
                        # Add to old_faces for future reference
                        old_cursor.execute("""
                            INSERT INTO faces (image_path, encoding, quality_score, timestamp) 
                            VALUES (?, ?, ?, ?)
                        """, (new_image_path, new_encoding_blob, new_quality, new_timestamp))
                        
                        faces_to_remove.append(new_face_id)
                        new_people_count += 1
                
                processed_count += 1
                
            except Exception as e:
                print(f"❌ Error processing face {new_face_id}: {e}")
                continue
        
        # Remove all processed faces from new_faces database
        if faces_to_remove:
            placeholders = ','.join('?' * len(faces_to_remove))
            new_cursor.execute(f"DELETE FROM faces WHERE id IN ({placeholders})", faces_to_remove)
            print(f"🧹 Removed {len(faces_to_remove)} processed faces from new_faces database")
        
        # Commit all changes
        new_conn.commit()
        old_conn.commit()
        master_conn.commit()
        
        print(f"✅ Face comparison process completed!")
        print(f"📊 Summary:")
        print(f"   • Total faces processed: {processed_count}")
        print(f"   • Exact duplicates removed: {duplicate_count}")
        print(f"   • Similar faces (visits increased): {similar_count}")
        print(f"   • New people added: {new_people_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in face comparison process: {e}")
        return False
        
    finally:
        # Close all connections
        try:
            new_conn.close()
            old_conn.close()
            master_conn.close()
        except:
            pass

def print_database_stats():
    """Print detailed statistics for all databases"""
    print("\n📊 DATABASE STATISTICS:")
    print("-" * 50)
    
    databases = [
        ("new_faces.db", "faces", "New Faces (Pending)"),
        ("old_faces.db", "faces", "Old Faces (Processed)"), 
        ("face_master.db", "people", "Known People")
    ]
    
    for db_name, table_name, display_name in databases:
        try:
            conn = sqlite3.connect(f"./db/{db_name}")
            cursor = conn.cursor()
            
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            
            print(f"📈 {display_name}: {count} records")
            
            # Additional stats for face_master
            if db_name == "face_master.db" and count > 0:
                cursor.execute("SELECT SUM(visits) FROM people")
                total_visits = cursor.fetchone()[0] or 0
                print(f"   • Total visits across all people: {total_visits}")
                
                cursor.execute("SELECT COUNT(*) FROM people WHERE visits > 1")
                returning_people = cursor.fetchone()[0]
                print(f"   • People with multiple visits: {returning_people}")
                
                cursor.execute("SELECT name, visits FROM people ORDER BY visits DESC LIMIT 3")
                top_visitors = cursor.fetchall()
                if top_visitors:
                    print(f"   • Top visitors:")
                    for name, visits in top_visitors:
                        print(f"     - {name}: {visits} visits")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Error reading {db_name}: {e}")

def get_people_list():
    """Get list of all people from master database"""
    try:
        conn = sqlite3.connect("./db/face_master.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, visits, first_seen, last_seen, quality_score
            FROM people 
            ORDER BY visits DESC, last_seen DESC
        """)
        
        people = cursor.fetchall()
        conn.close()
        return people
        
    except Exception as e:
        print(f"❌ Error getting people list: {e}")
        return []

def reset_system(keep_master=False):
    """Reset the system databases"""
    try:
        if not keep_master:
            response = input("⚠️ This will delete ALL data including known people! Continue? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Reset cancelled")
                return False
        
        # Clear new_faces and old_faces
        for db_name in ['new_faces', 'old_faces']:
            if not keep_master or db_name != 'face_master':
                db_path = f"./db/{db_name}.db"
                if os.path.exists(db_path):
                    os.remove(db_path)
                    print(f"🗑️ Deleted {db_name}.db")
        
        if not keep_master:
            db_path = "./db/face_master.db"
            if os.path.exists(db_path):
                os.remove(db_path)
                print(f"🗑️ Deleted face_master.db")
        
        # Clean up images directory
        faces_dir = "faces"
        if os.path.exists(faces_dir):
            for filename in os.listdir(faces_dir):
                file_path = os.path.join(faces_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            print(f"🗑️ Cleaned up faces directory")
        
        print("✅ System reset completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error during reset: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Enhanced Face Comparison Module")
    print("=" * 50)
    
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'process':
            process_interval()
        elif command == 'stats':
            print_database_stats()
        elif command == 'people':
            people = get_people_list()
            if people:
                print(f"\n👥 All Known People ({len(people)} total):")
                for person_id, name, visits, first_seen, last_seen, quality in people:
                    print(f"   • ID {person_id}: {name}")
                    print(f"     Visits: {visits}, Quality: {quality:.3f if quality else 0:.3f}")
                    print(f"     First seen: {first_seen}, Last seen: {last_seen}")
            else:
                print("👥 No people found in database")
        elif command == 'clear_new':
            clear_new_faces_db()
        elif command == 'reset':
            reset_system(keep_master=False)
        elif command == 'soft_reset':
            reset_system(keep_master=True)
        else:
            print("❌ Unknown command")
            print("Available commands: process, stats, people, clear_new, reset, soft_reset")
    else:
        print("🎯 Available commands:")
        print("  process     - Run face comparison process")
        print("  stats       - Show database statistics") 
        print("  people      - Show all known people")
        print("  clear_new   - Clear only new_faces database")
        print("  reset       - Full system reset (deletes everything)")
        print("  soft_reset  - Reset but keep known people")
        print("\n💡 Usage: python db_face_compare.py [command]")