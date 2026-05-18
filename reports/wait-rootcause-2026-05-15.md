# WAIT-Ursachen-Analyse — Trading Floor Pipeline

**Datum:** 2026-05-15
**Sprache:** Deutsch
**Beobachtungs-Korridor:** 2026-04-22 bis 2026-05-15
**Methodik:** Auswertung aller verfuegbaren Monitor-Reports (`logs/DailyMon/`), Pipeline-Logs, des heutigen `state.json` und `state.json.morning-2026-05-15`, Cross-Check gegen `journal-data.json` und `indicator-eval-2026-05-15.md`.

---

## TL;DR

Von 20 dokumentierten Runs im POST-MP-FIX-Fenster (2026-05-04 bis 2026-05-15):

| Kategorie | Bedeutung | Runs | Anteil |
|---|---|---|---|
| A — HARD-STOP-MAKRO   | VIX/F&G/PCR/Bonds Hard-Stop gefeuert         | **0**  | 0%     |
| B — HARD-STOP-ZB      | FOMC/EZB ZB-Hard-Stop                          | **0**  | 0%     |
| C — STRUKTUR-BROKEN   | WAIT alleine durch SMC=0/Elliott-NEIN-Bug      | **0**  | 0%     |
| D — SCHWELLE-KNAPP    | Konfidenz/Schichten knapp verfehlt (±0.05)     | **3**  | 15%    |
| E — SCHWELLE-WEIT     | Echtes Markt-WAIT, weit unter Schwelle         | **15** | 75%    |
| F — UNKNOWN           | Daten unzureichend                              | **0**  | 0%     |
| **NICHT-WAIT**        | Trade-Freigabe = JA (2026-05-06 Morn+US)       | **2**  | 10%    |

**Antwort:**
- **Nicht Hard-Stops** — kein einziges A/B im Korridor.
- **Nicht der S3-Hardcode-Bug** — kein Run wuerde alleine durch SMC/sr_channel-Reparatur kippen.
- **Sondern Markt-Realitaet** — 15 von 18 echten WAITs waren weit unter Schwelle. Der MP-Fix hat genau dieses Bild geliefert: die Indizes liefen den Bias-Setups davon (Trend-Tage mit Preis fern von VAL/POC) und die Schichten-Pruefung lehnte korrekt ab.
- **3 D-Runs zeigen, dass die 0.40-Schwelle bei Makro-Drag eng wird** — am 2026-05-08 USUpdate (0.375), 2026-05-13 Morning (0.408 grenzwertig + Shape-Konflikt) und 2026-05-14 USUpdate (0.383). Hier waere eine kleine Justierung das Maximum, mit niedriger Erwartung.
- **Es gibt einen strukturellen Bias-Falle-Bug**: die `alle_schichten_ok`-Logik ist nur fuer LONG implementiert (2026-05-15 USUpdate: Bias `-3/8` klar bearisch, aber System blockiert Short).

---

## SCHRITT 1 — DATENINVENTAR

