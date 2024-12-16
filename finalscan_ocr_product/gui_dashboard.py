import json
from PIL import Image, ImageTk , ImageDraw, ImageFont
import os
from tkinter import *
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from threading import Thread, Lock
# from ROIselect import ROIApp
from pages.serial_processor import (
    start_process,
    stop_process,
    set_work_order_details,
    is_running,
    get_ok_ng_counts,
    get_last_image,
    get_csv_row_count,
    initialize_camera,
    release_camera,
)
from pages.all_items import AllItems
from pages.roiselect_page import ROISlectPage
from pages.configuration_page import ConfigurationPage

# Styling variables (Ensure these are globally defined)
button_color = '#007bff'
header_font = ('Helvetica', 12, 'bold')
font_large = ('Helvetica', 22, 'bold')
font_medium_bold = ('Helvetica', 18, 'bold')
font_small = ('Helvetica', 12)
font_header_font = ('Helvetica', 14, 'bold')

# Initialize the root window
root = Tk()

# Get the screen width and height
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# Set the window geometry to fit the screen
root.geometry(f"{screen_width}x{screen_height}")
root.config(bg="white")
root.title("QC Dashboard")

# Globals
work_order_id = None
total_items = None
current_item_id = None
process_done = False  # Tracks if the process is marked "Done"
start_stop_button_state = "Start"  # "Start", "Stop", "Resume"
lock = Lock()  # Lock for thread-safe operations


def update_dashboard():
    global work_order_id, total_items, process_done, start_stop_button_state

    # Update OK and NG counts
    ok_count, ng_count = get_ok_ng_counts()
    total_ok_count.config(text=f"{ok_count}")
    total_ng_count.config(text=f"{ng_count}")

    # Update Work Order ID
    if work_order_id:
        work_order_id_label.config(text=work_order_id)

    # Update Total Objects
    total_objects = get_csv_row_count() - 1  # Exclude header
    total_processed_count.config(text=str(max(total_objects, 0)))  # Handle negatives gracefully

    print(f"Debug: Before updating dashboard: total_objects={total_objects}, total_items={total_items}, process_done={process_done}")

    # Check process completion
    with lock:
        if total_items is not None and total_objects >= total_items and not process_done:
            process_done = True
            status_label.config(text="Done", fg="green")
            stop_process()  # Stop the process automatically
            release_camera()  # Release camera resources
            start_stop_button.config(state=DISABLED)  # Disable the button
            print("Debug: Process marked as Done")
            return  # Prevent further updates

    print(f"Debug: After checking process completion: total_objects={total_objects}, total_items={total_items}, process_done={process_done}")

    # Update status based on process state
    if process_done:
        status_label.config(text="Done", fg="green")
    elif start_stop_button_state == "Start":
        status_label.config(text="Idle", fg="orange")
    elif start_stop_button_state == "Stop":
        status_label.config(text="Running", fg="blue")
    elif start_stop_button_state == "Resume":
        status_label.config(text="Stopped", fg="red")

    # Show the latest image in Result Snapshots
    latest_image_path = get_last_image()
    if latest_image_path and os.path.exists(latest_image_path):
        img = Image.open(latest_image_path).resize((int(screen_width * 0.4), int(screen_height * 0.4)))
        img_tk = ImageTk.PhotoImage(img)
        result_snapshot_label.config(image=img_tk)
        result_snapshot_label.image = img_tk

    # Schedule the next update
    root.after(100, update_dashboard)


def save_work_order(workID, spinboxes, itemsID_dropdown, top):
    global work_order_id, current_item_id, process_done, start_stop_button_state, total_items  # Add total_items here
    
    # Initialize the camera when saving the work order
    initialize_camera()

    # Extract values
    work_order_id = workID.get().strip()  # Get Work Order ID from the entry widget
    total_items_input = ''.join([spinbox.get() for spinbox in spinboxes])  # Get concatenated spinbox values
    current_item_id = itemsID_dropdown.get()  # Get the selected item ID from dropdown

    # Debug: Print extracted values
    print(f"Debug: work_order_id={work_order_id}, total_items_input={total_items_input}, current_item_id={current_item_id}")

    # Validate inputs
    if not work_order_id or not total_items_input or not current_item_id:
        messagebox.showerror("Error", "All fields are required!")
        return

    # Validate that Total Items is a number
    if not total_items_input.isdigit():
        messagebox.showerror("Error", "Total Items must be a number!")
        return

    # Update the global total_items variable
    total_items = int(total_items_input)  # Convert Total Items to integer

    # Debug: Confirm total_items update
    print(f"Debug: total_items after save={total_items}")

    # Reset process_done flag and start/stop button state
    process_done = False
    start_stop_button_state = "Start"
    start_stop_button.config(state=NORMAL, text="Start")

    # Set the Work Order details in the processing script
    try:
        set_work_order_details(work_order_id, total_items, current_item_id)
    except ValueError as e:
        messagebox.showerror("Error", str(e))
        return

    # Update Work Order ID in the dashboard
    work_order_id_label.config(text=work_order_id)

    # Set status to Idle
    status_label.config(text="Idle", fg="orange")

    # Show success message and close the popup
    messagebox.showinfo("Success", "Work Order Created Successfully!")
    top.destroy()
