import requests
import time
import json
import sys

API_URL = "http://localhost:8000/api"
FILE_PATH = "test_img.jpeg"

def main():
    print(f"Uploading {FILE_PATH}...")
    with open(FILE_PATH, "rb") as f:
        files = {"file": (FILE_PATH, f, "image/jpeg")}
        response = requests.post(f"{API_URL}/upload", files=files)
        
    if response.status_code != 200:
        print(f"Upload failed: {response.status_code} - {response.text}")
        sys.exit(1)
        
    task_id = response.json()["task_id"]
    print(f"Upload successful. Task ID: {task_id}")
    
    print("Polling for results...")
    while True:
        res = requests.get(f"{API_URL}/result/{task_id}")
        data = res.json()
        status = data["status"]
        
        if status == "done":
            print("\nProcessing completed successfully!")
            print(json.dumps(data["result"], indent=2))
            break
        elif status == "failed":
            print("\nProcessing failed!")
            print(f"Error: {data.get('error')}")
            sys.exit(1)
        else:
            stage = data.get("stage", "unknown")
            progress = data.get("progress", 0.0)
            print(f"Status: {status}, Stage: {stage}, Progress: {progress*100:.1f}%")
            time.sleep(2)

if __name__ == "__main__":
    main()
