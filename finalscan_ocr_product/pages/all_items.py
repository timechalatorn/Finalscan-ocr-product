import cv2
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import os
import json


class AllItems(tk.Toplevel):
    def __init__(self, parent, data_file, items_folder):
        super().__init__(parent)

        self.title("All Registered Items")
        self.geometry("600x400")  # Adjusted size for additional column
        self.data_file = data_file
        self.items_folder = items_folder

        # Create a canvas and a scrollbar for the table
        self.canvas = tk.Canvas(self)
        self.canvas.pack(side="left", fill="both", expand=True)

        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.table_frame = tk.Frame(self.canvas)

        # Add the frame to the canvas
        self.canvas.create_window((0, 0), window=self.table_frame, anchor="nw")

        # Bind the canvas to adjust the scroll region dynamically
        self.table_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Add "Add Item" button
        self.add_item_button = tk.Button(self.table_frame, text="Add Item", command=self.add_item_window, font=("Arial", 12))
        self.add_item_button.grid(row=0, column=0, sticky="w", padx=10, pady=10)

        # Load and display items
        self.load_and_display_items()

    def load_and_display_items(self):
        """Load all registered items and display them in a table."""
        # Clear the table frame, except for the "Add Item" button
        for widget in self.table_frame.winfo_children():
            if widget != self.add_item_button:
                widget.destroy()

        # Load item data
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as f:
                data = json.load(f)
        else:
            data = {}

        # Display table headers
        headers = ["Item ID", "Expected Number", "Items", "   Edit   ", "Delete"]
        for col, header in enumerate(headers):
            tk.Label(self.table_frame, text=header, font=("Arial", 12, "bold"), borderwidth=1, relief="solid").grid(
                row=1, column=col, sticky="nsew", padx=0, pady=0)

        # Display each item
        for row, (item_id, item_data) in enumerate(data.items(), start=2):
            # Display Item ID and Expected Number
            tk.Label(self.table_frame, text=item_id, font=("Arial", 12), borderwidth=1, relief="solid").grid(
                row=row, column=0, sticky="nsew", padx=0, pady=0)
            tk.Label(self.table_frame, text=item_data["expected_number"], font=("Arial", 12), borderwidth=1, relief="solid").grid(
                row=row, column=1, sticky="nsew", padx=0, pady=0)

            # Create a thumbnail button
            thumbnail_button = self.create_thumbnail_button(item_id)
            if thumbnail_button:
                thumbnail_button.grid(row=row, column=2, sticky="nsew", padx=0, pady=0)

            # Add an Edit button
            edit_button = tk.Button(self.table_frame, text="Edit",font='bold', command=lambda i=item_id: self.edit_item(i),bg='yellow',fg='black')
            edit_button.grid(row=row, column=3, sticky="nsew", padx=0, pady=0)

            # Add a Delete button
            delete_button = tk.Button(self.table_frame, text="Delete",font='bold', command=lambda i=item_id: self.delete_item(i),bg='red',fg='white')
            delete_button.grid(row=row, column=4, sticky="nsew", padx=0, pady=0)

        # Adjust column widths
        for col in range(len(headers)):
            self.table_frame.grid_columnconfigure(col, weight=1)

    def create_thumbnail_button(self, item_id):
        """Create a button with a thumbnail of the item."""
        item_path = os.path.join(self.items_folder, f"{item_id}.jpg")
        if os.path.exists(item_path):
            try:
                # Open the image and resize it for thumbnail
                img = Image.open(item_path)
                img.thumbnail((150, 150))  # Resize to 150x150
                thumbnail = ImageTk.PhotoImage(img)

                # Create a button with the thumbnail
                button = tk.Button(self.table_frame, image=thumbnail, command=lambda: self.show_full_image(item_id))
                button.image = thumbnail  # Keep a reference to avoid garbage collection
                return button
            except Exception as e:
                print(f"Error creating thumbnail for {item_id}: {e}")
                return None
        else:
            return None

    def show_full_image(self, item_id):
        """Show the full-sized image of the selected item in a new window."""
        item_path = os.path.join(self.items_folder, f"{item_id}.jpg")
        if os.path.exists(item_path):
            new_window = tk.Toplevel(self)
            new_window.title(f"Item: {item_id}")

            # Open and display the full-sized image
            img = Image.open(item_path)
            imgtk = ImageTk.PhotoImage(img)

            label = tk.Label(new_window, image=imgtk)
            label.imgtk = imgtk  # Keep a reference to avoid garbage collection
            label.pack()

            # Close Button
            close_button = tk.Button(new_window, text="Close", command=new_window.destroy)
            close_button.pack(pady=10)
        else:
            messagebox.showerror("Error", f"No image found for Item ID: {item_id}")

    def add_item_window(self):
        """Open a popup window to add a new item."""
        EditItemWindow(self, None, self.data_file, self.items_folder, self.load_and_display_items)

    def edit_item(self, item_id):
        """Open a window to edit the selected item's ID and Expected Number."""
        EditItemWindow(self, item_id, self.data_file, self.items_folder, self.load_and_display_items)

    def delete_item(self, item_id):
        """Delete the selected item from the data file and its image."""
        confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete Item ID: {item_id}?")
        if not confirm:
            return

        # Load item data
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as f:
                data = json.load(f)
        else:
            data = {}

        # Delete the item data
        if item_id in data:
            del data[item_id]

            # Save the updated data file
            with open(self.data_file, "w") as f:
                json.dump(data, f, indent=4)

            # Delete the image file
            item_path = os.path.join(self.items_folder, f"{item_id}.jpg")
            if os.path.exists(item_path):
                os.remove(item_path)

            # Update the table
            self.load_and_display_items()

            messagebox.showinfo("Deleted", f"Item ID: {item_id} has been deleted.")
        else:
            messagebox.showerror("Error", f"Item ID: {item_id} not found.")


