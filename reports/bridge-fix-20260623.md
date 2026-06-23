# MCP-Bridge OAuth Well-Known Fix -- 2026-06-23

## Status: ERFOLG

## Was geaendert

### server.py -- Aenderung 1: Route-Append-Block deaktiviert (ex. Zeilen 187-200)

Kommentiert: Import `from starlette.routing import Route`, doppelter Import `from starlette.requests import Request`, zwei Handler-Funktionen `oauth_protected_resource` / `oauth_authorization_server`, sowie `app = mcp.http_app()` und beide `app.routes.append(...)` Zeilen.

Grund: Diese Routen wurden auf dem Starlette-App-Objekt registriert und fingen `.well-known`-Requests ab bevor `_WellKnownMiddleware` greifen konnte.

### server.py -- Aenderung 2: @mcp.custom_route-Handler deaktiviert (ex. Zeilen 207-215)

Kommentiert: Beide `@mcp.custom_route("/.well-known/...")` Dekoratoren und die zugehoerigen Funktionskoerper.

Grund: Dopplung der Route-Registrierung via FastMCP-internem Router.

### server.py -- Aenderung 3: BOM-Fix in _WellKnownMiddleware._get_base()

`encoding="utf-8"` -> `encoding="utf-8-sig"` beim Lesen von tunnel-url.txt.

Grund: tunnel-url.txt wurde mit UTF-8-BOM (﻿) geschrieben. Das fuehrte dazu dass `url.startswith("http")` False zurueckgab und der Fallback `https://localhost:8765` verwendet wurde -- obwohl der richtige URL im File stand.

### tunnel-url.txt

Neu geschrieben ohne BOM via Python. Cloudflare-Service schreibt beim Restart eine neue URL.

### Backup

`C:\Users\chris\TradingFloor\mcp-bridge\server.py.backup-cc-fix-20260623`

---

## Testergebnis

Tunnel URL zum Testzeitpunkt: `https://indication-democrat-toolkit-adequate.trycloudflare.com`

### GET /.well-known/oauth-protected-resource

```json
{
  "resource": "https://indication-democrat-toolkit-adequate.trycloudflare.com",
  "authorization_servers": ["https://indication-democrat-toolkit-adequate.trycloudflare.com"]
}
```

HTTP 200 -- authorization_servers enthaelt korrekte Tunnel-URL (nicht leer, nicht localhost).

### GET /.well-known/oauth-authorization-server

```json
{
  "issuer": "https://indication-democrat-toolkit-adequate.trycloudflare.com",
  "authorization_endpoint": "https://indication-democrat-toolkit-adequate.trycloudflare.com/oauth/authorize",
  "token_endpoint": "https://indication-democrat-toolkit-adequate.trycloudflare.com/oauth/token",
  "registration_endpoint": "https://indication-democrat-toolkit-adequate.trycloudflare.com/oauth/register",
  "response_types_supported": ["code"],
  "grant_types_supported": ["authorization_code"],
  "code_challenge_methods_supported": ["S256"]
}
```

HTTP 200 -- issuer ist korrekte Tunnel-URL (nicht localhost).

---

## Root Cause Zusammenfassung

Drei Bugs zusammen verhinderten korrekte Responses:

1. Zwei aeltere Handler-Bloecke (route-append + custom_route) fingen `.well-known`-Requests ab bevor `_WellKnownMiddleware` griff.
2. Zusaetzlich hatte tunnel-url.txt einen UTF-8-BOM, der dazu fuehrte dass `_get_base()` auf `https://localhost:8765` fallback machte.
3. Nach dem Fix der Handler (Bug 1) offenbarte sich Bug 2 -- deswegen war ein zweiter Neustart notwendig.
