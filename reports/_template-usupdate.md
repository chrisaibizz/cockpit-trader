# USUpdate Template — 14:45 US-Session Briefing

**{{UPDATE_TIMESTAMP}}** · Symbole: GER40, DJ30, SP500
*Update zum Morning-Briefing vom {{MORNING_TIMESTAMP}}*

══════════════════════════════════════════════
## 1. DELTA SEIT MORNING
══════════════════════════════════════════════

**Was hat sich in den letzten ~6h geändert?**

### Bias-Wechsel
| Symbol | Morning | Jetzt | Veränderung |
|---|---|---|---|
| GER40 | {{MORN_GER40_BIAS}} | {{NOW_GER40_BIAS}} | {{GER40_BIAS_DELTA}} |
| DJ30  | {{MORN_DJ30_BIAS}}  | {{NOW_DJ30_BIAS}}  | {{DJ30_BIAS_DELTA}} |
| SP500 | {{MORN_SP500_BIAS}} | {{NOW_SP500_BIAS}} | {{SP500_BIAS_DELTA}} |

### Konfidenz-Wechsel
| Symbol | Morning | Jetzt | Delta |
|---|---|---|---|
| GER40 | {{MORN_GER40_KONFIDENZ}} | {{NOW_GER40_KONFIDENZ}} | {{GER40_KONFIDENZ_DELTA}} |
| DJ30  | {{MORN_DJ30_KONFIDENZ}}  | {{NOW_DJ30_KONFIDENZ}}  | {{DJ30_KONFIDENZ_DELTA}} |
| SP500 | {{MORN_SP500_KONFIDENZ}} | {{NOW_SP500_KONFIDENZ}} | {{SP500_KONFIDENZ_DELTA}} |

### MP-Shape-Wechsel
| Symbol | Morning | Jetzt | Bemerkung |
|---|---|---|---|
| GER40 | {{MORN_GER40_SHAPE}} | {{NOW_GER40_SHAPE}} | {{GER40_SHAPE_NOTE}} |
| DJ30  | {{MORN_DJ30_SHAPE}}  | {{NOW_DJ30_SHAPE}}  | {{DJ30_SHAPE_NOTE}} |
| SP500 | {{MORN_SP500_SHAPE}} | {{NOW_SP500_SHAPE}} | {{SP500_SHAPE_NOTE}} |

### Hard-Stop-Bewegung
| Indikator | Morning | Jetzt | Trend |
|---|---|---|---|
| VIX | {{MORN_VIX}} | {{NOW_VIX}} | {{VIX_TREND}} |
| F&G | {{MORN_FG}}  | {{NOW_FG}}  | {{FG_TREND}}  |
| PCR | {{MORN_PCR}} | {{NOW_PCR}} | {{PCR_TREND}} |
| Bonds 10Y | {{MORN_BONDS}} | {{NOW_BONDS}} | {{BONDS_TREND}} |

### Trade-Freigabe-Wechsel
- **Morning:** {{MORN_TRADE_FREIGABE}}
- **Jetzt:**   {{NOW_TRADE_FREIGABE}}
- **Veränderung:** {{FREIGABE_DELTA}}

══════════════════════════════════════════════
## 2. MARKT-ENTWICKLUNG 08:00 → 14:45
══════════════════════════════════════════════

**Was war heute schon im EU-Markt los?**

### POC-Migration (Session 0 Verlauf)
| Symbol | Morning POC | Aktuelle POC | Drift | Interpretation |
|---|---|---|---|---|
| GER40 | {{MORN_GER40_POC}} | {{NOW_GER40_POC}} | {{GER40_POC_DRIFT}} | {{GER40_POC_INTERP}} |
| DJ30  | {{MORN_DJ30_POC}}  | {{NOW_DJ30_POC}}  | {{DJ30_POC_DRIFT}}  | {{DJ30_POC_INTERP}}  |
| SP500 | {{MORN_SP500_POC}} | {{NOW_SP500_POC}} | {{SP500_POC_DRIFT}} | {{SP500_POC_INTERP}} |

### Value-Area-Migration
| Symbol | VAH-Drift | VAL-Drift | Range-Veränderung |
|---|---|---|---|
| GER40 | {{GER40_VAH_DRIFT}} | {{GER40_VAL_DRIFT}} | {{GER40_RANGE_DELTA}} |
| DJ30  | {{DJ30_VAH_DRIFT}}  | {{DJ30_VAL_DRIFT}}  | {{DJ30_RANGE_DELTA}}  |
| SP500 | {{SP500_VAH_DRIFT}} | {{SP500_VAL_DRIFT}} | {{SP500_RANGE_DELTA}} |

