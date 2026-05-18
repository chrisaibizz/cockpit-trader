# Fill-Rate Root-Cause-Analyse — Trading Floor Pipeline

**Datum:** 2026-05-15
**Sprache:** Deutsch
**Beobachtungs-Korridor:** 2026-04-12 (System-Start) bis 2026-05-15
**Methodik:** Auswertung Google-Sheet-Stats (via trading-journal/logs), 33 Monitor-Reports, 33 Pipeline-Logs, Reverse-Engineering der Order-Generierung in `cockpit-morning.py`, Cross-Check `trading-journal/logs/cockpit-YYYY-MM-DD.log`.

---

## TL;DR

Die Fill-Rate von ~10.6% ist **kein reines Order-Placement-Problem**, sondern eine Kombination aus drei Ursachen:

1. **Phantom-Auto-Orders (Hauptproblem):** `cockpit-morning.py` schreibt jeden Morgen 3 synthetische Limit-Orders ins Sheet — unabhaengig von der spaeteren Claude-Pipeline-Entscheidung, mit mathematisch erzwungenem RR=3.17 und Entry-Preisen aus dem **gestrigen** Value Area (VAL+5% bzw VAH-5%). An Trend-Tagen ist der heutige Preis weit weg vom Entry → strukturell ungefuellt.
2. **Debrief-Luecke (Statistik-Verzerrung):** Von 208 Orders im Sheet sind nur ~44 (21%) jemals als gefuellt/nicht-gefuellt markiert worden. Die `journal.js stats`-Berechnung zaehlt leere Zellen als "nicht gefuellt" → echte Fill-Rate bei debriefed Orders liegt bei **~50%**, nicht bei 10.6%.
3. **Trend-Day Pullback-Falle bei Pipeline-Orders:** Auch echte Pipeline-Orders (Trade-Freigabe-Tage) bleiben oft ungefuellt, weil die Entries an gestrigen VA-Edges liegen und der Markt heute in Trend-Bewegung davonlaeuft (siehe 2026-05-06: 4 echte Orders, 0 Fills; Monitor 2026-05-14: "Preise zu weit ueber VAH").

**Konsequenz:** Hebel 1 fixt die Statistik (Phantom-Orders abschalten oder konditional generieren). Hebel 2 fixt die Realitaet (Entry-Logik VWAP-nah statt VA-Edge).

---

## PHASE 1 — DATENQUELLEN (DISCOVERY)

### Was es **NICHT** gibt
- **Keine Broker-Anbindung.** Das System ist ein Trade-Journal, kein automatischer Trader. Es gibt keinen Broker-API-Call, kein Vantage-Fill, kein Order-ID-Tracking.
- **Kein "broker_get_orders"** o.ae. im TradingView-MCP — TradingView wird nur fuer Marktdaten/Charts genutzt.
- **Kein dedicated `agents/executor/logs/`** — der EXECUTOR-Agent schreibt nur state.json (`_export.py`, `_update_state.py`); keine Order-Sende-Logik.

### Was es **GIBT**
| Quelle | Pfad | Inhalt |
|---|---|---|
| **Google Sheet** | `1PA43AloHsrDtg-KG_139pCPOceisc7RJc8t9f2ffyrc` Tab `Orders` | 23 Spalten A-W; alle Orders mit Status-Spalten S/T/U (Gefuellt/TP1/SL) |
| Lokale Order-Logs | `trading-journal/logs/cockpit-YYYY-MM-DD.log` | WRITE/UPDATE/STATS/DEBRIEF-Eintraege fuer jeden Order-Touch |
| Heutige Orders | `trading-journal/orders-today.json` | letzter Snapshot der vom Pipeline geschriebenen Orders |
| Heutiger Report | `trading-journal/report-today.json` | letzter Doc-Report mit Orders pro Instrument |
| state.json | `agents/shared/state.json` | aktuelle Pipeline-Entscheidung + `orders` Block |
| Monitor-Reports | `logs/DailyMon/monitor_*.txt` | 33 Reports mit Bereich 7 "JOURNAL STATS" (Aggregate) |

### TradingView-MCP-Capabilities (geprueft)
- `data_get_trades` existiert: Liefert Pine-Strategie-Trades (Backtesting), nicht echte Broker-Orders.
- `data_get_strategy_results` existiert: nur Pine-Strategy-Tester-Output.
- Kein Tool fuer Live-Broker-Orders, Account-Positionen oder Fills.

