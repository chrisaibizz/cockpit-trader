# Fix A: Order-Befuell-Block reaktivieren (cockpit-morning.py)

STATUS: OK (mit WICHTIGEM Hinweis - siehe Abschnitt "BEFUND")

Datum: 2026-06-16
Backup: cockpit-trader/cockpit-morning.py.backup-20260616-fixa (92.961 Bytes)
Syntax: python -m py_compile -> Exit 0

HINWEIS ZUR RACE-CONDITION: Waehrend dieser Bearbeitung wurde die Datei von einem
parallelen Vorgang gleichzeitig editiert (Edit-Tool meldete "modified since read").
Dieser Parallel-Block enthielt zwei Abweichungen von der Aufgabenstellung:
(a) eine zusaetzliche `ALLOWED_INSTRUMENTS`-Whitelist (nicht beauftragt) und
(b) eine NEUTRAL-mit-Score-Ausnahme (widerspricht "Bias LONG/SHORT").
Beides wurde zugunsten der exakten Aufgaben-Spezifikation zurueckgebaut. Der finale
Code (unten dokumentiert) ist die Single-Source-of-Truth im File.

---

## SCHRITT 1 - IST-Analyse

### cockpit-morning.py
- `generate_journal_data()` (ab Z.1323) baut Orders NICHT aus state.json, sondern selbst:
  pro Instrument `generate_order(display_name, mp, price, bias_data, shape_name)` -> `orders_list`.
- `generate_order()` (Z.1215-1294) liefert Dict mit `entry/sl/tp1/tp2/rr/p_fill/p_tp1/...`
  (alle Preise als **String**). Liefert `None` bei fehlendem MP/Preis, VAH==VAL oder RR<1.0.
- Auskommentierter Block (urspruenglich Z.1419-1434, Commit a6aa848 vom 2026-05-18):
  schrieb `orders_list` nur dann nach `all_orders_for_sheet`, wenn
  `bias_str != "NEUTRAL" and abs(score) >= 4`.
- NACH dem Block: `all_orders_for_sheet` wird zurueckgegeben und in `run_pipeline()` (Z.1485)
  bei `if orders:` per `node journal.js write-multiple <json>` ins Google Sheet geschrieben.
  Bei leerer Liste: "Keine Orders (NEUTRAL Bias)".
- Instrument-Anzeigenamen in diesem Pfad: GER40 / US30 / SPX500.

### state.json - wo liegen die "echten" Orders?
- `state["orders"]["orders"]` = kanonische Order-Liste (vom EXECUTOR), `validierung` daneben.
  Heute: **leer (0 Orders)**.
- `state["captain"]` haelt Entscheidung/Konfidenz (`trade_freigabe`, `konfidenz_details`).
- WICHTIG: cockpit-morning.py laeuft als ERSTER Pipeline-Schritt. Zur Laufzeit von
  morning.py existiert die heutige CAPTAIN-Konfidenz noch NICHT.

## SCHRITT 2 - Backup
cockpit-trader/cockpit-morning.py.backup-20260616-fixa angelegt (92.961 Bytes).

## SCHRITT 3 - Reaktivierung (vorher/nachher)

VORHER (16 Zeilen, komplett auskommentiert):
```python
# if bias_str != "NEUTRAL" and abs(score) >= 4:
#     for ord_data in orders_list:
#         sheet_order = { ... }
#         sheet_order.update(ord_data)
#         all_orders_for_sheet.append(sheet_order)
```

NACHHER - neue Helper-Funktion (Z.1300-1320), exakt nach Aufgaben-Spezifikation:
```python
def is_valid_sheet_order(ord_data, bias_str, confluence_pct):
    """Phantom-Schutz: Entry>0, SL>0, Bias LONG/SHORT, Konfidenz>0.30."""
    try:
        entry = float(ord_data.get("entry", 0) or 0)
        sl    = float(ord_data.get("sl", 0) or 0)
    except (TypeError, ValueError):
        return False, "entry/sl nicht numerisch"
    if entry <= 0:                          return False, f"entry={entry} <= 0"
    if sl <= 0:                             return False, f"sl={sl} <= 0"
    if bias_str not in ("BULLISH","BEARISH"): return False, f"bias={bias_str} nicht LONG/SHORT"
    konfidenz = (confluence_pct or 0) / 100.0
    if konfidenz <= 0.30:                   return False, f"konfidenz={konfidenz:.3f} <= 0.30"
    return True, "ok"
```

NACHHER - reaktivierter Block im for-display_name-Loop (Z.1442-1467):
```python
for ord_data in orders_list:
    ok, grund = is_valid_sheet_order(ord_data, bias_str, conf_pct)
    if not ok:
        print(f"    [DEBUG] Order uebersprungen ({display_name}): {grund}")
        continue
    sheet_order = { date, time, instrument, bias, bias_pct, confluence, notes }
    sheet_order.update(ord_data)
    all_orders_for_sheet.append(sheet_order)
```
Zwei str_replace-Eingriffe (Helper + Block). Keine anderen Funktionen/Importe/Ausgaben
angefasst. `conf_pct`, `conf_label`, `bias_str`, `bias_de`, `bias_pct`, `today`,
`today_time`, `vix_price` sind alle bereits im Scope.

## Phantom-Schutz-Bedingungen (exakt nach Aufgabe, alle implementiert)
1. Entry echter float > 0 (try/float, sonst SKIP)
2. SL echter float > 0 (try/float, sonst SKIP)
3. Bias LONG/SHORT == BULLISH/BEARISH (NEUTRAL/WAIT wird verworfen)
4. Konfidenz > 0.30 (strikt; 0.30 wird verworfen)
Jede verworfene Order -> `print("    [DEBUG] Order uebersprungen (...): <Grund>")`, kein Write.

