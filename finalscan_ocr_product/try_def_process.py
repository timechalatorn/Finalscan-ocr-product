import cv2
import time
import numpy as np
from paddleocr import PaddleOCR
from sort import Sort  # SORT tracking library
from difflib import SequenceMatcher
import csv
import os
from collections import Counter
import json

# Global variables for better modularization
ocr = None
tracker = None
temp_images = {}
processed_ids = set()
starttime = None


def initialize_system():
    """Initialize the OCR engine, tracker, and create necessary folders."""
    global ocr, tracker
    # Initialize PaddleOCR for detection and recognition
    ocr = PaddleOCR(det=True, rec=True, cls=False, use_angle_cls=True)

    # Initialize the SORT tracker
    tracker = Sort()

    # Create folder for saving final images
    output_folder = "final_images"
    os.makedirs(output_folder, exist_ok=True)

    print("System initialized successfully.")


def write_csv_header(output_csv="detected_texts.csv"):
    """Write the header for the output CSV file."""
    with open(output_csv, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "Process time", "Tracking ID", "Detected Text", "Similarity (%)", "Status", "Image Path"])


def get_detections_from_ocr(roi, rect_top_left, frame):
    """
    Perform OCR on the ROI and return detections and OCR results.
    Adjust bounding box coordinates to align with the full frame.
    """
    global starttime
    result = ocr.ocr(roi)
    detections = []
    ocr_texts = []

    if result and result[0]:  # Ensure result is not None and contains detected lines
        for line in result[0]:
            text = line[1][0]  # Detected text
            confidence = line[1][1]  # Confidence level
            points = line[0]  # Bounding box points (quadrilateral)

            # Convert quadrilateral points to bounding box coordinates
            x_min = int(min(point[0] for point in points)) + rect_top_left[0]
            y_min = int(min(point[1] for point in points)) + rect_top_left[1]
            x_max = int(max(point[0] for point in points)) + rect_top_left[0]
            y_max = int(max(point[1] for point in points)) + rect_top_left[1]

            # Add detection
            detections.append([x_min, y_min, x_max, y_max, confidence])
            ocr_texts.append((text, confidence, (x_min, y_min, x_max, y_max)))

            # Debug: Draw OCR quadrilateral on the frame
            points = np.array(points, dtype=np.int32) + np.array([rect_top_left[0], rect_top_left[1]])
            cv2.polylines(frame, [points], isClosed=True, color=(255, 0, 0), thickness=1)

            # Debug: Draw the bounding box for better clarity
            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 1)
            cv2.putText(frame, text, (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)

    # Convert detections to a NumPy array
    detections = np.array(detections)
    if detections.size == 0:  # Ensure proper shape for SORT tracker
        detections = np.empty((0, 5))

    starttime = time.time()  # Record the start time
    return detections, ocr_texts


def process_frame(frame, master_text, rect_top_left, rect_bottom_right,x_width,y_height, similarity_threshold=50, output_csv="detected_texts.csv",roi_json_path="config/roi.json"):
    """Process a single frame to detect, track, and save recognized text."""
    global temp_images, processed_ids

    # Extract ROI
    roi = frame[rect_top_left[1]:rect_bottom_right[1], rect_top_left[0]:rect_bottom_right[0]]

    # Get OCR detections
    detections, ocr_texts = get_detections_from_ocr(roi, rect_top_left, frame)

    # Update tracker
    tracked_objects = tracker.update(detections)
    print(x_width)
    print(y_height)
    # Process tracked objects
    for obj in tracked_objects:
        x_min, y_min, x_max, y_max, track_id = map(int, obj)

        # Skip already processed IDs
        if track_id in processed_ids:
            continue

        # Find matching OCR text for the tracked object
        matched_text = ""
        for text, _, bbox in ocr_texts:
            bx_min, by_min, bx_max, by_max = bbox
            iou = max(0, min(x_max, bx_max) - max(x_min, bx_min)) * max(0, min(y_max, by_max) - max(y_min, by_min))
            if iou > 0:  # If overlap exists, match the text
                matched_text = text
                break

        if not matched_text:
            continue

        # Compute similarity
        similarity = SequenceMatcher(None, master_text, matched_text).ratio() * 100
        if similarity < similarity_threshold:
            continue

        
        rect_top_left, rect_bottom_right = load_roi_from_json(roi_json_path)
        # Display result on the frame
        status = "OK" if similarity == 100 else "NG"
        color = (0, 255, 0) if status == "OK" else (0, 0, 255)
        cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), color, 2)
        cv2.putText(frame, f"{matched_text} ({status})", (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        color_frame = (0, 255, 0) if status == "OK" else (0, 0, 255)
        cv2.rectangle(frame, (0,0), (x_width,y_height), color_frame, 4)                    ################################################


        # Save temp images for majority voting
        if track_id not in temp_images:
            temp_images[track_id] = []
        if len(temp_images[track_id]) < 1:
            frame_path = f"temp_image_{track_id}_{len(temp_images[track_id])}.jpg"
            cv2.imwrite(frame_path, frame)
            temp_images[track_id].append((matched_text, frame_path))

        # If temp images are full, save final result
        if len(temp_images[track_id]) == 1:
            save_final_result(temp_images[track_id], track_id, similarity, status, output_csv)


def save_final_result(temp_images_list, track_id, similarity, status, output_csv):
    """Save the final recognized text and image to a file and CSV."""
    global processed_ids

    # Majority voting for text
    text_counts = Counter([entry[0] for entry in temp_images_list])
    majority_text, _ = text_counts.most_common(1)[0]

    # Save the final image
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_folder = "final_images"
    majority_image_path = next(path for text, path in temp_images_list if text == majority_text)
    final_image_path = os.path.join(output_folder, f"final_image_{track_id}_{timestamp}.jpg")

    # Ensure unique filename
    counter = 1
    original_path = final_image_path
    while os.path.exists(final_image_path):
        final_image_path = original_path.replace(".jpg", f"_{counter}.jpg")
        counter += 1

    os.rename(majority_image_path, final_image_path)

    # Write result to CSV
    endtime = time.time()
    process_time = endtime - starttime
    with open(output_csv, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, process_time, track_id, majority_text, f"{similarity:.2f}", status, final_image_path])

    # Cleanup temp images
    for _, path in temp_images_list:
        if os.path.exists(path) and path != majority_image_path:
            os.remove(path)

    # Mark ID as processed
    processed_ids.add(track_id)
    del temp_images[track_id]


def load_roi_from_json(json_path):
    """Load ROI coordinates from a JSON file."""
    try:
        with open(json_path, 'r') as file:
            data = json.load(file)
            # Ensure required keys are present
            if all(key in data for key in ["start_x", "start_y", "end_x", "end_y"]):
                rect_top_left = (data["start_x"], data["start_y"])
                rect_bottom_right = (data["end_x"], data["end_y"])
                return rect_top_left, rect_bottom_right
            else:
                raise ValueError("Invalid JSON format: Missing required keys.")
    except Exception as e:
        print(f"Error loading ROI from JSON: {e}")
        return None, None


def main(master_text, video_source=1, roi_json_path="config/roi.json"):
    """Main function to process video and detect text."""
    initialize_system()
    write_csv_header()
    cap = cv2.VideoCapture(video_source)
    x_width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))   # float `width`
    y_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))  # float `height`
    if not cap.isOpened():
        print("Error: Could not open video source.")
        return

    print("Press 'q' to quit.")

    # Load ROI coordinates from JSON
    rect_top_left, rect_bottom_right = load_roi_from_json(roi_json_path)
    if rect_top_left is None or rect_bottom_right is None:
        print("Error: Could not load ROI coordinates. Exiting.")
        return

    print(f"Loaded ROI: Top-left {rect_top_left}, Bottom-right {rect_bottom_right}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        process_frame(frame, master_text, rect_top_left, rect_bottom_right,x_width,y_height)

        # Show the frame
        cv2.rectangle(frame, rect_top_left, rect_bottom_right, (0, 255, 0), 2)
        # cv2.imshow("Text Detection and Tracking", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()



if __name__ == "__main__":
    master_text = input("Enter the master text: ").strip()   ########### โหลด expect number เข้ามาในนี้
    main(master_text)
