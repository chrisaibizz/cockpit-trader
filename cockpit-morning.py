#!/usr/bin/env python3
"""
Cockpit-Trader: Vollautomatisches Morning Briefing
SP500 & Dow Jones KASSA — Market Profile, VWAP, Bias-Ampel
Symbole: ^GSPC (S&P 500 Cash), ^DJI (Dow Jones Cash)
GitHub Actions: laeuft automatisch Mo-Fr 07:00 Uhr
iPhone URL: https://chrisaibizz.github.io/cockpit-trader/
"""

import json, os, sys, traceback
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf

print(">>> Script gestartet")

try:
    import finnhub
    FINNHUB_KEY = os.environ.get("FINNHUB_API_KEY", "")
    fh = finnhub.Client(api_key=FINNHUB_KEY) if FINNHUB_KEY else None
    print(f">>> Finnhub: {'OK (Key vorhanden)' if FINNHUB_KEY else 'Kein Key - Kalender deaktiviert'}")
except ImportError:
    fh = None
    print(">>> Finnhub nicht installiert - Kalender deaktiviert")

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
                    if e.get("impact") in ("high", "medium")
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

# ============================================================
# 2. MARKET PROFILE
# ============================================================

# TradingView Symbol-Mapping (Yahoo Finance → Vantage/TradingView)
TV_SYMBOL_MAP = {
    "^GSPC": "Vantage:SP500",
    "^DJI":  "Vantage:DJ30",
    "^GDAXI": "Vantage:GER40",
}

def get_tv_data(ticker, timeframe="30"):
    """
    Liest Market Profile (POC/VAH/VAL) und Cumulative Delta Volume (CVD)
    direkt aus TradingView via CDP (Port 9222).
    MP: letzte Session der pine lines (color=0=POC, min/max color=1=VAL/VAH)
    CVD: aktueller Wert + Trend der letzten 5 Bars (Divergenz mit Preis)
    Gibt (mp, cvd) zurueck — beide None wenn TV nicht verfuegbar (GitHub Actions).
    """
    tv_symbol = TV_SYMBOL_MAP.get(ticker)
    if not tv_symbol:
        return None, None
    try:
        import requests as _req
        import websocket as _ws
        import time

        # 1. CDP Target finden
        resp = _req.get("http://localhost:9222/json", timeout=2)
        targets = resp.json()
        tv_target = next((t for t in targets if "webSocketDebuggerUrl" in t), None)
        if not tv_target:
            return None, None

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

        # 2. Symbol + Timeframe setzen
        _eval(f"(function(){{var c=window.TradingViewApi._activeChartWidgetWV.value();c.setSymbol({json.dumps(tv_symbol)},function(){{}});}})()")
        time.sleep(2.5)
        _eval(f"(function(){{var c=window.TradingViewApi._activeChartWidgetWV.value();c.setResolution({json.dumps(timeframe)},function(){{}});}})()")
        time.sleep(1.5)

        # 3. Market Profile pine lines lesen
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

        # 4. CVD Werte lesen (aktuell + letzte 5 Bars fuer Trend)
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

        ws.close()

        # 5. MP verarbeiten
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
                print(f"    MP (TradingView): POC={poc} VAH={vah} VAL={val}")
                mp = {"poc": poc, "vah": vah, "val": val, "vwap": None,
                      "day_high": vah, "day_low": val,
                      "shape": {"name": "n/a", "description": ""},
                      "volume_profile": [], "source": "tradingview"}
            else:
                print("    TV CDP: MP — POC oder VA Lines fehlen")

        # 6. CVD verarbeiten
        cvd = None
        if cvd_items and cvd_items.get("current") is not None:
            val_cvd = cvd_items["current"]
            direction = "bullish" if val_cvd > 0 else "bearish"
            print(f"    CVD (TradingView): {val_cvd:+.0f} ({direction})")
            cvd = {"value": val_cvd, "direction": direction}

        return mp, cvd

    except Exception as e:
        print(f"    TV CDP nicht verfuegbar ({type(e).__name__}): {e}")
        return None, None


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
                "description": "Zwei Value Areas — oft Trend-Folgetag."}
    if middle > 0.4*total:
        return {"name": "Normal Day",
                "description": "Ausbalanciert — Range-Trading um POC."}
    return {"name": "Normal Variation",
            "description": "Leichte Richtung — Abwarten auf Breakout aus VA."}

