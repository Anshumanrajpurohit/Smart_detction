import sqlite3
import firebase_admin
from firebase_admin import credentials, db

# Load Firebase credentials
cred = credentials.Certificate("bharat-camera-detctnn-firebase-adminsdk-fbsvc-dab4da7a6b.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://bharat-camera-detctnn-default-rtdb.firebaseio.com/'
})

# Connect to SQLite database
conn = sqlite3.connect('db/people.db')
cursor = conn.cursor()

# Fetch all records
cursor.execute("SELECT name, image_path, encoding, visits, first_seen, last_seen, gender, quality_score FROM people")
rows = cursor.fetchall()

# Reference to Firebase
ref = db.reference('people')

# Push each record
for row in rows:
    person_data = {
        'name': row[0],
        'image_path': row[1],
        'encoding': row[2],
        'visits': row[3],
        'first_seen': row[4],
        'last_seen': row[5],
        'gender': row[6],
        'quality_score': row[7]
    }
    ref.push(person_data)

print("✅ Data migration to Firebase completed.")
