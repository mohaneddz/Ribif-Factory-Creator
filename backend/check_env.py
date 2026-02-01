"""Test Serper with explicit .env loading"""

import sys
import os
from pathlib import Path

# Explicitly load .env
backend_dir = Path(__file__).parent
env_file = backend_dir / ".env"

print(f"Looking for .env at: {env_file}")
print(f"Exists: {env_file.exists()}")

if env_file.exists():
    print(f"\n.env file contents (first 20 lines):")
    print("=" * 60)
    with open(env_file, 'r') as f:
        lines = f.readlines()[:20]
        for i, line in enumerate(lines, 1):
            # Hide actual key values for security
            if 'API_KEY' in line and '=' in line:
                key_name = line.split('=')[0]
                print(f"{i}. {key_name}=***HIDDEN***")
            else:
                print(f"{i}. {line.rstrip()}")
    
    # Now load it
    from dotenv import load_dotenv
    load_dotenv(env_file)
    print("\n✓ .env loaded")
    
    # Check again
    serper_key = os.getenv("SERPER_API_KEY")
    if serper_key:
        print(f"✓ SERPER_API_KEY found (length: {len(serper_key)})")
        
        # Test it
        print("\n=== Testing Serper API ===")
        sys.path.append(str(backend_dir))
        try:
            from utils.web_search import serper
            results = serper.search_google("CNC machine", num_results=3)
            print(f"✅ SUCCESS! Found {len(results)} results:")
            for i, r in enumerate(results, 1):
                print(f"  {i}. {r.title[:60]}")
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print("❌ SERPER_API_KEY not found in .env file")
        print("\nPlease add this line to your .env file:")
        print("SERPER_API_KEY=your_actual_key_here")
else:
    print(f"\n❌ .env file not found at {env_file}")
    print("\nCreate the file and add:")
    print("SERPER_API_KEY=your_actual_key_here")