### Struktur-Indikatoren (S2-Schicht-Delta)
| Symbol | VWAP-Lage Morning → Jetzt | CVD-Delta heute | Efficiency Ratio |
|---|---|---|---|
| GER40 | {{GER40_VWAP_TREND}} | {{GER40_CVD_DELTA}} | {{GER40_ER_VALUE}} |
| DJ30  | {{DJ30_VWAP_TREND}}  | {{DJ30_CVD_DELTA}}  | {{DJ30_ER_VALUE}}  |
| SP500 | {{SP500_VWAP_TREND}} | {{SP500_CVD_DELTA}} | {{SP500_ER_VALUE}} |

### Markt-Lesart
> {{MARKT_LESART_EU_SESSION}}

══════════════════════════════════════════════
## 3. NEUE BIAS US-SESSION
══════════════════════════════════════════════

**Bias-Übersicht für die US-Session (15:30–22:00):**

| Symbol | Profil | Bias | Konfidenz | Freigabe |
|---|---|---|---|---|
| GER40 | {{NOW_GER40_SHAPE}} ({{NOW_GER40_POS}}) | {{NOW_GER40_BIAS}} | {{NOW_GER40_KONFIDENZ}} | {{NOW_GER40_FREIGABE}} |
| DJ30  | {{NOW_DJ30_SHAPE}} ({{NOW_DJ30_POS}})   | {{NOW_DJ30_BIAS}}  | {{NOW_DJ30_KONFIDENZ}}  | {{NOW_DJ30_FREIGABE}}  |
| SP500 | {{NOW_SP500_SHAPE}} ({{NOW_SP500_POS}}) | {{NOW_SP500_BIAS}} | {{NOW_SP500_KONFIDENZ}} | {{NOW_SP500_FREIGABE}} |

**Profil-Erklärung (Glossar):**
- **b-Shape** — Käufer haben nachgelassen, Verkäufer kontrollieren oberhalb POC
- **P-Shape** — Verkäufer-Schwäche, Käufer kontrollieren unterhalb POC
- **D-Shape** — Balanciert, Auktion in Range
- **B-Shape** — Doppelte Verteilung, Regime-Wechsel möglich
- **Trend Day** — Direktionaler Lauf ohne Konsolidierung
- **pos-Wert** — POC-Position in Value Area (0.0=VAL, 1.0=VAH)

══════════════════════════════════════════════
## 4. PRE-OPEN-CHECK + US-EVENTS
══════════════════════════════════════════════

### Levels für US-Open 15:30

#### GER40
| Trigger | Level | Lese-Logik US-Open |
|---|---|---|
| POC | {{NOW_GER40_POC}} | Halten = Bias bestätigt |
| VAH | {{NOW_GER40_VAH}} | Bruch oben = Extension |
| VAL | {{NOW_GER40_VAL}} | Bruch unten = Trend-Wechsel |
| VWAP 30M | {{NOW_GER40_VWAP}} | Über = bullish |
| 200-SMA | {{NOW_GER40_200SMA}} | Trend-Filter HTF |

#### DJ30
| Trigger | Level | Lese-Logik US-Open |
|---|---|---|
| POC | {{NOW_DJ30_POC}} | Halten = Bias bestätigt |
| VAH | {{NOW_DJ30_VAH}} | Bruch oben = Entry-Trigger |
| VAL | {{NOW_DJ30_VAL}} | Bruch unten = Entry-Trigger |
| VWAP 30M | {{NOW_DJ30_VWAP}} | Über = bullish |
| 200-SMA | {{NOW_DJ30_200SMA}} | Trend-Filter HTF |

#### SP500
| Trigger | Level | Lese-Logik US-Open |
|---|---|---|
| POC | {{NOW_SP500_POC}} | Halten = Bias bestätigt |
| VAH | {{NOW_SP500_VAH}} | Bruch oben = Continuation |
| VAL | {{NOW_SP500_VAL}} | Bruch unten = Schwäche-Signal |
| VWAP 30M | {{NOW_SP500_VWAP}} | Über = bullish |
| 200-SMA | {{NOW_SP500_200SMA}} | Trend-Filter HTF |

### US-Session Events (15:30–22:00)
{{US_SESSION_EVENTS}}

### Volatilitäts-Fenster US-Session
- 15:30–15:45 (US-Open Spike)
- {{ADDITIONAL_US_VOLATILITY_WINDOWS}}

══════════════════════════════════════════════
## 5. SCHLUSSIMPULS US-SESSION
══════════════════════════════════════════════

**Strategie US-Session:** {{US_STRATEGY_LABEL}}
**Max-Risk:** {{US_MAX_RISK}}% · **Max-Trades:** {{US_MAX_TRADES}}
**Trade-Freigabe:** {{US_TRADE_FREIGABE}}

**Begründung:**
> {{US_SCHLUSSIMPULS_BEGRUENDUNG}}

**Top-Warnung US-Session:**
> {{US_TOP_WARNING}}

**Was tun zwischen 15:30 und 22:00:**
{{US_SESSION_PLAN}}

---
*Auto-generated by KOORDINATOR (USUpdate-Branch) · Source: agents/shared/state.json + state.json.morning-{{MORNING_DATE}}*
