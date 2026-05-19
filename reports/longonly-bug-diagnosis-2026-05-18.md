# LONG-only Bug: Diagnose und Fix-Plan

**Datum:** 2026-05-18
**Modus:** Diagnose (NUR Lesen + Analyse, kein Patch)
**Sprache:** Deutsch
**Trigger:** 2026-05-15 USUpdate Bias -3/8 klar bearisch, System blockierte Short strukturell.
**Belegrun (heute):** state.json USUpdate 14:55 — alignment +5/8 BULLISH, alle_ok 2/3, konfidenz 0.375 < 0.40 → WAIT.

---

## Executive Summary

Der LONG-only-Bug ist KEIN einzelner Hardcode-String "BUY" sondern eine **konsistent LONG-zentrische Algebra** an drei Stellen der Pipeline: (1) Analyst-Schichten-Freigabe `alle_schichten_ok` prueft nur s1>=0.20, s2>=0.25, s3>=0.00 (nur LONG); (2) Captain-Konfidenz-Formel `konfidenz = alignment/8 * chart_w + macro/12 * makro_w` produziert NEGATIVE Werte bei bearischen Setups und vergleicht gegen +0.40, was -0.40 strukturell nie erreichen kann; (3) Captain-Session-Bias-Mapping prueft `alignment >= 4` fuer SHORT-LEAN, was bei NEGATIVEN alignment_scores nie zutrifft. Die Order-Generierung (`generate_order` in cockpit-morning.py) und das Sheet-Schema (journal.js) sind beide bereits SHORT-faehig. Es ist also kein Output-Bug, sondern ein DECISION-Bug.

**Schweregrad:** **MITTEL-KRITISCH** — verhindert ca. 25-50% aller potentiellen Trade-Tage in Bear-Phasen, aber stoppt nicht den Pipeline-Run.

**Fix-Aufwand:** ca. 60-100 Zeilen Code in 4 Python-Files + Spec-Updates in 4 CLAUDE.md-Files. Geschaetzt 30-60 Min Spawn-Zeit inkl. Verifikation. Risiko NIEDRIG, da die Aenderung Symmetrie herstellt, keine neue Logik einfuehrt.

**Vantage-Restriktion:** KEINE. Belegt durch `fillrate-rootcause-2026-05-15.md`: "Keine Broker-Anbindung. Das System ist ein Trade-Journal, kein automatischer Trader." Vantage CFDs erlauben Long UND Short, `Vantage:GER40` ist nur ein Symbol-String fuer TradingView.

---

## Root-Cause-Analyse

### PHASE 1 — Score/Bias-Berechnung

#### 1.1 `cockpit-morning.py` — `compute_bias()` (Zeile 768-1081)

**Symmetrie-Bewertung:** SYMMETRISCH (kein Bug).

```python
# Zeile 1021-1025
raw_score = sum(s["score"] for s in auto_signals)
sc        = round(raw_score / total_weight * 100)
bias = "BULLISH" if sc > 25 else "BEARISH" if sc < -25 else "NEUTRAL"
```

Bullish und Bearish Signale werden mit gleichem Gewicht erzeugt: `Preis > VWAP +2` ↔ `Preis < VWAP -2`, `>VAH +2` ↔ `<VAL -2`, `P-Shape (-1 bei Reversal-Logik) / Trend Day Up +2 / Trend Day Down -2` etc. Auch FRED-Signale sind symmetrisch (CPI > 4 → -2, CPI < 2.5 → +1; etwas asymmetrisch begrenzt, aber kein Long-Bias).

Auswirkung auf SHORT-Trades: KEINE — `compute_bias()` liefert BEARISH wenn der Markt bearisch ist.

#### 1.2 `agents/analyst/_update_state.py` — Schichten + alle_schichten_ok (Zeile 122-125)

**Symmetrie-Bewertung:** LONG-ZENTRISCH (Bug).

```python
# Zeile 122-125
freigabe_s1 = s1_score >= 0.20
freigabe_s2 = s2_score >= 0.25
freigabe_s3 = s3_score >= 0.00
alle_ok     = freigabe_s1 and freigabe_s2 and freigabe_s3
```

Die Scores s1/s2/s3 sind selbst symmetrisch konstruiert (Range -1..+1, P-Shape +3 ↔ b-Shape -3 etc.). ABER: `alle_schichten_ok` prueft NUR die positive Richtung. Ein S1-Score von -0.50 (klar bearisch) erfuellt die Freigabe-Bedingung nicht und kann nie zur Trade-Eroeffnung fuehren — obwohl `-0.50` genauso aussagekraeftig ist wie `+0.50` (nur in die andere Richtung).

