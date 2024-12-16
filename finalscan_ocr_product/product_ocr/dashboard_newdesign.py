from tkinter import *
from tkinter import ttk
from PIL import Image, ImageTk , ImageDraw, ImageFont
import csv
import os
from tkinter import ttk, messagebox
import os
import json
from all_items import AllItems


# Initialize the root window
root = Tk()

# Get the screen width and height
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# Set the window geometry to fit the screen
root.geometry(f"{screen_width}x{screen_height}")
root.config(bg="white")
root.title("QC Dashboard")

# Global variables
data = []
data_index = 0  # Keeps track of the current image to display

# Styling variables
bg_color = '#f0f0f0'
button_color = '#007bff'
header_font = ('Helvetica', 12, 'bold')
font_large = ('Helvetica', 22, 'bold')
font_medium_bold = ('Helvetica', 18, 'bold')
font_small = ('Helvetica', 12)
spinboxes = []

def open_all_items_window():
    items_data_file = "./config/items_data.json"  # Path to the JSON file
    items_images_folder = "./config/items"       # Path to the folder containing item images
    AllItems(root, items_data_file, items_images_folder)


# Function to save the work order
def save_work_order(workID, spinbox_values, item_id, top):
    if not all([workID, spinbox_values, item_id]):
        messagebox.showerror("Error", "All fields are required!")
        return

    total_items = ''.join(spinbox_values)
    # Print collected data (replace with actual save logic)
    print(f"Work ID: {workID}")
    print(f"Total Items: {total_items}")
    print(f"Item ID: {item_id}")

    # Confirmation Message
    messagebox.showinfo("Success", "Work Order saved successfully!")
    top.destroy()  # Close the popup window

# Function to get and print all spinbox values
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

# Function to create a popup window for "Create Work Order"
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

    Label(top, text="Item ID:", font=font_small, bg="white").place(x=50, y=170)
    itemsID_dropdown = ttk.Combobox(
        top, values=["A1", "A2"], state="readonly", font=font_small, width=20
    )
    itemsID_dropdown.current(0)
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

    # Add a save button
    Button(
        top,
        text="Save Work Order",
        font=header_font,
        bg=button_color,
        fg="white",
        command=lambda: save_work_order(
            workID.get(),  # RTSP Link
            get_spinbox_values(),  # Spinbox Values (Total Items)
            itemsID_dropdown.get(),  # Item ID
            top  # Pass the top window to close it
        ),
    ).place(x=250, y=530)

    # Add a cancel button
    Button(
        top,
        text="Cancel",
        font=header_font,
        bg=button_color,
        fg="white",
        command=top.destroy  # This will close the window when clicked
    ).place(x=150, y=530)


# Function to load data from the CSV file
def load_data_from_csv(file_path):
    global data
    try:
        with open(file_path, 'r') as file:
            reader = csv.DictReader(file)
            data = list(reader)  # Store all rows as dictionaries
            if not data:
                print("Error: CSV file is empty.")
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        data = []


# Function to update the "Result Snapshots" section dynamically
def update_dashboard():
    global data_index

    # If data exists and we are within the bounds of the dataset
    if data and data_index < len(data):
        row = data[data_index]  # Get the current row
        text = row.get('Text', 'N/A')  # Extract the "Text" column
        count = row.get('count', '0')  # Extract the "Count" column
        image_path = row.get('Image_Path', '')  # Extract the "Image_Path" column

        # Update Processed, OK, and NG counts
        total_processed_count.config(text=f"{int(count)}")  # Total Processed
        total_ok_count.config(text=f"{int(count)}")  # Example OK count (adjust as needed)
        total_ng_count.config(text="10")  # Example NG count (adjust as needed)

        # Load and display the image in "Result Snapshots"
        if os.path.exists(image_path):
            img = Image.open(image_path).resize((int(screen_width * 0.4), int(screen_height * 0.4)))  # Resize image dynamically
            img_tk = ImageTk.PhotoImage(img)
            result_snapshot_label.config(image=img_tk, text="", compound=None)
            result_snapshot_label.image = img_tk
        else:
            # Display placeholder if the image is not found
            result_snapshot_label.config(
                image='', text="No Image Found", font=font_medium_bold, fg='gray', compound=CENTER
            )
            result_snapshot_label.image = None

        # Move to the next item in the data
        data_index += 1
    else:
        # Reset to the beginning of the dataset
        data_index = 0

    # Schedule the next update
    root.after(1000, update_dashboard)


# Dynamic Positioning
def update_layout():
    # Header Section
    header_frame.place(relx=0, rely=0, relwidth=1, relheight=0.1)

    # Result Snapshots Section
    result_snapshots_frame.place(relx=0.02, rely=0.12, relwidth=0.45, relheight=0.7)

    # Metrics Section (Status, Work Order ID, and Total)
    metrics_frame.place(relx=0.5, rely=0.12, relwidth=0.45, relheight=0.1)

    # OK and NG Counts Section
    ok_ng_frame.place(relx=0.5, rely=0.24, relwidth=0.45, relheight=0.58)

    # OK Section
    ok_frame.place(relx=0.05, rely=0, relwidth=0.9, relheight=0.4)

    # NG Section
    ng_frame.place(relx=0.05, rely=0.45, relwidth=0.9, relheight=0.4)


