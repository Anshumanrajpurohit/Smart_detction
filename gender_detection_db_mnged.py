from deepface import DeepFace
import numpy as np
import os
import sqlite3

genders = ['Female', 'Male']

def update_database_with_gender(db_path="../db/face_master.db"):
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all records with image paths
    cursor.execute("SELECT id, name, image_path FROM people")
    records = cursor.fetchall()
    
    print(f"Found {len(records)} records to process")
    
    for record_id, name, image_path in records:
        try:
            # Check if image file exists
            if not os.path.exists(image_path):
                print(f"Image not found: {image_path}")
                cursor.execute("UPDATE people SET gender = ? WHERE id = ?", ("File Not Found", record_id))
                continue
            
            # Analyze gender using DeepFace
            print(f"Processing: {name}")
            gender = DeepFace.analyze(img_path=image_path, actions=['gender'], enforce_detection=False)
            gender_scores = gender[0]['gender']
            predicted_gender = genders[np.argmax(list(gender_scores.values()))]
            confidence = max(gender_scores.values())
            
            # Update database with gender prediction
            cursor.execute("UPDATE people SET gender = ? WHERE id = ?", (predicted_gender, record_id))
            print(f"Updated {name}: {predicted_gender} (confidence: {confidence:.2f})")
            
        except Exception as e:
            print(f"Error processing {name}: {e}")
            cursor.execute("UPDATE people SET gender = ? WHERE id = ?", ("Error", record_id))
    
    conn.commit()
    conn.close()
    print("Database updated successfully!")

# Run the gender detection and database update
update_database_with_gender()
