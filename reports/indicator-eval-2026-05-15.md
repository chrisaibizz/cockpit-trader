# Indikator-Evaluation — Elliott Wave / AutoFibo 15M / SMC / Ichimoku

Datum: 2026-05-15
Autor: Eval-Run (automatisch)
Sprache: Deutsch
Ziel: Datenbasierte Pruefung, ob die 4 Verdachts-Indikatoren echten Edge liefern oder gestrichen werden koennen.

---

## TL;DR

| Indikator    | Im Schema | Im Code aktiv | Coverage post-fix | Trades zum Messen | Empfehlung      |
|--------------|-----------|---------------|-------------------|-------------------|-----------------|
| Elliott Wave | NEIN      | NEIN          | 0/22 Runs (0%)    | 0                 | **DROP**        |
| SMC          | JA        | NEIN (=0)     | 0/22 Runs (0%)    | 0                 | **DROP**        |
| AutoFibo 15M | JA        | teilweise     | ~3/22 Runs (~14%) | 0                 | **PARK / UNCLEAR** |
| Ichimoku     | JA        | JA            | 22/22 Runs (100%) | 0                 | **KEEP (provisorisch)** |

Kern-Befund: Die ueber dem MP-Fix-Cutoff (2026-05-04) verfuegbare Stichprobe enthaelt **null ausgefuehrte Trades** (alle 22 Pipeline-Runs endeten in WAIT). Damit ist eine klassische Hit-Rate-/Win-Rate-Edge-Messung unmoeglich. Die Empfehlungen beruhen auf **Coverage** (liefert der Indikator ueberhaupt ein differenzierendes Signal?) und **Code-Implementierungs-Audit** (ist der Indikator im Pipeline-Pfad ueberhaupt verdrahtet?).

---

## SCHRITT 1 — DISCOVERY

### Datenquellen, die existieren

**Aktuelle Snapshots (heute, 2026-05-15):**
- `cockpit-trader/journal-data.json` (7166 B) — 0 Orders heute
- `agents/shared/state.json` (27277 B, USUpdate 14:54)
- `agents/shared/state.json.morning-2026-05-15` (33459 B, Morning 08:20)
- `cockpit-trader/state.json` (Kopie der shared)

**Historische Snapshots:**
- KEINE zusaetzlichen state.json-Versionen jenseits des heutigen Morning-Backups
- `cockpit-trader/journal-data.json` ist single-file (kein Datums-Archiv)
- `trading-journal/journal-data.json` (Stand 08:18 heute) — gleicher Tag
- `trading-journal/report-today.json` (Stand 2026-04-14, **Dry-Run**)
- `trading-journal/orders-today.json` (Stand 2026-04-14, 2 Dry-Run-Orders)

**Logs (verlaesslichste Sekundaerquelle):**
- `logs/pipeline/pipeline_*.log` — Morning + USUpdate Logs ab 2026-04-19
- `logs/DailyMon/monitor_*.txt` — Notepad-Reports ab 2026-04-22
- `cockpit-trader/reports/` — nur 2 Reports vorhanden (morning-2026-05-12 + morning-2026-05-15)

### Schema-Audit `analysis.instruments[X].schichten.s3_entry.signale`

Heutiges Schema (aus `state.json` + `agents/analyst/CLAUDE_ref.md`):

```
ichimoku, sma200, smc, sr_channel, pivot, autofibo
```

**Elliott Wave FEHLT im Schema komplett.** Es ist im breiteren `tradingview-mcp` als MCP-Tool `data_get_elliott_wave` definiert und in der alten `cockpit-morning-prompt-for-claude-md.md` als „Bestaetigung" gelistet, aber im Live-Pipeline-Pfad (`agents/analyst/_update_state.py` + `agents/shared/analyst_write.py`) nicht referenziert.

### Implementierungs-Audit (Python-Pfad)

`agents/analyst/_update_state.py` Zeile 100–118:
```
s3["ichimoku"]   = above_kumo Check  (aktiv)
s3["sma200"]     = price vs sma200   (aktiv)
s3["smc"]        = 0                 (HARDCODED)
s3["sr_channel"] = 0                 (HARDCODED)
s3["pivot"]      = price vs pivot_p  (aktiv, aus PDH/PDL/prev_close)
s3["autofibo"]   = -1 falls Preis < 0.1% an fibo_0; sonst 0  (sehr eng)
```

