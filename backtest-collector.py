#!/usr/bin/env python3
"""
Cockpit-Trader: Backtest Collector
====================================
Wertet die taeglichen Snapshots aus snapshots/index.json aus.

Stufe 1 (jetzt):     Outcomes erfassen — war der Bias korrekt?
Stufe 2 (4 Wochen):  Trefferquoten nach Shape, Confluence, VIX
Stufe 3 (3 Monate):  Mustererkennung — welche Kombination gewinnt?

Aufruf:
  python3 backtest-collector.py              # Vollauswertung + Report
  python3 backtest-collector.py update       # Nur Outcomes nachtragen
  python3 backtest-collector.py report       # Nur Auswertung ausgeben
  python3 backtest-collector.py summary      # Kurze Zusammenfassung
"""

import json, os, sys, math, traceback
from datetime import datetime, timedelta
from collections import defaultdict

try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False
    print("WARNUNG: yfinance nicht installiert — pip install yfinance")

# ── Konfiguration ─────────────────────────────────────────────────────────────

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
SNAPSHOTS_DIR = os.path.join(SCRIPT_DIR, "snapshots")
INDEX_PATH    = os.path.join(SNAPSHOTS_DIR, "index.json")
REPORT_PATH   = os.path.join(SNAPSHOTS_DIR, "backtest-report.json")

TICKER_MAP = {
    "GER40":  "^GDAXI",
    "US30":   "^DJI",
    "SPX500": "^GSPC",
}

# Mindest-Bewegung in % der Tagesrange damit Bias als "korrekt" gilt
MIN_MOVE_PCT = 0.20

# ── JSON Helper ───────────────────────────────────────────────────────────────

class SafeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        return super().default(obj)

# ── Index laden / speichern ───────────────────────────────────────────────────

def load_index():
    if not os.path.exists(INDEX_PATH):
        print(f"Index nicht gefunden: {INDEX_PATH}")
        print("Starte cockpit-morning.py mindestens einmal.")
        return {"snapshots": []}
    with open(INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)

def save_index(index):
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False, cls=SafeEncoder)

# ── Stufe 1: Outcomes erfassen ────────────────────────────────────────────────

def fetch_outcome(ticker_yf, date_str, bias, poc, vah, val, price_signal):
    """
    Holt Tagesdaten und bewertet ob der Bias korrekt war.

    BULLISH korrekt  → Close > Open UND Aufwaertsbewegung >= MIN_MOVE_PCT der Range
    BEARISH korrekt  → Close < Open UND Abwaertsbewegung >= MIN_MOVE_PCT der Range
    NEUTRAL korrekt  → Nettobewegung < MIN_MOVE_PCT der Range
    partial          → Ziel (VAH/VAL) angelaufen aber Bias nicht bestaetigt
    """
    if not HAS_YF:
        return None
    try:
        date_dt = datetime.strptime(date_str, "%Y-%m-%d")
        end_dt  = date_dt + timedelta(days=3)
        hist    = yf.Ticker(ticker_yf).history(
            start=date_str,
            end=end_dt.strftime("%Y-%m-%d")
        )
        if hist.empty:
            return None

        hist.index = (hist.index.tz_localize(None)
                      if hist.index.tz else hist.index)
        rows = hist[hist.index.date >= date_dt.date()]
        if rows.empty:
            return None

        row       = rows.iloc[0]
        day_open  = float(row["Open"])
        day_high  = float(row["High"])
        day_low   = float(row["Low"])
        day_close = float(row["Close"])
        day_range = day_high - day_low
        if day_range == 0:
            return None

        net_move  = day_close - day_open
        move_up   = day_high  - day_open
        move_down = day_open  - day_low

        if bias == "BULLISH":
            closed_up   = day_close > day_open
            move_enough = move_up / day_range >= MIN_MOVE_PCT
            correct     = closed_up and move_enough
            partial     = (vah is not None and day_high >= vah) and not correct

        elif bias == "BEARISH":
            closed_down = day_close < day_open
            move_enough = move_down / day_range >= MIN_MOVE_PCT
            correct     = closed_down and move_enough
            partial     = (val is not None and day_low <= val) and not correct

        else:  # NEUTRAL
            net_pct = abs(net_move) / day_range
            correct = net_pct < MIN_MOVE_PCT
            partial = False

        return {
            "day_open":   round(day_open,  2),
            "day_high":   round(day_high,  2),
            "day_low":    round(day_low,   2),
            "day_close":  round(day_close, 2),
            "day_range":  round(day_range, 2),
            "net_move":   round(net_move,  2),
            "correct":    correct,
            "partial":    partial,
            "fetched_at": datetime.now().isoformat(),
        }
    except Exception as e:
        print(f"    Outcome FEHLER ({ticker_yf} {date_str}): {e}")
        return None


