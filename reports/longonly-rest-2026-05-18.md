# LONG-only Restbestaende Fix - 2026-05-18

Spawn 3 von 3. Symmetrisierung der drei in Spawn 2 dokumentierten Restbestaende
(siehe longonly-fix-2026-05-18.md Abschnitt "Asymmetrische Stellen ausserhalb
des Fix-Scopes"). Konfidenz-Logik bleibt: max(konfidenz_long, konfidenz_short).

---

## Phase A: Discovery

Grep ueber das gesamte Repo nach Aufrufen / Importen der 3 Stellen:

### A.1 agents/shared/analyst_write.py
- Existiert: JA
- Grep-Pattern: `analyst_write`
- Aufrufe gefunden: KEINE (ausserhalb von Reports unter cockpit-trader/reports/).
  Keine `import`, kein `python -c`, kein Aufruf aus .bat / .ps1 / .js / .py.
- Inhalt: Eigenes komplettes ANALYST-Script mit hartkodierten Werten fuer
  Snapshot 2026-05-18 (Preise 24126/49671/7397, Phase-Begruendung als String-
  Konstante). Erfindet die Analyse fuer einen einzelnen Tag, nicht die
  Pipeline-Logik.
- Aktive Pipeline laeuft ueber `agents/analyst/_update_state.py` (in Spawn 2
  bereits symmetrisiert).
- **Status: TOT / SNAPSHOT-LEGACY. Kein Patch.**

### A.2 agents/shared/captain_write.py
- Existiert: JA
- Grep-Pattern: `captain_write`
- Aufrufe gefunden: KEINE (ausserhalb von Reports).
- Inhalt: Eigenes komplettes CAPTAIN-Script mit hartkodiertem Trade-Plan-Text
  fuer Snapshot 2026-05-18 (POC/VAH/VAL/VWAP/PDH/PDL eingefroren). Die
  Konfidenz/Schwellen-Logik ist bereits abs()-basiert (Zeilen 91, 98), die
  Session-Bias-Mapping-Branches (Zeilen 106-115) sind LONG/SHORT-symmetrisch.
- Aktive Pipeline laeuft ueber `agents/captain/_update_state.py` (in Spawn 2
  bereits direction-aware konfidenz_long / konfidenz_short ergaenzt).
- **Status: TOT / SNAPSHOT-LEGACY. Kein Patch.**

### A.3 agents/executor/CLAUDE.md + CLAUDE_ref.md
- Existiert: BEIDE JA
- Grep-Pattern: `alignment_score < 4`, `alignment_score >= 4`
- Aktive Spec-Doku (wird von Claude als Agent-Instruction beim EXECUTOR-Lauf
  geladen).
- Treffer:
  - `CLAUDE.md:9` -- `R:R < 1.5 oder alignment_score < 4 -> Order ablehnen`
  - `CLAUDE_ref.md:8` -- `alignment_score >= 4`
- Code-Datei `agents/executor/_update_state.py` enthaelt KEINE
  alignment-Schwellen-Logik (liest nur `captain.trade_freigabe`, vertraut
  CAPTAIN). `_export.py` und `_usupdate_export.py` haben ebenfalls keine
  Schwellenchecks gegen alignment_score, sie nutzen den Wert nur als Anzeige.
- **Status: AKTIVE SPEC. Patch noetig (nur Markdown).**

### A.4 Entscheidungs-Matrix

| Stelle                              | Status         | Patch noetig |
|-------------------------------------|----------------|--------------|
| shared/analyst_write.py             | TOT / SNAPSHOT | NEIN         |
| shared/captain_write.py             | TOT / SNAPSHOT | NEIN         |
| executor/CLAUDE.md + CLAUDE_ref.md  | AKTIV / SPEC   | JA           |

Nicht alle 3 tot -> Phase B/C/D fuer Stelle 3 ausgefuehrt.

---

## Phase B: Backups

Backup-Verzeichnis: `C:\Users\chris\TradingFloor\backups\longonly-rest-20260518-174220\`

Angelegte Backups (nur fuer gepatchte Dateien):
- `executor-CLAUDE.md.backup-longonly-rest`
- `executor-CLAUDE_ref.md.backup-longonly-rest`

Tote Dateien (analyst_write.py, captain_write.py) wurden NICHT gesichert,
da NICHT veraendert.

---

## Phase C: Patches

### C.3a agents/executor/CLAUDE.md (Zeile 9)

Vorher:
```
- R:R < 1.5 oder alignment_score < 4 -> Order ablehnen
```

Nachher:
```
- R:R < 1.5 oder abs(alignment_score) < 4 -> Order ablehnen (LONG+SHORT symmetrisch)
```

Diff: 1 Zeile veraendert. Logik unchanged, nur Symmetrie explizit gemacht.
Ein Setup mit alignment_score = -6 (klares Bear-Setup) erfuellt nun
NICHT mehr `< 4` und wird durchgelassen (sofern R:R >= 1.5).

### C.3b agents/executor/CLAUDE_ref.md (Zeile 8)

Vorher:
```
## Order-Anforderungen (Minimum)
- MP (POC/VAH/VAL) vorhanden
- VP (Volume Profile) vorhanden
- Mindestens 2 weitere: VWAP, ER, Inter-Market, Momentum, CVD
- R:R >= 1.5:1
- alignment_score >= 4
```

Nachher:
```
## Order-Anforderungen (Minimum)
- MP (POC/VAH/VAL) vorhanden
- VP (Volume Profile) vorhanden
- Mindestens 2 weitere: VWAP, ER, Inter-Market, Momentum, CVD
- R:R >= 1.5:1
- abs(alignment_score) >= 4 (LONG: >= 4, SHORT: <= -4 — symmetrisch)
```

Diff: 1 Zeile veraendert.

### Markdown-Lesbarkeit

Beide Dateien syntaktisch unveraendert (kein Frontmatter, keine Tabellen
geaendert, keine Liste-Hierarchie geaendert). Markdown bleibt parseable.
SL-/TP-Hierarchien sind in CLAUDE_ref.md bereits getrennt fuer LONG und
SHORT dokumentiert (Zeilen 14-23) — diese Symmetrie war schon vorhanden.

---

## Phase D: Verifikation

### Syntax-Checks

Keine Python-Dateien gepatched -> kein py_compile noetig.
Markdown braucht keinen Syntax-Check.

### Grep-Verifikation

```
grep "alignment_score < 4" agents/executor/
  -> nur in CLAUDE.md.backup (alte Sicherung, irrelevant)
grep "alignment_score >= 4" agents/executor/
  -> nur in CLAUDE.md.backup
grep "abs(alignment_score)" agents/executor/
  -> CLAUDE.md:9 + CLAUDE_ref.md:8 (neu, korrekt)
```

Keine asymmetrischen Schwellen mehr in aktiven Executor-Specs.

---

## Was uebrig bleibt

### Tote Dateien (dokumentiert, NICHT geloescht)

- `agents/shared/analyst_write.py` -- Snapshot-Script vom 2026-05-18,
  keine Aufrufe im Repo. Falls jemals reaktiviert: Symmetrie analog
  Spawn 2 nachziehen (alle_long_ok / alle_short_ok / bias_direction).
- `agents/shared/captain_write.py` -- ebenfalls Snapshot-Script,
  keine Aufrufe. Konfidenz bereits abs()-basiert, Bias-Mapping bereits
  LONG/SHORT-symmetrisch (Zeilen 106-115), aber `konfidenz` ist noch
  signed (Vorzeichen kommt aus alignment_score/8 * chart_w + makro/12 * makro_w).
  Falls reaktiviert: zusaetzlich konfidenz_long / konfidenz_short / max()
  Pattern aus `agents/captain/_update_state.py` nachziehen.

### Weitere LONG-zentrische Patterns (informativ, ausserhalb Scope)

Beim Grep gefunden, aber nicht gepatched, weil ausserhalb der 3 in der
Aufgabe enumerierten Stellen:

1. `agents/executor/_export.py:41` -- `invalidation` String pro Instrument
   hardcoded: `"Schluss unter VAL ... negiert bullische Setup-Lage."`
   Fuer ein SHORT-Setup (Bias=BEARISH) ist diese Begruendung sachlich
   falsch. Empfehlung: aus `analysis.instruments[X].bias` ableiten
   (bullisch fuer LONG, baerisch fuer SHORT). Score-Schwelle nicht
   betroffen, nur Doku-String im journal-data.json.

2. `agents/executor/_export.py:27` -- `bias_pct = int(round((alignment_score / 8.0) * 100))`
   Bei alignment_score = -6 wird das -75. Falls Dashboard das als
   Fortschrittsbalken rendert: Anzeige bricht. Vorschlag: `abs(score)/8*100`
   plus separates `bias_direction`-Feld.

3. `agents/executor/_usupdate_export.py` -- enthaelt hartkodierte
   Begruendungstexte und `bias_pct`-Formel `(50 + bias_score * 8)` die
   bei Score=-6 auf 2% kollabiert. Snapshot-spezifisch; vor naechstem
   USUpdate-Lauf saubermachen.

Empfehlung: Separater Folgepatch fuer `_export.py` / `_usupdate_export.py`
falls Dashboard-Anzeige unter SHORT-Bias falsch rendert. Nicht Teil
dieses Auftrags (Aufgabe enumeriert nur die 3 Stellen oben).

---

## Rollback-Anleitung

Falls EXECUTOR-Lauf nach dem Patch unerwartet Orders ablehnt oder
zulaesst (was bei reinem Markdown-Patch unwahrscheinlich ist):

```powershell
$src = "C:\Users\chris\TradingFloor\backups\longonly-rest-20260518-174220"
Copy-Item "$src\executor-CLAUDE.md.backup-longonly-rest"     "C:\Users\chris\TradingFloor\agents\executor\CLAUDE.md" -Force
Copy-Item "$src\executor-CLAUDE_ref.md.backup-longonly-rest" "C:\Users\chris\TradingFloor\agents\executor\CLAUDE_ref.md" -Force
```

---

## Zusammenfassung

- 2 von 3 Restbestaenden waren tote Snapshot-Files (kein Patch).
- 1 von 3 (Executor-Specs) gepatched: 2 Zeilen, beide Mal `< 4`/`>= 4`
  -> `abs(...) < 4`/`abs(...) >= 4`.
- 2 Backups erstellt.
- Keine Code-Dateien betroffen, keine Syntax-Checks noetig.
- 3 weitere LONG-zentrische Patterns in `_export.py` / `_usupdate_export.py`
  gefunden und dokumentiert (Doku/Anzeige-Strings, nicht Logik).
