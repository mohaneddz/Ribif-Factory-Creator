
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path("d:/Programming/AI/Hackathons/.Competitions/EliteHack/ribif/backend")
sys.path.append(str(backend_path))

try:
    print("Testing import of agentic search...")
    from utils.web_search.agentic import agentic_search
    print("SUCCESS: agentic_search imported.")
    
    print("Testing import of module_1...")
    from utils.module_1 import core as mod1
    print("SUCCESS: module_1 imported.")

    print("Testing import of module_4...")
    from utils.module_4 import core as mod4
    print("SUCCESS: module_4 imported.")
    
except Exception as e:
    print(f"FAILURE: {e}")
    import traceback
    traceback.print_exc()
