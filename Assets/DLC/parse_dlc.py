import os
import json

# List of common image file extensions
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif']

def find_album_art(files):
    # Iterate through the list of files to find the first image file
    for file in files:
        if any(file.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
            return file
    return None

def scan_and_collect_data(root_dir):
    master_index = []
    
    # Walk through the directory
    for subdir, _, files in os.walk(root_dir):
        # Gather all files in the current directory
        all_files = os.listdir(subdir)
        
        # Calculate the relative path from the root directory
        relative_folder_path = os.path.relpath(subdir, root_dir)
        
        # Find the first image file in the folder
        album_art = find_album_art(all_files)
        
        for file in files:
            # Process only .txt files
            if file == 'TrackData.txt':
                file_path = os.path.join(subdir, file)
                
                # Read and parse the JSON content from the .txt file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                        # Extract only the desired fields
                        extracted_data = {
                            "AlbumName": data.get("AlbumName"),
                            "SongName": data.get("SongName"),
                            "SongArtist": data.get("SongArtist"),
                            "Year": data.get("Year"),
                            "DLCSource": data.get("DLCSource"),
                            "FolderPath": relative_folder_path,  # Add the relative folder path to the exported data
                            "FilesInFolder": all_files,  # Add the list of files in the folder
                            "AlbumArtFileName": album_art  # Add the album art file name if found
                        }

                        master_index.append(extracted_data)
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON from {file_path}: {e}")
                except Exception as e:
                    print(f"Error processing file {file_path}: {e}")
    
    return master_index

def write_master_index(master_index, output_file):
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(master_index, f, indent=4)
        print(f"Master index successfully written to {output_file}")
    except Exception as e:
        print(f"Error writing master index to {output_file}: {e}")

if __name__ == "__main__":
    # Specify the directory to scan and the output file
    root_directory = "."  # Replace with your directory path
    output_file = "dlc_index.json"

    # Scan the directory and collect data
    master_index_data = scan_and_collect_data(root_directory)

    # Write the collected data to the master index file
    write_master_index(master_index_data, output_file)
