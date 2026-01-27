"""Debug Alibaba HTML to see actual structure"""

import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

url = "https://www.alibaba.com/trade/search?SearchText=CNC+machine"
print(f"Fetching: {url}")

try:
    response = requests.get(url, headers=headers, timeout=15)
    print(f"Status: {response.status_code}")
    print(f"Content Length: {len(response.text)}")
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Save HTML to file for inspection
    with open("alibaba_debug.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print("✓ Saved HTML to alibaba_debug.html")
    
    # Try to find product containers with various selectors
    selectors_to_try = [
        "[class*='organic-offer-wrapper']",
        "[class*='J-offer-wrapper']",
        ".list-no-v2-item",
        "[class*='offer']",
        "[class*='product']",
        "[class*='item-']",
        ".organic-list-offer",
        "div[data-content='product']",
    ]
    
    print("\n=== Testing Selectors ===")
    for selector in selectors_to_try:
        matches = soup.select(selector)
        print(f"{selector:50} → {len(matches)} matches")
        if matches and len(matches) > 0:
            print(f"  First match tag: {matches[0].name}, classes: {matches[0].get('class')}")
    
    # Try to find any div with "offer" or "product" in class name
    print("\n=== All divs with 'offer' or 'product' in class ===")
    all_divs = soup.find_all("div", class_=True)
    relevant = [d for d in all_divs if any(x in str(d.get('class')) for x in ['offer', 'product', 'item'])]
    unique_classes = set()
    for d in relevant[:20]:
        classes = ' '.join(d.get('class', []))
        if classes and classes not in unique_classes:
            unique_classes.add(classes)
            print(f"  {classes}")
    
except Exception as e:
    print(f"Error: {e}")
