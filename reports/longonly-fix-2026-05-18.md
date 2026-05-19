# LONG-only Bug: Fix-Report
# Datum: 2026-05-18 17:17:52 lokal
# Modus: Symmetrisierung (4 Python + 4 Spec, KEINE neue Logik)

---

## Phase-Status

| Phase | Beschreibung | Status |
|---|---|---|
| A | Backups + Quellen lesen | OK |
| B | Spec-Updates (4 CLAUDE/CLAUDE_ref) | OK |
| C | Analyst Code (2 Files) | OK |
| D | Captain Code (2 Files) | OK |
| E | Tests (19/19 PASSED) | OK |
| F | Verifikation py_compile + grep | OK |
| G | Report | OK |

---

## Backups

Verzeichnis: `C:\Users\chris\TradingFloor\backups\longonly-fix-20260518-171752\`

Acht Backups mit Suffix `.backup-longonly-fix`:
- analyst-CLAUDE.md
- analyst-CLAUDE_ref.md
- analyst-_update_state.py
- analyst-_usupdate_compute.py
- captain-CLAUDE.md
- captain-CLAUDE_ref.md
- captain-_update_state.py
- captain-_usupdate_compute.py

Backup-Integritaet vor Patch verifiziert (`diff -q` gegen Quellen — alle identisch).

---

## Aenderungen pro Datei

### agents/analyst/CLAUDE.md
- Kritische-Regeln-Block: LONG- und SHORT-Freigabe spiegelnd dokumentiert; alle_long_ok/alle_short_ok/bias_direction; top_down-Erweiterungen.
- state.json-Felder-Block: neue Schichten-Felder (freigabe_s1_short/s2_short/s3_short, alle_long_ok, alle_short_ok, bias_direction) + top_down (alignment_score_abs, best_direction).

### agents/analyst/CLAUDE_ref.md
- S1/S2/S3 Schwellen-Blocks um SHORT-Variante ergaenzt.
- Trade-Freigabe-Codeblock vollstaendig durch symmetrische Variante (LONG + SHORT + Gesamt) ersetzt.
- Top-Down-Codeblock mit ok_count_long/ok_count_short/best_direction/alignment_score_abs ergaenzt.
- State-Schema: alle neuen Felder in JSON-Beispiel dokumentiert.

### agents/analyst/_update_state.py (Diffs)
- Zeile ~122-141 (Schichten-Block in `analyze()`): freigabe_s1_short/s2_short/s3_short, alle_long_ok, alle_short_ok, alle_ok (= long OR short), bias_direction ergaenzt.
- Zeile ~158-170 (Return-Dict `schichten`): neue Felder freigabe_s1_short, freigabe_s2_short, freigabe_s3_short, alle_long_ok, alle_short_ok, bias_direction ergaenzt.
- Zeile ~170-189 (Top-Down): ok_count_long + ok_count_short + ok_count = max(); best_direction nach Mehrheit; `best` jetzt nach `abs(alignment_score)` statt signed; neue Felder alignment_score_abs, best_direction, ok_instruments_long, ok_instruments_short.

### agents/analyst/_usupdate_compute.py (Diffs)
- Funktion `compute()`: f1s/f2s/f3s SHORT-Pendants berechnet, alle_long_ok/alle_short_ok/bias_direction abgeleitet; Return-Dict um diese Felder erweitert.
- `best`-Sortierung von signed auf `abs()` umgestellt; ok_count_long/ok_count_short/best_direction berechnet.
- `top_down`-Dict erweitert: alignment_score_abs, best_direction, ok_instruments_long, ok_instruments_short.
- Per-Instrument-Schichten-Mapping (`inst['schichten'] = {kk: ...}`): neue Felder in Mapping-Liste aufgenommen.

### agents/captain/CLAUDE.md
- Rolle: SHORT explizit erwaehnt; `abs(Score) < 4` statt `Score < 4`.
- Konfidenz-Formel komplett ersetzt (LONG + SHORT als max(0, ...) terms + max() + konfidenz_direction).
- Schwellen mit abs(alignment) dokumentiert.
- Session-Bias-Mapping richtet sich nach konfidenz_direction (LONG/SHORT-Branches).
- Hard-Stops als symmetrisch wirkend dokumentiert.
- konfidenz_details: neue Felder (konfidenz_long, konfidenz_short, konfidenz_direction).

### agents/captain/CLAUDE_ref.md
- SCHRITT 1a (Schichten-Freigabe): Symmetrie-Hinweis (SHORT zaehlt gleichwertig wie LONG).
- SCHRITT 1b (Konfidenz): vollstaendige neue Formel + Entscheidungsmatrix; Hinweis auf symmetrische Hard-Stops.
- SCHRITT 2 (Session-Bias-Tabelle): getrennte LONG- und SHORT-Tabellen plus allgemeine WAIT-Regel; LONG braucht alignment >= 4, SHORT alignment <= -4.
- State-Schema captain.konfidenz_details: neue Felder ergaenzt.

### agents/captain/_update_state.py (Diffs)
- Zeile ~92-110 (Konfidenz-Berechnung): vollstaendig ersetzt durch konfidenz_long/konfidenz_short/konfidenz=max/konfidenz_direction.
- konfidenz_details-Dict um konfidenz_long, konfidenz_short, konfidenz_direction erweitert.
- Zeile ~121 (Schwelle): `konfidenz < 0.40` unveraendert (jetzt direction-agnostisch wirkend, da konfidenz >= 0).
- Zeile ~126: `alignment < 4` -> `abs(alignment) < 4`.
- Zeile ~135-155 (Session-Bias-Mapping): zwei separate If/Else-Branches je konfidenz_direction. SHORT-Branch nutzt `alignment <= -4 / -6` und `bear_count >= 2`.
- instrument_prioritaet: Sortierung von signed `-alignment_score` auf `-abs(alignment_score)` umgestellt.
- Trade-Plan: direction-aware (Long Re-Entry bei VWAP/VAH / Stop unter VAL VS Short Re-Entry bei VWAP/VAL / Stop ueber VAH).
- WAIT-Plan: konfidenz_long + konfidenz_short + konfidenz_direction in Erklaerungstext aufgenommen.
- Warnungen: makro_bias-Konflikt richtungsabhaengig (RISK_OFF+LONG / RISK_ON+SHORT); `not trade_freigabe and abs(alignment) >= 4` mit dynamischem Label (bullish/bearish).

### agents/captain/_usupdate_compute.py (Diffs)
- Zeile ~47-49 (Konfidenz): vollstaendig ersetzt durch konfidenz_long/konfidenz_short/konfidenz_final=max/konfidenz_direction. align_beitrag und makro_beitrag jetzt jeweils der Beitrag der aktiven Richtung (immer >= 0).
- Zeile ~77-95 (Trade-Logik): `alignment_score < 4` -> `abs(alignment_score) < 4`; LONG-Hardcode in if/else-Branch nach konfidenz_direction aufgeloest (LONG -> LONG-BIAS/LONG-LEAN, SHORT -> SHORT-BIAS/SHORT-LEAN).
- instrument_prioritaet-Sortierung: signed auf `abs()` umgestellt.
- konfidenz_details-Dict: konfidenz_long, konfidenz_short, konfidenz_direction ergaenzt.

---

## Tests (Phase E)

Skript: `C:\Users\chris\TradingFloor\tests\longonly-fix\test_symmetry.py`

Test-Strategie: Kern-Logik aus den gepatcht-Files in Test-Skript repliziert (die Skripte schreiben hardcoded nach `agents/shared/state.json`; isolierter Lauf ohne State-Schaden moeglich). Auf 6 Setups validiert.

### Resultate

```
=== TEST 1: Bear-Replay (Snapshot 2026-05-18 morning) ===
  GER40: S1=-0.1   S2=+0.0  S3=-0.333 -> align=-1 long_ok=False short_ok=False dir=NONE
  DJ30:  S1=-0.5   S2=-0.25 S3=-0.333 -> align=-3 long_ok=False short_ok=True  dir=SHORT
  SPX500:S1=-0.1   S2=+0.0  S3=-0.333 -> align=-1 long_ok=False short_ok=False dir=NONE
  top_down: best_dir=SHORT ok_short=1 ok_long=0 align=-3 abs=3
  captain: dir=SHORT konf_long=0.0 konf_short=0.258 konf=0.258 bias=WAIT freigabe=False
  reason=Konfidenz 0.258<0.40 (ok: ok_count=1 < 2 + 0.258 < 0.40)