Folgewirkung Zeile 170-176:
```python
ok_count    = sum(1 for v in instruments.values() if v["schichten"]["alle_schichten_ok"])
max_align   = max(v["schichten"]["alignment_score"] for v in instruments.values())
top_down["trade_freigabe"] = ok_count >= 1   # ← LONG-only
```

`max()` liefert bei drei alignment_scores [-7,-6,-5] = -5 (am wenigsten bearisch), nicht "+7 vom Betrag her als SHORT-Setup". Damit ist top_down ebenfalls LONG-zentrisch.

Auswirkung auf SHORT: BLOCKIERT. Selbst bei klarem 3-fach-Bear-Setup (alignment -8 auf allen 3 Instr) ist `alle_ok = false`, `ok_count = 0`, `trade_freigabe = false`.

#### 1.3 `agents/analyst/_usupdate_compute.py` — gleiche Logik (Zeile 32-34, 41)

```python
f1 = s1_score >= 0.20
f2 = s2_score >= 0.25
f3 = s3_score >= 0.00
...
'alle_schichten_ok': f1 and f2 and f3
```

Identischer Bug, gespiegelt in USUpdate-Pfad.

#### 1.4 Spec-Quellen

- `agents/analyst/CLAUDE.md` Zeile 7: `Trade-Freigabe NUR: S1>=0.20 UND S2>=0.25 UND S3>=0.00 (alle 3 muessen OK sein)` — schreibt die LONG-Logik vor.
- `agents/analyst/CLAUDE_ref.md` Zeile 75-81: identisch.

---

### PHASE 2 — Confidence-Berechnung

#### 2.1 `agents/captain/_update_state.py` — Konfidenz (Zeile 92-94)

**Symmetrie-Bewertung:** LONG-ZENTRISCH (Bug).

```python
# Zeile 92-94
konfidenz_chart = (alignment / 8.0) * chart_w
konfidenz_makro = (macro_score / 12.0) * makro_w
konfidenz       = round(konfidenz_chart + konfidenz_makro, 3)
```

Bei alignment = -6 und macro_score = -8 (klares Bear-Setup, RISK_OFF):
- konfidenz_chart = -6/8 * 0.6 = -0.45
- konfidenz_makro = -8/12 * 0.4 = -0.267
- **konfidenz = -0.717**

Das System interpretiert dies als "EXTREM negative LONG-Konfidenz" — aber semantisch ist es "EXTREM hohe SHORT-Konfidenz" und sollte ein Trade-Trigger sein.

#### 2.2 Schwellenwert-Check (Zeile 112)

```python
elif konfidenz < 0.40:
    session_bias = "WAIT"
```

Es gibt KEINEN Vergleich gegen `konfidenz <= -0.40`. Negative Konfidenzen fallen automatisch in WAIT.

#### 2.3 Score-Schwelle (Zeile 117)

```python
elif alignment < 4:
    session_bias = "WAIT"
```

`alignment < 4` ist fuer alle negativen alignment_scores (Bear-Setup) wahr → IMMER WAIT.

#### 2.4 Session-Bias-Mapping (Zeile 132-143)

```python
biases = [analysis["instruments"][s]["bias"] for s in ["GER40","DJ30","SPX500"]]
bull_count = sum(1 for b in biases if "BULLISH" in b)
bear_count = sum(1 for b in biases if "BEARISH" in b)
if regime == "RISK_ON" and bull_count >= 2 and alignment >= 6:
    session_bias = "LONG-BIAS (stark)"
elif (regime == "RISK_ON" ...) and bull_count >= 2 and alignment >= 4:
    session_bias = "LONG-BIAS"
elif bull_count >= 2 and alignment >= 4:
    session_bias = "LONG-LEAN"
elif bear_count >= 2 and alignment >= 4:   # ← BUG
    session_bias = "SHORT-LEAN"
else:
    session_bias = "RANGE"
```

**Der SHORT-LEAN-Branch verlangt `alignment >= 4`**, aber bearische Setups haben NEGATIVE alignment_scores. Diese Bedingung ist mathematisch fuer ein echtes Bear-Setup nie wahr. Korrekt waere `alignment <= -4`.

#### 2.5 `agents/captain/_usupdate_compute.py` (Zeile 89-92)

```python
if alignment_score >= 5:
    session_bias = 'LONG-BIAS'
else:
    session_bias = 'LONG-LEAN'
```