def update_outcomes(index, force=False):
    """Traegt Outcomes fuer alle auswertbaren Snapshots nach."""
    today   = datetime.now().date()
    updated = 0

    for snap in index["snapshots"]:
        date_str = snap["date"]
        snap_dt  = datetime.strptime(date_str, "%Y-%m-%d").date()

        if snap_dt >= today:
            continue
        if snap.get("outcome") and not force:
            continue

        print(f"  Outcome holen: {date_str}...")
        bias_data = snap.get("bias") or {}
        outcomes  = {}

        for inst_name, ticker_yf in TICKER_MAP.items():
            b = bias_data.get(inst_name) or {}
            oc = fetch_outcome(
                ticker_yf    = ticker_yf,
                date_str     = date_str,
                bias         = b.get("bias", "NEUTRAL"),
                poc          = b.get("poc"),
                vah          = b.get("vah"),
                val          = b.get("val"),
                price_signal = b.get("price"),
            )
            if oc:
                oc["bias"]             = b.get("bias", "NEUTRAL")
                oc["score"]            = b.get("score", 0)
                oc["confluence_pct"]   = b.get("confluence_pct", 0)
                oc["confluence_label"] = b.get("confluence_label", "n/a")
                oc["shape"]            = b.get("shape", "n/a")
                outcomes[inst_name]    = oc
                st = "✅" if oc["correct"] else ("⚡ partial" if oc["partial"] else "❌")
                print(f"    {inst_name}: {oc['bias']} → {st} "
                      f"Open={oc['day_open']} Close={oc['day_close']}")

        if outcomes:
            snap["outcome"] = outcomes
            updated += 1

    if updated:
        save_index(index)
        print(f"\n  {updated} Snapshot(s) aktualisiert.")
    else:
        print("  Keine neuen Outcomes.")
    return updated


# ── Stufe 2: Auswertung ───────────────────────────────────────────────────────

def pct(correct, total):
    return round(correct / total * 100, 1) if total > 0 else 0.0

def conf_tier(p):
    if p is None: return "n/a"
    if p >= 75:   return "hoch (>=75%)"
    if p >= 50:   return "mittel (50-74%)"
    return               "niedrig (<50%)"

def counter():
    return {"total": 0, "correct": 0, "partial": 0}

