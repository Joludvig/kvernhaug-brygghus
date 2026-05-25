import requests
from bs4 import BeautifulSoup

url = "https://vestbrygg.no"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

res = requests.get(url, headers=headers, timeout=10)
print(f"Statuskode: {res.status_code}")

soup = BeautifulSoup(res.text, "html.parser")

# Test 1: Sjekk om det i det hele tatt finnes noen lenker eller produkter
produkter_klasse = soup.select(".product")
print(f"Antall elementer med '.product': {len(produkter_klasse)}")

# Test 2: Sjekk hva slags overskrifter som finnes på siden
h2_tags = soup.find_all("h2")
print(f"Antall H2-overskrifter funnet: {len(h2_tags)}")
if h2_tags:
    print(f"Første H2-tekst: '{h2_tags[0].get_text(strip=True)}'")