**HARDCODED LONG.** Es gibt KEINEN SHORT-Branch ueberhaupt in der USUpdate-Variante. alignment_score = -6 fuehrt zu `session_bias = 'LONG-LEAN'` (semantisch absurd). Wird im aktuellen Run durch den `konfidenz < 0.40`-Branch davor abgefangen (WAIT), aber wenn die Konfidenz-Formel jemals symmetrisch wird, ist dies die zweite Schranke.

#### 2.6 Spec-Quellen

- `agents/captain/CLAUDE.md` Zeile 6: `Score <4 oder Konfidenz <0.40 → immer WAIT` — schreibt LONG-Schwelle vor.
- `agents/captain/CLAUDE_ref.md` Zeile 81-87: Konfidenz-Formel + Entscheidungsmatrix ohne Vorzeichen-Handling.
- `agents/captain/CLAUDE_ref.md` Zeile 93-103: Session-Bias-Tabelle nennt SHORT-BIAS/SHORT-LEAN, aber die zugrundeliegende Algebra (alignment >= 4) macht die Eintraege unerreichbar.

---

### PHASE 3 — Order-Direction

#### 3.1 `cockpit-morning.py` — `generate_order()` (Zeile 1135-1214)

**Symmetrie-Bewertung:** SYMMETRISCH (kein Bug).

```python
# Zeile 1183-1194
if effective_bias == "BULLISH":
    entry = round(min(val, vwap) + va_range * 0.05, 2)
    sl    = round(entry - va_range * 0.30, 2)
    tp1   = round(vah, 2)
    tp2   = round(vah + va_range * 0.50, 2)
    order_type = "Limit Buy"
else:
    entry = round(max(vah, vwap) - va_range * 0.05, 2)
    sl    = round(entry + va_range * 0.30, 2)
    tp1   = round(val, 2)
    tp2   = round(val - va_range * 0.50, 2)
    order_type = "Limit Sell"
```

SL/TP korrekt invertiert: bei SHORT entry knapp unter VAH, SL ueber Entry, TP1 = VAL, TP2 unter VAL. R:R Berechnung mit abs(). NEUTRAL-Fallback (Zeile 1153-1162) waehlt direction basierend auf score-Vorzeichen + Preis-Lage.

Auswirkung auf SHORT: KEIN BUG — wenn `bias_data["bias"]` als "BEARISH" ankommt, wird korrekt ein Limit-Sell-Auftrag erzeugt.

#### 3.2 `agents/executor/_update_state.py` und `_export.py`

**Symmetrie-Bewertung:** PASS-THROUGH (kein Bug).

```python
# _update_state.py Zeile 17-19
if trade_freigabe:
    # placeholder - hier keine Orders, WAIT
    pass
```

Der Executor erzeugt im aktuellen Zustand keine Orders direkt; bei `trade_freigabe=true` werden die Orders separat (vermutlich durch das Captain-Sub-Agent-Prompt) erzeugt und in `orders`-Array geschrieben. Es gibt kein hardcoded "BUY" oder "LONG". Wenn der Captain `richtung=SHORT` setzen wuerde, gibt der Executor das durch.

#### 3.3 `trading-journal/journal.js` (Zeile 44-61)

**Symmetrie-Bewertung:** SYMMETRISCH (kein Bug).

```javascript
const row = [..., o.type || '', o.entry || '', o.sl || '', o.tp1 || '', ...]
```

Schreibt `o.type` als String in Spalte D. "Limit Buy" oder "Limit Sell" sind beide moeglich. Sheet-Header (Setup, Zeile 37): `'Datum','Zeit','Instrument','Typ','Entry','SL','TP1','TP2','R:R'...` — keine Long/Short-spezifischen Spalten.

---

### PHASE 4 — Hardcoded LONG/BUY/BULLISH

#### 4.1 Hardcoded LONG-Strings

| Stelle | Code | Bewertung |
|---|---|---|
| `cockpit-morning.py:278-280` | `"Vantage:SP500"`, `"Vantage:DJ30"`, `"Vantage:GER40"` | KEIN BUG — Ticker-Strings |
| `agents/captain/_usupdate_compute.py:89-92` | `session_bias = 'LONG-BIAS' / 'LONG-LEAN'` | BUG — keine SHORT-Variante |
| `agents/captain/_update_state.py:134-141` | LONG-Branches dominant, SHORT-LEAN-Branch mathematisch unerreichbar | BUG (siehe 2.4) |
| `tradingview-mcp/src/agents/prompts.js:74` | `"VIX > 30: note as warning, no longs"` | KEIN BUG — nur LONGs blocken bei VIX>30 ist konservativ, SHORTs sind dann sogar opportun |
| `cockpit-morning.py:1183` | `if effective_bias == "BULLISH": ... else: SELL` | KEIN BUG (siehe 3.1) |
| `cockpit-morning.py:1301-1306` | `if bias_str == "BULLISH": ... elif "BEARISH": ... else:` | KEIN BUG — beide Zweige da |

