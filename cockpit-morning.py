#!/usr/bin/env python3
"""
Cockpit-Trader: Vollautomatisches Morning Briefing
SP500 & Dow Jones KASSA – Market Profile, VWAP, Bias-Ampel
Symbole: ^GSPC (S&P 500 Cash), ^DJI (Dow Jones Cash)
GitHub Actions: laeuft automatisch Mo-Fr 07:00 Uhr
iPhone URL: https://chrisaibizz.github.io/cockpit-trader/
"""

import json, os, sys, traceback, math, logging, shutil
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf


class SafeJSONEncoder(json.JSONEncoder):
    """Converts float NaN/Inf to null so output is valid JSON."""
    def iterencode(self, o, _one_shot=False):
        return super().iterencode(self._fix_nan(o), _one_shot)

    def _fix_nan(self, obj):
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        try:
            if isinstance(obj, np.floating) and (np.isnan(obj) or np.isinf(obj)):
                return None
            if isinstance(obj, np.integer):
                return int(obj)
        except Exception:
            pass
        if isinstance(obj, dict):
            return {k: self._fix_nan(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._fix_nan(v) for v in obj]
        return obj


_log_path = os.path.join(os.path.dirname(__file__), 'logs', 'cockpit-morning.log')
os.makedirs(os.path.dirname(_log_path), exist_ok=True)
logging.basicConfig(
    filename=_log_path,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.info("cockpit-morning.py gestartet")
print(">>> Script gestartet")

try:
    import finnhub
    FINNHUB_KEY = os.environ.get("FINNHUB_API_KEY", "")
    fh = finnhub.Client(api_key=FINNHUB_KEY) if FINNHUB_KEY else None
    print(f">>> Finnhub: {'OK (Key vorhanden)' if FINNHUB_KEY else 'Kein Key - Kalender deaktiviert'}")
except ImportError:
    fh = None
    print(">>> Finnhub nicht installiert - Kalender deaktiviert")

try:
    from fredapi import Fred
    FRED_KEY = os.environ.get("FRED_API_KEY", "")
    fred = Fred(api_key=FRED_KEY) if FRED_KEY else None
    print(f">>> FRED: {'OK (Key vorhanden)' if FRED_KEY else 'Kein Key - FRED deaktiviert'}")
except ImportError:
    fred = None
    print(">>> fredapi nicht installiert - pip install fredapi")

# ============================================================
# 1. DATEN HOLEN
# ============================================================

def fetch_intraday(ticker, period="5d", interval="30m"):
    print(f"    fetch_intraday({ticker})...")
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval)
        print(f"    -> {len(df)} Zeilen")
        return df
    except Exception as e:
        print(f"    -> FEHLER: {e}")
        traceback.print_exc()
        import pandas as pd
        return pd.DataFrame()

def fetch_quote(ticker):
    print(f"    fetch_quote({ticker})...")
    try:
        h = yf.Ticker(ticker).history(period="2d")
        if len(h) < 1:
            print(f"    -> Keine Daten")
            return None
        last = h.iloc[-1]
        prev = h.iloc[-2] if len(h) > 1 else h.iloc[-1]
        p, pc = float(last["Close"]), float(prev["Close"])
        result = {
            "price":      round(p, 2),
            "change":     round(p - pc, 2),
            "change_pct": round((p - pc) / pc * 100, 2),
            "high":       round(float(last["High"]), 2),
            "low":        round(float(last["Low"]),  2),
            "open":       round(float(last["Open"]), 2),
            "prev_close": round(pc, 2),
        }
        print(f"    -> {result['price']}")
        return result
    except Exception as e:
        print(f"    -> FEHLER: {e}")
        traceback.print_exc()
        return None

def fetch_calendar():
    if not fh:
        print("    Kalender: kein Finnhub-Key")
        return []
    try:
        future_dates = [
            (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(7)
        ]
        all_events = []
        for date_str in future_dates:
            try:
                cal = fh.calendar_economic(date_str, date_str)
                events = [
                    {"time":     e.get("time", ""),
                     "event":    e.get("event", ""),
                     "country":  e.get("country", ""),
                     "impact":   e.get("impact", ""),
                     "estimate": e.get("estimate"),
                     "prior":    e.get("prior"),
                     "date":     date_str}
                    for e in cal.get("economicCalendar", [])
                    if e.get("impact") == "high"
                    and e.get("country", "").upper() in ("US", "DE")
                ]
                if events:
                    all_events.append({"date": date_str, "events": events})
            except Exception as e:
                print(f"    Kalender FEHLER fuer {date_str}: {e}")
                continue

        result = []
        for day in all_events[:2]:
            result.extend(day["events"])

        print(f"    Kalender: {len(result)} Events ueber {min(len(all_events), 2)} Tage")
        return result

    except Exception as e:
        print(f"    Kalender FEHLER: {e}")
        return []

def fetch_fred_data():
    """
    Holt makrooekonomische Daten von FRED:
      FEDFUNDS  - US Leitzins (monatlich)
      T10Y2Y    - Yield Curve Spread 10J-2J (taeglich)
      CPIAUCSL  - US CPI Inflation YoY (monatlich)
      UNRATE    - US Arbeitslosenquote (monatlich)
    """
    if not fred:
        print("    FRED: kein Key -- uebersprungen")
        return None
    try:
        from datetime import timedelta
        result = {}
        series_config = {
            "FEDFUNDS": {"name": "Fed Funds Rate",     "unit": "%"},
            "T10Y2Y":   {"name": "Yield Curve 10Y-2Y", "unit": "%"},
            "CPIAUCSL": {"name": "CPI Inflation YoY",  "unit": "% YoY"},
            "UNRATE":   {"name": "Arbeitslosenquote",  "unit": "%"},
        }
        for series_id, cfg in series_config.items():
            try:
                end   = datetime.now()
                start = end - timedelta(days=120)
                data  = fred.get_series(series_id, observation_start=start, observation_end=end)
                data  = data.dropna()
                if len(data) < 1:
                    continue
                current = round(float(data.iloc[-1]), 2)
                prev    = round(float(data.iloc[-2]), 2) if len(data) >= 2 else current
                # CPI: YoY berechnen
                if series_id == "CPIAUCSL" and len(data) >= 13:
                    current = round((float(data.iloc[-1]) / float(data.iloc[-13]) - 1) * 100, 2)
                    prev    = round((float(data.iloc[-2]) / float(data.iloc[-14]) - 1) * 100, 2) if len(data) >= 14 else current
                change = round(current - prev, 2)
                result[series_id] = {
                    "name":   cfg["name"],
                    "value":  current,
                    "prev":   prev,
                    "change": change,
                    "unit":   cfg["unit"],
                    "date":   str(data.index[-1].date()),
                }
                print(f"    FRED {series_id}: {current}{cfg['unit']} (prev {prev}, delta {change:+.2f})")
            except Exception as e:
                print(f"    FRED {series_id} FEHLER: {e}")
                continue
        print(f"    FRED: {len(result)}/4 Serien geladen")
        return result if result else None
    except Exception as e:
        print(f"    FRED FEHLER: {e}")
        return None

# ============================================================
# 2. MARKET PROFILE
# ============================================================

TV_SYMBOL_MAP = {
    "^GSPC":  "Vantage:SP500",
    "^DJI":   "Vantage:DJ30",
    "^GDAXI": "Vantage:GER40",
}

def detect_shape_from_tpo(sess, poc, vah, val):
    from collections import Counter
    all_lines = [l for l in sess if l["ci"] in (0, 1, 2)]
    if len(all_lines) < 5:
        return {"name": "n/a", "description": "Zu wenig TPO-Daten"}

    raw_prices = sorted(set(round(l["y1"], 2) for l in all_lines))
    diffs = [raw_prices[i+1] - raw_prices[i]
             for i in range(len(raw_prices)-1)
             if raw_prices[i+1] - raw_prices[i] > 0.001]
    if not diffs:
        return {"name": "n/a", "description": "Preis-Aufloesung nicht bestimmbar"}
    raw_tick = min(diffs)
    if raw_tick < 0.1:
        tick = 0.01
    elif raw_tick < 0.5:
        tick = 0.25
    elif raw_tick < 2.0:
        tick = 1.0
    else:
        tick = max(1.0, round(raw_tick))

    price_counts = Counter()
    for l in all_lines:
        lvl = round(round(l["y1"] / tick) * tick, 4)
        price_counts[lvl] += 1

    sorted_levels = sorted(price_counts.keys())
    tpo_vals = [price_counts[p] for p in sorted_levels]
    n = len(sorted_levels)
    if n < 3:
        return {"name": "n/a", "description": "Zu wenig Preis-Level"}

    total_tpo = sum(tpo_vals)
    third = max(1, n // 3)
    upper_tpo  = sum(tpo_vals[2*third:])
    middle_tpo = sum(tpo_vals[third:2*third])
    lower_tpo  = sum(tpo_vals[:third])

    price_range = sorted_levels[-1] - sorted_levels[0]
    if price_range == 0:
        return {"name": "Normal Day", "description": "Keine Range – kein Muster erkennbar"}

    poc_pos  = (poc - sorted_levels[0]) / price_range
    va_size  = vah - val
    va_ratio = va_size / price_range if price_range > 0 else 0

    if poc_pos > 0.80:
        return {"name": "Trend Day (Up)",
                "description": "POC am oberen Extrem – starker Aufwaerts-Trend, Continuation-Bias"}
    if poc_pos < 0.20:
        return {"name": "Trend Day (Down)",
                "description": "POC am unteren Extrem – starker Abwaerts-Trend, Continuation-Bias"}
    if upper_tpo > 0.50 * total_tpo and lower_tpo < 0.20 * total_tpo:
        return {"name": "P-Shape",
                "description": "Distribution oben, Buying Tail unten – Short Covering. Oft bearish reversal."}
    if lower_tpo > 0.50 * total_tpo and upper_tpo < 0.20 * total_tpo:
        return {"name": "b-Shape",
                "description": "Distribution unten, Selling Tail oben – Long Liquidation. Oft bullish reversal."}
    peaks = [i for i in range(1, n-1)
             if tpo_vals[i] > tpo_vals[i-1] and tpo_vals[i] > tpo_vals[i+1]
             and tpo_vals[i] > 0.25 * max(tpo_vals)]
    if len(peaks) >= 2 and abs(peaks[0] - peaks[-1]) > third:
        return {"name": "Double Distribution",
                "description": "Zwei Value Areas mit LVN dazwischen – Trend-Continuation wahrscheinlich"}
    if va_ratio > 0.85:
        return {"name": "Non-Trend Day",
                "description": "Breite VA – Range-Bound, kein klarer Richtungs-Bias"}
    if middle_tpo > 0.40 * total_tpo and 0.30 < poc_pos < 0.70:
        return {"name": "Normal Day",
                "description": "Ausbalanciert, POC zentral – Range-Trading um POC wahrscheinlich"}
    if poc_pos > 0.55:
        return {"name": "Normal Variation (Up)",
                "description": "Leicht bullischer Bias – Abwarten auf Breakout aus VA"}
    if poc_pos < 0.45:
        return {"name": "Normal Variation (Down)",
                "description": "Leicht bearischer Bias – Abwarten auf Breakdown aus VA"}
    return {"name": "Normal Variation",
            "description": "Ausgewogen ohne klare Richtung – Range-Handel"}


def get_tv_data(ticker, timeframe="30"):
    tv_symbol = TV_SYMBOL_MAP.get(ticker)
    if not tv_symbol:
        return None, None, None
    try:
        import requests as _req
        import websocket as _ws
        import time

        resp = _req.get("http://localhost:9222/json", timeout=2)
        targets = resp.json()
        tv_target = next((t for t in targets if "webSocketDebuggerUrl" in t), None)
        if not tv_target:
            return None, None, None

        ws = _ws.create_connection(tv_target["webSocketDebuggerUrl"], timeout=10)
        _msg_id = [0]

        def _eval(js):
            _msg_id[0] += 1
            mid = _msg_id[0]
            ws.send(json.dumps({
                "id": mid, "method": "Runtime.evaluate",
                "params": {"expression": js, "returnByValue": True}
            }))
            for _ in range(30):
                r = json.loads(ws.recv())
                if r.get("id") == mid:
                    return r.get("result", {}).get("result", {}).get("value")
            return None

        _eval(f"(function(){{var c=window.TradingViewApi._activeChartWidgetWV.value();c.setSymbol({json.dumps(tv_symbol)},function(){{}});}})()")
        time.sleep(2.5)
        _eval(f"(function(){{var c=window.TradingViewApi._activeChartWidgetWV.value();c.setResolution({json.dumps(timeframe)},function(){{}});}})()")
        time.sleep(1.5)

        mp_items = _eval("""
            (function() {
              var chart = window.TradingViewApi._activeChartWidgetWV.value()._chartWidget;
              var sources = chart.model().model().dataSources();
              for (var si = 0; si < sources.length; si++) {
                var s = sources[si];
                if (!s.metaInfo) continue;
                try {
                  var name = s.metaInfo().description || s.metaInfo().shortDescription || '';
                  if (name.indexOf('Market Profile') === -1) continue;
                  var coll = s._graphics._primitivesCollection.dwglines.get('lines').get(false);
                  if (!coll || !coll._primitivesDataById) continue;
                  var out = [];
                  coll._primitivesDataById.forEach(function(v, id) {
                    if (v.y1 === v.y2) out.push({y1: v.y1, x1: v.x1, ci: v.ci});
                  });
                  return out;
                } catch(e) {}
              }
              return [];
            })()
        """)

        cvd_items = _eval("""
            (function() {
              var chart = window.TradingViewApi._activeChartWidgetWV.value()._chartWidget;
              var sources = chart.model().model().dataSources();
              for (var si = 0; si < sources.length; si++) {
                var s = sources[si];
                if (!s.metaInfo) continue;
                try {
                  var name = s.metaInfo().description || s.metaInfo().shortDescription || '';
                  if (name.indexOf('Cumulative Delta') === -1) continue;
                  var dwv = s.dataWindowView();
                  if (!dwv) continue;
                  var items = dwv.items();
                  if (!items) continue;
                  var current = null;
                  for (var i = 0; i < items.length; i++) {
                    var item = items[i];
                    if (item._title && item._value && item._value !== '\u2205') {
                      var v = parseFloat(item._value.replace(/[^0-9.\-]/g, ''));
                      if (!isNaN(v)) { current = v; break; }
                    }
                  }
                  return current !== null ? {current: current} : null;
                } catch(e) {}
              }
              return null;
            })()
        """)

        vwap_val = _eval("""
            (function() {
              var chart = window.TradingViewApi._activeChartWidgetWV.value()._chartWidget;
              var sources = chart.model().model().dataSources();
              for (var si = 0; si < sources.length; si++) {
                var s = sources[si];
                if (!s.metaInfo) continue;
                try {
                  var name = (s.metaInfo().description || s.metaInfo().shortDescription || '').toUpperCase();
                  if (name.indexOf('VWAP') === -1) continue;
                  var dwv = s.dataWindowView();
                  if (!dwv) continue;
                  var items = dwv.items();
                  if (!items) continue;
                  for (var i = 0; i < items.length; i++) {
                    var item = items[i];
                    if (item._value && item._value !== '\u2205') {
                      var v = parseFloat(item._value.replace(/[^0-9.\-]/g, ''));
                      if (!isNaN(v) && v > 10) return v;
                    }
                  }
                } catch(e) {}
              }
              return null;
            })()
        """)

        tv_price_raw = _eval("""
            (function() {
              try {
                var chart = window.TradingViewApi._activeChartWidgetWV.value()._chartWidget;
                var ms = chart.model().model().mainSeries();
                if (ms.dataWindowView) {
                  var dwv = ms.dataWindowView();
                  if (dwv && dwv.items) {
                    var items = dwv.items();
                    for (var i = 0; i < (items||[]).length; i++) {
                      var it = items[i];
                      var title = (it._title||'').toUpperCase();
                      if ((title==='C'||title==='CLOSE'||title==='LAST') && it._value && it._value!=='\u2205') {
                        var v = parseFloat(it._value.replace(/[^0-9.\-]/g,''));
                        if (!isNaN(v) && v > 10) return v;
                      }
                    }
                    for (var i = 0; i < (items||[]).length; i++) {
                      var it = items[i];
                      if (it._value && it._value!=='\u2205') {
                        var v = parseFloat(it._value.replace(/[^0-9.\-]/g,''));
                        if (!isNaN(v) && v > 10) return v;
                      }
                    }
                  }
                }
                var bars = ms.data().bars();
                var n = bars.size();
                if (n > 0) {
                  var last = bars.get(n-1);
                  if (last && last.value) {
                    for (var idx = 4; idx >= 1; idx--) {
                      if (typeof last.value[idx]==='number' && last.value[idx]>10) return last.value[idx];
                    }
                  }
                }
                return null;
              } catch(e) { return null; }
            })()
        """)

        ws.close()

        mp = None
        if mp_items:
            x1_vals = sorted(set(l["x1"] for l in mp_items))
            session_starts = [x1_vals[0]]
            for i in range(1, len(x1_vals)):
                if x1_vals[i] - x1_vals[i-1] > 3:
                    session_starts.append(x1_vals[i])
            last_start = session_starts[-1]
            sess = [l for l in mp_items if l["x1"] >= last_start]
            poc_lines = [l for l in sess if l["ci"] == 0]
            va_lines  = [l for l in sess if l["ci"] == 1]
            if poc_lines and va_lines:
                poc = round(poc_lines[0]["y1"], 2)
                vah = round(max(l["y1"] for l in va_lines), 2)
                val = round(min(l["y1"] for l in va_lines), 2)
                shape = detect_shape_from_tpo(sess, poc, vah, val)
                vwap_rounded = round(float(vwap_val), 2) if (vwap_val is not None and str(vwap_val).lower() != "nan") else None
                print(f"    MP (TradingView): POC={poc} VAH={vah} VAL={val} VWAP={vwap_rounded} Shape={shape['name']}")
                mp = {"poc": poc, "vah": vah, "val": val, "vwap": vwap_rounded,
                      "day_high": vah, "day_low": val,
                      "shape": shape,
                      "volume_profile": [], "source": "tradingview"}
            else:
                print("    TV CDP: MP – POC oder VA Lines fehlen")

        cvd = None
        if cvd_items and cvd_items.get("current") is not None:
            val_cvd = cvd_items["current"]
            direction = "bullish" if val_cvd > 0 else "bearish"
            print(f"    CVD (TradingView): {val_cvd:+.0f} ({direction})")
            cvd = {"value": val_cvd, "direction": direction}

        tv_price = None
        if tv_price_raw is not None:
            try:
                tv_price = round(float(tv_price_raw), 2)
                print(f"    Kurs (TradingView live): {tv_price}")
            except (TypeError, ValueError):
                pass

        return mp, cvd, tv_price

    except Exception as e:
        print(f"    TV CDP nicht verfuegbar ({type(e).__name__}): {e}")
        return None, None, None


def compute_market_profile(df_day):
    if df_day.empty:
        print("    MP: DataFrame leer")
        return None
    try:
        prices  = df_day[["Open","High","Low","Close"]].values
        volumes = df_day["Volume"].values
        day_high = float(df_day["High"].max())
        day_low  = float(df_day["Low"].min())
        if day_high == day_low:
            print("    MP: Range = 0")
            return None

        num_bins    = 40
        bin_edges   = np.linspace(day_low, day_high, num_bins + 1)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        vol_profile = np.zeros(num_bins)

        for i in range(len(df_day)):
            bl = float(prices[i][2])
            bh = float(prices[i][1])
            bv = float(volumes[i]) if volumes[i] > 0 else 1
            for j in range(num_bins):
                if bin_edges[j+1] >= bl and bin_edges[j] <= bh:
                    vol_profile[j] += bv

        poc_idx = np.argmax(vol_profile)
        poc     = round(float(bin_centers[poc_idx]), 2)

        total_vol      = vol_profile.sum()
        va_vol         = vol_profile[poc_idx]
        lo_idx, hi_idx = poc_idx, poc_idx
        while va_vol < total_vol * 0.70:
            add_lo = vol_profile[lo_idx-1] if lo_idx > 0 else 0
            add_hi = vol_profile[hi_idx+1] if hi_idx < num_bins-1 else 0
            if add_hi >= add_lo and hi_idx < num_bins-1:
                hi_idx += 1; va_vol += add_hi
            elif lo_idx > 0:
                lo_idx -= 1; va_vol += add_lo
            else:
                break

        vah  = round(float(bin_edges[hi_idx+1]), 2)
        val  = round(float(bin_edges[lo_idx]),   2)
        tp   = (df_day["High"] + df_day["Low"] + df_day["Close"]) / 3
        vwap = round(float((tp * df_day["Volume"]).sum() / df_day["Volume"].sum()), 2)

        vp_list = [
            {"price":  round(float(bin_centers[i]), 2),
             "volume": round(float(vol_profile[i]), 0)}
            for i in range(num_bins)
        ]

        shape = detect_mp_shape(vol_profile, poc_idx, num_bins, df_day)
        print(f"    MP: POC={poc} VAH={vah} VAL={val} VWAP={vwap} Shape={shape['name']}")

        return {
            "poc": poc, "vah": vah, "val": val, "vwap": vwap,
            "day_high": round(day_high, 2), "day_low": round(day_low, 2),
            "shape": shape, "volume_profile": vp_list,
        }
    except Exception as e:
        print(f"    MP FEHLER: {e}")
        traceback.print_exc()
        return None

def detect_mp_shape(vol_profile, poc_idx, num_bins, df_day):
    third  = num_bins // 3
    upper  = vol_profile[2*third:].sum()
    middle = vol_profile[third:2*third].sum()
    lower  = vol_profile[:third].sum()
    total  = vol_profile.sum()
    op     = float(df_day.iloc[0]["Open"])
    cl     = float(df_day.iloc[-1]["Close"])
    rng    = float(df_day["High"].max() - df_day["Low"].min())
    if rng == 0:
        return {"name": "Normal", "description": "Balanced day"}
    move_pct = abs(cl - op) / rng

    if move_pct > 0.6 and (poc_idx > 2*third or poc_idx < third):
        d = "Up" if cl > op else "Down"
        return {"name": f"Trend Day ({d})",
                "description": "Starke direktionale Bewegung, Continuation wahrscheinlich"}
    if upper > 0.5*total and lower < 0.2*total:
        return {"name": "P-Shape",
                "description": "Short Covering Rally. Oft bearish reversal am Folgetag."}
    if lower > 0.5*total and upper < 0.2*total:
        return {"name": "b-Shape",
                "description": "Long Liquidation. Oft bullish reversal am Folgetag."}
    peaks = []
    for i in range(1, num_bins-1):
        if vol_profile[i] > vol_profile[i-1] and vol_profile[i] > vol_profile[i+1]:
            if vol_profile[i] > 0.3 * vol_profile.max():
                peaks.append(i)
    if len(peaks) >= 2 and abs(peaks[0] - peaks[-1]) > third:
        return {"name": "Double Distribution",
                "description": "Zwei Value Areas – oft Trend-Folgetag."}
    if middle > 0.4*total:
        return {"name": "Normal Day",
                "description": "Ausbalanciert – Range-Trading um POC."}
    return {"name": "Normal Variation",
            "description": "Leichte Richtung – Abwarten auf Breakout aus VA."}

# ============================================================
# 3. BIAS-AMPEL MIT CONFLUENCE-SCORE
# ============================================================
#
# Confluence-Score zeigt wie viele der messbaren Kriterien in dieselbe
# Richtung zeigen — analog zum 7-Schritte-Morgen-Prozess.
#
# Jedes Signal hat:
#   label     – Text fuer das Dashboard
#   score     – Gewichtung: +2 stark bullisch, +1 leicht bullisch,
#                           0 neutral, -1 leicht bearisch, -2 stark bearisch
#   direction – "bullish" / "bearish" / "neutral"
#   category  – Welcher der 7 Schritte (fuer Confluence-Zaehlung)
#   auto      – True = automatisch berechnet, False = manuell zu pruefen
#
# Confluence:
#   Zaehlt nur Kategorien mit auto=True.
#   Gibt an: X von Y automatisch messbaren Kriterien zeigen in Bias-Richtung.
#   Manuelle Kriterien (OTF, Gap, Session Expectation) werden separat
#   als "manuell_offen" gelistet – sie erinnern den Trader was noch zu pruefen ist.

def compute_bias(mp, price, context, cvd=None, fred_data=None):
    """
    Berechnet Bias-Ampel mit Confluence-Score.

    FIX #1: mp und price werden zuerst auf None geprueft –
            kein AttributeError mehr wenn MP nicht geladen werden konnte.
    FIX #2: Dummy-Signale (Daily OTF / Gap / Session Expectation) werden
            nicht mehr in den Score eingerechnet, sondern als offene
            manuelle Checks zurueckgegeben.
    NEU:    confluence_score = Anzahl auto-Signale die in Bias-Richtung zeigen
            confluence_total = Gesamtzahl auto-messbarer Signale
            confluence_pct   = Prozentsatz (fuer Ampel-Faerbung)
    """

    # ── FIX #1: Fruehzeitiger Abbruch wenn keine Kerndaten vorhanden ──────────
    if mp is None or price is None:
        print("    Bias: Keine MP/Preis-Daten – NEUTRAL (kein Score)")
        return {
            "score": 0, "bias": "NEUTRAL", "color": "yellow",
            "signals": [],
            "confluence_score": 0,
            "confluence_total": 0,
            "confluence_pct":   0,
            "confluence_label": "0/0 – Keine Daten",
            "manual_checks":    ["Daily OTF Check", "Gap Analysis", "Session Expectation"],
        }

    # VWAP-Fallback: wenn kein VWAP vorhanden, POC verwenden
    if mp.get("vwap") is None or str(mp.get("vwap")).lower() == "nan":
        mp["vwap"] = mp.get("poc", price)

    signals = []
    vwap = mp["vwap"]
    vah  = mp["vah"]
    val  = mp["val"]
    poc  = mp["poc"]

    # ── SCHRITT 1: Preis vs. VWAP (Gewicht 2) ──────────────────────────────────
    if price > vwap:
        signals.append({"label":     f"Preis > VWAP ({price:.0f} > {vwap:.0f})",
                         "score":     2, "direction": "bullish",
                         "category":  "vwap", "auto": True})
    else:
        signals.append({"label":     f"Preis < VWAP ({price:.0f} < {vwap:.0f})",
                         "score":    -2, "direction": "bearish",
                         "category":  "vwap", "auto": True})

    # ── SCHRITT 2: Preis vs. Value Area ────────────────────────────────────────
    if price > vah:
        signals.append({"label":     f"Ueber VAH – Breakout ({price:.0f} > {vah:.0f})",
                         "score":     2, "direction": "bullish",
                         "category":  "value_area", "auto": True})
    elif price < val:
        signals.append({"label":     f"Unter VAL – Breakdown ({price:.0f} < {val:.0f})",
                         "score":    -2, "direction": "bearish",
                         "category":  "value_area", "auto": True})
    else:
        signals.append({"label":     f"In Value Area ({val:.0f} – {vah:.0f})",
                         "score":     0, "direction": "neutral",
                         "category":  "value_area", "auto": True})

    # ── SCHRITT 3: Preis vs. POC ───────────────────────────────────────────────
    if price > poc:
        signals.append({"label":     f"Preis > POC ({price:.0f} > {poc:.0f})",
                         "score":     1, "direction": "bullish",
                         "category":  "poc", "auto": True})
    else:
        signals.append({"label":     f"Preis < POC ({price:.0f} < {poc:.0f})",
                         "score":    -1, "direction": "bearish",
                         "category":  "poc", "auto": True})

    # ── SCHRITT 4: MP Shape ────────────────────────────────────────────────────
    sn = mp["shape"]["name"]
    if   "Trend Day (Up)"    in sn: shape_sc, shape_dir =  2, "bullish"
    elif "Trend Day (Down)"  in sn: shape_sc, shape_dir = -2, "bearish"
    elif "b-Shape"           in sn: shape_sc, shape_dir =  1, "bullish"
    elif "P-Shape"           in sn: shape_sc, shape_dir = -1, "bearish"
    elif "Normal Variation (Up)"   in sn: shape_sc, shape_dir =  1, "bullish"
    elif "Normal Variation (Down)" in sn: shape_sc, shape_dir = -1, "bearish"
    else:                           shape_sc, shape_dir =  0, "neutral"
    signals.append({"label":     f"Shape: {sn}",
                     "score":     shape_sc, "direction": shape_dir,
                     "category":  "shape", "auto": True})

    # ── SCHRITT 5: Overnight Inventory (Preis-Position in Value Area) ──────────
    mid = (vah + val) / 2
    if price > mid:
        signals.append({"label":     "Overnight Inventory: Long (Preis > VA-Mitte)",
                         "score":     1, "direction": "bullish",
                         "category":  "inventory", "auto": True})
    else:
        signals.append({"label":     "Overnight Inventory: Short (Preis < VA-Mitte)",
                         "score":    -1, "direction": "bearish",
                         "category":  "inventory", "auto": True})

    # ── CVD: Kauf-/Verkaufsdruck ───────────────────────────────────────────────
    if cvd and cvd.get("value") is not None:
        v = cvd["value"]
        if v > 0:
            signals.append({"label":     f"CVD positiv ({v:+.0f}) – Kaufdruck",
                             "score":     1, "direction": "bullish",
                             "category":  "cvd", "auto": True})
        else:
            signals.append({"label":     f"CVD negativ ({v:+.0f}) – Verkaufsdruck",
                             "score":    -1, "direction": "bearish",
                             "category":  "cvd", "auto": True})
        # Divergenz: Preis in VA aber CVD extrem
        if val <= price <= vah:
            if v < -50000:
                signals.append({"label":    "CVD-Divergenz: Preis in VA, starker Verkaufsdruck",
                                 "score":   -2, "direction": "bearish",
                                 "category": "cvd_divergenz", "auto": True})
            elif v > 50000:
                signals.append({"label":    "CVD-Divergenz: Preis in VA, starker Kaufdruck",
                                 "score":    2, "direction": "bullish",
                                 "category": "cvd_divergenz", "auto": True})

    # ── Context: VIX ──────────────────────────────────────────────────────────
    vix = context.get("VIX",   {}) or {}
    dxy = context.get("DXY",   {}) or {}
    y10 = context.get("US10Y", {}) or {}

    if vix.get("price"):
        v = vix["price"]
        if   v < 15: signals.append({"label": f"VIX {v} – Low Vol",    "score":  2, "direction": "bullish", "category": "vix", "auto": True})
        elif v < 20: signals.append({"label": f"VIX {v} – Normal",     "score":  1, "direction": "bullish", "category": "vix", "auto": True})
        elif v < 25: signals.append({"label": f"VIX {v} – Elevated",   "score": -1, "direction": "bearish", "category": "vix", "auto": True})
        else:        signals.append({"label": f"VIX {v} – High Fear",  "score": -2, "direction": "bearish", "category": "vix", "auto": True})

    if vix.get("change_pct"):
        cp = vix["change_pct"]
        if   cp < -3: signals.append({"label": "VIX faellt stark",    "score":  1, "direction": "bullish", "category": "vix_chg", "auto": True})
        elif cp >  3: signals.append({"label": "VIX steigt stark",    "score": -1, "direction": "bearish", "category": "vix_chg", "auto": True})
        # VIX stabil wird NICHT mehr als neutrales Gewicht eingetragen –
        # ein nicht-Ereignis soll den Score nicht verwaessern.

    if dxy.get("change_pct"):
        cp  = dxy["change_pct"]
        dpx = dxy.get("price")
        dpy = f" ({dpx:.2f})" if dpx else ""
        if   cp < -0.3: signals.append({"label": f"Dollar schwaecher{dpy}", "score":  1, "direction": "bullish", "category": "dxy", "auto": True})
        elif cp >  0.3: signals.append({"label": f"Dollar staerker{dpy}",  "score": -1, "direction": "bearish", "category": "dxy", "auto": True})

    if y10.get("change_pct"):
        cp  = y10["change_pct"]
        ypx = y10.get("price")
        ypy = f" ({ypx:.2f}%)" if ypx else ""
        if   cp >  2: signals.append({"label": f"Yields steigen stark{ypy}", "score": -1, "direction": "bearish", "category": "yields", "auto": True})
        elif cp < -2: signals.append({"label": f"Yields fallen stark{ypy}",  "score":  1, "direction": "bullish", "category": "yields", "auto": True})

    # ── FRED: Makrooekonomische Signale ─────────────────────────────────────────
    if fred_data:
        # Fed Funds Rate
        ff = fred_data.get("FEDFUNDS")
        if ff and ff.get("value") is not None:
            v, p = ff["value"], ff["prev"]
            if   v > 5.0: signals.append({"label": f"Fed Funds {v}% — restriktiv",         "score": -2, "direction": "bearish", "category": "fred_fedfunds", "auto": True})
            elif v > 4.0: signals.append({"label": f"Fed Funds {v}% — erhoeht",             "score": -1, "direction": "bearish", "category": "fred_fedfunds", "auto": True})
            elif v < 2.0: signals.append({"label": f"Fed Funds {v}% — akkommodativ",        "score":  1, "direction": "bullish", "category": "fred_fedfunds", "auto": True})
            elif v < p:   signals.append({"label": f"Fed Funds sinkend ({v}%)",             "score":  1, "direction": "bullish", "category": "fred_fedfunds", "auto": True})
            elif v > p:   signals.append({"label": f"Fed Funds steigend ({v}%)",            "score": -1, "direction": "bearish", "category": "fred_fedfunds", "auto": True})

        # Yield Curve
        yc = fred_data.get("T10Y2Y")
        if yc and yc.get("value") is not None:
            v, p = yc["value"], yc["prev"]
            if   v < -0.5: signals.append({"label": f"Yield Curve stark invertiert ({v}%)", "score": -2, "direction": "bearish", "category": "fred_yieldcurve", "auto": True})
            elif v < 0:    signals.append({"label": f"Yield Curve invertiert ({v}%)",       "score": -1, "direction": "bearish", "category": "fred_yieldcurve", "auto": True})
            elif v > 0.5:  signals.append({"label": f"Yield Curve positiv ({v}%)",          "score":  1, "direction": "bullish", "category": "fred_yieldcurve", "auto": True})
            elif v > p:    signals.append({"label": f"Yield Curve steilt auf ({v}%)",       "score":  1, "direction": "bullish", "category": "fred_yieldcurve", "auto": True})

        # CPI
        cpi = fred_data.get("CPIAUCSL")
        if cpi and cpi.get("value") is not None:
            v, p = cpi["value"], cpi["prev"]
            if   v > 4.0: signals.append({"label": f"CPI {v}% — Fed unter Druck",          "score": -2, "direction": "bearish", "category": "fred_cpi", "auto": True})
            elif v > 3.0: signals.append({"label": f"CPI {v}% — erhoeht",                  "score": -1, "direction": "bearish", "category": "fred_cpi", "auto": True})
            elif v < 2.5: signals.append({"label": f"CPI {v}% — nahe Ziel",                "score":  1, "direction": "bullish", "category": "fred_cpi", "auto": True})
            elif v < p:   signals.append({"label": f"CPI sinkend ({v}%)",                  "score":  1, "direction": "bullish", "category": "fred_cpi", "auto": True})
            elif v > p:   signals.append({"label": f"CPI steigend ({v}%)",                 "score": -1, "direction": "bearish", "category": "fred_cpi", "auto": True})

        # Arbeitslosenquote
        ur = fred_data.get("UNRATE")
        if ur and ur.get("value") is not None:
            v, p = ur["value"], ur["prev"]
            if   v < 4.0: signals.append({"label": f"Arbeitslosigkeit {v}% — stark",       "score":  1, "direction": "bullish", "category": "fred_unrate", "auto": True})
            elif v > 5.0: signals.append({"label": f"Arbeitslosigkeit {v}% — schwach",     "score": -1, "direction": "bearish", "category": "fred_unrate", "auto": True})
            elif v > p:   signals.append({"label": f"Arbeitslosigkeit steigt ({v}%)",      "score": -1, "direction": "bearish", "category": "fred_unrate", "auto": True})
            elif v < p:   signals.append({"label": f"Arbeitslosigkeit sinkt ({v}%)",       "score":  1, "direction": "bullish", "category": "fred_unrate", "auto": True})

    # ── FIX #2: Manuelle Checks NICHT im Score – separat zurueckgeben ─────────
    manual_checks = [
        "Daily OTF Check (4H/Daily Trend manuell pruefen)",
        "Gap Analysis (Gap vom Vortag open/close pruefen)",
        "Session Expectation (Makro-Kontext / News manuell bewerten)",
    ]

    # ── Score berechnen ───────────────────────────────────────────────────────
    auto_signals = [s for s in signals if s.get("auto")]
    total_weight = sum(abs(s["score"]) for s in auto_signals) or 1
    raw_score    = sum(s["score"] for s in auto_signals)
    sc           = round(raw_score / total_weight * 100)

    bias  = "BULLISH" if sc > 25 else "BEARISH" if sc < -25 else "NEUTRAL"
    color = "green"   if sc > 25 else "red"     if sc < -25 else "yellow"

    # ── Confluence-Score berechnen ────────────────────────────────────────────
    # Zaehlt wie viele auto-Kategorien klar in Bias-Richtung zeigen (score != 0)
    # Jede Kategorie zaehlt nur einmal (erstes Signal dieser Kategorie).
    seen_categories = {}
    for s in auto_signals:
        cat = s.get("category", "other")
        if cat not in seen_categories:
            seen_categories[cat] = s

    confluence_for  = 0  # zeigt IN Bias-Richtung
    confluence_against = 0
    confluence_neutral = 0
    confluence_total = len(seen_categories)

    for cat, s in seen_categories.items():
        if s["score"] == 0:
            confluence_neutral += 1
        elif (bias == "BULLISH" and s["score"] > 0) or \
             (bias == "BEARISH" and s["score"] < 0):
            confluence_for += 1
        else:
            confluence_against += 1

    # Bei NEUTRAL: zaehle bullische vs bearische Kategorien
    if bias == "NEUTRAL":
        bull_cats = sum(1 for s in seen_categories.values() if s["score"] > 0)
        bear_cats = sum(1 for s in seen_categories.values() if s["score"] < 0)
        confluence_label = (
            f"{bull_cats} bullisch / {bear_cats} bearisch / "
            f"{confluence_neutral} neutral von {confluence_total}"
        )
        confluence_pct = 50  # neutral = 50%
    else:
        confluence_pct = round(confluence_for / confluence_total * 100) if confluence_total > 0 else 0
        confluence_label = (
            f"{confluence_for}/{confluence_total} "
            f"({'bullisch' if bias == 'BULLISH' else 'bearisch'})"
        )

    print(f"    Bias: {bias} (Score={sc}) | Confluence: {confluence_label}")

    return {
        "score":             sc,
        "bias":              bias,
        "color":             color,
        "signals":           signals,
        # ── NEU: Confluence ──────────────────────────────────────────────────
        "confluence_score":  confluence_for,
        "confluence_against": confluence_against,
        "confluence_total":  confluence_total,
        "confluence_pct":    confluence_pct,
        "confluence_label":  confluence_label,
        # ── NEU: Manuelle Checks ─────────────────────────────────────────────
        "manual_checks":     manual_checks,
    }

# ============================================================
# 4. INSTRUMENT VERARBEITEN
# ============================================================

def process_instrument(ticker, name):
    print(f"\n--- {name} ({ticker}) ---")
    df = fetch_intraday(ticker)
    if df.empty:
        print(f"  FEHLER: Keine Intraday-Daten")
        return {"name": name, "ticker": ticker, "error": "Keine Daten"}

    df.index = (df.index.tz_localize(None) if df.index.tz is None
                else df.index.tz_convert(None))
    dates = df.index.date
    ud    = sorted(set(dates))
    print(f"  Verfuegbare Tage: {ud}")

    if len(ud) < 2:
        print(f"  FEHLER: Nur {len(ud)} Tag(e) verfuegbar")
        return {"name": name, "ticker": ticker, "error": "Nicht genug Handelstage"}

    last_full_day = ud[-2]
    print(f"  Letzter vollstaendiger Tag: {last_full_day}")
    df_day = df[dates == last_full_day]
    print(f"  Bars fuer MP: {len(df_day)}")

    mp_tv, cvd, tv_price = get_tv_data(ticker)
    mp = mp_tv or compute_market_profile(df_day)
    q  = fetch_quote(ticker)

    if tv_price is not None and q:
        prev_close       = q["prev_close"]
        q["price"]       = tv_price
        q["change"]      = round(tv_price - prev_close, 2)
        q["change_pct"]  = round((tv_price - prev_close) / prev_close * 100, 2)
        q["source"]      = "tradingview_live"
        print(f"    Kurs Dashboard (TV live): {tv_price} "
              f"({q['change']:+.2f} / {q['change_pct']:+.2f}% vs Vortag)")
    elif q:
        q["source"] = "yahoo_eod"

    return {
        "name": name, "ticker": ticker,
        "quote": q, "market_profile": mp,
        "cvd": cvd,
        "current_price": tv_price if tv_price else (q["price"] if q else None),
    }

# ============================================================
# 5. ORDER-GENERIERUNG
# ============================================================

def generate_order(inst, mp, price, bias_data, shape_name):
    if not mp or not price:
        return None
    poc  = mp.get("poc", 0)
    vah  = mp.get("vah", 0)
    val  = mp.get("val", 0)
    vwap = mp.get("vwap") or poc
    if vah == val:
        return None

    va_range = vah - val
    bias     = bias_data.get("bias", "NEUTRAL")
    score    = bias_data.get("score", 0)
    signals  = bias_data.get("signals", [])

    # Confluence-Qualitaet fuer P(Fill) / P(TP1) nutzen
    confluence_pct = bias_data.get("confluence_pct", 50)

    if bias == "NEUTRAL":
        below_val  = price < val
        above_vah  = price > vah
        below_vwap = price < vwap
        if score < 0 or below_val or (below_vwap and score <= 0):
            effective_bias = "BEARISH"
        elif score > 0 or above_vah or (not below_vwap and score >= 0):
            effective_bias = "BULLISH"
        else:
            effective_bias = "BEARISH"
        neutral_penalty = 15
    else:
        effective_bias  = bias
        neutral_penalty = 0

    direction_sigs = [s["label"] for s in signals
                      if (effective_bias == "BULLISH" and s["direction"] == "bullish")
                      or (effective_bias == "BEARISH" and s["direction"] == "bearish")]
    confluence = " + ".join(direction_sigs[:3]) or "MP-Levels + Score-Richtung"
    if bias == "NEUTRAL":
        confluence += " (NEUTRAL Bias – geringere Konfluenz)"

    vwap_pos = ("Preis ueber VWAP" if price > vwap
                else "Preis unter VWAP" if price < vwap
                else "Preis an VWAP")

    # P(Fill) und P(TP1) jetzt confluence_pct-basiert
    p_fill = max(20, min(75, int(confluence_pct * 0.75)) - neutral_penalty)
    p_tp1  = max(15, min(65, int(confluence_pct * 0.60)) - neutral_penalty)

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

    rr_raw = abs(tp1 - entry) / abs(sl - entry) if abs(sl - entry) > 0 else 0
    if rr_raw < 1.0:
        return None

    return {
        "type":               order_type,
        "entry":              str(entry),
        "sl":                 str(sl),
        "tp1":                str(tp1),
        "tp2":                str(tp2),
        "rr":                 str(round(rr_raw, 2)),
        "p_fill":             str(p_fill),
        "p_tp1":              str(p_tp1),
        "tf":                 "30M",
        "confluence":         confluence,
        "mp_shape_yesterday": shape_name,
        "mp_shape_forecast":  shape_name,
        "vwap_position":      vwap_pos,
    }

# ============================================================
# 6. JOURNAL
# ============================================================

def generate_journal_data(instruments_map, ctx, cal, script_dir):
    import subprocess
    today      = datetime.now().strftime("%Y-%m-%d")
    today_time = datetime.now().strftime("%H:%M")

    vix_price = (ctx.get("VIX") or {}).get("price", 0)
    vix_chg   = (ctx.get("VIX") or {}).get("change_pct", 0)
    dxy_chg   = (ctx.get("DXY") or {}).get("change_pct", 0)

    journal_instruments  = []
    all_orders_for_sheet = []
    warnings             = []

    if vix_price > 25:
        warnings.append(f"VIX {vix_price:.1f} – High Fear! Stops enger setzen")
    elif vix_price > 20:
        warnings.append(f"VIX {vix_price:.1f} – Elevated, Vorsicht bei Einstiegen")
    if abs(vix_chg) > 5:
        direction = "steigt" if vix_chg > 0 else "faellt"
        warnings.append(f"VIX {direction} stark ({vix_chg:+.1f}%) – Volatilitaet im Wandel")
    if abs(dxy_chg) > 0.5:
        direction = "steigt" if dxy_chg > 0 else "faellt"
        warnings.append(f"USD {direction} ({dxy_chg:+.2f}%) – Richtungsrisiko beachten")

    best_inst  = None
    best_score = -999

    for display_name, inst in instruments_map.items():
        mp         = inst.get("market_profile") or {}
        price      = inst.get("current_price")
        bias_data  = inst.get("bias") or {}
        cvd        = inst.get("cvd") or {}
        q          = inst.get("quote") or {}
        shape_name = (mp.get("shape") or {}).get("name", "n/a")
        bias_str   = bias_data.get("bias", "NEUTRAL")
        score      = bias_data.get("score", 0)

        bias_de  = {"BULLISH": "Bullisch", "BEARISH": "Baerisch", "NEUTRAL": "Neutral"}.get(bias_str, "Neutral")
        bias_pct = min(95, 50 + abs(score))

        key_levels = []
        if mp.get("vah"):  key_levels.append({"level": "VAH Vortag", "price": str(mp["vah"]), "source": "Market Profile"})
        if mp.get("poc"):  key_levels.append({"level": "POC Vortag", "price": str(mp["poc"]), "source": "Market Profile"})
        if mp.get("val"):  key_levels.append({"level": "VAL Vortag", "price": str(mp["val"]), "source": "Market Profile"})
        if mp.get("vwap"): key_levels.append({"level": "VWAP 30M",  "price": str(mp["vwap"]), "source": "VWAP"})

        vwap     = mp.get("vwap") or mp.get("poc", 0)
        vwap_txt = ("ueber VWAP" if price and price > vwap else "unter VWAP") if price else "?"
        in_va    = (mp.get("val", 0) <= (price or 0) <= mp.get("vah", 0)) if price else False
        va_txt   = "in Value Area" if in_va else "ausserhalb Value Area"

        cvd_txt = ""
        if cvd.get("value") is not None:
            v = cvd["value"]
            cvd_txt = f" CVD {v:+.0f} ({'Kaufdruck' if v > 0 else 'Verkaufsdruck'})."

        # Confluence-Zusammenfassung fuer Dashboard
        conf_label  = bias_data.get("confluence_label", "n/a")
        conf_pct    = bias_data.get("confluence_pct", 0)
        manual_chks = bias_data.get("manual_checks", [])

        h30m_summary = (
            f"Kurs {price} {vwap_txt} ({vwap}), {va_txt}. "
            f"POC={mp.get('poc')} VAH={mp.get('vah')} VAL={mp.get('val')}.{cvd_txt} "
            f"Shape: {shape_name}. Confluence: {conf_label}."
        )
        daily_summary = (
            f"Bias {bias_de} (Score {score}, Confluence {conf_pct}%). "
            f"Vortag Range: {mp.get('day_low')} – {mp.get('day_high')}. "
            f"VIX={vix_price:.1f}."
        )

        order      = generate_order(display_name, mp, price, bias_data, shape_name)
        orders_list = [order] if order else []

        if bias_str == "BULLISH":
            invalidation = f"Kurs schliesst unter {mp.get('val')} – bullischer Bias negiert"
        elif bias_str == "BEARISH":
            invalidation = f"Kurs schliesst ueber {mp.get('vah')} – bearischer Bias negiert"
        else:
            invalidation = f"Kurs bricht aus Value Area ({mp.get('val')}–{mp.get('vah')}) aus"

        journal_instruments.append({
            "name":                display_name,
            "bias":                bias_de,
            "bias_color":          bias_data.get("color", "yellow"),
            "bias_score":          score,
            "bias_pct":            str(bias_pct),
            "bias_signals":        bias_data.get("signals", []),
            # ── NEU: Confluence-Felder ──────────────────────────────────────
            "confluence_score":    bias_data.get("confluence_score", 0),
            "confluence_against":  bias_data.get("confluence_against", 0),
            "confluence_total":    bias_data.get("confluence_total", 0),
            "confluence_pct":      conf_pct,
            "confluence_label":    conf_label,
            "manual_checks":       manual_chks,
            # ────────────────────────────────────────────────────────────────
            "cvd":                 cvd,
            "quote":               q,
            "market_profile":      mp,
            "current_price":       price,
            "daily_summary":       daily_summary,
            "h4_summary":          "Manuelle Analyse erforderlich (4H-Daten nicht verfuegbar)",
            "h1_summary":          "Manuelle Analyse erforderlich (1H-Daten nicht verfuegbar)",
            "h30m_summary":        h30m_summary,
            "mp_shape_yesterday":  shape_name,
            "mp_shape_forecast":   shape_name,
            "mp_5day_sequence":    "5-Tage-Sequenz: automatische Berechnung folgt",
            "key_levels":          key_levels,
            "orders":              orders_list,
            "invalidation":        invalidation,
        })

        for ord_data in orders_list:
            sheet_order = {
                "date":        today,
                "time":        today_time,
                "instrument":  display_name,
                "bias":        bias_de,
                "bias_pct":    str(bias_pct),
                "confluence":  conf_label,
                "notes":       f"Auto-generiert | VIX={vix_price:.1f}",
            }
            sheet_order.update(ord_data)
            all_orders_for_sheet.append(sheet_order)

        if score > best_score:
            best_score = score
            best_inst  = display_name

    stats = {"total": len(all_orders_for_sheet), "fill_rate": "n/a", "tp1_rate": "n/a", "trend": "laufend"}
    old_journal_path = os.path.join(script_dir, "journal-data.json")
    if os.path.exists(old_journal_path):
        try:
            with open(old_journal_path, encoding="utf-8") as f:
                old = json.load(f)
            stats = old.get("stats", stats)
        except Exception:
            pass

    journal = {
        "date":      today,
        "timestamp": datetime.now().isoformat(),
        "debrief": {
            "orders_checked": len(all_orders_for_sheet),
            "fill_rate":      stats.get("fill_rate", "n/a"),
            "tp1_rate":       stats.get("tp1_rate", "n/a"),
            "trend":          stats.get("trend", "laufend"),
            "learnings":      [],
        },
        "instruments": journal_instruments,
        "summary": {
            "best_instrument": best_inst or "n/a",
            "total_orders":    len(all_orders_for_sheet),
            "warnings":        warnings,
            "notes": (
                f"Auto-generiert {datetime.now().strftime('%H:%M')}. "
                f"VIX={vix_price:.1f}. Beste Konfluenz: {best_inst}."
            ),
        },
        "stats": stats,
    }

    jpath = os.path.join(script_dir, "journal-data.json")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(journal, f, indent=2, ensure_ascii=False, cls=SafeJSONEncoder)
    print(f"    -> {jpath}")
    print(f"    -> {len(journal_instruments)} Instrumente, {len(all_orders_for_sheet)} Orders")

    return journal, all_orders_for_sheet

# ============================================================
# 7. PIPELINE (Sheet / Doc / git)
# ============================================================

def run_pipeline(journal, orders, script_dir):
    import subprocess

    journal_js = os.path.normpath(
        os.path.join(script_dir, "..", "trading-journal", "journal.js")
    )
    if not os.path.exists(journal_js):
        print(f"    WARNUNG: journal.js nicht gefunden: {journal_js}")
        return

    today = datetime.now().strftime("%Y-%m-%d")

    if orders:
        print("\n>>> Google Sheet: Orders schreiben...")
        orders_json = json.dumps(orders, ensure_ascii=False, cls=SafeJSONEncoder)
        try:
            result = subprocess.run(
                ["node", journal_js, "write-multiple", orders_json],
                capture_output=True, text=True, timeout=30, encoding="utf-8"
            )
            if result.returncode == 0:
                print(f"    -> {result.stdout.strip()}")
            else:
                print(f"    FEHLER: {result.stderr.strip()[:200]}")
        except Exception as e:
            print(f"    FEHLER (Sheet): {e}")
    else:
        print("\n>>> Google Sheet: Keine Orders (NEUTRAL Bias)")

    print("\n>>> Google Docs: Morning Report erstellen...")
    report_payload = {
        "date":        today,
        "timestamp":   journal["timestamp"],
        "instruments": journal["instruments"],
        "summary":     journal["summary"],
        "context":     {},
    }
    report_json = json.dumps(report_payload, ensure_ascii=False, cls=SafeJSONEncoder)
    try:
        result = subprocess.run(
            ["node", journal_js, "report", report_json],
            capture_output=True, text=True, timeout=60, encoding="utf-8"
        )
        if result.returncode == 0:
            print(f"    -> {result.stdout.strip()[:300]}")
        else:
            print(f"    FEHLER: {result.stderr.strip()[:200]}")
    except Exception as e:
        print(f"    FEHLER (Doc): {e}")

    print("\n>>> Google Sheet: Stats aktualisieren...")
    try:
        result = subprocess.run(
            ["node", journal_js, "stats"],
            capture_output=True, text=True, timeout=30, encoding="utf-8"
        )
        if result.returncode == 0:
            out = json.loads(result.stdout.strip())
            print(f"    -> Fill Rate: {out.get('fill_rate','?')}  "
                  f"TP1 Rate: {out.get('tp1_rate','?')}  "
                  f"Trend: {out.get('trend','?')}")
        else:
            print(f"    FEHLER: {result.stderr.strip()[:200]}")
    except Exception as e:
        print(f"    FEHLER (Stats): {e}")

    print("\n>>> Git push...")
    try:
        subprocess.run(["git", "add", "-A"],
                       capture_output=True, text=True, cwd=script_dir, encoding="utf-8")
        commit_msg = f"Morning Briefing {today} – GER40/US30/SPX500 Auto-Pipeline"
        commit_result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            capture_output=True, text=True, cwd=script_dir, encoding="utf-8"
        )
        if "nothing to commit" in commit_result.stdout:
            print("    -> Keine neuen Aenderungen zum Committen")
        else:
            print(f"    -> Commit: {commit_result.stdout.strip()[:100]}")
            push_result = subprocess.run(
                ["git", "push", "origin", "main"],
                capture_output=True, text=True, cwd=script_dir, encoding="utf-8"
            )
            print(f"    -> Push: {'OK' if push_result.returncode == 0 else push_result.stderr.strip()[:100]}")
    except Exception as e:
        print(f"    FEHLER (git): {e}")

# ============================================================
# 8. MAIN
# ============================================================

def main():
    print("\n>>> main() gestartet")

    spx = process_instrument("^GSPC",  "S&P 500 (Kassa)")
    dji = process_instrument("^DJI",   "Dow Jones (Kassa)")
    ger = process_instrument("^GDAXI", "DAX (Kassa)")

    print("\n>>> Context-Daten holen...")
    ctx = {
        "VIX":   fetch_quote("^VIX"),
        "DXY":   fetch_quote("DX-Y.NYB"),
        "US10Y": fetch_quote("^TNX"),
        "DAX":   fetch_quote("^GDAXI"),
    }

    print("\n>>> FRED Daten holen...")
    fred_data = fetch_fred_data()

    print("\n>>> Bias berechnen...")
    spx["bias"] = compute_bias(spx.get("market_profile"), spx.get("current_price"), ctx, spx.get("cvd"), fred_data)
    dji["bias"] = compute_bias(dji.get("market_profile"), dji.get("current_price"), ctx, dji.get("cvd"), fred_data)
    ger["bias"] = compute_bias(ger.get("market_profile"), ger.get("current_price"), ctx, ger.get("cvd"), fred_data)

    print("\n>>> Kalender holen...")
    cal = fetch_calendar()

    script_dir = os.path.dirname(os.path.abspath(__file__))

    print("\n>>> journal-data.json generieren...")
    instruments_map = {"GER40": ger, "US30": dji, "SPX500": spx}
    journal, orders = generate_journal_data(instruments_map, ctx, cal, script_dir)

    out = {
        "timestamp":   datetime.now().isoformat(),
        "instruments": {"SPX": spx, "DJI": dji, "GER": ger},
        "context":     ctx,
        "fred":        fred_data,
        "calendar":    cal,
        "journal":     journal,
    }

    print("\n>>> Schreibe data.json...")
    json_path = os.path.join(script_dir, "data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, cls=SafeJSONEncoder)
    print(f"    -> {json_path}")

    # ── SNAPSHOT: data.json täglich archivieren (Basis für Backtesting) ──────
    print("\n>>> Snapshot archivieren...")
    today_str = datetime.now().strftime("%Y-%m-%d")
    snapshots_dir = os.path.join(script_dir, "snapshots")
    os.makedirs(snapshots_dir, exist_ok=True)
    snap_path = os.path.join(snapshots_dir, f"data_{today_str}.json")
    shutil.copy(json_path, snap_path)
    print(f"    -> {snap_path}")

    # Snapshot-Index aktualisieren (fuer backtest-collector.py)
    index_path = os.path.join(snapshots_dir, "index.json")
    try:
        with open(index_path, encoding="utf-8") as f:
            snap_index = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        snap_index = {"snapshots": []}

    # Eintrag hinzufuegen wenn noch nicht vorhanden
    existing_dates = [s["date"] for s in snap_index["snapshots"]]
    if today_str not in existing_dates:
        # Bias-Summary fuer den Index extrahieren
        bias_summary = {}
        for name, inst in [("GER40", ger), ("US30", dji), ("SPX500", spx)]:
            b = inst.get("bias") or {}
            mp = inst.get("market_profile") or {}
            bias_summary[name] = {
                "bias":             b.get("bias", "NEUTRAL"),
                "score":            b.get("score", 0),
                "confluence_label": b.get("confluence_label", "n/a"),
                "confluence_pct":   b.get("confluence_pct", 0),
                "poc":              mp.get("poc"),
                "vah":              mp.get("vah"),
                "val":              mp.get("val"),
                "vwap":             mp.get("vwap"),
                "shape":            (mp.get("shape") or {}).get("name", "n/a"),
                "price":            inst.get("current_price"),
            }
        snap_index["snapshots"].append({
            "date":     today_str,
            "file":     f"data_{today_str}.json",
            "bias":     bias_summary,
            # outcome wird spaeter von backtest-collector.py befuellt
            "outcome":  None,
        })
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(snap_index, f, indent=2, ensure_ascii=False, cls=SafeJSONEncoder)
        print(f"    -> Index: {len(snap_index['snapshots'])} Snapshots gesamt")

    print(">>> Lese cockpit-dashboard.html...")
    html_path = os.path.join(script_dir, "cockpit-dashboard.html")
    if not os.path.exists(html_path):
        print(f"    FEHLER: {html_path} nicht gefunden!")
        return

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    data_tag = (
        "<script>window.__COCKPIT_DATA__ = "
        + json.dumps(out, cls=SafeJSONEncoder)
        + ";</script>"
    )
    html_embedded = html.replace("</head>", data_tag + "\n</head>")

    for fname, label in [
        ("cockpit-briefing.html", "cockpit-briefing.html"),
        ("dashboard-legacy.html", "dashboard-legacy.html (GitHub Pages)"),
        ("index.html",            "index.html (GitHub Pages Einstieg)"),
    ]:
        fpath = os.path.join(script_dir, fname)
        print(f">>> Schreibe {label}...")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(html_embedded)
        print(f"    -> {fpath}")

    # ── Summary-Print ──────────────────────────────────────────────────────────
    print(f"\n{'='*55}")
    print(f"Timestamp: {out['timestamp']}")
    for ji in journal.get("instruments", []):
        mp = ji.get("market_profile") or {}
        print(f"\n  {ji['name']}:")
        q = ji.get("quote") or {}
        if q:
            print(f"    Kurs:       {q.get('price')}  ({q.get('change',0):+.2f} / {q.get('change_pct',0):+.2f}%)")
        print(f"    Levels:     POC={mp.get('poc')}  VAH={mp.get('vah')}  VAL={mp.get('val')}  VWAP={mp.get('vwap')}")
        print(f"    Shape:      {ji.get('mp_shape_yesterday','?')}")
        print(f"    Bias:       {ji.get('bias','?')} (Score: {ji.get('bias_score','?')})")
        print(f"    Confluence: {ji.get('confluence_label','?')}  ({ji.get('confluence_pct','?')}%)")
        if ji.get("manual_checks"):
            print(f"    Manuell:    {' | '.join(ji['manual_checks'])}")
        if ji.get("orders"):
            print(f"    Order:      {ji['orders'][0]['type']} @ {ji['orders'][0]['entry']}")

    print(f"\nKalender: {len(cal)} Events")
    for e in cal[:8]:
        print(f"  {e.get('date','')} {str(e['time'])[11:16]}  {e['event']} ({e['country']}) [{e['impact']}]")

    print("\n>>> Pipeline starten (Sheet / Doc / git)...")
    run_pipeline(journal, orders, script_dir)

    logging.info(f"Fertig. Instrumente: {list(instruments_map.keys())}")
    print("\nFertig!")
    print("   Lokal:  cockpit-briefing.html per Doppelklick oeffnen")
    print("   iPhone: https://chrisaibizz.github.io/cockpit-trader/")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ UNERWARTETER FEHLER:")
        traceback.print_exc()
        logging.error(f"UNERWARTETER FEHLER: {e}", exc_info=True)
        sys.exit(1)
    sys.exit(0)