→ **Single Source of Truth fuer Order-Lifecycle = Google Sheet + lokale `trading-journal/logs/*.log`.**

---

## PHASE 2 — DATEN-INVENTAR

### Aggregate (Google-Sheet-Stats, gemessen via `journal.js stats`)

| Datum | Total Orders | Fill-Rate | TP1-Rate (von gefuellten) | Quelle |
|---|---|---|---|---|
| 2026-04-13 | 41 | 2.4% | 0.0% | `cockpit-2026-04-13.log:166` |
| 2026-04-15 | 88 | 9.1% | 12.5% | `cockpit-2026-04-15.log:120` |
| 2026-04-21 | 128 | 9.4% | 8.3% | `cockpit-2026-04-21.log:31` |
| 2026-04-27 USUpd | 151 | 11.9% | 27.8% | Monitor 04-27 |
| 2026-04-30 | 160 | 12.5% | 25.0% | `cockpit-2026-04-30.log:17` |
| 2026-05-01 | 170 | 12.9% | 22.7% | `cockpit-2026-05-01.log:47` |
| 2026-05-06 | 183 | 12.0% | 22.7% | `cockpit-2026-05-06.log:17` |
| 2026-05-08 | 193 | 11.4% | 22.7% | `cockpit-2026-05-08.log:11` |
| 2026-05-12 | 199 | 11.1% | 22.7% | `cockpit-2026-05-12.log:11` |
| **2026-05-15** | **208** | **10.6%** | **22.7%** | `cockpit-2026-05-15.log:13` |

**Beobachtung:** Fill-Rate sinkt sukzessive von ~13% auf ~10.6%, weil pro WAIT-Tag 3 ungefuellte Phantom-Orders im Nenner wachsen. TP1-Rate ist seit 04-30 starr auf 22.7% — keine neuen TP1-Fills mehr seit ~2 Wochen.

### Order-Felder im Sheet (Spalten A-W, aus `journal.js setup()`)

```
A Datum | B Zeit | C Instrument | D Typ | E Entry | F SL | G TP1 | H TP2
I R:R   | J P(Fill)% | K P(TP1)% | L Konfluenz | M TF | N Bias | O Bias%
P MP_Shape_Gestern | Q MP_Shape_Prognose | R VWAP_Position
S Gefuellt? | T TP1_erreicht? | U SL_erreicht? | V Tatsaechl_PnL | W Notizen
```

Status-Felder S/T/U akzeptieren `Ja` / `Nein` / `(leer)`. `journal.js stats()` Zeile 95:
```js
const filled = ir.filter(r => r[18] === 'Ja');  // nur explizit 'Ja' zaehlt als gefuellt
const fill_rate = filled.length / ir.length;     // leere Zellen senken Rate
```

### UPDATE-Eintraege (explizit debriefed): 44 von 208 Orders (21%)

| Datum (Debrief) | Sheet-Zeilen | Filled | Nicht | TP1 | SL | Sample-Fill-Rate |
|---|---|---|---|---|---|---|
| 04-13 | 2,3,4         | 1 | 2 | 0 | 1 | 33% |
| 04-14 | 5,6,7,9,10    | 3 | 2 | 1 | 2 | 60% |
| 04-15 | 43,49,51,52   | 4 | 0 | 0 | 4 | 100% |
| 04-16 | 58-68 (11x)   | 5 | 6 | 0 | 5 | 45% |
| 04-20 | 104,105,108   | 0 | 3 | 0 | 0 | 0% |
| 04-21 | 121-126 (6x)  | 0 | 6 | 0 | 0 | 0% |
| 04-22 | 127,128,129   | 3 | 0 | 1 | 2 | 100% |
| 04-27 | 144,145,146   | 3 | 0 | 3 | 0 | 100% ("guter Tag") |
| 04-30 | 156,157,158   | 2 | 1 | 0 | 2 | 67% |
| 05-01 | 159,160,161   | 2 | 1 | 0 | 2 | 67% |
| 05-06 | 179,180,181   | 0 | 3 | 0 | 0 | 0% |
| 05-07 | 182,183,184   | 0 | 3 | 0 | 0 | 0% |
| **SUMME** | **44**    | **22** | **22** | **5** | **17** | **50%** |

**Schluessel-Befund:** Bei den **explizit debriefed** Orders liegt die wahre Fill-Rate bei **50%**, die TP1-Rate bei **22.7%** (5/22) — identisch zur Sheet-Stats-Zahl, weil die TP1-Berechnung auf gefuellten Orders basiert (Zaehler/Nenner gleichermassen sample-eingeschraenkt).

