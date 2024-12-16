import cv2
import time
import numpy as np
from paddleocr import PaddleOCR
from sort import Sort  # SORT tracking library
from difflib import SequenceMatcher
import csv
import os
from collections import Counter

# Initialize PaddleOCR for both detection and recognition
ocr = PaddleOCR(det=True, rec=True, cls=False, use_angle_cls=True)

# Initialize the SORT tracker
tracker = Sort()

# User-provided master text
master_text = input("Enter the master text to compare: ").strip()
similarity_threshold = 50  # Similarity threshold (in percentage)

# Open webcam
cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

print("Press 'q' to quit.")

# Define the region of interest (ROI) for text detection and recognition
rect_top_left = (100, 100)   # (x, y) of the top-left corner
rect_bottom_right = (400, 300)  # (x, y) of the bottom-right corner
roi_centroid_x = (rect_top_left[0] + rect_bottom_right[0]) // 2  # Calculate ROI centroid (X-axis)

# Create folder for saving final images
output_folder = "final_images"
os.makedirs(output_folder, exist_ok=True)

# CSV file setup: Write headers only once
output_csv = "detected_texts.csv"
with open(output_csv, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["Timestamp", "Process time" ,"Tracking ID", "Detected Text", "Similarity (%)", "Status", "Image Path"])  # Write headers

# Temp image storage for tracking IDs
temp_images = {}

# Set to store processed tracking IDs
processed_ids = set()

# Initialize variables for FPS calculation

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Extract the region of interest (ROI) from the frame
    roi = frame[rect_top_left[1]:rect_bottom_right[1], rect_top_left[0]:rect_bottom_right[0]]

    # Perform OCR on the ROI
    result = ocr.ocr(roi)
    detections = []  # List of detections for SORT
    ocr_texts = []  # List to store OCR results and their bounding boxes

    # Check if result contains data
    if result and result[0]:  # Ensure result is not None and contains detected lines
        for line in result[0]:
            text = line[1][0]  # Extract detected text
            confidence = line[1][1]  # Extract confidence level
            points = line[0]  # Get bounding box points

            # Convert quadrilateral points to bounding box coordinates
            x_min = int(min(point[0] for point in points)) + rect_top_left[0]  # Add ROI offset
            y_min = int(min(point[1] for point in points)) + rect_top_left[1]
            x_max = int(max(point[0] for point in points)) + rect_top_left[0]
            y_max = int(max(point[1] for point in points)) + rect_top_left[1]

            # Add detection to the list (format: [x_min, y_min, x_max, y_max, confidence])
            detections.append([x_min, y_min, x_max, y_max, confidence])

            # Store the OCR result along with its bounding box
            ocr_texts.append((text, confidence, (x_min, y_min, x_max, y_max)))

        starttime = time.time()     ########### start time #########################################################################################

    # Convert detections to a NumPy array
    detections = np.array(detections)

    # Ensure detections array has the correct shape
    if detections.size == 0:  # If there are no detections, create an empty array with shape (0, 5)
        detections = np.empty((0, 5))

    # Update SORT tracker with current detections
    tracked_objects = tracker.update(detections)  # Returns tracked objects as [x_min, y_min, x_max, y_max, track_id]

    # Match OCR results with tracked objects and process them
    for obj in tracked_objects:
        x_min, y_min, x_max, y_max, track_id = map(int, obj)  # Extract tracking info

        # Skip if the tracking ID has already been processed
        if track_id in processed_ids:
            continue

        # Calculate the centroid of the tracked box
        tracked_centroid_x = (x_min + x_max) // 2

        # Find the OCR result associated with this bounding box
        matched_text = ""
        for text, confidence, bbox in ocr_texts:
            bx_min, by_min, bx_max, by_max = bbox
            iou = max(
                0,
                min(x_max, bx_max) - max(x_min, bx_min)
            ) * max(0, min(y_max, by_max) - max(y_min, by_min))  # Intersection area

            # Match if bounding boxes overlap significantly (adjust threshold as needed)
            if iou > 0:
                matched_text = text
                break

        # Skip if no matched text is found
        if not matched_text:
            continue

        # Compute similarity
        similarity = SequenceMatcher(None, master_text, matched_text).ratio() * 100  # Similarity percentage

        # Skip if the similarity is below the threshold
        if similarity < similarity_threshold:
            continue

        if similarity == 100:
            display_text = f"{matched_text} (OK)"
            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
            cv2.rectangle(frame, (0, 0), (640, 480), (0, 255, 0), 4)
            cv2.putText(frame, display_text, (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            display_text = f"{matched_text} (NG)"
            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 0, 255), 2)
            cv2.rectangle(frame, (0, 0), (640, 480), (0, 0, 255), 4)
            cv2.putText(frame, display_text, (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # Skip if the box's centroid doesn't align with ROI's centroid
        if abs(tracked_centroid_x - roi_centroid_x) > 30:  # Allow a small threshold (±10 pixels)
            continue

        # Save temporary images for majority voting
        if track_id not in temp_images:
            temp_images[track_id] = []

        # Add the frame to the buffer (max 5 images)
        if len(temp_images[track_id]) < 1:
            frame_path = f"temp_image_{track_id}_{len(temp_images[track_id])}.jpg"
            cv2.imwrite(frame_path, frame)  # Save temporary frame
            temp_images[track_id].append((matched_text, frame_path))

        # If the buffer for this tracking ID is full, process it
        if len(temp_images[track_id]) == 1:
            # Perform majority voting
            text_counts = Counter([entry[0] for entry in temp_images[track_id]])
            majority_text, _ = text_counts.most_common(1)[0]

            # Select one of the majority images
            majority_image_path = next(path for text, path in temp_images[track_id] if text == majority_text)

            # Save the final image with a unique name
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            final_image_path = os.path.join(output_folder, f"final_image_{track_id}_{timestamp}.jpg")

            # Ensure the final image file name is unique
            original_final_image_path = final_image_path
            counter = 1
            while os.path.exists(final_image_path):
                final_image_path = original_final_image_path.replace(".jpg", f"_{counter}.jpg")
                counter += 1

            os.rename(majority_image_path, final_image_path)

            # Write the result to CSV
            status = "OK" if similarity == 100 else "NG"
            endtime = time.time()
            process_time = endtime - starttime
            with open(output_csv, mode="a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow([timestamp,process_time,track_id, majority_text, f"{similarity:.2f}", status, final_image_path])

            # Delete all temporary images except the selected final one
            for _, path in temp_images[track_id]:
                if path != majority_image_path and os.path.exists(path):
                    os.remove(path)

            # Mark the tracking ID as processed
            processed_ids.add(track_id)

            # Remove the tracking ID from temp_images
            del temp_images[track_id]

    # Draw the ROI on the frame
    cv2.rectangle(frame, rect_top_left, rect_bottom_right, (0, 255, 0), 2)

    

    # Show the frame
    cv2.imshow("Text Detection Inside ROI with Tracking", frame)

    # Exit when 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
