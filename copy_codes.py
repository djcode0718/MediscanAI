import os

def collect_code(base_path, output_file="output.txt"):
    # Only these subfolders will be considered
    target_folders = {"backend", "frontend", "data", "indexes", "tests"}
    
    with open(output_file, "w", encoding="utf-8") as out:
        # Write the main folder name
        out.write(f"Main Folder: {os.path.basename(base_path)}\n")
        
        for root, dirs, files in os.walk(base_path):
            # Keep only target folders
            dirs[:] = [d for d in dirs if d in target_folders]
            
            # Get relative path of current folder
            rel_path = os.path.relpath(root, base_path)
            if rel_path != ".":
                out.write(f"\nSubfolder: {rel_path}\n")
            
            for file in files:
                file_path = os.path.join(root, file)
                
                # Python file → include code
                if file.endswith(".py"):
                    out.write(f"\nFile: {file}\n")
                    out.write("------ CODE START ------\n")
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            out.write(f.read() + "\n")
                    except Exception as e:
                        out.write(f"[Error reading file: {e}]\n")
                    out.write("------ CODE END ------\n")
                
                else:
                    # Non-Python file → only name
                    out.write(f"\nFile: {file}\n")
    
    print(f"✅ Done! Output saved to {output_file}")


# Example usage:
collect_code('/Users/sj/Downloads/mediscanai')