def get_spinbox_values():
    values = [spinbox.get() for spinbox in spinboxes]
    return values

# Function to load item details from JSON
def load_item_details(item_id):
    try:
        # Open and load the JSON file containing item data
        with open("./config/items_data.json", "r") as file:
            data = json.load(file)
            item_data = data.get(item_id, {})
            return item_data
    except FileNotFoundError:
        print("Error: items_data.json file not found.")
        return {}
    except json.JSONDecodeError:
        print("Error: Failed to decode JSON.")
        return {}

def overlay_text_on_image(image, text, position=(35, 10), font_size=30):
    # Load a custom font with the desired size (ensure the font file is available)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)  # Replace with your font path
    except IOError:
        font = ImageFont.load_default()  # Fallback to default if custom font is not available
    
    # Create a drawing context
    draw = ImageDraw.Draw(image)
    
    # Draw the text on the image with the specified font and position
    draw.text(position, text, font=font, fill="black")  # Change fill to any color you want
    
    return image

def work_order():
    global spinboxes  # Declare as global so the spinboxes list can be accessed later
    spinboxes = []


    # Create a new popup window
    top = Toplevel(root)
    top.title("Create Work Order")
    top.geometry('925x600+300+200')  # Size of the popup
    top.configure(bg='white')
    top.resizable(False, False)

    frame = Frame(top, width=640, height=410, bg='white')
    frame.place(x=100, y=200)

    # Add a title
    Label(top, text="Work Order Details", font=font_medium_bold, bg="white").pack(pady=10)

    # Create entry fields
    Label(top, text="Work Order ID:", font=font_small, bg="white").place(x=50, y=70)
    workID = Entry(top, width=50)
    workID.place(x=200, y=70)

    Label(top, text="Total Items:", font=font_small, bg="white").place(x=50, y=120)
    # Create 5 Spinboxes
    for i in range(5):
        spinbox = Spinbox(top, from_=0, to=9, width=3, font=font_small, wrap=True)
        spinbox.place(x=200 + (i * 50), y=120)  # Adjust x-coordinate for each spinbox
        spinboxes.append(spinbox)

        # Create the dropdown menu dynamically
     # Dynamically load Item IDs from the JSON file
    def load_item_ids():
        try:
            with open("./config/items_data.json", "r") as file:
                data = json.load(file)
                return list(data.keys())  # Extract item IDs (keys)
        except FileNotFoundError:
            print("Error: items_data.json file not found.")
            return []  # Return an empty list if the file doesn't exist
        except json.JSONDecodeError:
            print("Error: Failed to decode JSON.")
            return []  # Return an empty list if the JSON is invalid

    # Create the dropdown menu dynamically
    Label(top, text="Item ID:", font=font_small, bg="white").place(x=50, y=170)
    item_ids = load_item_ids()  # Load item IDs dynamically
    itemsID_dropdown = ttk.Combobox(
        top, values=item_ids, state="readonly", font=font_small, width=20
    )
    if item_ids:
        itemsID_dropdown.current(0)  # Set the first item as selected by default
    itemsID_dropdown.place(x=200, y=170)

    # Default image
    default_image_path = "noframe.png"
    image = Image.open(default_image_path)
    image = image.resize((650, 300), Image.LANCZOS)
    img = ImageTk.PhotoImage(image)

    # Store a reference to the image to prevent garbage collection
    frame.img = img  # Attach img to the frame or top

    image_label = Label(frame, image=img)
    image_label.place(x=0, y=10, width=580, height=300)

    # Function to update the image and display item details
    def update_image():
        item_id = itemsID_dropdown.get()  # Get the selected item ID
        image_path = f"./config/items/{item_id}.jpg"  # Construct the image path

        if os.path.exists(image_path):  # Check if the file exists
            new_image = Image.open(image_path)
        else:  # Fallback to default image
            new_image = Image.open(default_image_path)

        # Load item details from JSON
        item_details = load_item_details(item_id)
        if item_details:
            expected_number = item_details.get("expected_number", "N/A")
            # Overlay text on the image
            text = f"Item ID: {item_id}\nExpected Number: {expected_number}"
            new_image = overlay_text_on_image(new_image, text, position=(35, 10), font_size=30)

        new_image = new_image.resize((650, 300), Image.LANCZOS)
        new_img = ImageTk.PhotoImage(new_image)

        # Update the image in the label
        image_label.config(image=new_img)
        image_label.image = new_img  # Store a reference to avoid garbage collection

    # Button to capture the picture and display details
    pic_button = Button(top, text="Show", font=header_font, bg='red', fg='white', command=update_image)
    pic_button.place(x=420, y=165)


