import requests

url = "https://www.aad.org/public/diseases/eczema/childhood/triggers"

html = requests.get(
    url,
    headers={"User-Agent": "Mozilla/5.0"}
).text

with open("page.html", "w", encoding="utf-8") as f:
    f.write(html)