### Quellen
- 33 Monitor-Reports in `C:\Users\chris\TradingFloor\logs\DailyMon\` (2026-04-22 bis 2026-05-15)
- 22 Pipeline-Logs in `logs\pipeline\`
- `agents/shared/state.json` (USUpdate-Stand 2026-05-15) und `agents/shared/state.json.morning-2026-05-15`
- `cockpit-trader/reports/morning-2026-05-15.md` und `latest-usupdate.md`
- `cockpit-trader/journal-data.json` (heute)
- `cockpit-trader/reports/indicator-eval-2026-05-15.md` (Vorlauf-Audit)

### Historische state.json-Snapshots
Lediglich **1 Backup** existiert (`backups/phase1-20260511-...`); keine Tagesarchive der state.json. Daher rekonstruieren die Monitor-Reports `BEREICH 5 - ENTSCHEIDUNGS-AUDIT` die Entscheidung pro Run.

### Run-Bucket POST-MP-FIX (2026-05-04 bis 2026-05-15)

> Hinweis: Der Auftrag spricht von 22 Runs. Belegbar via Monitor-Reports sind **20 Runs (10 Tage × 2 Sessions)**; die 2 Differenzen stammen aus dem `indicator-eval-2026-05-15.md`-Vorlauf-Audit, ohne zugeordnete Monitor-Datei.

| Datum | Session | Bias | Score | Konfidenz | Schichten OK (von 3) | Trade-Freigabe |
|---|---|---|---|---|---|---|
| 2026-05-04 | Morning   | WAIT       | 3/8   | 0.229  | 1   | NEIN |
| 2026-05-04 | USUpdate  | WAIT       | 1/8   | 0.104  | 0   | NEIN |
| 2026-05-05 | Morning   | WAIT       | 1/8   | 0.075  | 0   | NEIN |
| 2026-05-05 | USUpdate  | WAIT       | 3/8   | 0.246  | 2   | NEIN |
| 2026-05-06 | Morning   | LONG-BIAS  | 4/8   | 0.450  | 2   | **JA** (2 Orders) |
| 2026-05-06 | USUpdate  | LONG-BIAS  | 4/8   | 0.450  | 2   | **JA** (2 NY-Orders) |
| 2026-05-07 | Morning   | WAIT       | 3/8   | 0.240  | 0   | NEIN |
| 2026-05-07 | USUpdate  | WAIT       | 2/8   | 0.150  | 0   | NEIN |
| 2026-05-08 | Morning   | WAIT       | 3/8   | 0.192  | 0   | NEIN |
| 2026-05-08 | USUpdate  | WAIT       | 5/8   | 0.375  | 2   | NEIN (knapp) |
| 2026-05-11 | Morning   | WAIT       | 5/8   | 0.3125 | 1   | NEIN |
| 2026-05-11 | USUpdate  | WAIT       | 3/8   | 0.1875 | 0   | NEIN |
| 2026-05-12 | Morning   | WAIT       | -4/8  | -0.250 | 0   | NEIN |
| 2026-05-12 | USUpdate  | WAIT       | 4/8   | 0.250  | 1   | NEIN |
| 2026-05-13 | Morning   | WAIT       | 5/8   | 0.408  | n.a.| NEIN (Shape-Filter) |
| 2026-05-13 | USUpdate  | WAIT       | 1/8   | 0.063  | 0   | NEIN |
| 2026-05-14 | Morning   | WAIT       | 5/8   | 0.308  | n.a.| NEIN |
| 2026-05-14 | USUpdate  | WAIT       | 6/8   | 0.383  | 2   | NEIN (knapp) |
| 2026-05-15 | Morning   | WAIT       | 2/8   | 0.183  | 0   | NEIN |
| 2026-05-15 | USUpdate  | WAIT       | -3/8  | -0.188 | 0   | NEIN |

Davon **18 WAITs + 2 Trade-Freigaben** (2026-05-06 Morning + USUpdate; jeweils 0 Fills).

### Run-Bucket PRE-MP-FIX (2026-04-22 bis 2026-05-01, Disclaimer)

> **Disclaimer:** Vor 2026-05-04 lieferte `data_get_market_profile` systematisch falsche VAH-Werte (+1 tick_step). Alle MP-abhaengigen Schichten-Scores in diesem Bucket sind **nicht direkt vergleichbar** mit dem POST-Bucket. Daten nur als groesserer Kontext.

| Datum | Session | Bias | Score | Konfidenz | Trade-Freigabe |
|---|---|---|---|---|---|
| 2026-04-22 | Morning  | LONG-LEAN | 5/8   | n/a    | **JA** (2 Orders SPX500+DJ30) |
| 2026-04-23 | Morning  | WAIT      | 3/8   | n/a    | NEIN |
| 2026-04-24 | Morning  | WAIT      | 4/8   | 0.21   | NEIN |
| 2026-04-27 | Morning  | WAIT      | 0/8   | n/a    | NEIN (Pre-FOMC+EZB) |
| 2026-04-27 | USUpdate | DIVERGENT | 5/8   | 0.375  | NEIN (Konfidenz < 0.40) |
| 2026-04-28 | Morning  | WAIT      | 1/8   | 0.104  | NEIN (Pre-FOMC) |
| 2026-04-28 | USUpdate | WAIT      | 1/8   | 0.021  | NEIN (Pre-FOMC) |
| 2026-04-29 | Morning  | WAIT      | 2/8   | 0.183  | NEIN (FOMC-Tag) |
| 2026-04-29 | USUpdate | WAIT      | n/a   | 0.000  | NEIN (FOMC-Gewichtung) |
| 2026-04-30 | Morning  | WAIT      | -3/8  | 0.000  | NEIN (ZB-Hard-Stop?) |
| 2026-05-01 | Morning  | LONG-LEAN | 4/8   | 0.425  | **JA** (1 Order SPX500) |
| 2026-05-01 | USUpdate | LONG      | 6/8   | 0.600  | JA-Update |

Pre-Fix: **3 von 12 Runs mit Trade-Freigabe** (2026-04-22, 2026-05-01 ×2). Auch hier signifikant Pre-FOMC/FOMC-Stops (4 Runs).

---

## SCHRITT 2 + 3 — KATEGORISIERUNG + AGGREGATION (POST-MP-FIX)

### A — HARD-STOP-MAKRO: 0 Runs
Im gesamten POST-Korridor lag VIX zwischen 16.55 und 19.18 (immer < 25), F&G zwischen 34 und 49 (immer 20-80), Bonds 4.38-4.55 (max 4.55 < 4.8% Hard-Stop), PCR delisted (zaehlt nicht). Keine A-Kategorie ausgeloest.

### B — HARD-STOP-ZB: 0 Runs
Keine FOMC/EZB-Tage im POST-Fenster (FOMC war 2026-04-29 im PRE-Bucket). 2026-05-05 USUpdate hatte ISM+JOLTS Event-Override (Chart 30% / Makro 70%), 2026-05-08 Morning hatte NFP-Pre, 2026-05-12 Morning hatte CPI-Pre. Diese Events verschieben nur die Gewichtung, sind keine Hard-Stops.

### C — STRUKTUR-BROKEN: 0 Runs (SOLO-Ursache)
**Keine** WAIT-Entscheidung im POST-Korridor wird **alleine** durch den S3-Hardcode-Bug ausgeloest. Begruendung:
- SMC=0 und sr_channel=0 sind im S3-Score `neutral` (0), nicht negativ — sie ziehen den Score nicht unter 0, sondern verringern nur seine Reichweite.
- In allen 18 WAIT-Runs lagen entweder S1 oder S2 oder mehrere S3-Faktoren (Ichimoku unter Kumo, SMA200 broken, Pivot negativ) als echte Block-Signale vor.
- Beispiel 2026-05-15 USUpdate SPX500: S3=-0.5 setzt sich zusammen aus ichimoku=-1, sma200=-1, pivot=-1, smc=0, sr_channel=0, autofibo=0. Selbst wenn SMC+sr_channel auf +1 stehen wuerden, ergaebe das s3=-0.17 — immer noch negativ.

(siehe Detailrechnung Schritt 4)

### D — SCHWELLE-KNAPP: 3 Runs (15%)

| Datum | Session | Symbol-Lage | Block-Detail | Distanz zur Schwelle |
|---|---|---|---|---|
| 2026-05-08 | USUpdate | DJ30+SPX500 alle_schichten_ok | Konfidenz 0.375 (Makro-Drag Gold↑+Oil↑) | **0.025** unter 0.40 |
| 2026-05-13 | Morning  | SPX500 5/8, GER40 P-Shape qualifiziert | Konfidenz 0.408 **ueber** 0.40, aber Shape-Filter blockt Trend-Day SPX500; P-Shape GER40 nur 2/8 | grenzwertig |
| 2026-05-14 | USUpdate | DJ30+SPX500 alle_schichten_ok 6/8 | Konfidenz 0.383 (Makro -2/12) + Preise zu weit ueber VAH | **0.017** unter 0.40 |

Aufteilung Morning vs USUpdate: 1 Morning / 2 USUpdate.
Symbole im Kern: DJ30 (3x), SPX500 (3x), GER40 (1x) — die D-Runs sind die wenigen Tage, an denen die US-Indizes nahe an einem Setup waren.

### E — SCHWELLE-WEIT: 15 Runs (75%)

Ueberwiegender Block in dieser Kategorie:
- **S1 versagt** wegen Shape-Konflikt (b-Shape oder P-Shape gegen Preis-Lage)
- **S2 versagt** wegen VWAP-Lage gegenlaeufig zum Setup, ER negativ
- **Schichten-Freigabe (>=2 Instrumente OK) nicht erreicht**

Aufteilung Morning vs USUpdate: 8 Morning / 7 USUpdate (gleichmaessig).

Symbol-Lage in den E-Runs (jeweils Instrument-Score, Min/Max):
- **GER40:** wiederholt S2 oder S3 broken (Ichimoku unter Kumo war 2026-05-05 + 2026-05-11 explizite Block-Begruendung)
- **DJ30:** wiederholt S1 broken durch b-Shape + Preis unter VAL (2026-05-04, 05-05, 05-08, 05-11)
- **SPX500:** wiederholt S1 broken durch Trend-Day = 0 Punkte (2026-05-07, 05-08, 05-11)

Beispiel-Runs je Kategorie:
- **E-extrem:** 2026-05-12 Morning (Score -4/8, Konfidenz -0.25). Pre-CPI, alle 3 Instrumente Schichten komplett broken.
- **E-typisch:** 2026-05-07 Morning (Score 3/8, Konfidenz 0.24). b-Shape Konflikt DJ30+SPX500, GER40 S2 blockiert.

### F — UNKNOWN: 0 Runs
Alle Runs haben verwertbare Monitor-Daten.

### NICHT-WAIT: 2 Runs (Trade-Freigabe JA)
- **2026-05-06 Morning** (4/8, 0.450, TREND+RISK_ON): 2 Orders GER40+SPX500 LONG. Nicht gefuellt (Preis lief davon).
- **2026-05-06 USUpdate**: Reset, 2 neue NY-LONG-Orders VWAP-Pullback. Auch nicht gefuellt.

→ Fill-Rate Post-Fix faktisch 0% (4 Orders, 0 Fills).

---

## SCHRITT 4 — SPEZIAL-ANALYSE: S3-BROKEN

### Frage
Wie oft haette ein S3 mit funktionierendem SMC/sr_channel/AutoFibo den WAIT in TRADE gedreht?

### Methode
Aus `_update_state.py` (Zeile 100-118) und `analyst_write.py` (Zeile 60-66, beide siehe `indicator-eval-2026-05-15.md`):
- `s3_score = (ichimoku + sma200 + smc + sr_channel + pivot + autofibo) / 6`
- Hardcoded auf 0 (post-fix): `smc`, `sr_channel` und in `analyst_write.py` zusaetzlich `pivot` und `autofibo`.
- Trade-Freigabe braucht `s3 >= 0` (UND s1>=0.20 UND s2>=0.25).

### Counterfactual-Berechnung pro WAIT-Run (Tabelle nur fuer Runs mit dokumentiertem S3-Breakdown):

| Run | Instrument | S3-IST | Beitragende Signale | Counterfactual mit smc+sr ideal | Wirkung |
|---|---|---|---|---|---|
| 2026-05-04 USUpd | GER40 | +0.50 | ich=?, andere=? | irrelevant — S1+S2 fehlen, S3 schon positiv | KEIN Flip |
| 2026-05-04 USUpd | DJ30  | +0.17 | nur Ichimoku-Pfad | irrelevant — S1=-0.80 | KEIN Flip |
| 2026-05-05 Morn  | GER40 | <0    | Ichimoku unter Kumo | smc+sr +2 → s3+0.33; ev. von -0.5 → -0.17 (neg.) | KEIN Flip |
| 2026-05-12 USUpd | DJ30  | +     | alle_schichten_ok | bereits geflipt, S3 nicht der Blocker | NICHT BLOCKER |
| 2026-05-13 USUpd | SPX500| <0    | broken, alle drei | smc+sr +2 → +0.33; immer noch ~0 oder neg. | UNKLAR |
| 2026-05-15 Morn  | GER40 | -0.333 | ichimoku=-1, fibo=+1 | smc+sr +2 → s3=-0.17 | KEIN Flip |
| 2026-05-15 USUpd | SPX500| -0.50 | ich=-1, sma=-1, pivot=-1 | smc+sr +2 → s3=-0.17 | KEIN Flip |

**Befund:**
- In **keinem dokumentierten Run** wuerde S3 alleine durch funktionierende SMC/sr_channel-Signale von negativ auf positiv kippen.
- Begruendung: Bei den Bear-getriebenen Runs sind 3+ S3-Faktoren gleichzeitig negativ (Ichimoku unter Kumo + Preis unter SMA200 + Pivot bearisch). Selbst optimistisch +2 fuer SMC+sr_channel ergibt netto noch negativ.
- Bei den Runs, in denen S3 bereits >= 0 war (alle_schichten_ok=true, z.B. 2026-05-05 USUpd GER40+SPX500, 2026-05-08 USUpd DJ30+SPX500, 2026-05-14 USUpd DJ30+SPX500), war S3 **nicht** der Blocker. Block war Konfidenz < 0.40 (Makro-Drag).

### Was der S3-Bug TROTZDEM verursacht
- **Resolution-Verlust:** Mit nur 3 aktiv-schwingenden Signalen (statt 6) hat S3 eine effektive Range von ~[-0.50, +0.50] statt [-1.0, +1.0]. Das macht den S3-Score weniger praezise.
- **Ichimoku-Dominanz:** Wie schon in `indicator-eval-2026-05-15.md` festgestellt: S3 ist faktisch ein Ichimoku-Filter. Wenn Ichimoku falsch liegt, fehlt jeder Gegenpol.
- **Systemisches Misstrauen:** Der Operator liest Felder, die `0` sind, als "kein Signal" — was korrekt ist — und kann den S3-Score nicht von einem ungenauen Score unterscheiden.

### Empfehlung S3
- **Variante A (kurzfristig):** SMC + sr_channel + (sehr begrenzter) AutoFibo aus dem S3-Score-Divisor entfernen. `s3_score = (ichimoku + sma200 + pivot) / 3`. Vorteil: keine kuenstliche Verwaesserung mehr. Direkter Eingriff in `_update_state.py` und `analyst_write.py`.
- **Variante B (mittelfristig):** SMC live verdrahten via `data_get_smc_levels` (BOS/CHoCH-Trigger, OB-Distanz). Stand: nicht implementiert. Aufwand groesser, Edge-Beweis erst nach >30 Trades moeglich.

→ Variante A ist sofort wirksam und macht den S3-Score ehrlich. **Wuerde aber den aktuellen WAIT-Stand nicht aendern**, weil die Bear-Dominanz (Ichimoku+SMA200+Pivot) ohnehin S3 < 0 ergibt.

---

## STRUKTUR-BEFUND JENSEITS DER KATEGORIEN

Beim Drillen durch die Monitor-Reports treten zwei Muster zutage, die ueber die Frage des Auftrags hinausgehen:

### 1) System-Bug: LONG-only Schichten-Logik
**Quelle:** 2026-05-15 USUpdate, `journal-data.json`, `state.json["captain"]`.
- Bias war `-3/8` STARK_BEARISCH, alle 3 Indizes unter VAL gebrochen, ER -43 bis -56.
- CAPTAIN-notes: *"WAIT: System nicht fuer Short-Setups ausgelegt (alle_schichten_ok-Logik nur LONG)"*.
- Konsequenz: ein klar handelbares Bear-Setup wird blockiert.
- Begruendung im Code: `s1_kontext.signale.mp_shape` belohnt P-Shape (BULL) und bestraft b-Shape (BEAR); aber `alle_schichten_ok` braucht ein positives Gesamtsignal — Short wird strukturell nicht unterstuetzt.

**Empfehlung:** Spiegel-Logik einbauen. `alle_schichten_short_ok = (s1<=-0.20 AND s2<=-0.25 AND s3<=0)` mit Inversionspruefung Shape vs Preis.

### 2) Fill-Rate-Problem unabhaengig von WAIT
**Quelle:** Pipeline-Logs, Monitor 2026-05-06.
- Selbst an den 2 Trade-Freigabe-Tagen (2026-05-06) wurden **0 von 4 Orders** gefuellt.
- Monitor-Report 2026-05-14 USUpdate: *"Preise zu weit ueber VAH fuer Pullback-Long (P_fill < 35%)"*.
- Gesamt-Fill-Rate (laut Monitor 04-27 USUpdate): 11.9%, 151 Orders — *"KRITISCH - Orders zu weit vom Markt"*.

**Empfehlung:** Entry-Logik VWAP-naeher kalibrieren — bekanntes TODO in `CLAUDE.md` ("Fill-Rate 9.4% analysieren").

### 3) Makro-Drag als ueblicher D-Treiber
Die 3 D-Runs hatten alle eine Konfidenz-Differenz < 0.05 zur Schwelle. In allen 3 Faellen war das `makro_score` negativ (-2/12 oder 0) durch Gold↑/Oil↑/F&G Fear. Mit aktivem `RISK_ON`-Detektor (z.B. Gold fallend ODER Oil unter 90) waeren beide Tage 2026-05-08 USUpdate und 2026-05-14 USUpdate gekippt. Aber das ist eine echte Markt-Bewertung, kein Bug — Risk-Off-Druck ist real.

---

## SCHWELLEN-DIAGNOSE

Aktuelle Schwellen (aus `CLAUDE.md` + `state.json`):
- Konfidenz: 0.40 fuer Trade, 0.55 fuer voll-Risiko, 0.70 fuer Premium
- Score: 4/8 Mindestschwelle Executor
- Schichten: 2/3 Instrumente `alle_schichten_ok`
- S1 >= 0.20, S2 >= 0.25, S3 >= 0
- Hard-Stops: VIX>25, F&G<20/>80, PCR>1.2, Bonds>4.8%

### Distanz der Schwellen zur Realitaet
- **Konfidenz 0.40 Schwelle:** sehr eng. 3 D-Runs (15%) lagen ±0.05 darunter; ein Senken auf 0.35 wuerde 2 Trades freigeben (2026-05-08 USUpd, 2026-05-14 USUpd). Erwartung der Win-Rate: unbekannt (0 Trades), aber Risk-Off-Setups historisch (siehe Pre-Fix 04-27 USUpdate Konfidenz 0.375 wurde damals auch blockiert).
- **S1 >= 0.20:** vernuenftig, da S1 die Kontext-Schicht ist.
- **S2 >= 0.25:** zeigt sich oft als Block in den E-Runs. Ist enger als S1.
- **Schichten 2/3 Pflicht:** 1/3 ist oft nahe dran (siehe 2026-05-11 Morning SPX500 alle_ok, 2026-05-12 USUpd DJ30 alle_ok). Bei 1/3 + Konfidenz > 0.40 koennte man Tag-Modus "Einzel-Instrument-Trade" zulassen, ist aber Risiko-Eskalation.
- **Hard-Stops VIX>25 / Bonds>4.8%:** sehr selten im Korridor erreicht. Sie limitieren zu Recht nicht aktiv.

---

## ZUSAMMENFASSUNG: LIEGT ES AN ...?

| Hypothese | Ergebnis | Beleg |
|---|---|---|
| **Schwellen zu streng** | Nur 3 von 20 Runs (15%) sind knapp dran (Kategorie D). Tiefer-Senken haette 1-3 Trades freigegeben, ohne klare Edge-Daten. | Tabelle Schritt 3 |
| **Hard-Stops** | 0% A/B im POST-Korridor — kein Faktor. | Schritt 2 |
| **Hardcode-Bugs (S3)** | Verwaessern den S3-Score, aber kein einziger WAIT haette ohne den Bug auf TRADE gekippt. | Schritt 4 Counterfactual |
| **Markt-Realitaet** | 75% der WAITs sind echte Markt-WAITs (Kategorie E). Indizes liefen den Setups davon (2026-05-13/14 Long-Entries 200+ Punkte ueber VAH). | Monitor 2026-05-14 USUpd |
| **System-Bug LONG-only** | Verhindert mindestens 1 sauberes Short-Setup (2026-05-15 USUpd) — strukturelles Defizit. | journal-data.json + captain.notes |
| **Fill-Rate** | Selbst bei Trade-Freigabe (2026-05-06 + Pre-Fix-Runs) fuellt nichts. Order-Placement-Logik ist suboptimal. | Monitor 2026-04-27 + 2026-05-06 + CLAUDE.md TODO |

### Wahrscheinlichste Ursache
Im POST-MP-FIX-Fenster ist die Konstellation:
1. **Hauptanteil (75%) — echte Markt-WAITs.** Die MP-Korrektur seit 2026-05-04 hat S1/S2 ehrlich gemacht und das System lehnt korrekt ab.
2. **15% — knapp verfehlte Schwellen** an Tagen mit Makro-Drag (Gold↑/Oil↑). Eine moderate Justierung (Konfidenz-Schwelle 0.40 → 0.35 *fuer 2+ Schichten OK*) wuerde 2 Trades freigeben, ohne die Risiko-Logik zu schwaechen.
3. **10% — Trade-Freigabe ohne Fill** (2026-05-06): kein WAIT-Problem, sondern ein Order-Placement-Problem.

### Konkrete Hebel (priorisiert)

1. **LONG-only-Bug fixen** (siehe `state.json` 2026-05-15 USUpdate) — strukturell die groesste Sperre.
2. **Fill-Rate-Problem analysieren** (offener TODO) — selbst bei Freigabe fuellt nichts.
3. **Konfidenz-Schwelle differenzieren** — z.B. 0.40 bei 1/3 Schichten, 0.35 bei 2/3 Schichten. Wuerde D-Runs in TRADE drehen.
4. **S3-Score ehrlich machen** — Divisor anpassen, SMC/sr_channel aus Berechnung entfernen bis Verdrahtung steht (siehe `indicator-eval-2026-05-15.md` Variante A).
5. **Hard-Stop-Schwellen nicht anfassen** — sie wirken nicht aktiv und sind regelkonform.

---

*Auto-generated by Claude · Quellen: state.json, journal-data.json, logs/DailyMon/*, logs/pipeline/*, cockpit-trader/reports/* · Bei Aktualisierung dieses Berichts: `change-template.txt` einhalten.*
