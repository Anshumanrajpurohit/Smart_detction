<<<<<<< HEAD
# 📸 Smart_detection

This project focuses on **real-time detection and counting of unique individuals** appearing in a camera frame. Alongside counting, it also **extracts key features** such as:

- **Height**
- **Weight**
- **Gender**
- **Age**

All detected and extracted data is stored in a **structured database** for further analysis and tracking.

---

## 🚀 Features

- ✅ Real-time object/person detection using camera feed  
- ✅ Tracking and counting of **unique individuals**  
- ✅ Facial analysis to predict **gender** and **age**  
- ✅ Height & weight estimation based on visual data and sensor input (if applicable)  
- ✅ Automated storage of data
---

## 📦 Technologies Used

- **Python**
- **OpenCV** – Image processing and real-time video analysis  
- **DeepFace / Dlib / MTCNN** – Facial recognition and feature extraction  
- **SQL / SQLite / MySQL** – Database operations  

---

## 🛠️ Setup Instructions

1. **Clone the Repository**
   ```bash
     git clone https://github.com/your-username/people-counter-feature-extraction.git
     cd people-counter-feature-extraction
   
2. **Create a virtual environment (optional but recommended)**
   ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
3. **Install dependencies**
   ```bash
     pip install -r requirements.txt
4.**Run the program**
```bash
    python main.py
=======
# Face_Count Project

A face detection and recognition system with optional Firebase integration.

## 📁 Folder Structure

- `creating_db.py` – Create the local database (if used)
- `db_face_compare.py` – Compare stored faces with input
- `detecting_storing.py` – Detect faces from webcam and store
- `main-prg-mangr.py` – Main program logic
- `migrate_to_firebase.py` – Upload to Firebase (optional)
- `genedder.py` – (Possibly gender classification)
- `faces/` – Stores captured face images
- `env-reqmt.txt` – Python dependencies

## 🚀 Quickstart

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r env-reqmt.txt
python main-prg-mangr.py
>>>>>>> ce771a6 (all updated)