#### 4.2 Asymmetrische Operationen (max/abs/Filter)

| Stelle | Code | Bewertung |
|---|---|---|
| `agents/analyst/_update_state.py:171` | `max_align = max(v[...]["alignment_score"] for v in instruments.values())` | **BUG** — bei [-7,-6,-5] liefert -5 statt "best SHORT" |
| `agents/analyst/_usupdate_compute.py:70-71` | `best = max(results.keys(), key=lambda k: results[k]['alignment_score'])` | **BUG** — selbe max()-Falle |
| `cockpit-morning.py:1180-1181` | `p_fill = max(20, min(75, int(confluence_pct * 0.75)) - neutral_penalty)` | KEIN BUG — Wahrscheinlichkeits-Clamp |
| `cockpit-morning.py:1196` | `rr_raw = abs(tp1 - entry) / abs(sl - entry)` | KEIN BUG (R:R braucht abs) |

---

### PHASE 5 — Makro-Filter

#### 5.1 Makro-Score Symmetrie

`agents/macro/_update_state.py` Zeile 22-67: Bullish und Bearish Punkte werden gleichberechtigt gezaehlt (`bullish += 1` / `bearish += 1`), gesamt_score = bullish - bearish (Range -12..+12). Bias-Mapping (Zeile 69-78) ist symmetrisch (`>=5 RISK_ON` ↔ `<=-6 RISK_OFF`).

**Symmetrie-Bewertung:** SYMMETRISCH (kein Bug).

ABER: Die Captain-Konfidenz-Formel multipliziert `(macro_score/12) * makro_w`. Bei negativem macro_score wirkt das gegen einen positiven alignment_score (LONG) — das ist korrekt. Bei einem bearischen Setup (alignment negativ, macro_score negativ) wirkt das aber ZU GUNSTEN der semantischen Bear-These — und produziert genau dadurch eine groessere negative Konfidenz-Zahl, die den 0.40-Filter erst recht verfehlt.

Das ist der eigentliche Bug: das Vorzeichen ist semantisch korrekt nur in einer Richtung kodiert.

#### 5.2 Hard-Stops

`agents/captain/CLAUDE_ref.md` Zeile 142-150 und `agents/macro/CLAUDE.md`:
- VIX > 30 → WAIT immer (in `agents/captain/_update_state.py:172-174` implementiert)
- F&G < 20 / > 80 → Warnung (kein Hard-Stop, korrekt)
- Bonds > 4.8% → Warnung
- VIX > 25 → Warnung
- BALANCE + RISK_OFF → WAIT erzwingen
- TREND + RISK_OFF → max_risk -0.50%

**Symmetrie-Bewertung:** SYMMETRISCH — Hard-Stops blockieren alle Trades (auch SHORTs). Das ist semantisch korrekt: bei Vola-Spikes (VIX>30) ist auch ein SHORT-Setup gefaehrlich (Whipsaw-Risiko).

ABER ein subtiler Punkt: `BALANCE + RISK_OFF → WAIT erzwingen` in `agents/captain/_update_state.py:168-170` killt explizit auch ein potentielles SHORT-Setup, das gerade in Balance+RISK_OFF besonders attraktiv waere. Das ist eher eine konservative Wahl als ein Bug, sollte aber im Fix bedacht werden.

---

### PHASE 6 — Broker-Restriktion

#### 6.1 Vantage-Recherche

Treffer-Quellen:
- `cockpit-trader/reports/fillrate-rootcause-2026-05-15.md` Zeile 25: *"Keine Broker-Anbindung. Das System ist ein Trade-Journal, kein automatischer Trader. Es gibt keinen Broker-API-Call, kein Vantage-Fill, kein Order-ID-Tracking."*
- `cockpit-morning.py:278-280`: `"^GSPC": "Vantage:SP500"` etc. — nur TradingView-Symbol-Strings.
- `tradingview-mcp/CLAUDE.md:249`: *"Broker: Vantage (kein echtes Boersenvolumen)"* — Vermerk zum CFD-Tick-Volumen, keine Long-Restriktion.
- `tradingview-mcp/src/agents/prompts.js:6,79`: *"CFD instruments ... via Vantage broker"* — sagt nur was die Symbole sind.

**Ergebnis:** KEINE Vantage-Restriktion auf LONG-Only. CFDs bei Vantage erlauben Long UND Short. Annahme fuer Fix: SHORTs sind erlaubt.

#### 6.2 Sheet-Schema (journal.js Spalten)

