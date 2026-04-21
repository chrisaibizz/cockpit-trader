@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Trading Floor - US Update 14:00
set LOGFILE=C:\Users\chris\TradingFloor\cockpit-run.log
set MCP_DIR=C:\Users\chris\TradingFloor\tradingview-mcp
set CDP_PORT=9222
set BRAVE=C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe
set TV_URL=https://www.tradingview.com/chart/
set PROFILE=C:\Users\chris\TradingFloor\BraveProfile-Trading

echo ============================================ >> "%LOGFILE%"
echo [US Update] Start %DATE% %TIME% >> "%LOGFILE%"
echo ============================================ >> "%LOGFILE%"

:: -- SCHRITT 1: Harter Reset (TV + CDP + Claude + Node) -------------
echo [1/4] Harter Reset... >> "%LOGFILE%"
taskkill /f /im brave.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1
taskkill /f /im claude.exe >nul 2>&1
taskkill /f /im python.exe >nul 2>&1
timeout /t 5 /nobreak >nul
echo Reset OK. >> "%LOGFILE%"

:: -- SCHRITT 2: Brave + TradingView neu starten ----------------------
echo [2/4] Starte Brave + TradingView... >> "%LOGFILE%"
start "" "%BRAVE%" ^
    --remote-debugging-port=%CDP_PORT% ^
    --remote-allow-origins=http://localhost:%CDP_PORT% ^
    --user-data-dir="%PROFILE%" ^
    --no-first-run "%TV_URL%"

:: CDP Warteschleife (max. 3 Min, alle 10 Sek)
echo Warte auf CDP... >> "%LOGFILE%"
set CDP_OK=0
for /L %%i in (1,1,18) do (
    if !CDP_OK!==0 (
        curl -s http://localhost:%CDP_PORT%/json/version >nul 2>&1
        if !errorlevel!==0 (
            set CDP_OK=1
            echo CDP aktiv nach %%i x 10 Sek. >> "%LOGFILE%"
        ) else (
            timeout /t 10 /nobreak >nul
        )
    )
)
if !CDP_OK!==0 (
    echo FEHLER: CDP nicht erreichbar nach 3 Min! >> "%LOGFILE%"
    echo [US Update] ABBRUCH - CDP Fehler %TIME% >> "%LOGFILE%"
    goto :CLEANUP
)

:: Zusaetzlich 30 Sek fuer Indikator-Load
echo Warte auf Indikatoren (30 Sek)... >> "%LOGFILE%"
timeout /t 30 /nobreak >nul

:: -- SCHRITT 3: Claude Code US Update -------------------------------
echo [3/4] Claude Code US Update... >> "%LOGFILE%"
echo %TIME% >> "%LOGFILE%"
cd /d "%MCP_DIR%"
node "C:\Users\chris\TradingFloor\cockpit-us-runner.js" "C:\Users\chris\TradingFloor\cockpit-us-prompt.txt" "mcp__tradingview__*,Bash,Read,Write" >> "%LOGFILE%" 2>&1
echo Claude Code fertig. >> "%LOGFILE%"
echo %TIME% >> "%LOGFILE%"

:: -- CLEANUP: Alles sauber killen -----------------------------------
:CLEANUP
echo [4/4] Cleanup - Stoppe alle Prozesse... >> "%LOGFILE%"
taskkill /f /im brave.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1
taskkill /f /im claude.exe >nul 2>&1
timeout /t 3 /nobreak >nul
echo Cleanup OK. >> "%LOGFILE%"

echo [4/4] DONE %DATE% %TIME% >> "%LOGFILE%"
echo ============================================ >> "%LOGFILE%"