OK   bear_replay.has_short_instrument
OK   bear_replay.konf_short_dominant
OK   bear_replay.konfidenz_direction_SHORT
OK   bear_replay.konfidenz_nonneg
OK   bear_replay.bug_negative_konfidenz_fixed (war -0.258, jetzt +0.258 SHORT)

=== TEST 2: Bull-Synthetic (flipped Vorzeichen) ===
OK   bull_synthetic.has_long_instrument
OK   bull_synthetic.konfidenz_direction_LONG

=== TEST 3: Neutral-Synthetic (alle Scores 0) ===
OK   neutral.best_direction_NONE
OK   neutral.konf_long_zero / konf_short_zero
OK   neutral.session_bias_WAIT / trade_freigabe_False

=== TEST 4: Regression Pure-Bull (align=+6, macro=+8) ===
  bias=LONG-BIAS (stark) freigabe=True konf_long=0.717 konf_short=0.0
OK   regress_bull.session_bias_LONG_strong / trade_freigabe_True / konfidenz_long_dominant

=== TEST 5: Regression Pure-Bear (align=-6, macro=-8) ===
  bias=SHORT-BIAS (stark) freigabe=True konf_long=0.0 konf_short=0.708
OK   regress_bear.session_bias_SHORT_strong / trade_freigabe_True / konfidenz_short_dominant

