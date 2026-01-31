
import sys
import os
from pathlib import Path

# Add current dir to path
sys.path.append(str(Path(__file__).parent))

from utils.module_1.helpers import safe_json_loader, normalize_headers
from utils.web_search.base import _normalize_headers # Testing the local shim too

def test_safe_json_loader():
    print("Testing safe_json_loader...")
    
    # Case 1: Perfect JSON with markdown
    raw1 = "```json\n{\"key\": \"value\"}\n```"
    assert safe_json_loader(raw1) == {"key": "value"}
    
    # Case 2: Broken JSON (unterminated string)
    raw2 = "{\"key\": \"unterminated"
    # Our helper should try to fix it
    res2 = safe_json_loader(raw2)
    print(f"Broken string result: {res2}")
    
    # Case 3: JSON with text around it
    raw3 = "Here is the result: {\"success\": true} and some more text."
    assert safe_json_loader(raw3) == {"success": True}
    
    # Case 4: Smart quotes and trailing comma
    raw4 = "{\u201ckey\u201d: \u201cvalue\u201d,}"
    assert safe_json_loader(raw4) == {"key": "value"}
    
    print("safe_json_loader tests passed!")

def test_normalize_headers():
    print("\nTesting normalize_headers...")
    headers = {
        "Content-Type": "application/json",
        "X-Enabled": True,
        "X-Count": 10
    }
    normalized = normalize_headers(headers)
    assert normalized["X-Enabled"] == "True"
    assert normalized["X-Count"] == "10"
    assert normalized["Content-Type"] == "application/json"
    
    # Test the internal shim in web_search.base
    shim_normalized = _normalize_headers(headers)
    assert shim_normalized["X-Enabled"] == "True"
    
    print("normalize_headers tests passed!")

def test_shared_executor_import():
    print("\nTesting SHARED_EXECUTOR availability...")
    from utils.module_1.enricher import SHARED_EXECUTOR
    assert SHARED_EXECUTOR is not None
    print("SHARED_EXECUTOR available.")

if __name__ == "__main__":
    try:
        test_safe_json_loader()
        test_normalize_headers()
        test_shared_executor_import()
        print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
    except Exception as e:
        print(f"\nVERIFICATION FAILED: {e}")
        sys.exit(1)
