import tkinter as tk
from tkinter import Scale, Button, messagebox
from PIL import Image, ImageTk
import cv2
import json
import os

class ConfigurationPage:
    def __init__(self, parent):
        self.parent = parent  # Reference to the main application for navigation

        # Set default values
        self.default_brightness = 128
        self.default_focus = 128

        # Initialize camera capture variable; only start it when the page is shown
        self.cap = None

        # Create the Toplevel window (pop-up window)
        self.window = tk.Toplevel(parent)
        self.window.title("Configuration")
        self.window.geometry("800x600")  # Adjust the size as needed

        # Set up UI components inside the Toplevel window
        self.create_widgets()

        # Call on_show to start the video feed
        self.on_show()

        # Handle window close event to release camera
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        """Create and place UI components inside the Toplevel window."""
        # Title Label
        label = tk.Label(self.window, text="Configuration", font=("Arial", 24), bg="#ffffff", fg="#333333")
        label.grid(row=0, column=0, columnspan=2, pady=20)

        # Brightness Slider
        brightness_label = tk.Label(self.window, text="Brightness", font=("Arial", 14))
        brightness_label.grid(row=1, column=0, sticky="e", padx=10, pady=10)

        self.brightness_slider = Scale(self.window, from_=255, to=0, orient="vertical",
                                       resolution=1, command=self.update_brightness)
        self.brightness_slider.grid(row=1, column=1, padx=10, pady=10)

        # Focus Slider
        focus_label = tk.Label(self.window, text="Focus", font=("Arial", 14))
        focus_label.grid(row=2, column=0, sticky="e", padx=10, pady=10)

        self.focus_slider = Scale(self.window, from_=255, to=0, orient="vertical",
                                  resolution=1, command=self.update_focus)
        self.focus_slider.grid(row=2, column=1, padx=10, pady=10)

        # Default, Save, and Back Buttons
        default_button = Button(self.window, text="Default", font=("Arial", 12), command=self.reset_to_default)
        default_button.grid(row=3, column=0, padx=10, pady=20)

        save_button = Button(self.window, text="Save", font=("Arial", 12), command=self.save_settings)
        save_button.grid(row=3, column=1, padx=10, pady=20)

        back_button = Button(self.window, text="Back", font=("Arial", 12), command=self.go_back)
        back_button.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

        # Right-side label for video feed
        self.video_label = tk.Label(self.window)
        self.video_label.grid(row=0, column=2, rowspan=5, padx=10, pady=10, sticky="n")

    def load_camera_config(self):
        """Load focus and brightness values from camera_config.json if it exists."""
        config_path = os.path.join("config", "camera_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as config_file:
                config = json.load(config_file)
                brightness = config.get("brightness", self.default_brightness)
                focus = config.get("focus", self.default_focus)
        else:
            # Use default values if config file does not exist
            brightness, focus = self.default_brightness, self.default_focus
        return brightness, focus

    def update_brightness(self, value):
        """Update brightness factor based on slider position."""
        self.brightness_factor = int(value)
    
    def update_focus(self, value):
        """Update focus value based on slider position."""
        self.focus_value = int(value)
        if self.cap and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FOCUS, self.focus_value)

    def reset_to_default(self):
        """Reset both sliders to their default values (128)."""
        self.brightness_slider.set(self.default_brightness)
        self.focus_slider.set(self.default_focus)

    def save_settings(self):
        """Save current brightness and focus values to JSON file and close the window."""
        config = {
            "brightness": self.brightness_factor,
            "focus": self.focus_value
        }

        # Ensure "config" directory exists
        os.makedirs("config", exist_ok=True)
        config_path = os.path.join("config", "camera_config.json")

        # Write configuration to JSON file
        with open(config_path, "w") as config_file:
            json.dump(config, config_file, indent=4)
        print("Settings saved to", config_path)

        # Display a confirmation pop-up
        messagebox.showinfo("Settings Saved", "Your settings have been successfully saved!")

        # Close the configuration window after saving
        self.window.destroy()

    def adjust_frame_brightness(self, frame):
        """Adjust the brightness of the frame based on the brightness factor."""
        return cv2.convertScaleAbs(frame, alpha=self.brightness_factor / 128, beta=0)

    def update_video_feed(self):
        """Capture and display the video feed."""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                frame = self.adjust_frame_brightness(frame)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                imgtk = ImageTk.PhotoImage(image=img)
                
                # Display the image in the Tkinter label
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)

            # Schedule the next frame update (this is crucial for continuous video feed)
            self.video_label.after(10, self.update_video_feed)  # Updates every 10ms

    def on_show(self):
        """Load settings from camera_config and start camera feed each time the page is shown."""
        # Reload camera settings
        self.brightness_factor, self.focus_value = self.load_camera_config()

        # Update sliders with loaded values
        self.brightness_slider.set(self.brightness_factor)
        self.focus_slider.set(self.focus_value)

        # Initialize camera if not already initialized
        if not self.cap or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)  # Open the camera

        self.cap.set(cv2.CAP_PROP_FOCUS, self.focus_value)

        # Start video feed
        self.update_video_feed()

    def on_close(self):
        """Release the camera when page is closed."""
        if self.cap and self.cap.isOpened():
            self.cap.release()  # Release the camera
        self.video_label.config(image=None)  # Clear the image in the label
        self.window.destroy()  # Close the window

    def go_back(self):
        """Navigate back to the main page without saving."""
        self.window.destroy()  # Close the configuration pop-up window