Spalten: `Datum, Zeit, Instrument, Typ, Entry, SL, TP1, TP2, R:R, P(Fill)%, P(TP1)%, Konfluenz, TF, Bias, Bias%, MP_Shape_Gestern, MP_Shape_Prognose, VWAP_Position, Gefuellt?, TP1_erreicht?, SL_erreicht?, Tatsaechl_PnL, Notizen`.

Keine Long-Only-Spalten. `Typ` akzeptiert `"Limit Buy" | "Limit Sell"`, `Bias` akzeptiert beliebigen String (Bullisch / Baerisch / Neutral werden bereits in cockpit-morning.py Zeile 1257 gesetzt).

---

## Hauptverursacher

Nur **3 Kern-Stellen** muessen wirklich gefixt werden — alles andere ist Konsequenz:

### 1. **Analyst `alle_schichten_ok` ist LONG-only**

**Stellen:**
- `agents/analyst/_update_state.py` Zeile 122-125 (Morning, geschrieben in jeder Pipeline)
- `agents/analyst/_usupdate_compute.py` Zeile 32-34 + 41 (USUpdate)
- Spec: `agents/analyst/CLAUDE.md` Zeile 7, `agents/analyst/CLAUDE_ref.md` Zeile 75-81

**Wirkung:** Generiert das `alle_schichten_ok`-Flag, das CAPTAIN als harten Filter benutzt. Bearische Setups erreichen nie `ok_count >= 2` → strukturelles WAIT.

### 2. **Captain Konfidenz-Formel kennt nur eine Richtung**

**Stellen:**
- `agents/captain/_update_state.py` Zeile 92-94 (Konfidenz-Berechnung)
- `agents/captain/_update_state.py` Zeile 112 (`konfidenz < 0.40 → WAIT`)
- `agents/captain/_usupdate_compute.py` Zeile 47-49 + 69
- Spec: `agents/captain/CLAUDE_ref.md` Zeile 81-87

**Wirkung:** Negative alignment + negative macro_score → konfidenz negativ → trifft den 0.40-Filter nicht. Auch wenn die Magnitude eines SHORTs `|0.72|` waere, wird `-0.72 < 0.40` ausgewertet → WAIT.

### 3. **Captain Session-Bias und Schwellen ohne abs()**

**Stellen:**
- `agents/captain/_update_state.py` Zeile 117 (`alignment < 4`)
- `agents/captain/_update_state.py` Zeile 138-141 (SHORT-LEAN braucht `alignment >= 4` — unerreichbar)
- `agents/captain/_usupdate_compute.py` Zeile 89-92 (hardcoded `LONG-BIAS/LONG-LEAN`)
- Spec: `agents/captain/CLAUDE.md` Zeile 6

**Wirkung:** Selbst wenn Konfidenz-Formel symmetrisch waere, wuerde der Score-Filter und das Bias-Mapping bearische Setups stoppen.

---

## Fix-Plan

### Hauptverursacher 1: Analyst-Schichten

**Was aendern:**

In `agents/analyst/_update_state.py` (und `_usupdate_compute.py`):
```python
# Statt nur LONG-Freigabe:
freigabe_s1_long  = s1_score >=  0.20
freigabe_s2_long  = s2_score >=  0.25
freigabe_s3_long  = s3_score >=  0.00
freigabe_s1_short = s1_score <= -0.20
freigabe_s2_short = s2_score <= -0.25
freigabe_s3_short = s3_score <=  0.00

alle_long_ok  = freigabe_s1_long  and freigabe_s2_long  and freigabe_s3_long
alle_short_ok = freigabe_s1_short and freigabe_s2_short and freigabe_s3_short
alle_ok       = alle_long_ok or alle_short_ok

# Neue Felder in state.json schreiben:
"freigabe_long":  alle_long_ok,
"freigabe_short": alle_short_ok,
"bias_direction": "LONG" if alle_long_ok else ("SHORT" if alle_short_ok else "NONE"),
"alle_schichten_ok": alle_ok
```

`top_down`-Berechnung anpassen (Zeile 170-179):
```python
ok_count_long  = sum(1 for v in ... if v["schichten"]["freigabe_long"])
ok_count_short = sum(1 for v in ... if v["schichten"]["freigabe_short"])
ok_count       = max(ok_count_long, ok_count_short)
best_direction = "LONG" if ok_count_long >= ok_count_short else "SHORT"
# best Instrument nach |alignment_score|
best = max(instruments.items(), key=lambda kv: abs(kv[1]["schichten"]["alignment_score"]))
top_down["best_direction"] = best_direction
top_down["alignment_score_abs"] = abs(best[1]["schichten"]["alignment_score"])
```

