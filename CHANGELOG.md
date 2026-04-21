# CHANGELOG — Cockpit Trader / Trading Floor
# Vollstaendige Aenderungshistorie fuer Claude Code
# Letzte Aktualisierung: 2026-04-21
# Claude Code: Lies diese Datei VOR jeder Aenderung!

---

## PROJEKT-UEBERSICHT

**Ziel:** Vollautomatisches Trading-Analyse-System fuer Futures (GER40, DJ30, SPX500)
**Strategie:** Auction Market Theory, Market Profile + Volume Profile als Fundament
**Maschine:** MINITRADER (Windows 11 Pro, Celeron J4125, 32GB RAM)
**Automatisierung:** Windows Task Scheduler -> BAT -> Claude Code -> 6 Agenten
**Dashboard:** https://chrisaibizz.github.io/cockpit-trader/

---

## SESSION #1 — iMac Setup (April 2026)

### Was gemacht wurde
- TradingView MCP Server installiert auf iMac (macOS Big Sur)
- Brave Browser als CDP-Ersatz fuer TradingView Desktop konfiguriert
- CDP Port 9222, `--remote-debugging-port=9222 --remote-allow-origins=http://localhost:9222`
- Claude Code installiert und authentifiziert
- MCP Server registriert via `claude mcp add` (NICHT via .mcp.json!)
- Alle 68 MCP-Tools getestet

### Wichtige Erkenntnisse
- MCP-Registrierung MUSS via CLI: `claude mcp add tradingview node [pfad]/server.js`
- Brave CDP: alle Instanzen killen BEVOR mit Debug-Flag starten
- `data_get_ohlcv` immer mit `summary: true` (verhindert Context-Overflow)
- `study_filter` immer angeben um spezifischen Indikator zu lesen

---

## SESSION #2 — Trading Cockpit Architektur (April 2026)

### Was gemacht wurde
- Multi-Agenten-Architektur entworfen (8 Agenten -> vereinfacht auf 6)
- state.json Schema definiert (Kommunikations-Hub zwischen Agenten)
- MINITRADER Setup: Ordnerstruktur, Windows Tasks, BAT-Dateien
- cockpit-morning.py: SafeJSONEncoder gegen NaN-Werte in data.json
- sys.exit(0) + Logging fuer Windows Task Scheduler (Exit Code 267014)
- Google Sheet ID: `1PA43AloHsrDtg-KG_139pCPOceisc7RJc8t9f2ffyrc`
- Google Drive Folder ID: `1i4g1GinXDUQHzeKopGorO1741oHLqxKw`

### Agenten-Struktur (final)
```
Agent 0: MACRO       -> Makrodaten (VIX, DXY, F&G, Put/Call, Bonds, Oil, Gold)
Agent 1: MARKETDATA  -> MP/VP/VWAP/ER/ONH/ONL/PDH/PDL per MCP
Agent 2: ANALYST     -> Bias pro Instrument (Score /8, 8 Signale)
Agent 3: CAPTAIN     -> Session-Bias, Strategie, Risikomanagement
Agent 4: EXECUTOR    -> Orders berechnen, Sheet/Doc/Push
Agent 5: MONITOR     -> 6 Bereiche pruefen, Statusreport, Notepad
KOORDINATOR          -> Orchestriert alle Agenten sequenziell
```

---

## SESSION #3 — Trading Floor Pipeline (April 2026)

### Was gemacht wurde
- TradingCockpit.bat: claude -p mit Prompt aus cockpit-morning-prompt.txt
- Option B Architektur: MCP-basierte MP-Extraktion via data_get_market_profile
- Option A (Pine Script Fork) verworfen: signifikante Wertabweichungen
- color=0 = POC, color=1 = Value Area, color=2 = Outside VA
- Dashboard neu designed: dark Cockpit-Theme, 3 Instrument-Karten
- 9 Bias-Signal-Dots (MP/VP/VWAP/SMC/ICH/S/R/EW/SMA/PIV)
- GitHub Pages: chrisaibizz.github.io/cockpit-trader/
- cockpit-morning.py schreibt dashboard-legacy.html, NICHT index.html

