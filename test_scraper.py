from modules.store_scraper import kjor_full_skanning

result = kjor_full_skanning()
print(f'\n=== RESULTAT ===\nMalt: {result[0]}\nHumle: {result[1]}\nGjær: {result[2]}')