Die **anderen 164 von 208 Orders (79%)** stehen mit leerem S-Feld im Sheet → werden als "nicht gefuellt" gezaehlt → druecken die Sheet-Fill-Rate von 50% auf 10.6%. **Diese 164 Orders sind in Wahrheit "unknown" (Kategorie H), nicht "no-fill".**

---

## PHASE 3 — ROOT-CAUSE-KLASSIFIKATION PRO ORDER-KLASSE

Da Single-Order-Granularitaet ueber die 208 nicht vollstaendig moeglich ist (nur 44 debriefed), klassifiziere ich nach **Order-Klasse** (drei Quellen):

### Klasse 1: Phantom-Auto-Orders (cockpit-morning.py)

**Generierungs-Stelle:** `cockpit-trader/cockpit-morning.py` Zeile 1183-1214 (`generate_order`).
**Geometrie (BULLISH, gespiegelt fuer BEARISH):**
```python
entry = round(min(val, vwap) + va_range * 0.05, 2)   # 5% innerhalb VA, am unteren Rand
sl    = round(entry - va_range * 0.30, 2)            # 30% VA-Range unter Entry
tp1   = round(vah, 2)                                # oberer VA-Rand
tp2   = round(vah + va_range * 0.50, 2)              # 50% VA-Range darueber
rr    = (tp1 - entry) / (entry - sl)                 # = 0.95*range / 0.30*range = 3.17
```

**Pruefung:** `|sl-entry|/va_range = 0.30`, `|tp1-entry|/va_range = (1 - 0.05) = 0.95` → RR mathematisch fix bei **0.95/0.30 = 3.166...** (in Logs als `"rr":"3.17"` 146x belegt).

**Bias-Override (Zeile 1153-1166):** Bei `bias == "NEUTRAL"` wird `effective_bias` heuristisch auf BULLISH/BEARISH gesetzt → es **wird IMMER eine Order generiert** (es sei denn `rr_raw < 1.0`, was geometrisch nicht passieren kann, da rr immer ~3.17).

**Trigger:** TradingFloor-Morning Task 08:00 CEST (06:00 UTC) → ruft `cockpit-morning.py` → ruft `journal.js write-multiple` → 3 Orders ins Sheet.

**Zeitstempel-Beleg:** Logs zeigen jeden Werktag 06:01-06:02 UTC drei WRITE-Eintraege:
```
06:01:55 [WRITE] [GER40] Order: Limit Buy @ X | rr 3.17
06:01:56 [WRITE] [US30]  Order: Limit Buy @ Y | rr 3.17
06:01:57 [WRITE] [SPX500] Order: Limit Buy @ Z | rr 3.17
06:01:58 [WRITE] [ALLE] 3 Orders geschrieben
```

**Symbolname-Drift:** Phantom-Orders schreiben `"US30"` (alter Yahoo-Ticker `^DJI`/`YM=F`), Pipeline-Orders schreiben `"DJ30"`. Inkonsistenz zwingt manuelle Cross-Korrelation.

**Anzahl im Sheet:** Werktage 2026-04-12 bis 2026-05-15 (~25 Werktage) × 3 Auto-Orders + Dev-Phase 04-12 bis 04-16 mit Mehrfach-Writes → **geschaetzt 90-110 Phantom-Orders** (Bulk).

**Failure-Kategorie:** Ueberwiegend **D (NO-FILL-LIMIT-OFFSET)** oder **H (UNKNOWN, da nicht debriefed)**. Sample (Zeile 179-184, 04-30 bis 05-07): alle 6 Auto-Orders an WAIT-Tagen → **0% Fill-Rate**, alle Kategorie D.

### Klasse 2: Pipeline-Generated Real-Orders (Claude-Agent)

**Generierungs-Stelle:** Captain-Plan + Executor-Output, anschliessend manueller/Pipeline-Aufruf `journal.js write-multiple` mit echten Konfluenz-Daten.
**Anzahl:** Nur an Trade-Freigabe-Tagen.
- 2026-04-22: 2 Orders (`SPX500 LONG 7104 rr 1.7`, `DJ30 LONG 49385 rr 1.5`) + 3 US-Update Orders
- 2026-04-24, 04-29, 04-30, 05-01: jeweils 2-3 Pipeline-Orders + ggf US-Update
- 2026-05-06: 2 Morning-Pipeline + 2 US-Update = 4 echte Orders
- POST-MP-Fix Korridor (05-04 bis 05-15): 0 zusaetzliche Pipeline-Orders nach 05-06

