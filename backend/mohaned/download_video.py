import os
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

url = "https://generativelanguage.googleapis.com/v1beta/files/m7lottb5y389:download?alt=media"
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("API Key not found! Make sure you created a .env file.")

headers = {
    "x-goog-api-key": api_key
}

r = requests.get(url, headers=headers, stream=True)

with open("video.mp4", "wb") as f:
    for chunk in r.iter_content(chunk_size=8192):
        if chunk:
            f.write(chunk)

print("Saved video.mp4")