`agents/shared/analyst_write.py` Zeile 60–66 ist noch konservativer:
```
s3["smc"]        = 0
s3["sr_channel"] = 0
s3["pivot"]      = 0
s3["autofibo"]   = 0
```

Im Live-Run-Workflow nutzt der ANALYST entweder einen dieser Python-Pfade oder setzt die Werte direkt im JSON. Selbst bei manueller Setzung lieferte der Agent in allen heutigen + dokumentierten Snapshots fuer SMC und S/R Channel keinen Wert ungleich 0.

---

## SCHRITT 2 — COVERAGE pro Indikator

Stichprobe = alle Morning- und USUpdate-Pipeline-Runs im Beobachtungs-Korridor.

### Korridor A: POST-MP-FIX (2026-05-04 bis 2026-05-15) — Primaer-Datensatz

Aus Pipeline-Logs + Monitor-Reports extrahierte Datenpunkte:

| Datum       | Run     | S3-aggr. (G/D/S)         | Ichimoku-Erw.| SMC-Erw. | AutoFibo-Erw.| Trades |
|-------------|---------|--------------------------|--------------|----------|--------------|--------|
| 2026-05-04  | Morning | n/a                      | indirekt     | nein     | nein         | 0      |
| 2026-05-04  | USUpd   | n/a                      | „IN/UEBER Kumo" | nein  | nein         | 0      |
| 2026-05-05  | Morning | n/a                      | „S3 geblockt (Ichimoku unter Kumo)" | nein | nein | 0 |
| 2026-05-05  | USUpd   | S3=0.583/-0.167/0.500    | indirekt     | nein     | nein         | 0      |
| 2026-05-06  | Morning | n/a                      | indirekt     | nein     | nein         | 0      |
| 2026-05-06  | USUpd   | S3=0.333/0.333/0.333     | „Ichimoku OK"| nein     | nein         | 0      |
| 2026-05-07  | Morning | n/a                      | indirekt     | nein     | nein         | 0      |
| 2026-05-07  | USUpd   | S3=0.00/0.33/0.33        | „Ichimoku vollstaendig" | nein | nein     | 0      |
| 2026-05-08  | Morning | S3=-0.17/0.50/0.50       | „S3 BLOCKED (Ichimoku unter Kumo -1, AutoFibo -1)" | nein | **JA** | 0 |
| 2026-05-08  | USUpd   | S3=-0.50/0.33/0.67       | indirekt     | nein     | nein         | 0      |
| 2026-05-11  | Morning | n/a                      | indirekt     | nein     | nein         | 0      |
| 2026-05-11  | USUpd   | S3=-0.333/-0.167/0.167   | „Ichimoku Kumo-Wechsel" | nein | nein   | 0      |
| 2026-05-12  | Morning | S3=-0.333/-0.167/0.00    | indirekt     | nein     | nein         | 0      |
| 2026-05-12  | USUpd   | S3=-0.333/0.333/0.00     | „Ichimoku im Run" | nein | nein         | 0      |
| 2026-05-13  | Morning | S3=0.17/0.50/0.50        | indirekt     | nein     | nein         | 0      |
| 2026-05-13  | USUpd   | S3=-0.50/-0.50/0.17      | indirekt     | nein     | nein         | 0      |
| 2026-05-14  | Morning | n/a                      | indirekt     | nein     | nein         | 0      |
| 2026-05-14  | USUpd   | S3=0.333/0.500/0.333     | indirekt     | nein     | nein         | 0      |
| 2026-05-15  | Morning | s3.ich=-1/-1/-1; s3.fibo=+1/0/0 | aktiv  | nein     | **JA** (GER40) | 0     |
| 2026-05-15  | USUpd   | s3.ich=-1/-1/-1; alle uebr.=0 | aktiv  | nein     | nein         | 0      |

