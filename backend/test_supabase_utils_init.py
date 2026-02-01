
import os
from dotenv import load_dotenv

load_dotenv(r"D:\Programming\AI\Hackathons\.Competitions\EliteHack\ribif\backend\.env")

# Must import AFTER dotenv to ensure env vars are set if the module reads them at top level
# But supabase_utils reads them at top level.
# So I need to set them BEFORE import if possible, or reload?
# However, load_dotenv sets os.environ.
# If I import the module now, it will read os.environ.

from supabase_utils import get_supabase

print("Calling get_supabase()...")
client = get_supabase()
print(f"Client: {client}")
print("Done.")
