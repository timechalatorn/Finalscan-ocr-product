import tkinter as tk
from tkinter import messagebox
import cv2
import json
import os
from PIL import Image, ImageTk

class CameraApp:
    def __init__(self, root, config_folder="config", config_file="camera_config.json", config_check_interval=1000):
        self.root = root
        self.root.title("Camera Feed")
        self.root.geometry("640x480")  # Set the window size

        # Set the path to the config file inside the config folder
        self.config_path = os.path.join(config_folder, config_file)

        # Initialize last modified time
        self.last_modified_time = self.get_file_mod_time(self.config_path)

        # Load camera config from JSON file
        self.config = self.load_config(self.config_path)

        # Create a label to hold the camera feed image
        self.video_label = tk.Label(self.root)
        self.video_label.pack()

        # Start the video capture
        self.cap = cv2.VideoCapture(1)  # 0 is usually the default camera

        if not self.cap.isOpened():
            messagebox.showerror("Error", "Unable to access the camera.")
            self.root.quit()
            return

        # Apply initial camera settings from the config file
        self.apply_camera_settings()

        # Update the feed
        self.update_frame()

        # Periodically check for changes in the configuration file
        self.check_config_changes(config_check_interval)

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
        self.cap = cv2.VideoCapture(1)  # Reopen the camera

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
        """Update the camera feed in the Tkinter window"""
        ret, frame = self.cap.read()

        if ret:
            # Convert the frame to RGB (OpenCV uses BGR by default)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Convert the frame to a format that can be used by Tkinter
            img = Image.fromarray(frame_rgb)
            img_tk = ImageTk.PhotoImage(image=img)

            # Update the label with the new image
            self.video_label.img_tk = img_tk
            self.video_label.config(image=img_tk)

        # Call the update_frame method again after 10ms
        self.root.after(10, self.update_frame)

    def on_closing(self):
        """Release the camera and close the window"""
        self.cap.release()
        self.root.quit()

# Set up the main window
root = tk.Tk()
app = CameraApp(root)

# Bind the close window event to properly release the camera
root.protocol("WM_DELETE_WINDOW", app.on_closing)

# Run the GUI
root.mainloop()