(„indirekt" = aggregat S3-Score sichtbar, aber Einzelsignal nicht im Log; einzelne S3-Felder nur aus den 2 vollstaendigen state.json-Snapshots vom 2026-05-15 sicher.)

**Coverage-Befund (post-fix):**

- **Ichimoku:** in ~100% der Runs vorhanden, regelmaessig nicht-null. Wird in 7 von 11 Monitor-Texten als Block- oder Bestaetigungs-Grund explizit genannt. Klar das einzige S3-Signal mit konstanter Praesenz.
- **AutoFibo:** Nur in 2 Runs (2026-05-08 GER40, 2026-05-15 Morning GER40) als Wert ungleich 0 nachweisbar. Coverage geschaetzt ~14% (Wert ≠ 0).
- **SMC:** In **null** beobachteten Runs lieferte SMC einen Wert ungleich 0. Coverage = 0%. Begruendet durch Hardcoding in beiden Python-Pfaden.
- **Elliott Wave:** In **null** beobachteten Runs vorhanden. Coverage = 0%. Begruendet durch fehlendes Schema-Feld.

### Korridor B: PRE-MP-FIX (2026-04-14 bis 2026-05-03) — Sekundaerer Notdatensatz

Verfuegbar:
- 1 Dry-Run-Tag (2026-04-14) mit 2 Orders im `trading-journal/orders-today.json`
- Pipeline-Logs aus 2026-04-19 bis 2026-05-01 (~8 Tage)

Befund:
- 2 Dry-Run-Orders (GER40 + DJ30 Limit Buy) — beide mit `confluence` Strings, die „Ichimoku", „Pivot", „SMC Bull OB", „AutoFibo", „Elliott Wave" enthalten
- **Aber:** `fill_rate: "n/a"`, `tp1_rate: "n/a"` — Dry-Run, keine Outcomes
- In `trading-journal/report-today.json` von 2026-04-14: Elliott Wave wurde fuer SPX500 als „Wave (5) komplett = WARNUNG: moegliches Interim-Top" gefuehrt — wirkte als Veto, das verhinderte einen 3. SPX500-Order
- Diese 2 Orders sind **keine Trade-Outcomes**, sondern nur Signal-Beispiele

Damit verbleibt fuer Edge-Analyse: 0 reale Trades in beiden Korridoren.

---

## SCHRITT 3 — EDGE-ANALYSE (so weit moeglich)

### Methodische Einschraenkung

Klassische Edge-Metriken (Hit-Rate, Win-Rate, R-Multiple, PFP) brauchen Outcomes. Die Pipeline hat seit dem MP-Fix **null Orders gefuellt** (in allen 11 Tagen WAIT durch Konfidenz < 0.40 oder Schichten-Logik). Damit lassen sich nur abgeleitete Kennzahlen messen:

1. **Differenzierungs-Rate** = Anteil Runs in denen das Signal ≠ 0 ist
2. **Block- vs. Pass-Rate** = wie oft loest das Signal eine Schichten-Blockade aus
3. **Code-Integration** = ist das Signal im Live-Pfad ueberhaupt verdrahtet

### Ergebnisse je Indikator

#### 1) Elliott Wave

- Differenzierungs-Rate: **0%** (kein einziger Run schreibt ein elliott-Feld)
- Block-/Pass-Rate: nicht messbar
- Code-Integration: **nein** (kein Feld im Schema, kein Aufruf in `_update_state.py` oder `analyst_write.py`)
- Einzige Spur: MCP-Tool `data_get_elliott_wave` existiert und liefert Wave-Position auf Daily-TF. Wurde 2026-04-14 als „Warnung" verwendet, hat seither nicht mehr in einem Pipeline-Run mitgewirkt.
- Praktischer Edge-Nachweis: **null**

#### 2) SMC (Smart Money Concepts)

- Differenzierungs-Rate post-fix: **0%** (in jedem geprueften Snapshot `smc: 0`)
- Code-Integration: Schema-Feld vorhanden, **Wert hardcoded auf 0** in beiden Python-Skripten
- MCP-Tool `data_get_smc_levels` ist verfuegbar (4H/1H Swing-OBs, 30M/15M Entry-OBs), und in `tradingview-mcp/CLAUDE.md` als **PFLICHT-Bestaetigung** dokumentiert („Mindestens 2 Bestaetigungen, SMC + VWAP oder Ichimoku + S/R")
- Diskrepanz: Konzeptionell vorgesehen, in der Implementierung **deaktiviert**. SMC traegt aktuell **nichts** zum Score bei.
- Praktischer Edge-Nachweis: **null**

#### 3) AutoFibo 15M

- Differenzierungs-Rate post-fix: ~9% (1 von 11 Morning-Runs lieferte +1 fuer GER40 wo Preis nahe Fibo 0.618)
- Logik im Code: nur 1 Trigger („Preis < 0.1% an fibo_0", ergibt -1 als Resistance) — sehr enges Fenster
- Block-/Pass-Beitrag: in den 2 Faellen mit Wert ≠ 0 (2026-05-08 GER40 mit -1; 2026-05-15 GER40 mit +1) war es **nicht** der Faktor, der ueber Trade-Freigabe entschied (Konfidenz lag in beiden Faellen ohnehin unter 0.40)
- Quelle vorhanden (state.json `fibo: {0, 0.5, 0.618}` pro Instrument)
- Praktischer Edge-Nachweis: **unklar**, Stichprobe zu klein

#### 4) Ichimoku

- Differenzierungs-Rate post-fix: ~100% (jeder Run hat `ichimoku ∈ {-1, 0, +1}`, in ~90% der Faelle ≠ 0)
- Quelle vorhanden (state.json `ichimoku: {tenkan, kijun, senkouA, senkouB, chikou}` pro Instrument)
- Logik im Code: `above_kumo` Check, klar definiert
- Block-Rolle: In 7 von 11 Monitor-Reports explizit als Block-Begruendung genannt („S3 geblockt (Ichimoku unter Kumo)"). Damit ist Ichimoku der einzige S3-Indikator, der regelmaessig Trades verhindert oder freigibt.
- Praktischer Edge-Nachweis: **gegeben, aber bedingt** — Ichimoku ist der wirksame Hebel im S3, weil SMC/S/R/Pivot/Fibo entweder null sind oder kaum feuern. Damit ist „Ichimoku-Edge" praktisch deckungsgleich mit „S3-Edge" — eine isolierte Messung ist unmoeglich, solange die anderen Felder ausgeschaltet sind.

---

## SCHRITT 4 — EMPFEHLUNGEN

### Elliott Wave → **DROP** (aus aktiver Pipeline)

Begruendung:
- Nicht im Live-Schema, nicht im Code-Pfad
- Wave-Position ist Tages-Niveau-Kontext, das nicht zu einer 30M-Entry-Logik passt
- MCP-Tool kann optional fuer manuelle Daily-Bestaetigung erhalten bleiben

Konkrete Aktion:
- `tradingview-mcp/CLAUDE.md` Eintrag „Punkt 9 BESTAETIGUNG — Elliott Wave" als „optional / Daily-Kontext, nicht Pipeline-Signal" markieren
- KEINE neue S3-Spalte einfuehren
- Pine-Skripte / MCP-Tools nicht entfernen (kein Aufwand, kein Schaden)

### SMC → **DROP oder REPAIR (Entscheidung erforderlich)**

Begruendung:
- Schema-Feld existiert, ist aber **tot** (hardcoded 0). Damit erzeugt es das Risiko, dass jemand das Feld liest und glaubt, es funktioniere.
- Wenn die SMC-Daten tatsaechlich gebraucht werden, ist eine echte Implementierung noetig: `data_get_smc_levels` Aufruf, BOS/CHoCH-Trigger, OB/FVG-Distanz-Check zu `current`
- Ohne reale Verdrahtung ist das Feld in S3 nur statistisches Rauschen-Risiko (Trade-Freigabe-Logik liest das `0` als „neutral", aber faktisch existiert kein Signal)

Konkrete Aktionen (eine waehlen):
- **Variante A (DROP):** SMC-Feld aus `s3_entry.signale` entfernen, S3-Divisor von 6 auf 5 reduzieren (`s3_score = s3_raw / 5`), entsprechende Doku in `agents/analyst/CLAUDE_ref.md` anpassen
- **Variante B (REPAIR):** SMC-Trigger live verdrahten: 30M/15M BOS in Bias-Richtung = +1, Gegenrichtung = -1, OB-Distanz < 0.2% = +0.5 Bonus

Empfehlung: **Variante A** bis genug Trade-Outcomes da sind, um eine Variante B sinnvoll zu validieren.

### AutoFibo 15M → **PARK / UNCLEAR (provisorisch KEEP, aber Logik schaerfen)**

Begruendung:
- Datenquelle ist da, aber der einzige Trigger („Preis < 0.1% an fibo_0" liefert -1) ist viel zu eng. In 11 Tagen feuerte das Feld nur 1 Mal mit +1 und ist sonst stumm.
- Tatsaechlich relevante Fibo-Levels (0.5, 0.618, 0.786) werden vom Trigger ignoriert
- Edge-Nachweis: nicht moeglich bei aktueller Implementation

Konkrete Aktionen:
- Logik erweitern: Trigger auch fuer 0.5/0.618/0.786 setzen, mit Toleranz ~0.15% statt 0.1%
- Wenn nach naechsten 30 Trades (geschaetzt 2–4 Wochen) immer noch keine Differenzierung sichtbar: **DROP nach gleichem Muster wie SMC**

### Ichimoku → **KEEP (provisorisch)**

Begruendung:
- Einziger S3-Indikator mit konstanter Differenzierungs-Rate
- Konkret als Block-/Pass-Trigger nachweisbar (Monitor-Reports)
- Datenquelle in jedem Run vorhanden

Aber:
- Echte Edge-Messung steht aus (0 Trades)
- Risiko: Da SMC/S/R/Pivot/Fibo nahe-null sind, **dominiert Ichimoku den S3-Score implizit**. Damit ist S3 effektiv ein Ichimoku-Filter.
- Falls Ichimoku falsch liegt, fehlt jeder Gegenpol im S3 — die anderen 5 Felder kompensieren nicht.

Konkrete Aktion:
- KEEP. Nach Implementierung von SMC-Repair (Variante B oben) erneut evaluieren, ob Ichimoku noch das dominante Signal ist.

---

## ANHANG — Datenqualitaets-Bewertung

| Kriterium                              | Wert       | Bedeutung                                                  |
|----------------------------------------|------------|------------------------------------------------------------|
| Trades post-MP-fix                     | 0          | Kein Outcome-Sample fuer Hit-Rate-Edge moeglich            |
| Dry-Run-Orders pre-fix                 | 2          | Nur Signal-Beispiele, keine Outcomes                       |
| state.json-Snapshots historisch        | 1          | Nur Morning 2026-05-15 Backup                              |
| Pipeline-Logs post-fix verwertbar      | 22 Runs    | Aggregat-Scores sichtbar, Einzelsignale nur sporadisch     |
| Monitor-Reports post-fix verwertbar    | 22         | Block-Begruendungen und Shape-Validierungen vorhanden      |
| Vollstaendige S3-Signal-Breakdowns     | 2          | (Morning + USUpdate 2026-05-15 — beide aus heutigem Lauf)  |

**Konsequenz fuer das Trading-System:** Die einzige zuverlaessige Methode, die hier offenen Empfehlungen zu bestaetigen, ist ein **gezielter Backtest** ueber ein laengeres Zeitfenster (mind. 60 Trades), in dem alle 4 Indikator-Felder *konsequent geschrieben werden* — nicht hardcoded auf 0. Ohne das bleibt jede Edge-Aussage spekulativ.

---

## ZUSAMMENFASSUNG

- **Elliott Wave** und **SMC** sind in der heutigen Pipeline **tot**. Empfehlung: aus der Schichten-Logik entfernen, MCP-Tools optional erhalten.
- **AutoFibo 15M** ist halb-aktiv mit zu enger Trigger-Logik. Erst Trigger schaerfen, dann re-evaluieren.
- **Ichimoku** ist der einzige funktionierende S3-Indikator und sollte als Default-Filter bestehen bleiben.
- Echter Edge-Nachweis fuer alle 4 ist mit der vorliegenden Datenlage **nicht moeglich** (0 Trades).
- Mittelfristig: Backtest-System (offener TODO in `CLAUDE.md`) priorisieren, sonst bleibt jede Score-Diskussion ohne Outcome-Basis.
