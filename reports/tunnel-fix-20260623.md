# Tunnel-Fix Report — 2026-06-23

## Diagnose

- PID 5416 war aktiv und responding, aber DNS loeste nicht auf
- netstat zeigte nur localhost:20241 (kein ausgehender Tunnel-Socket aktiv)
- Letzter Log-Eintrag: TUNNEL URL gesetzt, aber Cloudflare-DNS-Eintrag nicht mehr gueltig

## Alte URL

`https://fotos-accessible-operational-previous.trycloudflare.com`

Fehler: `Der angegebene Host ist unbekannt` — DNS-Aufloesung komplett gescheitert

## Massnahme

Dienst `TradingFloorCloudflare` neu gestartet:
- `net stop TradingFloorCloudflare` — erfolgreich
- `net start TradingFloorCloudflare` — erfolgreich
- 20 Sekunden gewartet bis neue URL registriert

## Neue URL

`https://eval-trim-pharmaceuticals-defense.trycloudflare.com`

## Testergebnis oauth-protected-resource

```json
{"resource": "https://eval-trim-pharmaceuticals-defense.trycloudflare.com", "authorization_servers": ["https://eval-trim-pharmaceuticals-defense.trycloudflare.com"]}
```

HTTP 200 — authorization_servers enthalten neue URL (nicht localhost)

## Status: ERFOLG
