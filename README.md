# Cockpit Trader

Vollautomatisches Trading-System für GER40, DJ30, SPX500.

## Setup nach git clone

**Bat-Files nach `C:\Users\chris\TradingFloor\` kopieren:**

```
copy TradingCockpit.bat       C:\Users\chris\TradingFloor\
copy TradingCockpit-US.bat    C:\Users\chris\TradingFloor\
copy cockpit-morning-runner.js C:\Users\chris\TradingFloor\
copy cockpit-us-runner.js      C:\Users\chris\TradingFloor\
```

Die Bat-Files referenzieren absolute Pfade unter `C:\Users\chris\TradingFloor\` und müssen dort liegen, damit der Windows Task Scheduler sie findet.

## Geplante Tasks (Windows Task Scheduler)

| Task | Zeit | Datei |
|---|---|---|
| TradingFloor-Morning | 08:00 | `TradingCockpit.bat` |
| TradingFloor-USUpdate | 14:45 | `TradingCockpit-US.bat` |
