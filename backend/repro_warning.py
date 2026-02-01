
import logging
from supabase import create_client
import os

# Mock env vars if not set, or rely on .env loading
# I'll rely on what's in the environment or set dummy values
url = "https://jkaplkmqdryarmnknomr.supabase.co/" # With trailing slash
key = "ey..."

# Configure logging to see if it's a log or print
logging.basicConfig(level=logging.DEBUG)

print("--- Init ---")
try:
    create_client(url, key)
except Exception as e:
    print(f"Error: {e}")
print("--- Done ---")