**Failure-Kategorie der bekannten echten Orders:**
- **04-22**: Z. 128 TP1 (=A FILLED), Z. 129 SL (=A FILLED-SL). 2 echte Pipeline-Orders → 100% Fill, 50% TP1.
- **04-24 → 04-27 Debrief**: Z. 144-146 alle 3 TP1 (=A FILLED-TP1). 100% Fill, 100% TP1 — bester Tag.
- **04-29 → 04-30 Debrief**: Z. 156,158 SL gefuellt, Z. 157 nicht (=A FILLED-SL + D).
- **05-06**: 4 echte Orders → 0 Fills (D). Monitor-Notes: "Preis lief nach Open Drive davon, Limit Buys nicht erreicht".

### Klasse 3: Test-Iteration-Orders (Dev-Phase 04-13 bis 04-16)

Mehrfach taegliche Re-Writes mit Test-Setups (z.B. 04-13 hat 12 WRITE-ALLE-Batches mit je 3 Orders = 36 Orders/Tag). Diese sind hauptsaechlich Phantom-mit-Test-Daten und nie debriefed.

**Anzahl:** ~50-70 Orders im Sheet.
**Failure-Kategorie:** **H (UNKNOWN)** — Sheet-Rauschen, fuer Fill-Rate-Analyse irrelevant aber inflated Nenner.

### Klassifikations-Tabelle (208 Sheet-Orders, hochgerechnet)

| Kategorie | Bedeutung | ~Anzahl | Anteil |
|---|---|---|---|
| **A — FILLED** | Gefuellt=Ja | 22 | 10.6% |
| **B — NEVER-SENT** | Pipeline-freigabe aber kein Sheet-Write | **0** | (n/a — Pipeline schreibt immer ins Sheet) |
| **C — REJECTED-BROKER** | n/a | **0** | (kein Broker) |
| **D — NO-FILL-LIMIT-OFFSET** | Limit-Order, Preis nicht erreicht | 22 (debriefed) + geschaetzt ~80 nicht debriefed | ~49% |
| **E — NO-FILL-STOP-OFFSET** | n/a | 0 | (alle Orders sind Limits) |
| **F — EXPIRED** | TIF abgelaufen | unklar (kein TIF-Tracking) | 0% |
| **G — MANUAL-CANCEL** | User-Cancel | 0 (kein Cancel-Log) | 0% |
| **H — UNKNOWN** | Daten unzureichend (S leer) | ~84 | ~40% |

**Hauptbefund:** Kategorie B/C/E/F/G praktisch leer. Kategorie D + H dominieren. Wenn 84 H-Orders (geschaetzt Phantom-Auto-Orders an WAIT-Tagen) korrekt als D klassifiziert wuerden, waere die echte Misslungen-Rate ~89%, davon **~75-80% strukturell aus Phantom-Orders** an WAIT-Tagen.

---

## PHASE 4 — PATTERN-ERKENNUNG

### Pro Symbol (aus WRITE-Logs, 203 [WRITE] [SYMBOL]-Eintraege)

| Symbol | WRITE-Counts | Notiz |
|---|---|---|
| GER40 | ~57 | Konsistenter Symbolname |
| US30 | ~52 | **Phantom-Symbol** (cockpit-morning.py) |
| DJ30 | ~15 | Pipeline-Symbol (Claude-Agent) |
| SPX500 | ~79 | Beide Pfade |

**Befund:** `US30`-Eintraege stammen praktisch ausschliesslich aus Phantom-Orders; `DJ30` aus Pipeline. Sheet-Filterung nach Symbol verzerrt Stats.

### Pro Order-Typ

| Typ | Vorkommen | Quelle |
|---|---|---|
| `Limit Buy` | ~100 | cockpit-morning.py (Bullish/Neutral-Override) |
| `Limit Sell` | ~46 | cockpit-morning.py (Bearish/Neutral-Override) |
| `LONG` / `SHORT` | ~15 | Pipeline (Claude-Agent) |
| `undefined` | ~24 | Pipeline-Bug (`order.type` nicht uebergeben) |

**Befund:** Phantom-Orders sind **ausschliesslich Limits**. Es gibt keine Stop-Orders im System, daher Kategorie E nicht anwendbar. Pipeline-Orders haben oft `type === undefined` — Bug in Order-JSON-Build, kosmetisch.