def analyse(index):
    snaps = [s for s in index["snapshots"] if s.get("outcome")]
    if not snaps:
        print("Noch keine Outcomes vorhanden. Erst 'update' ausfuehren.")
        return None

    total_signals = total_correct = total_partial = 0
    by_instrument = defaultdict(counter)
    by_bias       = defaultdict(counter)
    by_shape      = defaultdict(counter)
    by_confluence = defaultdict(counter)
    by_week       = defaultdict(counter)

    for snap in snaps:
        week = datetime.strptime(snap["date"], "%Y-%m-%d").strftime("%Y-W%V")
        for inst_name, oc in snap["outcome"].items():
            total_signals += 1
            ok  = oc.get("correct", False)
            par = oc.get("partial", False)
            bias  = oc.get("bias",  "NEUTRAL")
            shape = oc.get("shape", "n/a")
            tier  = conf_tier(oc.get("confluence_pct"))

            if ok:  total_correct += 1
            if par: total_partial += 1

            for grp, key in [
                (by_instrument, inst_name),
                (by_bias,       bias),
                (by_shape,      shape),
                (by_confluence, tier),
                (by_week,       week),
            ]:
                grp[key]["total"]   += 1
                if ok:  grp[key]["correct"] += 1
                if par: grp[key]["partial"] += 1

    def to_pct_dict(d, min_n=1, limit=None):
        rows = sorted(
            [(k, v) for k, v in d.items() if v["total"] >= min_n],
            key=lambda x: x[1]["total"], reverse=True
        )
        if limit:
            rows = rows[:limit]
        return {k: {**v, "pct": pct(v["correct"], v["total"])} for k, v in rows}

    report = {
        "generated_at":   datetime.now().isoformat(),
        "snapshots_used": len(snaps),
        "total_signals":  total_signals,
        "total_correct":  total_correct,
        "total_partial":  total_partial,
        "overall_pct":    pct(total_correct, total_signals),
        "partial_pct":    pct(total_partial, total_signals),
        "by_instrument":  to_pct_dict(by_instrument),
        "by_bias":        to_pct_dict(by_bias),
        "by_shape":       to_pct_dict(by_shape, min_n=2, limit=10),
        "by_confluence":  to_pct_dict(by_confluence),
        "by_week":        {k: {**v, "pct": pct(v["correct"], v["total"])}
                           for k, v in sorted(by_week.items())},
    }

    # ── Automatische Erkenntnisse ─────────────────────────────────────────────
    insights = []

    best_inst = max(report["by_instrument"].items(),
                    key=lambda x: x[1]["pct"], default=None)
    if best_inst and best_inst[1]["total"] >= 3:
        insights.append(
            f"Bestes Instrument: {best_inst[0]} "
            f"({best_inst[1]['pct']}% bei {best_inst[1]['total']} Signalen)"
        )

    ct = report["by_confluence"]
    if "hoch (>=75%)" in ct and "niedrig (<50%)" in ct:
        h, l = ct["hoch (>=75%)"], ct["niedrig (<50%)"]
        if h["total"] >= 3 and l["total"] >= 3:
            diff = h["pct"] - l["pct"]
            insights.append(
                f"Confluence-Effekt: hoch={h['pct']}% vs niedrig={l['pct']}% "
                f"(Δ {diff:+.1f}%)"
            )

    best_shape = max(
        [(k, v) for k, v in report["by_shape"].items() if v["total"] >= 3],
        key=lambda x: x[1]["pct"], default=None
    )
    if best_shape:
        insights.append(
            f"Beste Shape: {best_shape[0]} "
            f"({best_shape[1]['pct']}% bei {best_shape[1]['total']} Signalen)"
        )

    bd = report["by_bias"]
    if "BULLISH" in bd and "BEARISH" in bd:
        diff = bd["BULLISH"]["pct"] - bd["BEARISH"]["pct"]
        if abs(diff) >= 15:
            besser = "BULLISH" if diff > 0 else "BEARISH"
            insights.append(
                f"Bias-Asymmetrie erkannt: {besser} besser "
                f"(Bull {bd['BULLISH']['pct']}% vs Bear {bd['BEARISH']['pct']}%)"
            )

    if not insights:
        insights.append(
            "Noch zu wenig Daten fuer automatische Erkenntnisse "
            f"(aktuell {total_signals} Signale, mind. 15 empfohlen)."
        )

    report["insights"] = insights
    return report


# ── Output ────────────────────────────────────────────────────────────────────

