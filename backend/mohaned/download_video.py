import requests, os

url = "https://generativelanguage.googleapis.com/v1beta/files/m7lottb5y389:download?alt=media"
api_key = os.getenv("GEMINI_API_KEY")

headers = {
    "x-goog-api-key": api_key
}

r = requests.get(url, headers=headers, stream=True)

with open("video.mp4", "wb") as f:
    for chunk in r.iter_content(chunk_size=8192):
        if chunk:
            f.write(chunk)

print("Saved video.mp4")
