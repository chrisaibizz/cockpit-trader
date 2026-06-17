# Fix C: Preis-Fallback-Kette US30/SPX500 (+GER40)

STATUS: OK

Datei:  cockpit-trader/cockpit-morning.py
Backup: cockpit-trader/cockpit-morning.py.backup-20260616-fixc
Datum:  2026-06-16

---

## SCHRITT 1 — IST-Analyse (Preis-Fetch-Logik)

Preis wird pro Instrument in `process_instrument(ticker, name)` zusammengesetzt:

- `get_tv_data(ticker)` -> liefert `tv_price` (TradingView live via CDP, Z. 1109/542-637)
- `fetch_quote(ticker)`  -> liefert `q` mit `q["price"]` (yfinance EOD, Z. 80-104, 1111)
- ALT (vorher, Z. 1128):
  `"current_price": tv_price if tv_price else (q["price"] if q else None)`
- `compute_bias(...)` und `generate_journal_data(...)` lesen `inst["current_price"]`
  (Z. 1611-1613, 1249).
- `generate_order(inst, mp, price, ...)` (Z. 1135): erste Zeile
  `if not mp or not price: return None` -> bei `current_price=None` keine Order.

None-Behandlung vorher: keine Fallbacks. Wenn TV live UND yfinance beide ausfielen,
wurde `current_price=None` -> `generate_order` lieferte None -> keine Order.

## SCHRITT 2 — Backup
`cockpit-trader/cockpit-morning.py` -> `cockpit-trader/cockpit-morning.py.backup-20260616-fixc` (87497 Bytes)

## SCHRITT 3 — FIX (rein additiv)

Neue Helfer vor `process_instrument` eingefuegt (Abschnitt 4):
- `ALT_TICKER_MAP`  : `^DJI->YM=F`, `^GSPC->ES=F` (Futures-Fallback-Ticker)
- `STATE_INSTRUMENT_MAP` : `^GSPC->SPX500`, `^DJI->DJ30`, `^GDAXI->GER40`
- `_valid_price(p)` : True nur bei endlicher Zahl > 0 (faengt None/NaN/Inf/Strings ab)
- `_read_last_price_from_state(key)` : liest letzten Preis aus state.json
- `resolve_current_price(ticker, tv_price, q)` : Fallback-Kette, gibt `(preis, quelle)`

Fallback-Reihenfolge in `resolve_current_price`:
1. TV live > yfinance Primaer-Ticker        (bestehende Logik, unveraendert)
2. yfinance Retry mit Futures-Ticker         (DJ30->YM=F, SP500->ES=F)
3. letzter bekannter Preis aus state.json
4. alle Quellen None -> `[WARNING]` print + `logging.warning` -> `current_price=None`
   (bestehendes Verhalten: `generate_order` liefert None)

GER40 hat keinen Futures-Alt-Ticker -> ueberspringt Stufe 2, nutzt direkt Stufe 3
(state.json) -> Konsistenz-Anforderung erfuellt.

### Geaenderte Zeilen (vorher/nachher)

VORHER (process_instrument, return-Block):
```
    return {
        "name": name, "ticker": ticker,
        "quote": q, "market_profile": mp,
        "cvd": cvd,
        "current_price": tv_price if tv_price else (q["price"] if q else None),
    }
```
NACHHER:
```
    current_price, price_source = resolve_current_price(ticker, tv_price, q)

    return {
        "name": name, "ticker": ticker,
        "quote": q, "market_profile": mp,
        "cvd": cvd,
        "current_price": current_price,
        "price_source": price_source,
    }
```
Zusaetzlich: ~80 Zeilen Helfer-Block (ALT_TICKER_MAP, STATE_INSTRUMENT_MAP,
_valid_price, _read_last_price_from_state, resolve_current_price) vor
`def process_instrument`. KEINE bestehende Funktion entfernt/veraendert.

### ABWEICHUNG vom Auftrag (bewusst, dokumentiert)
Auftrag Stufe 3 nennt Pfad `state["instruments"][instrument]["last_price"]`.
Dieser Pfad existiert in der echten state.json NICHT. Tatsaechliche Struktur:
`state["market"]["instruments"][KEY]["price"]` (KEY = GER40/DJ30/SPX500).
`_read_last_price_from_state` prueft BEIDE Pfade (zuerst die echte Struktur,
dann den im Auftrag genannten Pfad als Vorwaerts-Kompatibilitaet). Andernfalls
waere Stufe 3 wirkungslos gewesen.
Instrument-Keys: ^DJI -> "DJ30" (nicht "US30") gemaess state.json market.instruments
und gemaess Auftrags-Notation "DJ30->YM=F".

## SCHRITT 4 — Syntax-Check
`python -m py_compile cockpit-morning.py` -> exit 0 (Python 3.11.9). FEHLERFREI.

## SCHRITT 5 — Smoke-Test (kein Live-Write, kein main())
Modul per importlib geladen, `resolve_current_price` isoliert getestet:

| Szenario | DJ30/US30 | SP500/SPX500 | GER40 |
|---|---|---|---|
| [A] state.json last_price direkt | 51839.45 | 7568.25 | 24921.69 |
| [B] tv_price gueltig (Stufe 1) | 12345.67 / tradingview_live | 12345.67 / tradingview_live | 12345.67 / tradingview_live |
| [C] tv None, q gueltig (Stufe 1) | 555.5 / yfinance_primary | 555.5 / yfinance_primary | 555.5 / yfinance_primary |
| [D] tv None, q None | 52181.0 / yfinance_alt:YM=F (Stufe 2) | 7623.5 / yfinance_alt:ES=F (Stufe 2) | 24921.69 / state_last_price (Stufe 3) |
| [E] tv NaN, q NaN | 52181.0 / yfinance_alt:YM=F (Stufe 2) | 7623.5 / yfinance_alt:ES=F (Stufe 2) | 24921.69 / state_last_price (Stufe 3) |

Smoke-Test exit 0. Stufe 4 (alle None) wurde fuer DJ30/SP500/GER40 nicht erreicht,
da Stufe 2 (Futures live) bzw. Stufe 3 (state.json) jeweils griffen — das ist das
gewuenschte Verhalten.

### Welcher Preis / welche Stufe (Fallback-Faelle D/E)
- DJ30/US30:  52181.0  ueber Stufe 2 (yfinance Futures YM=F)
- SP500/SPX500: 7623.5 ueber Stufe 2 (yfinance Futures ES=F)
- GER40:     24921.69  ueber Stufe 3 (state.json market.instruments.GER40.price)

## Hinweise
- `fredapi` ist in der Testumgebung nicht installiert (vorbestehend, ohne Bezug zum Fix).
- Nicht angefasst: `cockpit-trader/.github/workflows/cockpit-morning.py` (GitHub-Actions-Kopie,
  ausserhalb des Auftrags-Scopes).
- KEIN git commit/push durchgefuehrt (Auftrag endet mit Report; nicht angefordert).