**Tests:**
- Unit-Test (oder manueller Run): state.json mit allen 3 Instr. alignment=-6 fuettern, pruefen ob `freigabe_short=true` und `bias_direction="SHORT"`.
- Re-Run gegen Snapshot `agents/shared/state.json.morning-2026-05-15` und pruefen ob 2026-05-15 USUpdate-Setup (`-3/8`) als SHORT-Setup erkannt wird.

**Seiteneffekte:**
- Dashboard `index.html` / `journal.html` muss `bias_direction` lesen, sonst zeigt es weiter LONG-Bias an. Pruefen ob `bias_pct` aus alignment_score abgeleitet wird (cockpit-trader/index.html: TPO-Render lehnt sich an `bias`, sollte robust gegen SHORT sein).
- Monitor-Reports `logs/DailyMon/monitor_*.txt` referenzieren `alle_schichten_ok` direkt → muessen mitziehen oder neuen Schluessel lesen.

### Hauptverursacher 2: Captain-Konfidenz

**Was aendern:**

In `agents/captain/_update_state.py` Zeile 92-94 (und `_usupdate_compute.py` 47-49):
```python
# alte Formel (nur LONG):
# konfidenz = (alignment / 8.0) * chart_w + (macro_score / 12.0) * makro_w

# neu (direction-aware):
konfidenz_long  = ( alignment / 8.0) * chart_w + ( macro_score / 12.0) * makro_w
konfidenz_short = (-alignment / 8.0) * chart_w + (-macro_score / 12.0) * makro_w
konfidenz       = max(konfidenz_long, konfidenz_short)
konfidenz_direction = "LONG" if konfidenz_long >= konfidenz_short else "SHORT"

konfidenz_details["konfidenz_long"]  = round(konfidenz_long, 3)
konfidenz_details["konfidenz_short"] = round(konfidenz_short, 3)
konfidenz_details["konfidenz_direction"] = konfidenz_direction
konfidenz_details["konfidenz_final"]  = konfidenz  # immer >= 0
```

In Zeile 112 (Schwellen-Check):
```python
elif konfidenz < 0.40:           # bleibt: jetzt vergleicht es den MAX-Betrag
    session_bias = "WAIT"
```

**Tests:**
- Captain mit alignment=-6, macro_score=-8, chart_w=0.5, makro_w=0.5 → konfidenz_short = 0.708 → konfidenz=0.708 → Trade erlaubt.
- Captain mit alignment=+3, macro_score=-2, chart_w=0.6, makro_w=0.4 → konfidenz_long=0.158, konfidenz_short=-0.158 → konfidenz=0.158 → WAIT (korrekt: gemischtes Setup).
- Regression: alignment=+5, macro=+5 → konfidenz_long=0.542, konfidenz_short=-0.542 → konfidenz=0.542 → Trade (alter Wert hatte 0.542).

**Seiteneffekte:**
- Captain.notes / trade_plan-Texte sind heute LONG-zentrisch formuliert ("Long Re-Entry", "Pullback an VWAP fuer Long"). Plan-Generierung muss `konfidenz_direction` lesen und SHORT-Plan-Vorlagen anbieten.

### Hauptverursacher 3: Captain-Schwellen + Bias-Mapping

**Was aendern:**

In `agents/captain/_update_state.py` Zeile 117:
```python
elif abs(alignment) < 4:
    session_bias = "WAIT"
```

In Zeile 130-143 (Session-Bias-Mapping):
```python
biases = [analysis["instruments"][s]["bias"] for s in [...]]
bull_count = sum(1 for b in biases if "BULLISH" in b)
bear_count = sum(1 for b in biases if "BEARISH" in b)
direction = konfidenz_direction  # aus Hauptverursacher 2

if direction == "LONG":
    if regime == "RISK_ON" and bull_count >= 2 and alignment >= 6:
        session_bias = "LONG-BIAS (stark)"
    elif (regime == "RISK_ON" or makro_bias in ("RISK_ON","LEICHT_RISK_ON")) and bull_count >= 2 and alignment >= 4:
        session_bias = "LONG-BIAS"
    elif bull_count >= 2 and alignment >= 4:
        session_bias = "LONG-LEAN"
    else:
        session_bias = "RANGE"
elif direction == "SHORT":
    if regime == "RISK_OFF" and bear_count >= 2 and alignment <= -6:
        session_bias = "SHORT-BIAS (stark)"
    elif (regime == "RISK_OFF" or makro_bias in ("RISK_OFF","LEICHT_RISK_OFF")) and bear_count >= 2 and alignment <= -4:
        session_bias = "SHORT-BIAS"
    elif bear_count >= 2 and alignment <= -4:
        session_bias = "SHORT-LEAN"
    else:
        session_bias = "RANGE"
```

