"""
Test: yfinance Kalender-Moeglichkeiten
Was kann yfinance fuer Forward-looking Events liefern?
"""
import yfinance as yf
from datetime import datetime

print("=== yfinance Kalender Test ===\n")

# Test 1: SPX Earnings Calendar (naechste relevante Earnings)
print("[1] SPX Earnings Calendar (via ^GSPC)...")
try:
    spx = yf.Ticker("^GSPC")
    cal = spx.calendar
    print(f"    Ergebnis: {cal}")
except Exception as e:
    print(f"    FEHLER: {e}")

# Test 2: Earnings fuer grosse SPX-Komponenten (Apple, MSFT etc.)
print("\n[2] Naechste Earnings von grossen SPX-Titeln...")
for ticker in ["AAPL", "MSFT", "NVDA", "JPM", "META"]:
    try:
        t = yf.Ticker(ticker)
        cal = t.calendar
        if cal is not None and len(cal) > 0:
            print(f"    {ticker}: {cal}")
        else:
            print(f"    {ticker}: Keine Daten")
    except Exception as e:
        print(f"    {ticker}: FEHLER - {e}")

# Test 3: yfinance news (als Event-Proxy)
print("\n[3] Aktuelle News (SPX) als Event-Proxy...")
try:
    spx = yf.Ticker("^GSPC")
    news = spx.news
    if news:
        for n in news[:3]:
            print(f"    - {n.get('content', {}).get('title', 'kein Titel')[:80]}")
    else:
        print("    Keine News")
except Exception as e:
    print(f"    FEHLER: {e}")

print("\n=== Test abgeschlossen ===")
print("Fazit: yfinance hat KEINEN Wirtschaftskalender (FOMC, CPI, NFP)")
print("       Nur Earnings-Daten fuer einzelne Aktien.")