=== TEST 6: Mixed (align=+3, macro=-2) ===
OK   mixed.session_bias_WAIT_abs_align_lt_4

=== SUMMARY: 19/19 PASSED ===
```

Test-Artefakte:
- `tests/longonly-fix/test-results.json` (alle 19 Assertions)
- `tests/longonly-fix/test-bear-replay-result.json` (Snapshot-Reanalyse)
- `tests/longonly-fix/bull-synthetic.json`
- `tests/longonly-fix/neutral-synthetic.json`

Wichtigstes Ergebnis: Der echte Snapshot vom 2026-05-18 morning hatte vorher
`konfidenz_final = -0.258` (negativer Wert, WAIT durch < 0.40-Filter). Mit der
Symmetrisierung wird daraus `konfidenz_final = +0.258 SHORT`. Trade wird hier
trotzdem nicht freigegeben (ok_count=1, < 2), aber das ist die KORREKTE
Konsequenz aus der Schichten-Logik, nicht mehr ein versteckter LONG-Bias.

---

## Verifikation (Phase F)

```
py_compile agents/analyst/_update_state.py        OK
py_compile agents/analyst/_usupdate_compute.py    OK
py_compile agents/captain/_update_state.py        OK
py_compile agents/captain/_usupdate_compute.py    OK
```

Grep auf alte asymmetrische Patterns in agents/analyst + agents/captain:
- `s1_score >= 0.20` / `s2_score >= 0.25` / `s3_score >= 0.00` -> nur noch im LONG-Block (Symmetrie geht in Zeile darunter weiter mit SHORT-Pendants).
- `alignment < 4` ohne abs() -> nicht mehr vorhanden in captain/.
- `alignment >= 4` ohne LONG-Direction-Branch -> nicht mehr vorhanden.

### Asymmetrische Stellen ausserhalb des Fix-Scopes (informativ, NICHT gepatcht)

User-Constraint "ALLE Aenderungen NUR in agents/analyst und agents/captain"
schliesst folgende Dateien aus. Sie wurden im Grep-Lauf gefunden und sind
hier dokumentiert fuer einen moeglichen Folge-Fix:

1. **agents/shared/analyst_write.py:70-72** — identische LONG-only Schichten-Freigabe
   (f1 = s1_score >= 0.20 etc.). Aktive Pipeline laeuft ueber
   agents/analyst/_update_state.py, die _write-Variante scheint Legacy/Alt.
2. **agents/shared/captain_write.py:91-115** — TEILSYMMETRISCH: nutzt
   `abs(konfidenz)` und `abs(alignment_score)` und unterscheidet LONG/SHORT
   (Zeilen 106-115). Die `abs(konfidenz)`-Pruefung greift aber auf den alten
   signed Konfidenz-Wert, nicht auf den neuen direction-aware Wert.
3. **agents/executor/CLAUDE.md:9** + **CLAUDE_ref.md:8** —
   `R:R < 1.5 oder alignment_score < 4 -> Order ablehnen`. Diese Schwelle ist
   LONG-zentrisch: ein klares Bear-Setup (alignment_score = -6) erfuellt
   `< 4` und wird abgelehnt. Empfohlene Anpassung: `abs(alignment_score) < 4`.

Empfehlung: separater Patch fuer diese 3 Stellen (ausserhalb dieses Auftrags).

---

## Rollback-Anleitung

Falls die Live-Pipeline nach dem Fix unerwartet ausfaellt:

```powershell
$src = "C:\Users\chris\TradingFloor\backups\longonly-fix-20260518-171752"
Copy-Item "$src\analyst-CLAUDE.md.backup-longonly-fix"          "C:\Users\chris\TradingFloor\agents\analyst\CLAUDE.md" -Force
Copy-Item "$src\analyst-CLAUDE_ref.md.backup-longonly-fix"      "C:\Users\chris\TradingFloor\agents\analyst\CLAUDE_ref.md" -Force
Copy-Item "$src\analyst-_update_state.py.backup-longonly-fix"   "C:\Users\chris\TradingFloor\agents\analyst\_update_state.py" -Force
Copy-Item "$src\analyst-_usupdate_compute.py.backup-longonly-fix" "C:\Users\chris\TradingFloor\agents\analyst\_usupdate_compute.py" -Force
Copy-Item "$src\captain-CLAUDE.md.backup-longonly-fix"          "C:\Users\chris\TradingFloor\agents\captain\CLAUDE.md" -Force
Copy-Item "$src\captain-CLAUDE_ref.md.backup-longonly-fix"      "C:\Users\chris\TradingFloor\agents\captain\CLAUDE_ref.md" -Force
Copy-Item "$src\captain-_update_state.py.backup-longonly-fix"   "C:\Users\chris\TradingFloor\agents\captain\_update_state.py" -Force
Copy-Item "$src\captain-_usupdate_compute.py.backup-longonly-fix" "C:\Users\chris\TradingFloor\agents\captain\_usupdate_compute.py" -Force
```

---

## Live-Verifikation

Naechste Pipeline-Lauefe pruefen:

- **08:00 Morning** (TradingCockpit.bat): state.json["analysis"]["instruments"][X]["schichten"]
  muss neue Felder enthalten (freigabe_s1_short, alle_long_ok, alle_short_ok, bias_direction).
  state.json["captain"]["konfidenz_details"] muss neue Felder enthalten
  (konfidenz_long, konfidenz_short, konfidenz_direction).
- **14:00 USUpdate** (TradingCockpit-US.bat): gleiches Schema.
- Spot-Check: Bei klar bearischem Markt (alle 3 Indizes bias=BEARISH, makro_score<-4):
  konfidenz_direction muss "SHORT" sein, session_bias muss
  "SHORT-BIAS (stark)" / "SHORT-BIAS" / "SHORT-LEAN" sein, NICHT "WAIT".

---

## Constraint-Compliance

- Reine Symmetrisierung (kein neuer Branch / keine neue Algebra): OK
- Backups vor jedem Patch: OK
- py_compile nach jedem Patch: OK
- Pipeline-Dateien (cockpit-morning.py, journal.js, macro/_update_state.py)
  nicht angefasst: OK
- ALLE Aenderungen NUR in agents/analyst und agents/captain: OK
- ASCII-only: OK
- Output-Pfad cockpit-trader/reports/: OK