# Header Section
header_frame = Frame(root, bg='white')
# Button(header_frame, text="Back", font=header_font, bg=button_color, fg='white', padx=10, pady=5).place(relx=0.01, rely=0.2)
Button(
    header_frame, 
    text="Items Info", 
    font=header_font, 
    bg=button_color, 
    fg='white', 
    padx=10, 
    pady=5, 
    command=open_all_items_window
).place(relx=0.01, rely=0.2)

Label(header_frame, text="Station:", font=font_small, bg="white").place(relx=0.1, rely=0.3)
station_dropdown = ttk.Combobox(
    header_frame, values=["Station_01_Cam01", "Station_02_Cam02"], state="readonly", font=font_small
)
station_dropdown.current(0)
station_dropdown.place(relx=0.15, rely=0.3, relwidth=0.2)
Button(header_frame, text="Create Work Order", font=header_font, bg='blue', fg='white', padx=10, pady=5, command=work_order ).place(relx=0.7, rely=0.2)
Button(header_frame, text="Start/ Stop", font=header_font, bg='blue', fg='white', padx=10, pady=5).place(relx=0.85, rely=0.2)

# Result Snapshots Section
result_snapshots_frame = Frame(root, bg='lightgray', relief=RIDGE, bd=2)
Label(result_snapshots_frame, text="Result Snapshots", bg='lightgray', font=font_medium_bold).place(relx=0.5, rely=0.05, anchor='center')
result_snapshot_label = Label(result_snapshots_frame, bg='white')
result_snapshot_label.place(relx=0.5, rely=0.55, anchor='center')



# Metrics Section
metrics_frame = Frame(root, bg='white')
Label(metrics_frame, text="Status", bg="white", font=font_small).place(relx=0.05, rely=0.2)
Label(metrics_frame, text="Running", bg="white", font=font_medium_bold, fg="blue").place(relx=0.05, rely=0.6)
# Create a frame for the bounding box
# bounding_frame = Frame(metrics_frame, bg="black", bd=2, relief="solid")
# bounding_frame.place(relx=0.02, rely=0.1, relwidth=0.5, relheight=0.4)  # Adjust size and position as needed

# # Add labels inside the bounding frame
# Label(bounding_frame, text="Status", bg="white", font=font_small).place(relx=0.05, rely=0.2)
# Label(bounding_frame, text="Running", bg="white", font=font_medium_bold, fg="blue").place(relx=0.05, rely=0.6)

Label(metrics_frame, text="Work Order ID", bg="white", font=font_small).place(relx=0.4, rely=0.2)
Label(metrics_frame, text="WO_0001", bg="white", font=font_medium_bold).place(relx=0.4, rely=0.6)
Label(metrics_frame, text="Total", bg="white", font=font_small).place(relx=0.75, rely=0.2)
total_processed_count = Label(metrics_frame, text="0", bg="white", font=font_medium_bold)
total_processed_count.place(relx=0.75, rely=0.6)

#-------------------------------------------------------------------------------------------

# # OK and NG Counts Section
# ok_ng_frame = Frame(root, bg='blue')

# # OK Section
# ok_frame = Frame(ok_ng_frame, bg='lime', relief=RIDGE, bd=2)
# Label(ok_frame, text="OK", bg='lime', font=font_large, fg='white').place(relx=0.5, rely=0.3, anchor='center')
# total_ok_count = Label(ok_frame, text="0", bg='lime', font=('Helvetica', 70, 'bold'), fg='white')
# total_ok_count.place(relx=0.5, rely=0.7, anchor='center')

# # NG Section
# ng_frame = Frame(ok_ng_frame, bg='red', relief=RIDGE, bd=2)
# Label(ng_frame, text="NG", bg='red', font=font_large, fg='white').place(relx=0.5, rely=0.3, anchor='center')
# total_ng_count = Label(ng_frame, text="0", bg='red', font=('Helvetica', 70, 'bold'), fg='white')
# total_ng_count.place(relx=0.5, rely=0.7, anchor='center')

#-------------------------------------------------------------------------------------------
# OK and NG Counts Section
ok_ng_frame = Frame(root, bg='white', relief=RIDGE, bd=0)
ok_ng_frame.place(x=0, y=0, width=50, height=0)  # Adjust position and size of the parent frame

# OK Section (Green Box)
ok_frame = Frame(ok_ng_frame, bg='lime', relief=RIDGE, bd=2)
ok_frame.place(x=0, y=10, width=10, height=30)  # Position OK box within the parent frame
Label(ok_frame, text="OK", bg='lime', font=font_large, fg='white').place(relx=0.5, rely=0.3, anchor='center')
total_ok_count = Label(ok_frame, text="0", bg='lime', font=('Helvetica', 70, 'bold'), fg='white')
total_ok_count.place(relx=0.5, rely=0.7, anchor='center')

# NG Section (Red Box)
ng_frame = Frame(ok_ng_frame, bg='red', relief=RIDGE, bd=2)
ng_frame.place(x=0, y=20, width=10, height=30)  # Position NG box within the parent frame
Label(ng_frame, text="NG", bg='red', font=font_large, fg='white').place(relx=0.5, rely=0.3, anchor='center')
total_ng_count = Label(ng_frame, text="0", bg='red', font=('Helvetica', 70, 'bold'), fg='white')
total_ng_count.place(relx=0.5, rely=0.7, anchor='center')


# Load CSV data
load_data_from_csv('detected_texts.csv')

# Start updating the dashboard
update_dashboard()

# Dynamically position elements
update_layout()

# Run the application
root.mainloop()