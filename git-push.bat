@echo off
cd /d C:\Users\chris\TradingFloor\cockpit-trader
git add data.json cockpit-briefing.html dashboard-legacy.html journal-data.json index.html ki-analyse.html
git add reports/morning-*.md reports/usupdate-*.md reports/latest.md reports/latest-usupdate.md
git commit -m "Daily Update %date%"
git push origin main
