# Order-Diagnose — 2026-06-16

STATUS: ABGESCHLOSSEN (nur Diagnose, KEINE Fixes durchgefuehrt)

Auftrag: Warum werden seit ~01.06.2026 keine Orders ins Google-Sheet-Tab "Orders"
geschrieben?

Kernbefund vorweg: **Es liegt KEIN Schreib-Bug vor.** Der Schreibpfad ist intakt.
Es werden keine Order-Zeilen geschrieben, weil seit dem 02.06. an jedem Handelstag
**0 Orders generiert** werden — teils durch eine bewusste Design-Entscheidung
(auskommentierter Block), teils durch durchgaengige WAIT-Entscheidungen der Agenten,
teils durch fehlende Preise (null) fuer US30/SPX500.

---

## 0. Terminologie-Korrektur

Der Auftrag nennt eine Funktion `appendOrder()`. Eine solche Funktion existiert
NICHT in `journal.js`. Der Order-Schreibpfad heisst:
- `writeOrder(orderJson)` — Einzel-Order, CLI: `node journal.js write` (journal.js:44)
- `writeMultiple(ordersJson)` — Mehrere Orders, CLI: `node journal.js write-multiple` (journal.js:53)

Beide haengen via Sheets-API `values.append` an `Orders!A:W` an (journal.js:48 / 57).
Die folgende Analyse bezieht sich auf diese tatsaechlichen Funktionen.

---

## 1. Root Cause "appendOrder" (Order-Schreibpfad) — KEIN Fehler im Code

`writeMultiple` (journal.js:53-61) und `writeOrder` (journal.js:44-51) sind funktions-
faehig: kein try/catch der Fehler verschluckt, klarer `values.append` nach `Orders!A:W`,
Erfolg wird via `cloudLog` und stdout gemeldet. Kein Defekt.

Aufgerufen wird `write-multiple` ausschliesslich aus `cockpit-morning.py`:
- `run_pipeline()` (cockpit-morning.py:1405) ruft bei `if orders:` (Zeile 1417)
  `node journal.js write-multiple <orders_json>` auf (Zeile 1421-1424).
- `orders` stammt aus `generate_journal_data()` als zweiter Rueckgabewert
  `all_orders_for_sheet` (cockpit-morning.py:1399, aufgerufen 1623, durchgereicht 1738).

**Der entscheidende Punkt:** `all_orders_for_sheet` wird NIE befuellt. Der einzige Code,
der diese Liste fuellt, ist **auskommentiert** (cockpit-morning.py:1342-1354):

```python
# 1339 # Sheet-Write nur bei klarer Direktion + ausreichender Konfluenz.
# 1340 # Verhindert Phantom-Orders bei NEUTRAL/schwacher Bias.
# 1341 # Quelle: reports/fillrate-rootcause-2026-05-15.md (Root-Cause #1)
# 1342 # if bias_str != "NEUTRAL" and abs(score) >= 4:
# 1343 #     for ord_data in orders_list:
# ...
# 1354 #         all_orders_for_sheet.append(sheet_order)
```

Folge: `orders` ist in `run_pipeline` IMMER `[]` → der `else`-Zweig greift
(cockpit-morning.py:1431-1432): Ausgabe ">>> Google Sheet: Keine Orders (NEUTRAL Bias)".
`write-multiple` wird also vom Morning-Pfad gar nicht erst aufgerufen.

