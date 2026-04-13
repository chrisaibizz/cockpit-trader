@echo off
cd /d C:\Users\chris\TradingFloor\cockpit-trader
git add data.json cockpit-briefing.html index.html
git commit -m "Daily Update %date%"
git push origin main