# Start/Stop/Resume button functionality
def start_stop_process():
    global start_stop_button_state, process_done

    print(f"Debug: Start/Stop button pressed. Current state: {start_stop_button_state}")
    
    # Check if the process is already "Done"
    if process_done:
        messagebox.showinfo("Info", "Process is already completed. No further action required.")
        return

    # Check if total objects already meet/exceed total items
    total_objects = get_csv_row_count() - 1  # Exclude header
    if total_items is not None and total_objects >= total_items:
        # Mark the process as done
        process_done = True
        status_label.config(text="Done", fg="green")
        stop_process()  # Stop any ongoing process
        release_camera()  # Release camera resources
        start_stop_button.config(state=DISABLED)  # Disable the button
        messagebox.showinfo("Info", "Process completed successfully!")
        print("Debug: Process completed and marked as Done.")
        return

    # Handle Start, Stop, and Resume states
    if start_stop_button_state == "Start":
        print("Debug: Starting the process...")
        Thread(target=start_process, daemon=True).start()  # Start in a separate thread
        start_stop_button.config(text="Stop")  # Change button to Stop
        start_stop_button_state = "Stop"
        print("Debug: Process started.")
    elif start_stop_button_state == "Stop":
        print("Debug: Stopping the process...")
        Thread(target=stop_process, daemon=True).start()  # Stop in a separate thread
        start_stop_button.config(text="Resume")  # Change button to Resume
        start_stop_button_state = "Resume"
        print("Debug: Process stopped.")
    elif start_stop_button_state == "Resume":
        print("Debug: Resuming the process...")
        Thread(target=start_process, daemon=True).start()  # Start in a separate thread
        start_stop_button.config(text="Stop")  # Change button back to Stop
        start_stop_button_state = "Stop"
        print("Debug: Process resumed.")


def open_all_items_window():
    items_data_file = "./config/items_data.json"  # Path to the JSON file
    items_images_folder = "./config/items"       # Path to the folder containing item images
    ROISlectPage(root, config_folder="config", config_file="camera_config.json", config_check_interval=1000)

def open_config_page():
    ConfigurationPage(root)

# GUI Components
header_frame = Frame(root, bg='white')
header_frame.place(relx=0, rely=0, relwidth=1, relheight=0.1)


Button(
    header_frame, 
    text="Select ROI", 
    font=header_font, 
    bg=button_color, 
    fg='white', 
    padx=10, 
    pady=5, 
    command=open_all_items_window
).place(relx=0.01, rely=0.2)
Button(
    header_frame, 
    text="config", 
    font=header_font, 
    bg=button_color, 
    fg='white', 
    padx=10, 
    pady=5, 
    command=open_config_page
).place(relx=0.10, rely=0.2)