Das ist KEIN 01.06.-Regression, sondern eine bewusste Aenderung vom 2026-05-18
(dokumentiert in `reports/fillrate-rootcause-2026-05-15.md`, Root-Cause #1), um
Phantom-Orders bei NEUTRAL/schwacher Bias zu verhindern.

Zweiter potenzieller Schreibpfad: der **EXECUTOR-Agent** (08:00/14:00-Pipeline) kann
ebenfalls Orders via `journal.js write-multiple` schreiben, wenn er einen Trade freigibt.
Seit 02.06. lautet die Pipeline-Entscheidung jedoch durchgehend **WAIT** (Git-Belege
cockpit-trader: 06-02 bis 06-16 alle WAIT; heute "WAIT Konfidenz 0.367", Score 4/8).
Bei WAIT entstehen 0 Orders → nichts zu schreiben.

Verdaechtige Stellen:
- cockpit-morning.py:1230 — `all_orders_for_sheet = []` (wird nie gefuellt)
- cockpit-morning.py:1342-1354 — auskommentierter Befuell-Block (Kern-Ursache Morning-Pfad)
- cockpit-morning.py:1417/1431 — `if orders:` ist immer falsch → else-Zweig
- journal.js:53-61 — `writeMultiple` selbst: intakt, nicht ursaechlich

## 2. Root Cause Duplikat-Docs — Idempotenz reicht nur im Node-Pfad

`createReport()` (journal.js:128-165) und `appendKiAnalyse()` (journal.js:168-228)
sind node-seitig idempotent:
- `createReport`: Drive-Titel-Suche `q: name='Cockpit Briefing <date>' ...` und Skip,
  falls Doc existiert (journal.js:139-148).
- `appendKiAnalyse`: Marker-Check `=== KI-Analyse ===` im Doc-Text, Skip falls vorhanden
  (journal.js:201-209). `appendKiUpdate` analog mit Marker `=== KI-Update 14:45 ===`
  (journal.js:264-278).

Diese Idempotenz schuetzt aber NUR den Node-Pfad. `createReport` legt das Doc NICHT
selbst an — es schreibt nur `reportJson` nach `ReportData!A1` (journal.js:149); das
eigentliche Doc erzeugt ein an das Sheet gebundenes **Google Apps Script** (Kommentar
journal.js:151: "Apps Script erstellt Doc automatisch"). Ein Apps-Script-Trigger
(onEdit/onChange) feuert bei JEDEM A1-Write und kennt die Node-Idempotenz nicht.

Verstaerkend: zwei getrennte Doc-Phasen pro Tag (~08:02 cockpit-morning.py run_pipeline;
~08:19 EXECUTOR-Agent) plus moegliche Retries im 8s-Wartefenster (journal.js:152)
schreiben mehrfach nach A1 → Apps-Script erzeugt je Write ein Doc.

Einschraenkung: Das Apps Script liegt am Google-Sheet, NICHT in diesem Repo — die
eigentliche Dup-Quelle (Trigger ohne eigene Idempotenz) ist von hier aus nicht
einsehbar/fixbar. Node-Idempotenz ist korrekt und NICHT die Quelle.

Verdaechtige Stellen:
- journal.js:149 — A1-Write loest Apps-Script-Trigger aus (Doc-Erzeugung ausserhalb Node)
- journal.js:152 — 8s setTimeout, in dem Retries weitere A1-Writes ausloesen koennen
- Doppel-Aufruf `node journal.js report`: cockpit-morning.py:1445 + separat EXECUTOR-Agent

## 3. Root Cause nan/null-Preis US30/SPX500 — Symbol ist korrekt, Preis-Quelle faellt aus

Das verwendete Symbol ist NICHT die Ursache. `TV_SYMBOL_MAP` (cockpit-morning.py:277-281)
mappt bereits korrekt:
```python
"^GSPC":  "Vantage:SP500"
"^DJI":   "Vantage:DJ30"
"^GDAXI": "Vantage:GER40"
```
GER40 nutzt dasselbe Schema und funktioniert (data.json 2026-06-16:
`^GDAXI current_price: 24635.3`), waehrend `^GSPC` und `^DJI` `current_price: null` haben.

Preis-Logik (cockpit-morning.py:1128):
```python
"current_price": tv_price if tv_price else (q["price"] if q else None)
```
Fuer SPX/DJI lieferten HEUTE BEIDE Quellen null: TradingView-CDP-Live-Read (`tv_price`)
UND der yfinance-EOD-Fallback (`q["price"]`). Ergebnis: `current_price = None`.

Downstream-Effekt: `generate_order(inst, mp, price, ...)` gibt sofort `None` zurueck,
wenn `not price` (cockpit-morning.py:1136-1137). Also kein Order-Objekt fuer US30/SPX500,
selbst wenn der auskommentierte Sheet-Block (Punkt 1) wieder aktiv waere.

Wahrscheinliche Ursache: intermittierender Doppel-Ausfall — Vantage-Symbol im CDP-Chart
nicht rechtzeitig geladen (setSymbol fire-and-forget + feste sleeps) UND yfinance liefert
fuer ^GSPC/^DJI intraday haeufig leer. Sinnvoller Fix waere yfinance-Retry / robusterer
Fallback / laengeres CDP-Warten — NICHT das (bereits korrekte) Symbol-Mapping.

Verdaechtige Stellen:
- cockpit-morning.py:1128 — `current_price` wird None wenn beide Quellen leer
- cockpit-morning.py:1136-1137 — `generate_order` returnt None bei `not price`
- cockpit-morning.py:277-281 — Symbol-Map (korrekt, NICHT Ursache)

---

## Gesamt-Schlussfolgerung

Drei voneinander unabhaengige Gruende, dass "Orders" leer bleibt:
1. (Design) Morning-Pfad-Befuellung von `all_orders_for_sheet` ist auskommentiert
   (cockpit-morning.py:1342-1354) → `write-multiple` wird nie aufgerufen.
2. (Markt/Agent) EXECUTOR entscheidet seit 02.06. durchgehend WAIT → 0 Orders.
3. (Daten) US30/SPX500 ohne Preis (null) → `generate_order` returnt None.

Der Schreib-Code (`writeMultiple`/`writeOrder`, journal.js) ist gesund. Keine
Code-Aenderung in diesem Lauf — reine Diagnose gemaess Auftrag.

## Hinweis zu git log (Auftragsschritt 3)

`git -C C:\Users\chris\TradingFloor\trading-journal log` schlaegt fehl:
`trading-journal/` ist KEIN Git-Repo (einziges Repo ist `cockpit-trader/`, lt.
CLAUDE.md). Es existiert daher keine Commit-Historie fuer journal.js. Die oben
zitierten WAIT-Belege stammen aus `git -C cockpit-trader log`.