class EditItemWindow(tk.Toplevel):
    def __init__(self, parent, item_id, data_file, items_folder, refresh_callback):
        super().__init__(parent)

        self.title(f"{'Add Item' if item_id is None else 'Edit Item: ' + item_id}")
        self.geometry("800x500")
        self.item_id = item_id
        self.data_file = data_file
        self.items_folder = items_folder
        self.refresh_callback = refresh_callback

        self.roi_start = None
        self.roi_end = None
        self.drawing = False
        self.raw_image = None  # Initialize raw_image

        # Load item data
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as f:
                self.data = json.load(f)
        else:
            self.data = {}

        self.new_item_id = tk.StringVar(value=item_id if item_id else "")
        self.new_expected_number = tk.StringVar(value=self.data.get(item_id, {}).get("expected_number", "") if item_id else "")

        # Create entry fields for editing or adding
        form_frame = tk.Frame(self)
        form_frame.pack(side="left", fill="y", padx=10, pady=10)

        tk.Label(form_frame, text="Item ID:", font=("Arial", 12)).pack(pady=5)
        tk.Entry(form_frame, textvariable=self.new_item_id, font=("Arial", 12)).pack(pady=5)

        tk.Label(form_frame, text="Expected Number:", font=("Arial", 12)).pack(pady=5)
        tk.Entry(form_frame, textvariable=self.new_expected_number, font=("Arial", 12)).pack(pady=5)

        # Confirm and Cancel buttons
        button_frame = tk.Frame(form_frame)
        button_frame.pack(pady=20)
        tk.Button(button_frame, text="Confirm", command=self.confirm_edit).pack(side="left", padx=10)
        tk.Button(button_frame, text="Cancel", command=self.cancel_edit).pack(side="left", padx=10)

        # Create a placeholder for image or camera feed
        self.video_label = tk.Label(self, text="Loading...", bg="#ddd", width=50, height=20)
        self.video_label.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Check if an image exists for the item
        self.image_path = os.path.join(self.items_folder, f"{item_id}.jpg") if item_id else None
        self.cap = None

        if self.image_path and os.path.exists(self.image_path):
            self.load_existing_image()
        else:
            self.start_camera_feed()

    def load_existing_image(self):
        """Load an existing image and disable ROI drawing."""
        try:
            self.raw_image = cv2.imread(self.image_path)  # Load image into raw_image
            self.display_image(self.raw_image)

            # Disable ROI drawing for existing items
            self.video_label.unbind("<ButtonPress-1>")
            self.video_label.unbind("<B1-Motion>")
            self.video_label.unbind("<ButtonRelease-1>")
            print("ROI drawing disabled for existing image.")
        except Exception as e:
            print(f"Error loading image: {e}")
            messagebox.showerror("Error", f"Failed to load image for {self.item_id}. Starting camera feed.")
            self.start_camera_feed()

    def start_camera_feed(self):
        """Start the camera feed with parameters from camera_config.json."""
        self.cap.set(cv2.CAP_PROP_BRIGHTNESS, brightness)  # Normalize to 0.0 - 1.0 for OpenCV
        self.cap.set(cv2.CAP_PROP_FOCUS, focus)  # Use absolute value (0-255 for manual focus)
        
        self.cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

        # Load parameters from camera_config.json
        brightness, focus = self.load_camera_config()

        # Apply the parameters to the camera
        

        print(f"Applied camera settings: Brightness={brightness / 255}, Focus={focus}")

        self.activate_draw_roi()
        self.update_video_feed()

    def update_video_feed(self):
        """Update the video feed in the label."""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                self.raw_image = frame  # Update raw_image from camera feed

                # Draw ROI if available
                if self.roi_start and self.roi_end:
                    x1, y1 = self.roi_start
                    x2, y2 = self.roi_end
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                self.display_image(frame)

            self.video_label.after(10, self.update_video_feed)

    def display_image(self, frame):
        """Display an image or video frame in the label."""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        imgtk = ImageTk.PhotoImage(img)
        self.video_label.imgtk = imgtk
        self.video_label.config(image=imgtk, text="")

    def activate_draw_roi(self):
        """Enable ROI drawing."""
        self.video_label.bind("<ButtonPress-1>", self.start_roi)
        self.video_label.bind("<B1-Motion>", self.update_roi)
        self.video_label.bind("<ButtonRelease-1>", self.end_roi)

    def start_roi(self, event):
        """Start drawing ROI."""
        self.drawing = True
        self.roi_start = (event.x, event.y)

    def update_roi(self, event):
        """Update the ROI during mouse drag."""
        if self.drawing:
            self.roi_end = (event.x, event.y)

    def end_roi(self, event):
        """Finish drawing ROI."""
        self.drawing = False
        self.roi_end = (event.x, event.y)
        print(f"ROI drawn: {self.roi_start} to {self.roi_end}")

    def load_camera_config(self):
        """Load focus and brightness values from camera_config.json."""
        # config_path = f"config/camera_config.json"

        # Default values
        brightness = 146
        focus = 98

        # # Load from config file if it exists
        # if os.path.exists(config_path):
        #     with open(config_path, "r") as config_file:
        #         config = json.load(config_file)
        #         brightness = config.get("brightness", brightness)  # Fallback to 128 if key is missing
        #         focus = config.get("focus", focus)

        # print(f"Loaded camera config: Brightness={brightness}, Focus={focus}")
        return brightness, focus

    def confirm_edit(self):
        """Save the item with updated snapshots and ROI."""
        new_id = self.new_item_id.get()
        new_expected_number = self.new_expected_number.get()

        if not new_id or not new_expected_number:
            messagebox.showerror("Error", "Item ID and Expected Number cannot be empty.")
            return

        # Check if adding a new item with an existing ID
        if self.item_id is None and new_id in self.data:
            confirm = messagebox.askyesno(
                "Confirm Replacement", f"Item ID '{new_id}' already exists. Replace it?"
            )
            if not confirm:
                return

        # Handle renaming of Item ID
        if self.item_id and new_id != self.item_id:
            if new_id in self.data:
                messagebox.showerror("Error", f"Item ID '{new_id}' already exists. Choose a different ID.")
                return

            # Rename the JSON entry
            self.data[new_id] = self.data.pop(self.item_id)
            self.data[new_id]["expected_number"] = new_expected_number

            # Rename the image file if it exists
            old_file_path = os.path.join(self.items_folder, f"{self.item_id}.jpg")
            new_file_path = os.path.join(self.items_folder, f"{new_id}.jpg")
            if os.path.exists(old_file_path):
                os.rename(old_file_path, new_file_path)
                print(f"Renamed image file: {old_file_path} -> {new_file_path}")

        else:
            # Update the existing item's expected number
            if self.item_id:
                self.data[new_id]["expected_number"] = new_expected_number
            else:
                # New item case: Create a new entry
                self.data[new_id] = {"expected_number": new_expected_number}

            # Save the ROI only if a new ROI is drawn
            if self.roi_start and self.roi_end:
                x1, y1 = self.roi_start
                x2, y2 = self.roi_end
                x1, x2 = min(x1, x2), max(x1, x2)
                y1, y2 = min(y1, y2), max(y1, y2)
                self.data[new_id]["roi"] = {"start": [x1, y1], "end": [x2, y2]}

        # Save updated JSON data
        with open(self.data_file, "w") as f:
            json.dump(self.data, f, indent=4)
        print("Updated JSON file.")

        # Save image with ROI for new items or updated ROI
        if self.raw_image is not None:
            roi_image_path = os.path.join(self.items_folder, f"{new_id}.jpg")
            if self.roi_start and self.roi_end:
                # Draw ROI on the image
                x1, y1 = self.roi_start
                x2, y2 = self.roi_end
                cv2.rectangle(self.raw_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.imwrite(roi_image_path, self.raw_image)
            print(f"Saved image with ROI: {roi_image_path}")

        # Refresh the parent and close
        self.refresh_callback()
        messagebox.showinfo("Saved", f"Item '{new_id}' updated successfully!")
        self.on_close()


    def on_close(self):
        """Release resources when the window is closed."""
        if hasattr(self, 'cap') and self.cap and self.cap.isOpened():
            self.cap.release()  # Release the camera
            print("Camera released.")
        self.destroy()


    def cancel_edit(self):
        """Handle cancel action."""
        self.on_close()  # Ensure camera is released
        self.destroy()