def print_summary(index):
    print(f"\n{'─'*85}")
    print(f"{'Datum':<12} {'Instrument':<10} {'Bias':<10} {'Confluence':<22} {'Outcome'}")
    print(f"{'─'*85}")
    for snap in sorted(index["snapshots"], key=lambda s: s["date"]):
        bias_data = snap.get("bias") or {}
        outcomes  = snap.get("outcome") or {}
        for inst_name in TICKER_MAP:
            b  = bias_data.get(inst_name) or {}
            oc = outcomes.get(inst_name)
            bias_str = b.get("bias", "—")
            conf_lbl = b.get("confluence_label", "—")
            if oc:
                st = "✅" if oc["correct"] else ("⚡" if oc["partial"] else "❌")
                result = f"{st}  O={oc['day_open']}  C={oc['day_close']}  net={oc['net_move']:+.0f}"
            else:
                result = "⏳ ausstehend"
            print(f"{snap['date']:<12} {inst_name:<10} {bias_str:<10} {conf_lbl:<22} {result}")
    print(f"{'─'*85}\n")


def print_report(report):
    if not report:
        return
    print(f"\n{'═'*62}")
    print(f"  COCKPIT-TRADER BACKTEST REPORT")
    print(f"  {report['generated_at'][:16]}  |  {report['snapshots_used']} Tage")
    print(f"{'═'*62}")

    print(f"\n  GESAMT  {report['total_signals']} Signale:")
    print(f"  ✅ Korrekt:  {report['total_correct']}  ({report['overall_pct']}%)")
    print(f"  ⚡ Partial:  {report['total_partial']}  ({report['partial_pct']}%)")
    wrong = report['total_signals'] - report['total_correct'] - report['total_partial']
    print(f"  ❌ Falsch:   {wrong}")

    for section, title in [
        ("by_instrument", "NACH INSTRUMENT"),
        ("by_bias",       "NACH BIAS"),
        ("by_confluence", "NACH CONFLUENCE-TIER"),
    ]:
        print(f"\n  {title}:")
        for k, v in report[section].items():
            bar = "█" * int(v["pct"] / 5)
            print(f"  {k:<28} {v['pct']:>5.1f}%  {bar:<20}  n={v['total']}")

    shapes = [(k, v) for k, v in report["by_shape"].items() if v["total"] >= 2]
    if shapes:
        print(f"\n  NACH SHAPE (mind. 2 Signale):")
        for k, v in shapes:
            bar = "█" * int(v["pct"] / 5)
            print(f"  {k:<32} {v['pct']:>5.1f}%  {bar:<20}  n={v['total']}")

    if report["by_week"]:
        print(f"\n  WOCHENVERLAUF:")
        for k, v in report["by_week"].items():
            bar = "█" * int(v["pct"] / 5)
            print(f"  {k:<14} {v['pct']:>5.1f}%  {bar:<20}  n={v['total']}")

    print(f"\n  ERKENNTNISSE:")
    for ins in report["insights"]:
        print(f"  → {ins}")

    print(f"\n{'═'*62}\n")


def save_report(report):
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, cls=SafeEncoder)
    print(f"Report gespeichert: {REPORT_PATH}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.makedirs(SNAPSHOTS_DIR, exist_ok=True)
    index = load_index()

    if not index["snapshots"]:
        print("Keine Snapshots gefunden.")
        print(f"Verzeichnis: {SNAPSHOTS_DIR}")
        print("Starte cockpit-morning.py um den ersten Snapshot zu erzeugen.")
        return

    total        = len(index["snapshots"])
    with_outcome = sum(1 for s in index["snapshots"] if s.get("outcome"))
    print(f"Snapshots: {total} gesamt  |  {with_outcome} mit Outcome  |  {total - with_outcome} ausstehend")

    if mode in ("all", "update"):
        print("\n>>> Outcomes aktualisieren...")
        update_outcomes(index)

    if mode in ("all", "report"):
        print("\n>>> Auswertung...")
        report = analyse(index)
        if report:
            print_report(report)
            save_report(report)

    if mode in ("all", "summary"):
        print("\n>>> Zusammenfassung...")
        print_summary(load_index())   # neu laden damit Aenderungen sichtbar sind

    if mode not in ("all", "update", "report", "summary"):
        print(f"Unbekannter Modus: '{mode}'")
        print("Gueltig: all | update | report | summary")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ FEHLER:")
        traceback.print_exc()
        sys.exit(1)
