import os
import cv2
import csv
import json
from paddleocr import PaddleOCR
from sort import Sort  # SORT tracking library
from threading import Thread, Lock
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
import time
import numpy as np

# Globals
process_running = False
work_order_id = None
total_items = None
current_item_id = None
item_data = None
ocr = PaddleOCR(det=True, rec=True, cls=False, use_angle_cls=True)  # OCR initialization
tracker = Sort()  # SORT tracker
cap = None
lock = Lock()
image_counter = 1
object_counter = 1
csv_file = None
output_folder = "captured_images"
temp_images = {}
processed_ids = set()

# Set Work Order details
def set_work_order_details(order_id, items, item_id):
    global work_order_id, total_items, current_item_id, item_data, csv_file, output_folder

    # Set global details
    work_order_id = order_id
    total_items = int(items)
    current_item_id = item_id

    # Load item configuration
    with open("config/roi.json", "r") as f:
        items_data = json.load(f)

    item_data = items_data.get(current_item_id, {})

    if not item_data:
        raise ValueError(f"Item ID '{current_item_id}' not found in items_data.json.")

    # Prepare CSV file
    csv_file = f"{work_order_id}.csv"
    if not os.path.exists(csv_file):
        with open(csv_file, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "Process time" ,"Tracking ID", "Detected Text", "Similarity (%)", "Status", "Image Path"])

    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Initialize camera
    try:
        initialize_camera()
    except ValueError as e:
        print(f"Failed to initialize camera: {e}")
        raise


# Check if the process is running
def is_running():
    with lock:
        return process_running


# Initialize camera
def initialize_camera():
    """Initialize the camera."""
    global cap
    if cap is None:
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            cap = None  # Reset `cap` if initialization fails
            raise ValueError("Error: Unable to access the camera.")
        print("Camera initialized and running.")
    else:
        print("Camera is already initialized.")


# Release camera
def release_camera():
    """Release the camera resources."""
    global cap
    if cap:
        cap.release()
        cap = None
        print("Camera released.")


# Start the process
def start_process(update_status_callback=None):
    global process_running, cap

    if is_running():
        return

    # Initialize camera (if not already initialized)
    if cap is None:
        try:
            initialize_camera()
        except ValueError as e:
            print(f"Error initializing camera: {e}")
            return

    # Start process
    with lock:
        process_running = True

    print("Process started...")
    Thread(target=process_items, args=(update_status_callback,), daemon=True).start()


# Stop the process
def stop_process():
    global process_running, cap

    with lock:
        process_running = False

    # Release camera resources
    if cap:
        release_camera()

    print("Process stopped.")


# Process video frames with OCR and SORT in a separate thread
def process_items(update_status_callback=None):
    global image_counter

    while is_running():
        try:
            ret, frame = cap.read()
            if not ret:
                break

            # Define ROI for OCR (adjust according to your need)
            rect_top_left = (100, 100)
            rect_bottom_right = (400, 300)

            # Extract the region of interest (ROI) from the frame
            roi = frame[rect_top_left[1]:rect_bottom_right[1], rect_top_left[0]:rect_bottom_right[0]]

            # Perform OCR on the ROI
            result = ocr.ocr(roi)
            detections = []  # List of detections for SORT
            ocr_texts = []  # List to store OCR results and their bounding boxes

            if result and result[0]:  # Ensure result is not None and contains detected lines
                for line in result[0]:
                    text = line[1][0]  # Extract detected text
                    confidence = line[1][1]  # Extract confidence level
                    points = line[0]  # Get bounding box points

                    # Convert quadrilateral points to bounding box coordinates
                    x_min = int(min(point[0] for point in points)) + rect_top_left[0]
                    y_min = int(min(point[1] for point in points)) + rect_top_left[1]
                    x_max = int(max(point[0] for point in points)) + rect_top_left[0]
                    y_max = int(max(point[1] for point in points)) + rect_top_left[1]

                    detections.append([x_min, y_min, x_max, y_max, confidence])  # Add to detections list
                    ocr_texts.append((text, confidence, (x_min, y_min, x_max, y_max)))  # Save OCR data

            # Convert detections to NumPy array
            detections = np.array(detections)
            if detections.size == 0:  # If no detections, create an empty array
                detections = np.empty((0, 5))

            # Update SORT tracker with current detections
            tracked_objects = tracker.update(detections)  # Returns [x_min, y_min, x_max, y_max, track_id]

            # Match OCR results with tracked objects and process them
            for obj in tracked_objects:
                x_min, y_min, x_max, y_max, track_id = map(int, obj)

                # Skip if the tracking ID has already been processed
                if track_id in processed_ids:
                    continue

                matched_text = ""
                for text, confidence, bbox in ocr_texts:
                    bx_min, by_min, bx_max, by_max = bbox
                    iou = max(
                        0,
                        min(x_max, bx_max) - max(x_min, bx_min)
                    ) * max(0, min(y_max, by_max) - max(y_min, by_min))  # Intersection area

                    if iou > 0:  # If bounding boxes overlap
                        matched_text = text
                        break

                if not matched_text:
                    continue

                # Compute similarity to master text
                similarity = SequenceMatcher(None, "master_text", matched_text).ratio() * 100  # Similarity percentage

                # Skip if the similarity is below the threshold
                if similarity < 50:
                    continue

                # Save and log the result
                save_result(matched_text, track_id, frame, similarity)

                processed_ids.add(track_id)

        except Exception as e:
            print(f"Error during processing: {e}")

# Save result to CSV and image
def save_result(matched_text, track_id, frame, similarity):
    global object_counter

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    status = "OK" if similarity == 100 else "NG"

    # Save the final image
    final_image_path = os.path.join(output_folder, f"final_image_{track_id}_{timestamp}.jpg")
    cv2.imwrite(final_image_path, frame)

    # Write result to CSV
    with open(csv_file, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, status, track_id, matched_text, f"{similarity:.2f}", final_image_path])

    print(f"Logged result: {matched_text} (Status: {status})")
    object_counter += 1


# Count rows in the CSV
def get_csv_row_count():
    global csv_file
    if not csv_file or not os.path.exists(csv_file):
        return 0  # Return 0 if CSV file is not set or does not exist
    with open(csv_file, "r") as file:
        return sum(1 for _ in file)


# Fetch OK and NG counts
def get_ok_ng_counts():
    global csv_file
    if not csv_file or not os.path.exists(csv_file):
        return 0, 0  # No data yet
    ok_count = ng_count = 0
    with open(csv_file, "r") as file:
        reader = csv.reader(file)
        next(reader)  # Skip header
        for row in reader:
            if row[4] == "OK":
                ok_count += 1
            elif row[4] == "NG":
                ng_count += 1
    return ok_count, ng_count


# Get the last stored image
def get_last_image():
    global csv_file
    if not csv_file or not os.path.exists(csv_file):
        return None  # No images yet
    with open(csv_file, "r") as file:
        reader = csv.reader(file)
        rows = list(reader)
        if len(rows) > 1:  # Ensure there's at least one result row
            return rows[-1][5]
        return None
