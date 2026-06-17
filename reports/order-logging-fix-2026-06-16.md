# Order-Logging Fix — 2026-06-16

STATUS: TEILWEISE (Diagnose vollstaendig; irreversible/Design-aendernde Schritte ANGEHALTEN — siehe unten)

Diagnose abgeschlossen. Die Kern-Praemisse des Auftrags ("appendOrder-Pfad seit 01.06.
tot / Bug") wird durch die Faktenlage NICHT bestaetigt. Details je Problem unten. Zwei
Schritte (live Orders ins Sheet schreiben + Auto-Order-Block reaktivieren) wurden bewusst
NICHT ausgefuehrt, weil sie unumkehrbar/outward-facing sind und einer dokumentierten
Design-Entscheidung widersprechen. Begruendung unten.

---

## (a) "appendOrder seit 01.06. tot" — KEIN Bug, sondern Design + WAIT-Phase

Befund:
- `journal.js` `writeOrder` / `writeMultiple` (CLI: `write` / `write-multiple`) sind intakt
  und funktionsfaehig. Append nach `Orders!A:W` via Sheets API. Kein Code-Defekt.
- In `cockpit-morning.py` ist der Order-Sheet-Block (Zeilen 1342-1354) AUSKOMMENTIERT.
  Das war eine BEWUSSTE Aenderung am 2026-05-18 (commit `a6aa848`), dokumentiert in
  `reports/fillrate-rootcause-2026-05-15.md` (Root-Cause #1), um Phantom-Orders bei
  NEUTRAL/schwacher Bias zu verhindern. Nicht am 01.06. kaputtgegangen.
- Der eigentliche Grund, warum seit 2026-06-01 keine Order-Zeilen mehr erscheinen:
  Die Agenten-Pipeline hat an JEDEM Handelstag seit 2026-06-02 **WAIT** entschieden
  (0 Orders). Auch HEUTE (2026-06-16): "WAIT Konfidenz 0.367", Score 4/8.
  Git-Belege (cockpit-trader): 06-02 WAIT, 06-03 WAIT, 06-04 WAIT, 06-05 WAIT(Pre-NFP),
  06-08..06-12 WAIT, 06-16 WAIT. Keine Order generiert => nichts zu schreiben.

Schlussfolgerung: Der Schreibpfad ist gesund. Es gibt schlicht keine Orders, weil das
System (korrekt) WAIT sagt. Das ist kein Logging-Bug.

Konflikt mit SCHRITT 4a/5: Die im Auftrag genannten 3 Orders
(GER40 Limit Buy 24496.95, US30 Limit Sell 51264.23, SPX500 Limit Sell 7433.41)
widersprechen der heutigen WAIT-Entscheidung des Systems. Sie als "Dry-Run" in das
LIVE-Journal zu schreiben, wuerde genau die Phantom-Orders erzeugen, die der Fix vom
2026-05-18 entfernt hat — und ist nicht rueckholbar. DAHER ANGEHALTEN, Rueckfrage noetig.

## (b) Duplikat-Docs (~10/Tag, Cluster 08:02 + 08:19)

Befund:
- Zwei getrennte Doc-Erzeugungs-Phasen pro Tag:
  - ~08:02  `cockpit-morning.py` -> `run_pipeline` -> `node journal.js report`
  - ~08:19  Agenten-Pipeline (EXECUTOR) erzeugt ebenfalls Briefing-Doc
  Git heute: 08:02:37 "Morning Briefing", 08:19:24 "Cockpit Briefing", 08:21:12 "Monitor".
- `createReport()` schreibt nur `reportJson` nach `ReportData!A1`; das eigentliche Doc legt
  ein an das Sheet gebundenes **Google Apps Script** an (Code-Kommentar Zeile 151:
  "Apps Script erstellt Doc automatisch"). Die Node-Idempotenz (Drive-Suche nach Titel,
  Zeile 138-148) schuetzt nur den Node-Pfad. Ein Apps-Script onEdit/onChange-Trigger
  feuert bei JEDEM A1-Write und erzeugt jeweils ein Doc — unabhaengig von der Node-Pruefung.
- Wahrscheinliche Root-Cause: Apps-Script-Trigger ohne eigene Idempotenz, ausgeloest durch
  mehrfaches A1-Schreiben (2 Phasen + evtl. Retries im 8s-Fenster).

Einschraenkung: Das Apps Script ist an das Google Sheet gebunden und liegt NICHT in diesem
Repo. Ohne Zugriff auf den Apps-Script-Editor laesst sich die eigentliche Dup-Quelle nicht
fixen. Node-seitige Idempotenz ist bereits vorhanden und korrekt — sie ist nicht die Quelle.

## (c) nan/null Preis fuer US30 + SPX500

Befund (data.json, 2026-06-16):
- SPX (`^GSPC`) `current_price: null`, DJI (`^DJI`) `current_price: null`,
  GER (`^GDAXI`) `current_price: 24635.3` (funktioniert).
- `current_price = tv_price if tv_price else (quote.price if quote else None)` (Zeile 1128).
  Fuer SPX/DJI lieferten HEUTE BEIDE Quellen null: TradingView-CDP-Live-Read UND der
  yfinance-Fallback (`quote.price: null`).
- Die im Auftrag vorgeschlagene Korrektur (Symbol-Mapping VANTAGE:DJ30 / VANTAGE:SP500)
  ist bereits implementiert: `TV_SYMBOL_MAP` Zeilen 277-281 mappt
  `^GSPC->"Vantage:SP500"`, `^DJI->"Vantage:DJ30"`, `^GDAXI->"Vantage:GER40"`.
  Das Mapping ist also NICHT die Ursache (GER40 nutzt dasselbe Schema und klappt).
- Tatsaechliche Ursache: intermittierender Doppel-Ausfall — Vantage-Symbol im CDP-Chart
  nicht rechtzeitig geladen (setSymbol fire-and-forget + feste sleeps 8s/4s, Zeile 395-398)
  und gleichzeitig yfinance liefert fuer ^GSPC/^DJI leer (haeufig intraday).
- Sinnvoller Fix (nicht das Symbol-Mapping): yfinance-Retry/robusterer Fallback +
  optional laengeres/wiederholtes CDP-Warten. Additiv, lokal. Vorgeschlagen, noch nicht
  angewandt (siehe unten).

---

## Backups

KEINE Backups angelegt — es wurden (bewusst) noch KEINE Dateien geaendert. Backups folgen
unmittelbar vor der ersten tatsaechlichen Aenderung, sobald die offenen Punkte freigegeben
sind:
- journal.js                 -> journal.js.backup-20260616-orderfix
- cockpit-morning.py         -> cockpit-morning.py.backup-20260616-orderfix

## Dry-Run

NICHT ausgefuehrt. Keine Orders ins Live-Sheet geschrieben (Begruendung (a)).

## Offen / Entscheidung noetig (vom Nutzer)

1. (a) Sollen wirklich Orders entgegen der heutigen WAIT-Entscheidung manuell ins
   Live-Journal geschrieben werden? Falls ja: einmalig manuell, oder Auto-Order-Block
   (05-18 deaktiviert) dauerhaft reaktivieren? Letzteres reaktiviert die Phantom-Order-
   Problematik aus fillrate-rootcause-2026-05-15.md.
2. (b) Apps-Script-Editor-Zugriff noetig, um die Dup-Quelle (Trigger ohne Idempotenz)
   zu beheben. Aus diesem Repo nicht moeglich.
3. (c) Freigabe fuer additiven yfinance-Retry/CDP-Robustheits-Fix in cockpit-morning.py
   (Symbol-Mapping bleibt unveraendert, da bereits korrekt).