Mapping-Hinweis: cockpit-morning.py kennt KEINE LONG/SHORT/WAIT und KEINE CAPTAIN-Konfidenz
(diese entstehen erst spaeter). Daher: LONG/SHORT -> BULLISH/BEARISH (`bias_str`);
Konfidenz -> `confluence_pct / 100` als verfuegbarer Proxy (Schwelle 0.30 == 30%).
Gegenueber dem Parallel-Block bewusst WEGGELASSEN: ALLOWED_INSTRUMENTS-Whitelist und
NEUTRAL-mit-Score-Ausnahme (beide nicht in der Aufgabenstellung).

## SCHRITT 4 - Syntax-Check
`python -m py_compile cockpit-trader/cockpit-morning.py` -> **Exit 0**.
Grep-Verifikation: keine Reste von `ALLOWED_INSTRUMENTS` / `konfidenz_proxy` / `math.isnan`
im reaktivierten Block; `is_valid_sheet_order` exakt 1x definiert (Z.1300), 1x aufgerufen (Z.1452).

## SCHRITT 5 - Dry-Run (KEIN writeMultiple / run_pipeline)

state.json HEUTE:
- orders.orders count = **0**, captain.trade_freigabe = **False**
- konfidenz_final = **0.367** (LONG), Entscheidung = **WAIT** (< 0.40-Schwelle)
- Kontext: FOMC erst morgen (17.06 20:00), VIX 17.68, Makro nur +2 LEICHT_RISK_ON.

Heute ist ein WAIT-Tag (0 Live-Orders). Fuer den Dry-Run wurden Kandidaten-Orders aus den
realen MP-Levels (state.market.instruments) via `generate_order()` rekonstruiert; als
Konfidenz-Proxy je Instrument wurde `alignment_score/8` verwendet (verfuegbarer
per-Instrument-Wert in state.json zur morning.py-Laufzeit-Naeherung):

```
[GER40 ] bias=BULLISH score=2 align=2 konf=0.250 -> Limit Buy 24657.84/SL24611.22 rr8.83
         -> [DEBUG] uebersprungen: konfidenz=0.250 <= 0.30
[DJ30  ] bias=BULLISH score=4 align=4 konf=0.500 -> Limit Buy 50980.59/SL50908.09 rr13.28
         -> ANGENOMMEN (Sheet-Write)
[SPX500] bias=BULLISH score=4 align=4 konf=0.500 -> Limit Buy 7437.37/SL7417.23 rr6.24
         -> ANGENOMMEN (Sheet-Write)
ERGEBNIS: 2 angenommen, 1 uebersprungen
```

Gezielte Filter-Proben (synthetisch, entry=100/sl=90 sofern nicht anders):
```
Konfidenz-Schwelle:  cp=20 SKIP | cp=30 SKIP | cp=31 OK | cp=50 OK   (strikt > 0.30)
Bias:                BULLISH OK  | BEARISH OK | NEUTRAL SKIP
Entry/SL:            entry=0 SKIP | sl=0 SKIP | entry="x" SKIP (nicht numerisch)
```
Der Filter verhaelt sich exakt nach Spezifikation. writeMultiple/run_pipeline NICHT aufgerufen.

## BEFUND (WICHTIG - Diskrepanz, vor 08:00-Scharfschaltung pruefen)

Der reaktivierte Filter sitzt VOR der CAPTAIN-Entscheidung und kennt deren WAIT-Veto nicht:
- CAPTAIN sagt heute **WAIT / 0 Orders** (konfidenz 0.367 < 0.40, Chart+Makro geblendet).
- morning.py nutzt einen per-Instrument confluence/alignment-Proxy, der hoeher liegt als die
  geblendete CAPTAIN-Konfidenz und das Makro/FOMC-Veto NICHT enthaelt. Damit koennen an
  WAIT-Tagen dennoch Orders ins Sheet geschrieben werden.
- Genau aus diesem Grund (Phantom-Orders) wurde der Block am 2026-05-18 abgeschaltet
  (siehe fillrate-rootcause-2026-05-15.md, Root-Cause #1).

Empfehlung (NICHT umgesetzt, da nicht beauftragt): Sheet-Write zusaetzlich an die
CAPTAIN-Entscheidung koppeln - entweder morning.py erst NACH dem EXECUTOR aus
`state["orders"]["orders"]` schreiben lassen, oder den Write erst im EXECUTOR/journal.js
ausloesen. So bleibt das WAIT-Veto wirksam.

## Was beim naechsten 08:00-Lauf zu erwarten ist
- Block aktiv; py_compile sauber. Kein Git-Push (nicht beauftragt).
- Orders mit gueltigem Entry/SL, Bias BULLISH/BEARISH und Konfidenz-Proxy > 0.30 landen in
  `all_orders_for_sheet` -> `journal.js write-multiple` -> Google Sheet. Verworfene Orders
  erscheinen als `[DEBUG] Order uebersprungen (...)` im Pipeline-Log, ohne Sheet-Write.
- Bei einer heute-aehnlichen Lage koennen Orders geschrieben werden, OBWOHL CAPTAIN spaeter
  WAIT entscheidet - siehe BEFUND. Vor Scharfschaltung Nutzer-Entscheidung zur Diskrepanz noetig.