In `_usupdate_compute.py` Zeile 89-92 die hardcoded `LONG-BIAS / LONG-LEAN` durch dieselbe direction-aware Variante ersetzen.

In Zeile 168-170 (Makro-Alignment Risk-Anpassung):
```python
elif phase == "BALANCE" and makro_bias in ("RISK_OFF",):
    # nur LONG erzwingen, SHORT erlauben:
    if direction == "LONG":
        session_bias = "WAIT"; trade_freigabe = False
```

**Tests:**
- alignment=-6, RISK_OFF, bear_count=3 → SHORT-BIAS (stark)
- alignment=-4, NEUTRAL, bear_count=2 → SHORT-LEAN
- alignment=-3 → WAIT (|alignment|<4)
- Regression: alignment=+6, RISK_ON, bull_count=3 → LONG-BIAS (stark) (wie heute)

**Seiteneffekte:**
- Captain.trade_plan-String muss SHORT-Variante haben (z.B. "Pullback an VWAP/POC/VAH fuer Short Re-Entry, Stop ueber VAH"). Das spiegelt CLAUDE_ref.md Zeile 122-131.
- Strategie-Tabelle (Trend/Balance/Ausbruch) hat SHORT-Variante bereits dokumentiert — nur Code-Pfad fehlt.

### Vorgeschlagene Reihenfolge

1. **Spec-Updates zuerst** (Analyst CLAUDE.md + CLAUDE_ref.md, Captain CLAUDE.md + CLAUDE_ref.md) — dokumentiert die Symmetrie, damit nachfolgende Code-Aenderungen das Vorbild haben.
2. **Analyst _update_state.py + _usupdate_compute.py** patchen — neue Schichten-Felder.
3. **Captain _update_state.py + _usupdate_compute.py** patchen — Konfidenz + Bias-Mapping + Schwellen.
4. **Dashboard-Felder** (index.html / journal.html) checken: `bias_direction` rendern.
5. **Monitor CLAUDE.md** pruefen ob er die neuen Felder benoetigt.
6. **Regression-Run** gegen 2026-05-15 USUpdate-Snapshot (siehe Test-Strategie).

---

## Was NICHT angefasst werden sollte

| Stelle | Grund |
|---|---|
| `cockpit-morning.py:768-1081` compute_bias() | bereits symmetrisch (BULLISH/BEARISH mit gleichgewichteten Signalen) |
| `cockpit-morning.py:1135-1214` generate_order() | symmetrisch (Limit Buy ↔ Limit Sell, SL/TP korrekt invertiert) |
| `cockpit-morning.py:1301-1306` invalidation-Logik | beide Zweige existieren |
| `trading-journal/journal.js` writeMultiple / Sheet-Schema | "Typ" akzeptiert Limit Buy + Limit Sell |
| `agents/macro/_update_state.py` Scoring | gesamt_score ist -12..+12 symmetrisch |
| Hard-Stops VIX > 30 / 25, F&G < 20 / > 80, Bonds > 4.8% | wirken auf ALLE Trades, semantisch korrekt |
| `tradingview-mcp/src/agents/prompts.js` (ANALYST_PROMPT/CAPTAIN_PROMPT) | nicht im Hot-Path der Pipeline, separate Legacy-MCP-Agenten |
| MARKETDATA / mp_history-Logik | direction-agnostisch |
| `agents/analyst/_update_state.py:188-195` Marktphasen-Bestimmung | beide AUSBRUCH-Richtungen abgedeckt |

---

## Vantage-Restriktion: Ergebnis

**KEINE Long-Only-Beschraenkung gefunden.**

Belege:
- `cockpit-trader/reports/fillrate-rootcause-2026-05-15.md`: System ist Trade-Journal, kein automatischer Trader. Kein Broker-API-Call.
- `Vantage:GER40` / `Vantage:DJ30` / `Vantage:SP500`: nur TradingView-Symbol-Strings.
- CFDs auf Indizes erlauben standardmaessig Long + Short.
- Sheet-Schema unterstuetzt "Limit Sell".

**Annahme fuer Fix:** SHORT-Trades sind erlaubt. Falls der User spaeter eine reale Vantage-Account-Beschraenkung bestaetigt, muesste man im EXECUTOR einen Filter einbauen — heute nicht noetig.

---

## Test-Strategie

### Simulation ohne Live-Trade