# Define the reset function
def reset_dashboard():
    global work_order_id, total_items, current_item_id, process_done, start_stop_button_state

    # Reset global variables
    work_order_id = None
    total_items = None
    current_item_id = None
    process_done = False
    start_stop_button_state = "Start"

    # Reset GUI elements
    status_label.config(text="Idle", fg="orange")  # Reset status to "Idle"
    work_order_id_label.config(text="-")          # Reset Work Order ID to "-"
    total_processed_count.config(text="0")        # Reset total processed count to "0"
    total_ok_count.config(text="0")               # Reset OK count to "0"
    total_ng_count.config(text="0")               # Reset NG count to "0"

    # Clear the "Result Snapshots" image to the default image
    default_image_path = "Baksters.png"  # Replace with your prepared image path
    if os.path.exists(default_image_path):
        img = Image.open(default_image_path)
        img = img.resize((int(screen_width * 0.42), int(screen_height * 0.56)), Image.LANCZOS)
        img_tk = ImageTk.PhotoImage(img)
        result_snapshot_label.config(image=img_tk)
        result_snapshot_label.image = img_tk  # Keep a reference to avoid garbage collection

    # Reactivate Start/Stop button
    start_stop_button.config(state=NORMAL, text="Start")

    # Release resources (just in case)
    release_camera()
    stop_process()

    messagebox.showinfo("Reset", "Dashboard has been reset to its initial state.")


# Add the Reset button
Button(
    header_frame, 
    text="Reset", 
    font=header_font, 
    bg='red', 
    fg='white', 
    padx=10, 
    pady=5, 
    command=reset_dashboard
).place(relx=0.92, rely=0.3)


start_stop_button = Button(header_frame, text="Start", font=header_font, bg='blue', fg='white', padx=10, pady=5,
                           command=start_stop_process)
start_stop_button.place(relx=0.85, rely=0.3)

result_snapshots_frame = Frame(root, bg='lightgray', relief=RIDGE, bd=2)
Label(result_snapshots_frame, text="Result Snapshots", bg='lightgray', font=font_medium_bold).place(relx=0.5, rely=0.05, anchor='center')
result_snapshot_label = Label(result_snapshots_frame, bg='white')
result_snapshot_label.place(relx=0.5, rely=0.55, anchor='center')

#==================================================================================================== #add work order enter in main page

# Create entry fields
Label(root, text="Work Order ID:", font=font_small, bg="white").place(x=310, y=30)
workID = Entry(root, width=30, bd=2)
workID.place(x=430, y=30)

Label(root, text="Total Items:", font=font_small, bg="white").place(x=650, y=30)
spinbox = Entry(root, width=30, bd=2)
spinbox.place(x=750, y=30)

Label(root, text="Exacted match:", font=font_small, bg="white").place(x=960, y=30)
itemsID_dropdown = Entry(root, width=30, bd=2)
itemsID_dropdown.place(x=1080, y=30)

# Virtual keyboard input function
def insert_text(value):
    current_widget = root.focus_get()  # Get the currently focused widget
    if isinstance(current_widget, Entry) or isinstance(current_widget, Spinbox):
        current_widget.insert(INSERT, value)

# Keyboard visibility and position handling
keyboard_visible = False  # Initially set to False to hide the keyboard

def toggle_keyboard():
    global keyboard_visible
    if keyboard_visible:
        keyboard_frame.place_forget()  # Hide the keyboard
    else:
        keyboard_frame.place(relx=0.0, rely=0.8, relwidth=1.0, relheight=0.5, anchor='sw')  # Position keyboard at the bottom, taking 50% of the window height
        keyboard_frame.lift()  # Ensure keyboard stays on top of other widgets
    keyboard_visible = not keyboard_visible

# Create a frame for the virtual keyboard (initially hidden)
keyboard_frame = Frame(root, bg='black')

# Increase the row and column weight to allow buttons to expand
for i in range(5):  # We have 5 rows (including close button)
    keyboard_frame.grid_rowconfigure(i, weight=1, uniform="equal")
for i in range(10):  # We have 10 columns in the keyboard layout
    keyboard_frame.grid_columnconfigure(i, weight=1, uniform="equal")

# Close button for the keyboard
def close_keyboard():
    global keyboard_visible
    keyboard_frame.place_forget()  # Hide the keyboard
    keyboard_visible = False

# Create the "keys" for the virtual keyboard
keys = [
    ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
    ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
    ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
    ['Z', 'X', 'C', 'V', 'B', 'N', 'M', '<-', 'Space']
]

