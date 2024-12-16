import cv2
import time
from paddleocr import PaddleOCR

# Initialize PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='en')  # Set lang='en' for English OCR

# Open webcam feed
cap = cv2.VideoCapture(1)  # 1 indicates the external webcam, use 0 for default
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 680)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

print("Press 'q' to quit the application.")

# Initialize variables for FPS calculation
prev_time = time.time()

while True:
    ret, frame = cap.read()
    
    if not ret:
        print("Error: Could not read frame.")
        break

    # Resize frame for better performance
    # frame_resized = cv2.resize(frame, (1080, 720))

    # Calculate FPS
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time)
    prev_time = curr_time

    # OCR processing: Convert frame to RGB as PaddleOCR requires RGB input
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = ocr.ocr(rgb_frame, cls=True)

    # Check if result contains data
    if result and result[0]:  # Ensure result is not None and contains detected lines
        for line in result[0]:
            text = line[1][0]  # Extract detected text
            confidence = line[1][1]  # Extract confidence level
            points = line[0]  # Get bounding box points

            # Draw bounding box
            points = [(int(point[0]), int(point[1])) for point in points]
            for i in range(4):
                cv2.line(frame, points[i], points[(i + 1) % 4], (0, 255, 0), 2)

            # Put detected text on the frame
            text_position = (points[0][0], points[0][1] - 10)
            cv2.putText(frame, f"{text} ({confidence:.2f})", text_position,
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            print(text)
    else:
        # Display message when no text is detected
        cv2.putText(frame, "No text detected", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

    # Display FPS on the top-right corner
    fps_text = f"FPS: {fps:.2f}"
    cv2.putText(frame, fps_text, (frame.shape[1] - 150, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

    # Display the annotated frame
    cv2.imshow("Live OCR with FPS", frame)

    # Break loop on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
cap.release()
cv2.destroyAllWindows()
