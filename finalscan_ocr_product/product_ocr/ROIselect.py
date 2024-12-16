import tkinter as tk
from tkinter import messagebox
import cv2
import json
import os
from PIL import Image, ImageTk

class ROIApp:
    def __init__(self, root, config_folder="config", config_file="camera_config.json", config_check_interval=1000):
        self.root = root
        self.root.title("Camera Feed with ROI")
        self.root.geometry("640x480")  # Set the window size

        # Set the path to the config file inside the config folder
        self.config_path = os.path.join(config_folder, config_file)

        # Initialize last modified time
        self.last_modified_time = self.get_file_mod_time(self.config_path)

        # Load camera config from JSON file
        self.config = self.load_config(self.config_path)

        # Create a Canvas to hold the video feed and buttons
        self.canvas = tk.Canvas(self.root, width=640, height=480)
        self.canvas.pack()

        # Start the video capture
        self.cap = cv2.VideoCapture(0)  # 0 is usually the default camera

        if not self.cap.isOpened():
            messagebox.showerror("Error", "Unable to access the camera.")
            self.root.quit()
            return

        # Apply initial camera settings from the config file
        self.apply_camera_settings()

        # Initialize variables for ROI drawing
        self.start_x = self.start_y = 0  # Starting coordinates of the mouse click
        self.end_x = self.end_y = 0  # Ending coordinates of the mouse release
        self.drawing = False  # Flag to track if we are currently drawing the ROI

        # Create the Cancel and Confirm buttons, and place them on the canvas
        self.cancel_button = tk.Button(self.root, text="Cancel", command=self.on_cancel)
        self.cancel_button_window = self.canvas.create_window(480, 440, window=self.cancel_button)  # Place at (480, 440)

        self.confirm_button = tk.Button(self.root, text="Confirm", command=self.save_roi)
        self.confirm_button_window = self.canvas.create_window(560, 440, window=self.confirm_button)  # Place at (560, 440)

        # Update the feed
        self.update_frame()

        # Periodically check for changes in the configuration file
        self.check_config_changes(config_check_interval)

        # Bind mouse events to the window
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)  # Mouse click
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)  # Mouse drag
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)  # Mouse release

    def load_config(self, config_file):
        """Load the JSON configuration file"""
        try:
            with open(config_file, "r") as file:
                config = json.load(file)
            return config
        except FileNotFoundError:
            messagebox.showerror("Error", f"Configuration file {config_file} not found.")
            self.root.quit()
        except json.JSONDecodeError:
            messagebox.showerror("Error", f"Error parsing {config_file}.")
            self.root.quit()

    def get_file_mod_time(self, filepath):
        """Get the last modified time of the file"""
        return os.path.getmtime(filepath)

    def check_config_changes(self, interval):
        """Check periodically if the config file has changed"""
        current_mod_time = self.get_file_mod_time(self.config_path)
        if current_mod_time != self.last_modified_time:
            # Reload config and apply new settings
            print("Config file changed, reapplying settings...")
            self.config = self.load_config(self.config_path)
            self.apply_camera_settings()
            self.last_modified_time = current_mod_time

        # Check again after the specified interval (in ms)
        self.root.after(interval, self.check_config_changes, interval)

    def apply_camera_settings(self):
        """Apply the camera settings from the loaded config"""
        # Reinitialize the camera to apply new settings
        self.cap.release()  # Release the current camera
        self.cap = cv2.VideoCapture(0)  # Reopen the camera

        if not self.cap.isOpened():
            messagebox.showerror("Error", "Unable to access the camera.")
            self.root.quit()
            return

        # Apply settings from the JSON config file
        if "brightness" in self.config:
            brightness = self.config["brightness"]
            self.cap.set(cv2.CAP_PROP_BRIGHTNESS, brightness)
            # Check if the setting has been applied
            current_brightness = self.cap.get(cv2.CAP_PROP_BRIGHTNESS)
            print(f"Applied brightness: {brightness}, Current brightness: {current_brightness}")

        if "focus" in self.config:
            focus = self.config["focus"]
            self.cap.set(cv2.CAP_PROP_FOCUS, focus)
            # Check if the setting has been applied
            current_focus = self.cap.get(cv2.CAP_PROP_FOCUS)
            print(f"Applied focus: {focus}, Current focus: {current_focus}")

    def update_frame(self):
        """Update the camera feed on the canvas"""
        ret, frame = self.cap.read()

        if ret:
            # Draw the ROI if it's defined
            if self.drawing or (self.start_x != self.end_x and self.start_y != self.end_y):
                cv2.rectangle(frame, (self.start_x, self.start_y), (self.end_x, self.end_y), (0, 255, 0), 2)

            # Convert the frame to RGB (OpenCV uses BGR by default)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Convert the frame to a format that can be used by Tkinter
            img = Image.fromarray(frame_rgb)
            img_tk = ImageTk.PhotoImage(image=img)

            # Update the canvas with the new image
            self.canvas.img_tk = img_tk  # Keep a reference to the image
            self.canvas.create_image(0, 0, image=img_tk, anchor="nw")

        # Call the update_frame method again after 10ms
        self.root.after(10, self.update_frame)

    def on_mouse_press(self, event):
        """Handle mouse press event to start drawing the ROI"""
        self.start_x = event.x
        self.start_y = event.y
        self.drawing = True  # Start drawing the ROI

    def on_mouse_drag(self, event):
        """Handle mouse drag event to update the ROI during drawing"""
        self.end_x = event.x
        self.end_y = event.y

    def on_mouse_release(self, event):
        """Handle mouse release event to finish drawing the ROI"""
        self.end_x = event.x
        self.end_y = event.y
        self.drawing = False  # Stop drawing the ROI

        # Optionally, you can print or store the ROI coordinates
        print(f"ROI coordinates: ({self.start_x}, {self.start_y}) -> ({self.end_x}, {self.end_y})")

    def save_roi(self):
        """Save the ROI coordinates to a JSON file"""
        roi_data = {
            "start_x": self.start_x,
            "start_y": self.start_y,
            "end_x": self.end_x,
            "end_y": self.end_y
        }

        roi_file_path = os.path.join("config", "roi.json")

        # Ensure the config directory exists
        os.makedirs(os.path.dirname(roi_file_path), exist_ok=True)

        try:
            with open(roi_file_path, "w") as json_file:
                json.dump(roi_data, json_file, indent=4)
            messagebox.showinfo("Success", f"ROI coordinates saved to {roi_file_path}")
            self.root.quit()  # Close the window after saving the ROI
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save ROI: {e}")

    def on_cancel(self):
        """Close the window when Cancel is clicked"""
        self.root.quit()

    def on_closing(self):
        """Release the camera and close the window"""
        self.cap.release()
        self.root.quit()

def open_all_items_window():
    items_data_file = "./config/items_data.json"  # Path to the JSON file
    items_images_folder = "./config/items"       # Path to the folder containing item images
    # Open the ROIApp in the current window (root) rather than in a new Toplevel
    ROIApp(root, config_folder="config", config_file="camera_config.json", config_check_interval=1000)

# GUI Components
root = tk.Tk()

header_frame = tk.Frame(root, bg='white')
header_frame.place(relx=0, rely=0, relwidth=1, relheight=0.1)

header_font = ("Arial", 14)
button_color = "#4CAF50"

# Add "Items Info" button
tk.Button(
    header_frame, 
    text="Items Info", 
    font=header_font, 
    bg=button_color, 
    fg='white', 
    padx=10, 
    pady=5, 
    command=open_all_items_window
).place(relx=0.01, rely=0.2)

# Start the Tkinter main loop
root.mainloop()
