# Fix-A2: Sheet-Write von morning.py zum EXECUTOR verlagern

STATUS: OK

Datum: 2026-06-16
Syntax: `venv/Scripts/python.exe -m py_compile cockpit-morning.py` -> Exit 0

Ziel erreicht: cockpit-morning.py schreibt KEINE Orders mehr ans Google Sheet.
Das Sheet-Logging uebernimmt jetzt der EXECUTOR NACH seinem Lauf aus
`state["orders"]["orders"]` - dadurch bleibt das CAPTAIN-WAIT-Veto wirksam.

---

## RACE-CONDITION HINWEIS (wichtig)

Waehrend dieser Bearbeitung lief ein paralleler Vorgang, der die morning.py-Haelfte
(SCHRITT 3) bereits identisch erledigt hatte und auf einen Schwester-Report
`reports/fix-a2-morning-2026-06-16.md` verweist. Die morning.py-Aenderungen unten
stammen aus diesem Parallel-Lauf, sind inhaltlich korrekt und wurden hier nur
verifiziert (nicht doppelt angewandt). Die EXECUTOR-Haelfte (SCHRITT 4) wurde von
diesem Lauf erledigt.

---

## cockpit-morning.py - was auskommentiert wurde

Datei: `cockpit-trader/cockpit-morning.py`

1. Order-Befuell-Block in `generate_journal_data()` (Z. ~1451-1470):
   Die Schleife `for ord_data in orders_list:` mit `is_valid_sheet_order()`-Pruefung
   und `all_orders_for_sheet.append(sheet_order)` ist vollstaendig auskommentiert.
   -> `all_orders_for_sheet` bleibt jetzt immer leer; `journal-data.json`
      `total_orders`/`orders_checked` = 0.

2. writeMultiple-Aufruf in `run_pipeline()` (Z. ~1536-1551):
   Der gesamte `if orders: ... node journal.js write-multiple ... else: ...`-Block
   ist auskommentiert, ersetzt durch:
   `print(">>> Google Sheet: Order-Write deaktiviert (Fix-A2 2026-06-16)")`.
   -> morning.py ruft `journal.js write-multiple` fuer Orders NICHT mehr auf.

Unveraendert aktiv bleiben (schreiben KEINE Order-Zeilen):
- `node journal.js report` (Google Doc Morning Report)
- `node journal.js stats` (Stats-Tab-Aktualisierung)

`is_valid_sheet_order()` (Z.1300-1320) bleibt definiert, wird aber nicht mehr
aufgerufen (toter, harmloser Helper).

---

## EXECUTOR/CLAUDE_ref.md - was ergaenzt wurde

Datei: `agents/executor/CLAUDE_ref.md`
Neuer Abschnitt am Dateiende: **"## SCHRITT 7 - SHEET-LOGGING (NEU, Fix-A2 2026-06-16)"**
(ab Z.184, direkt nach dem Position-Sizing-Abschnitt).

Inhalt:
- Liest `state["orders"]["orders"]`.
- Schreibt nur, wenn Liste NICHT leer UND `captain.trade_freigabe == true`
  (Entscheidung != WAIT).
- Pro Order ein Aufruf `node journal.js write '<order-json>'`.
- Feld-Mapping state-Order -> journal.js-JSON dokumentiert.
- Bei leer/WAIT: `[INFO] WAIT - kein Sheet-Write`.

---

## Backups

- `cockpit-trader/cockpit-morning.py.backup-20260616-fixa2`
  (Pre-Edit-Snapshot = reaktivierter Fix-A-Stand; md5 e56578...; ueberschreibt
   einen aelteren gleichnamigen Snapshot aus einem abgebrochenen Lauf. Der
   kanonische Pre-Fix-A-Stand bleibt in `...backup-20260616-fixa`, 92.961 Bytes.)
- `agents/executor/CLAUDE_ref.md.backup-20260616-fixa2` (md5 fd7e01...)

---

## Dry-Run (state["orders"]["orders"] von heute, 2026-06-16)

```
=== DRY-RUN EXECUTOR SHEET-LOGGING (heute 2026-06-16) ===
state.orders.orders count: 0
captain.trade_freigabe: false | WAIT-Bedingung: true
-> [INFO] WAIT - kein Sheet-Write (Liste leer oder trade_freigabe=false)
-> EXECUTOR wuerde 0 Zeilen ins Sheet schreiben.
```

Heute ist ein WAIT-Tag (0 Live-Orders, trade_freigabe=false, konfidenz_final 0.367
< 0.40, FOMC morgen 17.06). Der EXECUTOR wuerde korrekt NICHTS ins Sheet schreiben.
An einem Trade-Tag mit gefuellter Order-Liste wuerde pro Order genau eine Zeile
geschrieben (Felder gemappt wie unten).

---

## Offene Frage: journal.js write CLI-Syntax (EXAKT, fuer morgen)

WICHTIG: Es gibt KEIN `write-order` in journal.js. Die Befehle sind:

| Befehl | Funktion | Argument |
|---|---|---|
| `node journal.js write '<json>'` | EINE Order | 1 JSON-Objekt (String) |
| `node journal.js write-multiple '<json>'` | mehrere Orders | 1 JSON-Array (String) |

`writeOrder(orderJson)` liest aus dem JSON genau diese Keys (alle optional,
fehlend -> leere Zelle), Reihenfolge der Sheet-Spalten A..W:
```
date, time, instrument, type, entry, sl, tp1, tp2, rr, p_fill, p_tp1,
confluence, tf, bias, bias_pct, mp_shape_yesterday, mp_shape_forecast,
vwap_position, notes
```
Namens-Fallen: Spalte heisst `confluence` (NICHT `konfluenz`) und `type`
(NICHT `typ`). Das EXECUTOR-Order-Objekt in state.json nutzt `konfluenz_score`
und `richtung` -> muss gemappt werden:
- `richtung` LONG/BULLISH -> `type` = "Limit Buy"; SHORT/BEARISH -> "Limit Sell"
- `konfluenz_score` -> `confluence`

Beispiel-Aufruf (eine Order):
```powershell
node C:\Users\chris\TradingFloor\trading-journal\journal.js write '{"date":"2026-06-16","time":"08:25","instrument":"DJ30","type":"Limit Buy","entry":50980.59,"sl":50908.09,"tp1":51200,"rr":3.0,"p_fill":65,"confluence":7,"tf":"30M","bias":"BULLISH","bias_pct":80,"notes":"ONL-Stop | PDH-TP1 | R:R 3.0"}'
```

## Offene Frage 2: Redundanz mit bestehendem SCHRITT 3

CLAUDE_ref.md enthaelt weiterhin den aelteren Abschnitt "Google Sheet Export
(SCHRITT 3)" via `agent-output/orders-export.json` + `write-multiple`. Neuer
SCHRITT 7 (write je Order aus state) und alter SCHRITT 3 ueberschneiden sich -
werden beide ausgefuehrt, entstehen Doppel-Zeilen. Empfehlung: im Live-Betrieb
nur EINEN Pfad nutzen (bevorzugt SCHRITT 7, da an state["orders"]["orders"]
und damit an die CAPTAIN-Freigabe gekoppelt). Nicht entfernt, da nicht beauftragt.
