import cv2
import time
from paddleocr import PaddleOCR

# Initialize PaddleOCR for detection only (we won't use OCR for reading the text, just detecting the regions)
ocr = PaddleOCR(det=True, rec=False, cls=False, use_angle_cls=True)

# Open webcam
cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

print("Press 'q' to quit.")

rect_top_left = (100, 100)   # (x, y) of the top-left corner
rect_bottom_right = (400, 300)  # (x, y) of the bottom-right corner


# Initialize variables for FPS calculation
prev_time = time.time()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Calculate FPS
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time)
    prev_time = curr_time

    # Perform detection (but no text recognition)
    result = ocr.ocr(frame)

    # Draw bounding boxes around detected text regions
    if result and result[0]:
        for detection in result[0]:  # Each detection contains points (bounding box)
            points = detection[0]  # Get only the bounding box points
            
            # Convert quadrilateral points to integer coordinates
            points = [(int(point[0]), int(point[1])) for point in points]

            # Draw the bounding box (quadrilateral) around the detected text region
            for i in range(4):
                cv2.line(frame, points[i], points[(i + 1) % 4], (0, 255, 0), 2)  # Green lines

    # Display FPS on the top-left corner
    fps_text = f"FPS: {fps:.2f}"
    cv2.putText(frame, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

    # Draw the static rectangle on the frame
    cv2.rectangle(frame, rect_top_left, rect_bottom_right, (0, 255, 0), 2)  # Green rectangle

    # Show frame with detected text bounding boxes
    cv2.imshow("Text Detection (Bounding Boxes Only)", frame)

    # Exit when 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
