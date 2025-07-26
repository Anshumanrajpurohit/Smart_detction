from deepface import DeepFace
import numpy as np
import os
import cv2
from PIL import Image

genders = ['Female', 'Male']

def predict_gender(img_bytes):
    try:

        image_path = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)

        result = DeepFace.analyze(img_path=image_path, actions=['gender'], enforce_detection=False)

        gender_scores = result[0]['gender']
        predicted_gender = genders[np.argmax(list(gender_scores.values()))]
        confidence = max(gender_scores.values())

        return predicted_gender

    except Exception as e:
        print(f"Error during prediction: {e}")
        return None


def predict_age(img_bytes):
    image_path = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)



    net = cv2.dnn.readNetFromCaffe('age_prediction.prototxt', 'model.caffemodel')

    blob = cv2.dnn.blobFromImage(image_path, scalefactor=1.0, size=(224, 224), mean=(104, 117, 123))
    net.setInput(blob)
    output = net.forward()
    bucket_idx = output[0].argmax()

    age = bucket_idx
    age_range = age
    if 0<age<10:
        age_range = "0-10"
    elif 10<age<20:
        age_range = "10-20"
    elif 20<age<30:
        age_range = "20-30"
    elif 30<age<40:
        age_range = "30-40"
    elif 40<age<50:
        age_range = "40-50"
    elif 50<age<60:
        age_range = "50-60"
    elif 60<age<70:
        age_range = "60-70"
    elif 70<age<80:
        age_range = "70-80"
    elif 80<age<90:
        age_range = "80-90"
    else:
        age_range = "90+"
    
    return age_range 


# genders = ['Female', 'Male']

# def update_database_with_gender(db_path="../db/face_master.db"):
#     # Connect to database
#     conn = sqlite3.connect(db_path)
#     cursor = conn.cursor()
    
#     # Get all records with image paths
#     cursor.execute("SELECT id, name, image_path FROM people")
#     records = cursor.fetchall()
    
#     print(f"Found {len(records)} records to process")
    
#     for record_id, name, image_path in records:
#         try:
#             # Check if image file exists
#             if not os.path.exists(image_path):
#                 print(f"Image not found: {image_path}")
#                 cursor.execute("UPDATE people SET gender = ? WHERE id = ?", ("File Not Found", record_id))
#                 continue
            
#             # Analyze gender using DeepFace
#             print(f"Processing: {name}")
#             gender = DeepFace.analyze(img_path=image_path, actions=['gender'], enforce_detection=False)
#             gender_scores = gender[0]['gender']
#             predicted_gender = genders[np.argmax(list(gender_scores.values()))]
#             confidence = max(gender_scores.values())
            
#             # Update database with gender prediction
#             cursor.execute("UPDATE people SET gender = ? WHERE id = ?", (predicted_gender, record_id))
#             print(f"Updated {name}: {predicted_gender} (confidence: {confidence:.2f})")
            
#         except Exception as e:
#             print(f"Error processing {name}: {e}")
#             cursor.execute("UPDATE people SET gender = ? WHERE id = ?", ("Error", record_id))
    
#     conn.commit()
#     conn.close()
#     print("Database updated successfully!")

# # Run the gender detection and database update
# update_database_with_gender()