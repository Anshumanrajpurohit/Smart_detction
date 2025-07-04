import cv2
import time
cap = cv2.VideoCapture(0)
start_time = time.time()

while (time.time() - start_time) < 40:
    ret, frame = cap.read()
    if not ret:
        print("❌ Failed to grab frame")
        continue

    cv2.imshow("Face Detection Preview", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("🛑 Detection manually stopped.")
        break

cap.release()
cv2.destroyAllWindows()
print("✅ Detection cycle complete")