### Schluessel-Dateipfade
```
C:\Users\chris\TradingFloor\
  cockpit-trader\cockpit-morning.py     <- Haupt-Morning-Script
  cockpit-trader\data.json              <- Yahoo Finance Fallback-Daten
  cockpit-trader\index.html             <- Dashboard (GitHub Pages)
  cockpit-trader\journal-data.json      <- Tages-Analyse-Daten
  cockpit-trader\state.json             <- Kopie des Agent-State
  agents\shared\state.json              <- Haupt-State (Agenten-Kommunikation)
  agents\[name]\CLAUDE.md              <- Agent-Instruktionen
  trading-journal\journal.js            <- Google Sheet/Doc Exporter
  tradingview-mcp\src\server.js         <- MCP Server
  logs\pipeline\pipeline_[DATUM].log   <- Pipeline-Logs
  logs\DailyMon\monitor_[DATUM].txt    <- Monitor-Reports (NEU)
  cockpit-morning-prompt.txt            <- Morgen-Prompt
  cockpit-us-prompt.txt                 <- US-Update-Prompt
  change-template.txt                   <- Aenderungs-Prozess (NEU)
  CHANGELOG.md                          <- Diese Datei (NEU)
  TradingCockpit.bat                    <- 08:00 Task
  TradingCockpit-US.bat                 <- 14:00 Task
```

---

## SESSION #4 — LEAN + Bias-Optimierung (16. April 2026)

### Was gemacht wurde
- LEAN Repo analysiert: zu komplex, kein Vantage CFD Support -> nicht integriert
- compute_bias() Bug gefixt: NoneType Crash wenn mp=None
- Confluence-Score als eigenes Feld hinzugefuegt
- Dummy-Signale (OTF Check, Gap Analysis) aus Score entfernt
- FRED API via python-dotenv eingebunden (load_dotenv() in cockpit-morning.py)
- CPI YoY Bug gefixt: 330% -> korrekte ~3% Berechnung (400 Tage Zeitfenster)
- STPO ALL Indikator analysiert: Naked POC + Poor High/Low aktiviert
- Tasks konsolidiert: 4 Tasks -> 2 aktive Tasks (CockpitMorning + CockpitGitPush disabled)

### Windows Tasks (aktueller Stand)
```
TradingFloor-Morning  -> C:\Users\chris\TradingFloor\TradingCockpit.bat     (08:00, AKTIV)
TradingFloor-USUpdate -> C:\Users\chris\TradingFloor\TradingCockpit-US.bat  (14:00, AKTIV)
CockpitMorning        -> DISABLED (alt)
CockpitGitPush        -> DISABLED (alt)
```

---

## SESSION #5 — Multi-Agenten Live (19.-20. April 2026)

### Was gemacht wurde
- Erste vollstaendige Live-Pipeline 08:00 (alle 5 Agenten OK)
- state.json Schema 2.0 eingefuehrt
- Pipeline-Log System: logs/pipeline/pipeline_[DATUM]_[UHRZEIT].log
- US-Update CDP-Problem identifiziert und geloest
- Dashboard: neue index.html mit state.json + journal-data.json Live-Daten
- Generalprobe: alle Checks gruen

### Erste Live-Ergebnisse (20.04.2026)
```
08:00 Pipeline: ALLES OK
  MACRO:      NEUTRAL Score:+1
  MARKETDATA: vollstaendig (MCP live)
  ANALYST:    Phase:TREND Score:5/7
  CAPTAIN:    LONG-LEAN Score:5/7
  EXECUTOR:   3 Orders (SPX500/DJ30/GER40 LONG)
  GitHub:     OK Commit cacf6a7

14:00 US-Update: CDP-Problem -> manuell geloest
  Ergebnis: ER kollabiert (DJ30=2.78, SPX500=7.32 CHOP)
  Orders: alle OPEN, nicht gefuellt (V-Recovery ohne Pullback)
```

---

## SESSION #6 — Shape-Fix + Monitor + Optimierung (21. April 2026)

### Geaenderte Agenten