# ============================================================
# 3. BIAS-AMPEL
# ============================================================

def compute_bias(mp, price, context, cvd=None):
    signals = []
    if mp and price:
        signals.append(("Preis > VWAP", 2, "bullish") if price > mp["vwap"]
                       else ("Preis < VWAP", -2, "bearish"))
        if   price > mp["vah"]: signals.append(("Ueber VAH — Breakout",   2, "bullish"))
        elif price < mp["val"]: signals.append(("Unter VAL — Breakdown", -2, "bearish"))
        else:                   signals.append(("In Value Area",           0, "neutral"))
        signals.append(("Preis > POC", 1, "bullish") if price > mp["poc"]
                       else ("Preis < POC", -1, "bearish"))
        sn = mp["shape"]["name"]
        if   "Up"      in sn: signals.append((f"Shape: {sn}",  2, "bullish"))
        elif "Down"    in sn: signals.append((f"Shape: {sn}", -2, "bearish"))
        elif "b-Shape" in sn: signals.append((f"Shape: {sn}",  1, "bullish"))
        elif "P-Shape" in sn: signals.append((f"Shape: {sn}", -1, "bearish"))
        else:                 signals.append((f"Shape: {sn}",  0, "neutral"))
        mid = (mp["vah"] + mp["val"]) / 2
        signals.append(("Overnight Inventory: Long",   1, "bullish") if price > mid
                       else ("Overnight Inventory: Short", -1, "bearish"))

    # CVD Signale
    if cvd and cvd.get("value") is not None:
        v = cvd["value"]
        if v > 0:
            signals.append((f"CVD positiv ({v:+.0f}) — Kaufdruck",   1, "bullish"))
        else:
            signals.append((f"CVD negativ ({v:+.0f}) — Verkaufsdruck", -1, "bearish"))
        # Divergenz: Preis in VA aber CVD stark negativ = Warnsignal
        if mp and price and price >= mp.get("val", 0) and price <= mp.get("vah", 999999):
            if v < -50000:
                signals.append(("CVD-Divergenz: Preis in VA, starker Verkaufsdruck", -2, "bearish"))
            elif v > 50000:
                signals.append(("CVD-Divergenz: Preis in VA, starker Kaufdruck",      2, "bullish"))

    vix = context.get("VIX",   {}) or {}
    dxy = context.get("DXY",   {}) or {}
    y10 = context.get("US10Y", {}) or {}

    if vix.get("price"):
        v = vix["price"]
        if   v < 15: signals.append((f"VIX {v} — Low Vol",   2, "bullish"))
        elif v < 20: signals.append((f"VIX {v} — Normal",    1, "bullish"))
        elif v < 25: signals.append((f"VIX {v} — Elevated", -1, "bearish"))
        else:        signals.append((f"VIX {v} — High Fear", -2, "bearish"))

    if vix.get("change_pct"):
        cp = vix["change_pct"]
        if   cp < -3: signals.append(("VIX falling sharply",  1, "bullish"))
        elif cp >  3: signals.append(("VIX rising sharply",  -1, "bearish"))
        else:         signals.append(("VIX stabil",            0, "neutral"))

    if dxy.get("change_pct"):
        cp = dxy["change_pct"]
        if   cp < -0.3: signals.append(("Dollar schwaecher",  1, "bullish"))
        elif cp >  0.3: signals.append(("Dollar staerker",   -1, "bearish"))
        else:           signals.append(("Dollar neutral",      0, "neutral"))

    if y10.get("change_pct"):
        cp = y10["change_pct"]
        if   cp >  2: signals.append(("Yields steigen stark", -1, "bearish"))
        elif cp < -2: signals.append(("Yields fallen stark",   1, "bullish"))
        else:         signals.append(("Yields stabil",          0, "neutral"))

    signals += [
        ("Daily OTF Check",     0, "neutral"),
        ("Gap Analysis",        0, "neutral"),
        ("Session Expectation", 0, "neutral"),
    ]

    ms    = sum(abs(s[1]) for s in signals) or 1
    sc    = round(sum(s[1] for s in signals) / ms * 100)
    bias  = "BULLISH" if sc > 30 else "BEARISH" if sc < -30 else "NEUTRAL"
    color = "green"   if sc > 30 else "red"     if sc < -30 else "yellow"
    return {
        "score": sc, "bias": bias, "color": color,
        "signals": [{"label": s[0], "score": s[1], "direction": s[2]} for s in signals],
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

    mp_tv, cvd = get_tv_data(ticker)
    mp = mp_tv or compute_market_profile(df_day)
    q  = fetch_quote(ticker)
    return {
        "name": name, "ticker": ticker,
        "quote": q, "market_profile": mp,
        "cvd": cvd,
        "current_price": q["price"] if q else None,
    }

# ============================================================
# 5. MAIN
# ============================================================

def main():
    print("\n>>> main() gestartet")

    spx = process_instrument("^GSPC", "S&P 500 (Kassa)")
    dji = process_instrument("^DJI",  "Dow Jones (Kassa)")

    print("\n>>> Context-Daten holen...")
    ctx = {
        "VIX":   fetch_quote("^VIX"),
        "DXY":   fetch_quote("DX-Y.NYB"),
        "US10Y": fetch_quote("^TNX"),
        "DAX":   fetch_quote("^GDAXI"),
    }

    print("\n>>> Bias berechnen...")
    spx["bias"] = compute_bias(spx.get("market_profile"), spx.get("current_price"), ctx, spx.get("cvd"))
    dji["bias"] = compute_bias(dji.get("market_profile"), dji.get("current_price"), ctx, dji.get("cvd"))

    print("\n>>> Kalender holen...")
    cal = fetch_calendar()

    out = {
        "timestamp":   datetime.now().isoformat(),
        "instruments": {"SPX": spx, "DJI": dji},
        "context":     ctx,
        "calendar":    cal,
    }

    script_dir = os.path.dirname(os.path.abspath(__file__))

    print("\n>>> Schreibe data.json...")
    json_path = os.path.join(script_dir, "data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"    -> {json_path}")

    print(">>> Lese cockpit-dashboard.html...")
    html_path = os.path.join(script_dir, "cockpit-dashboard.html")
    if not os.path.exists(html_path):
        print(f"    FEHLER: {html_path} nicht gefunden!")
        return

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    data_tag = (
        "<script>window.__COCKPIT_DATA__ = "
        + json.dumps(out, default=str)
        + ";</script>"
    )
    html_embedded = html.replace("</head>", data_tag + "\n</head>")

    briefing_path = os.path.join(script_dir, "cockpit-briefing.html")
    print(">>> Schreibe cockpit-briefing.html...")
    with open(briefing_path, "w", encoding="utf-8") as f:
        f.write(html_embedded)
    print(f"    -> {briefing_path}")

    index_path = os.path.join(script_dir, "dashboard-legacy.html")
    print(">>> Schreibe dashboard-legacy.html (GitHub Pages)...")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_embedded)
    print(f"    -> {index_path}")

    print(f"\n{'='*50}")
    print(f"Timestamp: {out['timestamp']}")
    for k, inst in out["instruments"].items():
        q  = inst.get("quote")          or {}
        mp = inst.get("market_profile") or {}
        b  = inst.get("bias",           {})
        print(f"\n  {k}:")
        if q:  print(f"    Kurs:  {q['price']}  ({q['change']:+.2f} / {q['change_pct']:+.2f}%)")
        if mp: print(f"    Levels: POC={mp['poc']}  VAH={mp['vah']}  VAL={mp['val']}  VWAP={mp['vwap']}")
        if mp: print(f"    Shape:  {mp['shape']['name']}")
        if b:  print(f"    Bias:   {b['bias']} (Score: {b['score']})")

    print(f"\nKalender: {len(cal)} Events")
    for e in cal[:8]:
        print(f"  {e.get('date','')} {str(e['time'])[11:16]}  {e['event']} ({e['country']}) [{e['impact']}]")

    print(f"\n✅ Fertig!")
    print(f"   Lokal:  cockpit-briefing.html per Doppelklick oeffnen")
    print(f"   iPhone: https://chrisaibizz.github.io/cockpit-trader/")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ UNERWARTETER FEHLER:")
        traceback.print_exc()
        sys.exit(1)