# Add the keys to the virtual keyboard
for row_index, row in enumerate(keys):
    for col_index, key in enumerate(row):
        if key == 'Space':
            btn = Button(keyboard_frame, text='Space', bg='black', fg='white', relief='flat', font=("Arial", 18), command=lambda: insert_text(' '))  # Space key
        elif key == '<-':
            btn = Button(keyboard_frame, text='<-', bg='black', fg='white', relief='flat', font=("Arial", 18), command=lambda: root.focus_get().delete(len(root.focus_get().get())-1, END))  # Backspace key
        else:
            btn = Button(keyboard_frame, text=key, bg='black', fg='white', relief='flat', font=("Arial", 18), command=lambda k=key: insert_text(k))  # Alphanumeric keys
        btn.grid(row=row_index, column=col_index, padx=5, pady=5, sticky="nsew")  # Make buttons expand to fill the grid cell

# Close button to close the keyboard
close_btn = Button(keyboard_frame, text="Close", command=close_keyboard, font=("Arial", 12), bg="red", fg="white", relief='flat')
close_btn.grid(row=4, column=0, padx=5, pady=5)

# Function to show keyboard when an entry is focused
def on_entry_focus(event):
    toggle_keyboard()

# Bind entry focus events to automatically show the keyboard
workID.bind("<FocusIn>", on_entry_focus)
spinbox.bind("<FocusIn>", on_entry_focus)
itemsID_dropdown.bind("<FocusIn>", on_entry_focus)

# Function to close the keyboard if the user clicks outside the text fields
def on_focus_out(event):
    if keyboard_visible:
        close_keyboard()

# Bind focus-out events to hide the keyboard when the user clicks outside the input fields
workID.bind("<FocusOut>", on_focus_out)
spinbox.bind("<FocusOut>", on_focus_out)
itemsID_dropdown.bind("<FocusOut>", on_focus_out)

metrics_frame = Frame(root, bg='white')
Label(metrics_frame, text="Status", bg="white", font=font_small).place(relx=0.05, rely=0.2)
status_label = Label(metrics_frame, text="Idle", bg="white", font=font_medium_bold, fg="orange")
status_label.place(relx=0.05, rely=0.6)
Label(metrics_frame, text="Work Order ID", bg="white", font=font_small).place(relx=0.4, rely=0.2)
work_order_id_label = Label(metrics_frame, text="-", bg="white", font=font_medium_bold)
work_order_id_label.place(relx=0.4, rely=0.6)
Label(metrics_frame, text="Total", bg="white", font=font_small).place(relx=0.75, rely=0.2)
total_processed_count = Label(metrics_frame, text="0", bg="white", font=font_medium_bold)
total_processed_count.place(relx=0.75, rely=0.6)

ok_ng_frame = Frame(root, bg='white', relief=RIDGE, bd=0)
ok_frame = Frame(ok_ng_frame, bg='lime', relief=RIDGE, bd=2)
Label(ok_frame, text="OK", bg='lime', font=font_large, fg='white').place(relx=0.5, rely=0.3, anchor='center')
total_ok_count = Label(ok_frame, text="0", bg='lime', font=('Helvetica', 70, 'bold'), fg='white')
total_ok_count.place(relx=0.5, rely=0.7, anchor='center')
ng_frame = Frame(ok_ng_frame, bg='red', relief=RIDGE, bd=2)
Label(ng_frame, text="NG", bg='red', font=font_large, fg='white').place(relx=0.5, rely=0.3, anchor='center')
total_ng_count = Label(ng_frame, text="0", bg='red', font=('Helvetica', 70, 'bold'), fg='white')
total_ng_count.place(relx=0.5, rely=0.7, anchor='center')

result_snapshots_frame.place(relx=0.02, rely=0.12, relwidth=0.45, relheight=0.7)
metrics_frame.place(relx=0.5, rely=0.12, relwidth=0.45, relheight=0.1)
ok_ng_frame.place(relx=0.5, rely=0.24, relwidth=0.45, relheight=0.58)
ok_frame.place(relx=0.05, rely=0, relwidth=0.9, relheight=0.4)
ng_frame.place(relx=0.05, rely=0.45, relwidth=0.9, relheight=0.4)

# Default image
default_image_path = "Baksters.png"  # Path to your prepared image
if os.path.exists(default_image_path):
    default_img = Image.open(default_image_path)
    default_img = default_img.resize((int(screen_width * 0.42), int(screen_height * 0.56)), Image.LANCZOS)
    default_img_tk = ImageTk.PhotoImage(default_img)
    result_snapshot_label.config(image=default_img_tk)
    result_snapshot_label.image = default_img_tk  # Store a reference to prevent garbage collection


# Start updating the dashboard
update_dashboard()

# Run the application
root.mainloop()