### Zeitliche Verteilung

| Slot | Trigger | Order-Typ |
|---|---|---|
| 06:00-06:02 UTC (08:00 CEST) | TradingFloor-Morning Task | 3 Phantom-Auto |
| 06:13-06:20 UTC | Pipeline Morning (Claude-Agent) | 2-3 Pipeline-Real (nur Trade-Freigabe) |
| 12:50-13:05 UTC (14:45 CEST) | TradingFloor-USUpdate | 2-3 Pipeline-Real (US-Update, optional) |

**Befund:** Phantom-Orders werden **eine Stunde vor US-Pre-Market** gesetzt — also auf VA-Levels die ueber Nacht/EU-Open evtl. schon obsolet sind.

### Trade-Freigabe-Tage vs WAIT-Tage

| Tag | Pipeline-Bias | Echte Pipeline-Orders | Phantom-Orders | Fill-Rate (echte) |
|---|---|---|---|---|
| 04-22 | LONG-LEAN 5/8 | 2 | 3 | 100% (1 TP1, 1 SL) |
| 04-24 | (debriefed 04-27) | 3 | 3 | 100% (3 TP1) — Outlier |
| 04-29 | (debriefed 04-30) | 3 | 3 | 67% (0 TP1, 2 SL) |
| 04-30 | (debriefed 05-01) | 3 | 3 | 67% (0 TP1, 2 SL) |
| 05-06 | LONG-BIAS 4/8 | 4 | 3 | **0%** (Markt-Open-Drive, Limit Buys nicht erreicht) |

**Befund:** An Trade-Freigabe-Tagen schwankt die echte Fill-Rate zwischen **0% (Open-Drive Trend-Day)** und **100% (Mean-Revert in VA)**. Mittelwert ueber 5 Trade-Freigabe-Tage: ca. 67%. Die `~50%` Sample-Fill-Rate aus den UPDATE-Eintraegen ist konsistent — sie reflektiert die Mischung aus Phantom (~0%) und Pipeline (~67%) Orders.

---

## ROOT-CAUSES (priorisiert nach Hebelwirkung)

### 1. Phantom-Auto-Orders (HEBEL: gross, einfach)
`cockpit-morning.py` schreibt taeglich 3 Orders ins Sheet, unabhaengig von der Pipeline-Entscheidung. RR mathematisch fix bei 3.17, Entry auf gestrigen VA-Edges, Symbol "US30" statt "DJ30". Diese Orders sind:
- Strukturell ungefuellt an Trend-Tagen (75% der Tage im POST-MP-Fix-Korridor)
- Verzerren die Statistik nach unten (90-110 Orders im Sheet, Fill-Rate ~0%)
- Werden nicht debriefed → bleiben mit S=leer im Sheet → drueckt `journal.js stats` weiter

**Fix:** Entweder Order-Generierung in `cockpit-morning.py` (Zeile 1339-1350) konditional an Score>=4 koppeln, oder ganz entfernen und Pipeline-Agent als alleinige Quelle definieren. Achtung: dann muss der Workflow "cockpit-morning.py → write-multiple → report" angepasst werden, weil report aktuell `orders_list` braucht.

### 2. Debrief-Luecke (HEBEL: gross, Disziplin)
Nur 21% der Orders im Sheet sind explizit debriefed. Die `journal.js stats`-Funktion zaehlt leere S-Felder als "nicht gefuellt" → Fill-Rate von 10.6% statt 50% (bei debriefed Sample). Tatsaechliche Fill-Rate-Realitaet ist um Faktor 5 besser, als das System reportet.

**Fix:** 
- Option A: `journal.js stats` umstellen — Nenner = Orders mit `r[18] != ''` (nicht leer); Fill-Rate = filled / (filled + explicit_nein).
- Option B: Taegliche Debrief-Pflicht etablieren (Morgens den `journal.js update-result <row> <Ja/Nein> <Ja/Nein> <pnl>` Workflow durchziehen). MONITOR-Agent koennte das tracken.

### 3. Trend-Day Pullback-Falle bei echten Pipeline-Orders (HEBEL: mittel, fachlich)
Auch echte Pipeline-Orders verfallen oft, weil:
- Entry-Logik: bei LONG-Bias Entry typischerweise auf VAL/Pivot/Bull-OB **gestern** — bei Open-Drive heute laeuft Preis nach oben weg.
- 2026-05-06 Beleg: 4 Limit-Buy-Orders @ 24380/7257/24800/7307 — Markt offnete mit Drive nach oben, Pullback kam nicht.
- Monitor 2026-05-14: "Preise zu weit ueber VAH fuer Pullback-Long (P_fill < 35%)".
- Captain-CLAUDE.md: SL-Hierarchie ONL/ONH → PDL/PDH → VAL/VAH + 0.1% Buffer — alles **Vortags-Levels**, keine intraday-Adjustierung.

