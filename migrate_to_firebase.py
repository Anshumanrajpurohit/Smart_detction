import sqlite3
import firebase_admin
from firebase_admin import credentials, firestore

# Step 1: Initialize Firebase
cred = credentials.Certificate("serviceAccountKey.json")  # Replace if filename is different
firebase_admin.initialize_app(cred)
db = firestore.client()

# Step 2: Connect to SQLite
conn = sqlite3.connect("your_local_db.sqlite")  # Change if your file name is different
cursor = conn.cursor()

# Step 3: Fetch data from your local table
# Change the query based on your actual table and column names
cursor.execute("SELECT user_id, pace, timestamp FROM pace_predictions")  
rows = cursor.fetchall()

# Step 4: Upload to Firebase
for row in rows:
    doc = {
        "user_id": row[0],
        "pace": row[1],
        "timestamp": row[2]
    }
    db.collection("pace_predictions").add(doc)

print(f"✅ Uploaded {len(rows)} records to Firebase!")

conn.close()