**agents/marketdata/CLAUDE.md** (KRITISCHE AENDERUNG)
- NEU: session_index=1 fuer Vortags-MP (NICHT aktuelle Session)
- NEU: Shape-Algorithmus: pos = (POC-VAL)/(VAH-VAL)
  * pos > 0.65 -> P-Shape (bullisch, +2)
  * pos < 0.35 -> b-Shape (baerisch, -2)
  * 0.35-0.65  -> D/B/Trend Day (neutral, 0)
- NEU: Double Distribution Check via LVN
- NEU: Plausibilitaets-Check bei pos > 0.90 oder < 0.10
- NEU: State-Felder: mp_shape_pos, mp_shape_bias, mp_shape_grund, mp_session
- LOG: gibt pos-Wert fuer alle 3 Instrumente aus

**agents/analyst/CLAUDE.md** (KRITISCHE AENDERUNG)
- NEU: MP-Shape als Signal #1 mit Gewichtung +/-2
- Score-Maximum: 7 -> 8
- Trade-Freigabe: >= 3 -> >= 4
- NEU: State-Felder: mp_shape, mp_shape_pos, mp_shape_signal, mp_shape_bias
- LOG: Shape + pos in Bestaetigung

**agents/captain/CLAUDE.md**
- Score: /7 -> /8, Schwellenwerte angepasst (>= 4 statt >= 3, stark >= 6 statt >= 5)
- NEU: Shape-Validierung: BESTAETIGT / KONFLIKT / NEUTRAL
- NEU: Konflikt -> max_risk -0.25%
- NEU: State-Feld shape_konflikt
- NEU: MP-SHAPES Block im Briefing-Output

**agents/executor/CLAUDE.md**
- Score: /7 -> /8, alignment_score >= 3 -> >= 4
- NEU: Shape-Konflikt -> P_Fill -10%
- NEU: mp_shape_yesterday mit pos: "b-Shape (pos=0.31)"
- NEU: Order-Felder mp_shape_pos, mp_shape_signal, mp_shape_konflikt
- Git Commit-Message: nur ASCII (kein Sonderzeichen!)

**agents/koordinator/CLAUDE.md**
- Score: /7 -> /8 ueberall
- NEU: Shape + pos in MARKETDATA/ANALYST/CAPTAIN Log-Zeilen
- NEU: Schritt 7 = MONITOR Agent
- NEU: MONITOR in Abschlusstabelle

**agents/monitor/CLAUDE.md** (NEUER AGENT)
- 6 Bereiche: Lokale Prozesse, Sheet+Doc, GitHub+Web, Datenqualitaet,
  Entscheidungs-Audit, Anomalien
- 2x taeglich Statusreport: logs/DailyMon/monitor_[DATUM]_[SESSION].txt
- Notepad automatisch oeffnen nach jedem Run
- Zusammenfassung: ALLES OK / X PROBLEME / X KRITISCH

### Geaenderte BAT-Dateien
**TradingCockpit.bat + TradingCockpit-US.bat**
- NEU: Harter Reset am Start (brave/node/claude/python killen)
- NEU: CDP-Warteschleife (alle 10 Sek, max 3 Min) statt blindem timeout 60
- NEU: +30 Sek fuer Indikator-Load nach CDP-Bestaetigung
- NEU: Cleanup am Ende (brave/node/claude killen)
- NEU: Abbruch-Pfad bei CDP-Fehler -> CLEANUP

### Geaenderte Prompts
**cockpit-us-prompt.txt**
- Umlaute entfernt (verursachten Execution error)
- NEU: FUEHRE AUS Marker bei jedem Schritt
- NEU: PFLICHT-ABSCHLUSS mit 5 Checkboxen
- NEU: Schritt 9 = Log-Datei schreiben (PowerShell-Code-Block)

### Neue Hilfsdateien
- `change-template.txt` -> 4-Schritt-Aenderungsprozess (IST/SOLL/Aenderung/Verifikation)
- `CHANGELOG.md` -> diese Datei

