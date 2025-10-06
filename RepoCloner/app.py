import os
import subprocess

file_path = "repos"

# Get current directory
current_dir = os.getcwd()

# Read the file line by line
with open(file_path, "r") as file:
    for line in file:
        slicelife_path = line.strip()
        if not slicelife_path:
            continue  # skip empty lines

        # Extract repo name from URL
        repo_name = slicelife_path.rstrip("/").split("/")[-1].replace(".git", "")
        target_path = os.path.join(current_dir, repo_name)
        full_url = f"git@github.com:slicelife/{repo_name}"

        if os.path.exists(target_path):
            print(f"Skipping {repo_name}: already exists.")
            continue

        print(f"Cloning {repo_name} into {target_path}...")
        try:
            subprocess.run(["git", "clone", full_url, target_path], check=True)
            print(f"✅ Successfully cloned {repo_name}")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to clone {slicelife_path}")