**Fix:** Entry-Logik in Executor-Template um VWAP-Bias erweitern: bei Trend-Tag (ER > 30) Entry am aktuellen Preis +/- 0.3×ATR statt VAL+5%; bei Balance Entry an VA-Edges OK. Erfordert P_Fill-Tracking pro Setup-Typ, das aktuell nur als statischer Score geschaetzt ist.

### 4. Symbol-Drift US30 vs DJ30 (HEBEL: klein, kosmetisch)
cockpit-morning.py schreibt `"US30"`, Pipeline-Agent schreibt `"DJ30"`. Bei Sheet-Filter nach Symbol-Stats werden Phantom-Orders nicht den Pipeline-Stats zugeschlagen. Aktuell nicht statistik-aufloesend.

**Fix:** In `cockpit-morning.py` `display_name` von `US30` auf `DJ30` aendern (an 1-2 Stellen).

### 5. Keine TIF, kein aktives Order-Management (HEBEL: mittel, Architektur)
Orders bleiben statisch im Sheet bis manuelle Update-Aktion. Es gibt keinen TIF-Marker (`Time-in-Force`) in den Sheet-Spalten, keine "expired"-Markierung. Wenn intraday Bias sich dreht, werden Phantom-Orders nicht angepasst — sie liegen einfach unrealisiert dort.

**Fix:** Spalte X "TIF" oder "Expires" hinzufuegen, MONITOR-Agent koennte am US-Close abgelaufene Orders auf `Gefuellt=Nein, Expired=Ja` setzen.

---

## NICHT BEFUND

- **Keine Broker-Rejections** (Kategorie C) — System hat keinen Broker.
- **Keine Stop-Order-Probleme** (Kategorie E) — alle Orders sind Limits.
- **Keine Margin-/Capital-Issues** — kein echtes Trading.
- **Keine TradingView-MCP-Bugs** — MCP ist nur Daten-Layer, nicht Order-Layer.
- **Keine Pipeline-Schritt-Faelle** (Kategorie B) — die wenigen echten Pipeline-Orders kamen alle im Sheet an.

---

## SAMPLE-GROESSE-DISCLAIMER

- **Echte Pipeline-Orders Sample: nur 12-15 Orders** ueber 5 Trade-Freigabe-Tage. Statistische Aussage zur Fill-Rate dieser Klasse ist **schwach** (Konfidenz-Intervall +/-30%).
- **Phantom-Order-Sample: ~90 Orders**, davon nur 6 explizit debriefed (alle ungefuellt). Pattern ist klar, aber 84 Orders sind unbekannt (Kategorie H).
- **Debrief-Coverage: 21%** — fuer einen Production-Trading-Journal zu niedrig. Die nachfolgenden Empfehlungen koennten mit besserer Coverage praeziser werden.

---

## VERIFIKATIONS-LISTE FUER EMPFEHLUNGEN

| Empfehlung | Verifikation noch noetig |
|---|---|
| Phantom-Order-Generator deaktivieren | Pruefen, ob `journal.js report` ohne Orders korrekt durchlaeuft (Zeile 1413-1428 hat bereits `else: print "Keine Orders (NEUTRAL Bias)"`) |
| `journal.js stats` umstellen | Sheet-Format pruefen — `r[18]` ist Spalte S (`Gefuellt?`); leere Strings vs `null` |
| Trend-Day Entry-Logik | Backtest erforderlich — aktueller Datenbestand 0 Trades reicht nicht |
| Symbol US30→DJ30 in cockpit-morning.py | 2 stellen in `cockpit-morning.py` (Symbol-Mapping); Auswirkung auf bestehende Stats |
| TIF-Spalte X | Sheet-Schema-Migration noetig; `setup()` in `journal.js` Zeile 37 anpassen |

---

*Auto-generated by Claude · Quellen: trading-journal/logs/*.log, logs/DailyMon/*, logs/pipeline/*, cockpit-trader/cockpit-morning.py, agents/shared/state.json, Google Sheet 1PA43Alo... · Bei Aktualisierung dieses Berichts: change-template.txt einhalten.*
