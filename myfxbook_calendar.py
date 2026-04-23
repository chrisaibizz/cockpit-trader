"""
Myfxbook Economic Calendar Fetcher
Einbauen in cockpit-morning.py (fetch_calendar Funktion ersetzen)

Filter: EUR + USD, High (red=3) + Medium (orange=2) Impact
Spalten: Zeit, Währung, Impact, Event, Actual, Forecast, Previous
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def fetch_myfxbook_calendar(days_ahead=5):
    """
    Holt Economic Calendar Events von Myfxbook.
    Gibt Liste von Dicts zurück, kompatibel mit state.json["calendar"].
    
    Filter:
    - Currencies: EUR, USD
    - Impact: 2 (medium/orange), 3 (high/red)
    - Zeitraum: heute bis days_ahead Tage voraus
    """
    try:
        today = datetime.now()
        end = today + timedelta(days=days_ahead)

        # filter=2-3 = medium+high impact, _EUR-USD = nur EUR und USD
        url = "https://www.myfxbook.com/calendar_statement.xml"
        params = {
            "start": today.strftime("%Y-%m-%d 00:00"),
            "end":   end.strftime("%Y-%m-%d 23:59"),
            "filter": "2-3_EUR-USD",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/xml, text/xml, */*",
        }

        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()

        root = ET.fromstring(resp.text)
        events = []

        for item in root.findall(".//statement"):
            # XML Felder aus Myfxbook
            raw_time   = item.findtext("date", "")        # z.B. "2025-04-23 14:30:00"
            currency   = item.findtext("economy", "")
            name       = item.findtext("title", "")
            impact_raw = item.findtext("impact", "0")     # 1=low, 2=medium, 3=high
            actual     = item.findtext("actual", "")
            forecast   = item.findtext("forecast", "")
            previous   = item.findtext("previous", "")

            try:
                impact_int = int(impact_raw)
            except ValueError:
                impact_int = 0

            # Impact-Label
            if impact_int == 3:
                impact_label = "high"
            elif impact_int == 2:
                impact_label = "medium"
            else:
                impact_label = "low"

            # Datum und Zeit parsen
            try:
                dt = datetime.strptime(raw_time, "%Y-%m-%d %H:%M:%S")
                date_str = dt.strftime("%Y-%m-%d")
                time_str = dt.strftime("%H:%M")
            except ValueError:
                date_str = raw_time[:10] if len(raw_time) >= 10 else raw_time
                time_str = ""

            # better_than_expected: actual > forecast (falls beide numerisch)
            better = None
            try:
                a_num = float(actual.replace("%", "").replace("K", "000").strip())
                f_num = float(forecast.replace("%", "").replace("K", "000").strip())
                better = a_num > f_num
            except (ValueError, AttributeError):
                pass

            events.append({
                "date":     date_str,
                "time":     time_str,
                "currency": currency,
                "name":     name,
                "impact":   impact_label,
                "actual":   actual.strip(),
                "forecast": forecast.strip(),
                "previous": previous.strip(),
                "better":   better,          # True/False/None
                "source":   "myfxbook",
            })

        # Sortieren nach Datum + Zeit
        events.sort(key=lambda x: (x["date"], x["time"]))

        logger.info(f"Myfxbook Calendar: {len(events)} Events geladen "
                    f"({today.strftime('%Y-%m-%d')} bis {end.strftime('%Y-%m-%d')})")
        return events

    except requests.RequestException as e:
        logger.warning(f"Myfxbook Calendar Fetch fehlgeschlagen: {e}")
        return []
    except ET.ParseError as e:
        logger.warning(f"Myfxbook XML Parse-Fehler: {e}")
        return []
    except Exception as e:
        logger.warning(f"Myfxbook Calendar unbekannter Fehler: {e}")
        return []


# ─── In cockpit-morning.py einbauen ───────────────────────────────────────────
#
# Alte Zeile suchen (irgendwo in der Hauptfunktion):
#   state["calendar"] = fetch_calendar()   (oder ähnlich)
#
# Ersetzen durch:
#   from myfxbook_calendar import fetch_myfxbook_calendar
#   state["calendar"] = fetch_myfxbook_calendar(days_ahead=5)
#
# ODER direkt die Funktion oben in cockpit-morning.py einfügen und aufrufen.
# ──────────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    # Schnelltest: python myfxbook_calendar.py
    logging.basicConfig(level=logging.INFO)
    events = fetch_myfxbook_calendar()
    print(f"\n{len(events)} Events gefunden:\n")
    for e in events:
        imp_sym = "🔴" if e["impact"] == "high" else "🟡"
        print(f"{imp_sym} {e['date']} {e['time']}  [{e['currency']}]  {e['name']}")
        if e["actual"]:
            better_str = " ▲" if e["better"] else (" ▼" if e["better"] is False else "")
            print(f"   Actual: {e['actual']}{better_str}  Forecast: {e['forecast']}  Prev: {e['previous']}")
