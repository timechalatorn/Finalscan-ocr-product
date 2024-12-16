# Count rows in CSV
def get_csv_row_count(file_path):
    with open(file_path, "r") as file:
        return sum(1 for _ in file)