1. **Synthetisches Bear-Setup:** `agents/shared/state.json` kopieren nach `state.test.json`, alignment_score auf -6 setzen, alle 3 Instrumente auf `bias="BEARISH"`, S1/S2/S3 negativ. Captain-Script mit Test-Pfad laufen lassen.
   - **Erwartung:** session_bias = "SHORT-BIAS (stark)" oder "SHORT-BIAS", konfidenz_final >= 0.40, trade_freigabe = true.

2. **Regression gegen 2026-05-15:** Snapshot `agents/shared/state.json.morning-2026-05-15` (laut wait-rootcause-Bericht: Bias -3/8) durch gepatchten Captain laufen lassen.
   - **Erwartung (Hypothese):** trade_freigabe wechselt von false auf true, konfidenz >= 0.40, session_bias = SHORT-BIAS, Order-Generierung erzeugt Limit Sell.

3. **Regression Bull-Tag 2026-05-06:** Snapshot pruefen.
   - **Erwartung:** Keine Verhaltensaenderung — alignment+4/8 BULLISH bleibt LONG-BIAS, konfidenz unveraendert.

4. **Mixed-Setup:** alignment=+2, macro_score=-2.
   - **Erwartung:** konfidenz_long ≈ 0.083, konfidenz_short ≈ -0.083 → konfidenz=0.083 → WAIT (korrekt).

### Wo simulierbar

- `state.json` ist ein flacher File → kann frei manipuliert werden.
- Python-Scripts sind idempotent (lesen state, schreiben state) → koennen wiederholt gegen Test-Snapshot laufen.
- Keine externen API-Calls fuer Score/Bias/Konfidenz → komplett offline testbar.

---

## Aufwand und Risiko

### Geschaetzte Zeilen-Aenderungen

| Datei | Zeilen | Art |
|---|---|---|
| `agents/analyst/_update_state.py` | ~15-20 | Schichten-Block + top_down |
| `agents/analyst/_usupdate_compute.py` | ~15-20 | identische Logik |
| `agents/captain/_update_state.py` | ~25-30 | Konfidenz + Schwellen + Bias-Mapping |
| `agents/captain/_usupdate_compute.py` | ~20-25 | dito + hardcoded LONG entfernen |
| `agents/analyst/CLAUDE.md` + `CLAUDE_ref.md` | ~10-15 | Spec-Update |
| `agents/captain/CLAUDE.md` + `CLAUDE_ref.md` | ~10-15 | Spec-Update |
| **Summe** | **~95-125** | Code + Doku |

### Spawn-Zeit

- Spec-Updates: 10-15 Min
- Code-Updates: 20-30 Min
- Verifikation (Test-Snapshots + state.json-Inspektion): 10-15 Min
- **Gesamt: 40-60 Min**

### Risiko

- **NIEDRIG:** Aenderung stellt Symmetrie her, keine neue Logik. Bestehender LONG-Pfad bleibt funktional identisch.
- **MITTEL bei Auslassen:** Wenn nicht ALLE 4 Code-Files konsistent gefixt werden, koennten Race-Conditions zwischen Morning- und USUpdate-Pfaden entstehen (z.B. Morning erkennt SHORT, USUpdate fuettert es weiter mit LONG-Defaults).
- **ZU PRUEFEN:** Dashboard (`index.html`) und Monitor-CLAUDE.md koennten neue Felder erwarten. Falls dort weiter `bias_score >= 0` als LONG-Heuristik haengt, kann Dashboard falsch rendern, ohne dass Pipeline ausfaellt.
- **Order-Generierung** ist robust — `generate_order` wartet auf `bias = "BEARISH"` und tut das Richtige.

### Was kann schief gehen

1. **Dashboard zeigt SHORT als "Bullisch %"** falls `bias_pct` aus positivem alignment_score abgeleitet wird (cockpit-morning.py Zeile 1258: `bias_pct = min(95, 50 + abs(score))`). Hier ist abs() schon korrekt → vermutlich kein Problem.
2. **Reports (morning-{date}.md)** koennen LONG-zentrische Texte enthalten — nicht-kritisch, kosmetisch.
3. **Order-Snapshot in sheets** kann verwirrend werden falls "Bias = Baerisch" + "Typ = Limit Sell" gleichzeitig stehen — semantisch korrekt, aber neu fuer den User.

---

*Auto-generated by Claude · Quellen: state.json (today USUpdate 14:55), wait-rootcause-2026-05-15.md, fillrate-rootcause-2026-05-15.md, agents/{analyst,captain,executor,macro}/_*.py + CLAUDE.md/CLAUDE_ref.md, cockpit-trader/cockpit-morning.py, trading-journal/journal.js · Diagnose-Modus: keine Datei modifiziert.*
