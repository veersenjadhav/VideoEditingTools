import os

# The folder where your ghost files are living
folder_path = r"C:\Users\veers\Downloads\Compressed\Vid_Edit"

# The exact names of the 0 KB files (Notice the trailing spaces!)
ghost_files = ["MCU 1 ", "MCU 2 ", "MCU 3 "]

print("Attempting to forcefully delete ghost files...")

for file_name in ghost_files:
    # Combine the directory and filename
    full_path = os.path.join(folder_path, file_name)
    
    # Prepend '\\\\?\\' to tell Windows: "Do NOT strip the trailing spaces!"
    extended_path = "\\\\?\\" + full_path
    
    try:
        os.remove(extended_path)
        print(f"Successfully deleted: '{file_name}'")
    except FileNotFoundError:
        print(f"File '{file_name}' was already gone or not found.")
    except Exception as e:
        print(f"Could not delete '{file_name}': {e}")

print("Cleanup complete!")