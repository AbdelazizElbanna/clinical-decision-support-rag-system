import os
import requests
from pathlib import Path

url = "https://www.aad.org/public/diseases/eczema/childhood/triggers"

html = requests.get(
    url,
    headers={"User-Agent": "Mozilla/5.0"}
).text

# Define temp directory to avoid cluttering data/raw
tmp_dir = Path("../../.tmp/scraped_html")
tmp_dir.mkdir(parents=True, exist_ok=True)

tmp_file = tmp_dir / "page.html"
with open(tmp_file, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Scraped HTML saved temporarily to {tmp_file}")
print("Run conversion script (e.g., convert_diseases_html_to_json.py) and then delete the .tmp folder.")