from deepface import DeepFace
import numpy as np
import os
import cv2
from PIL import Image

genders = ['Female', 'Male']

def predict_gender(image_path):
    if not os.path.exists(image_path):
        print(f"Image not found: {image_path}")
        return None

    try:
        # print(f"Processing image: {image_path}")
        result = DeepFace.analyze(img_path=image_path, actions=['gender'], enforce_detection=False)

        gender_scores = result[0]['gender']
        predicted_gender = genders[np.argmax(list(gender_scores.values()))]
        confidence = max(gender_scores.values())

        return predicted_gender

    except Exception as e:
        print(f"Error during prediction: {e}")
        return None


def predict_age(image_path):
    image_pil = Image.open(image_path).convert("RGB")

    image_np = np.array(image_pil)

    image_cv = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)



    net = cv2.dnn.readNetFromCaffe('age_prediction.prototxt', 'model.caffemodel')

    blob = cv2.dnn.blobFromImage(image_cv, scalefactor=1.0, size=(224, 224), mean=(104, 117, 123))
    net.setInput(blob)
    output = net.forward()
    bucket_idx = output[0].argmax()

    age = bucket_idx
    age_range = age
    if 0<age<5:
        age_range = "0-5"
    elif 5<age<10:
        age_range = "5-10"
    elif 10<age<15:
        age_range = "10-15"
    elif 15<age<20:
        age_range = "15-20"
    elif 20<age<25:
        age_range = "20-25"
    elif 25<age<30:
        age_range = "25-30"
    elif 30<age<35:
        age_range = "30-35"
    elif 35<age<40:
        age_range = "35-40"
    elif 40<age<45:
        age_range = "40-45"
    elif 45<age<50:
        age_range = "45-50"
    elif 50<age<55:
        age_range = "50-55"
    elif 55<age<60:
        age_range = "55-60"
    else:
        age_range = "70+"
    
    return age_range  # ( bhai if possible keep range thoda big approx width of 10)



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