### Dashboard index.html
- ENTFERNT: window.__COCKPIT_DATA__ (eingebettete Altdaten vom 17.04.)
- GEAENDERT: Score /7 -> /8 ueberall
- NEU: Liest live state.json + journal-data.json + data.json
- NEU: WAIT-Banner (gelb) wenn session_bias = WAIT
- NEU: Shape-Badge mit pos-Wert auf Instrument-Karte
- NEU: Warnungen-Block im Dashboard
- BEHALTEN: alle Nav-Links, Level-Charts, VP-Balken, Makro-Block
- ERGAENZT (21.04. Claude Code): Nav-Links Indicators + Wiki hinzugefuegt (fehlten noch)

### Erster Live-Run mit neuem System (21.04.2026)
```
08:00 Pipeline: WAIT (korrekte Entscheidung)
  MACRO:      NEUTRAL Score:0
  MARKETDATA: b-Shape alle 3 (pos: GER40=0.094, DJ30=0.031, SPX500=0.10)
  ANALYST:    Phase:BALANCE Score:2/8
  CAPTAIN:    WAIT - ZEW 09:00 + Alignment 2/8 < 4
  EXECUTOR:   0 Orders
  MONITOR:    (erster Run erwartet nach 14:00)
```

---

## OFFENE PUNKTE (TODO)

1. [ ] us-update Log pruefen (14:00 Run heute)
2. [ ] MONITOR erster Run pruefen (Notepad-Output)
3. [x] Dashboard live verifizieren: Nav komplett (Dashboard/Journal/Orders/Indicators/Wiki)
4. [ ] Fill-Rate 9.4% analysieren: Entries zu weit vom Markt
5. [ ] cockpit-morning-prompt.txt auf Umlaute pruefen
6. [ ] Backtesting-System (Phase 2 - spaeter)

---

## CHANGE-PROZESS (ab sofort fuer alle Aenderungen)

Vor jeder Datei-Aenderung: change-template.txt lesen!
Pfad: C:\Users\chris\TradingFloor\change-template.txt

Kurzversion:
1. IST-Analyse: Datei lesen, alle Bestandteile listen
2. SOLL-Definition: nur Delta definieren (hinzufuegen/aendern/entfernen)
3. Aenderung: str_replace wenn < 10 Zeilen, Backup wenn > 50%
4. Verifikation: alle alten Bestandteile noch da? Diff zeigen.
5. Erst dann: git commit + git push

Git Commit-Message Format (NUR ASCII):
"Fix [Dateiname]: [kurze Beschreibung] - [Datum]"

---

## ARCHITEKTUR-UEBERSICHT (aktuell)

```
08:00 TradingCockpit.bat
  -> Reset (brave/node/claude/python killen)
  -> CDP-Warteschleife (max 3 Min, alle 10 Sek)
  -> cockpit-morning.py -> data.json erneuern
  -> claude -p [cockpit-morning-prompt.txt] --dangerously-skip-permissions
     KOORDINATOR liest C:\...\agents\koordinator\CLAUDE.md
     -> Agent 0 MACRO:      VIX/DXY/F&G/P-C/Bonds/Oil/Gold
     -> Agent 1 MARKETDATA: Vortags-MP session_index=1, Shape pos=(POC-VAL)/(VAH-VAL)
     -> Agent 2 ANALYST:    8 Signale inkl. Shape +/-2, Score /8, Freigabe >= 4
     -> Agent 3 CAPTAIN:    Shape-Validierung, Konflikt-Check, Risiko
     -> Agent 4 EXECUTOR:   Orders, Sheet, Doc, state.json, Git Push
     -> Agent 5 MONITOR:    6 Bereiche, Notepad-Report in logs/DailyMon/
  -> Cleanup (brave/node/claude killen)

14:00 TradingCockpit-US.bat
  -> Identischer Reset + CDP-Start
  -> claude -p [cockpit-us-prompt.txt] --dangerously-skip-permissions
     -> Marktdaten aktualisieren (neue MP/VWAP/ER Werte)
     -> Orders validieren (VALID/ANPASSEN/VERFALLEN)
     -> journal.js report
     -> state.json kopieren
     -> git push
     -> us-update Log schreiben
  -> Cleanup
```

---
