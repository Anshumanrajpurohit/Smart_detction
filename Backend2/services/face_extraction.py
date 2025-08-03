import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis


app = FaceAnalysis(name='buffalo_l')
app.prepare(ctx_id=0, det_size=(640, 640)) 

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