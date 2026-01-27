
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv(r"D:\Programming\AI\Hackathons\.Competitions\EliteHack\ribif\backend\.env")

# Ensure trailing slash for storage endpoint
raw_url = os.getenv("SUPABASE_URL", "")
SUPABASE_URL = (raw_url.rstrip("/") + "/") if raw_url else "/"
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

print(f"URL: {SUPABASE_URL}")
print("Initializing client...")
try:
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Client initialized.")
except Exception as e:
    print(f"Error: {e}")
