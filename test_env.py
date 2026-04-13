from dotenv import load_dotenv
import os

load_dotenv()

fred_key = os.getenv("FRED_API_KEY")
finnhub_key = os.getenv("FINNHUB_API_KEY")

print("=== .env Test ===")
if fred_key:
    print(f"FRED_API_KEY:    {fred_key[:8]}... (OK)")
else:
    print("FRED_API_KEY:    NICHT GEFUNDEN!")

if finnhub_key:
    print(f"FINNHUB_API_KEY: {finnhub_key[:8]}... (OK)")
else:
    print("FINNHUB_API_KEY: NICHT GEFUNDEN!")

# FRED API Test
print("\n=== FRED API Test ===")
try:
    from fredapi import Fred
    f = Fred(api_key=fred_key)
    gdp = f.get_series("GDP").tail(1)
    print(f"FRED OK: {gdp}")
except Exception as e:
    print(f"FRED Fehler: {e}")

print("\n=== Test abgeschlossen ===")
