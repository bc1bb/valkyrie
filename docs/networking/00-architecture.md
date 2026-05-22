---
doc: net-architecture
title: Networking Architecture (Big Picture)
summary: Three communication planes — REST backend (libcurl/TLS), realtime UE4 replication over WebSockets (libwebsockets), and platform identity (Steam/Oculus).
keywords: [architecture, networking, rest, websocket, online subsystem, steam, oculus, planes, overview]
status: draft
updated: 2026-05-22
evidence: [E1, E2, E5]
---

# Networking Architecture — Big Picture

The client talks to the outside world over **three distinct planes**. Keeping
them separate is the key mental model for a server re-implementation.

```
                ┌─────────────────────────────────────────────┐
                │            EVE: Valkyrie client               │
                └───────┬───────────────┬───────────────┬──────┘
                        │               │               │
            (1) REST/HTTPS      (2) WebSocket NetDriver  (3) Platform SDK
            libcurl+OpenSSL     libwebsockets (+TLS)     Steamworks / Oculus
                        │               │               │
                ┌───────▼──────┐ ┌──────▼───────┐ ┌──────▼───────┐
                │ Backend REST │ │  Game server │ │ Steam / Oculus│
                │  services    │ │ (UE4 host)   │ │  platform     │
                │ (VkRestUtils)│ │ via WS replic│ │  (identity)   │
                └──────────────┘ └──────────────┘ └──────────────┘
```

## Plane 1 — REST backend (account, meta, matchmaking request)

- Library: **libcurl** over **OpenSSL** (HTTPS).
- Code: `VkRestUtils` module — a family of `Vk*Resource` classes, each wrapping
  one backend resource (auth, pilots, battles, sessions, store, leaderboards…).
- Purpose: login/SSO, profile & progression, virtual goods, loadouts,
  leaderboards, **requesting a match / battle server allocation**.
- This is request/response (likely JSON). It is *not* the realtime gameplay path.
- Detail: `networking/01-rest-backend.md`.

## Plane 2 — Realtime gameplay replication (WebSockets)

- Transport: UE4's **HTML5Networking `WebSocketNetDriver`** over **libwebsockets**.
- Notable: EVE Valkyrie does **not** use the default UE4 UDP `IpNetDriver` for
  replication — it uses WebSockets (TCP). This likely simplified NAT traversal /
  console+platform networking and let one transport serve all platforms.
- Carries the standard UE4 replication model (actor channels, property
  replication, RPCs) but framed inside WebSocket messages. (E5: engine-stock
  semantics; E1/E2: the driver selection is Vk-specific config.)
- Detail: `networking/02-websocket-netdriver.md`.

## Plane 3 — Platform identity / entitlement

- **Steamworks** (`steam_api64.dll`, SDK v132) + **`OnlineSubsystemVkSteam`**.
- **Oculus** path: `OnlineSubsystemVk/Private/VkOculusPlatform.cpp` → the game
  also supports Oculus platform identity (it launched on Oculus Home first).
- Role: obtain a platform identity / auth ticket, which Plane 1 likely exchanges
  for a backend session token (CCP SSO). Ordering TBD (open question).

## Likely session lifecycle (hypothesis, E5 — to verify by capture)

1. Platform login (Steam/Oculus) → platform ticket.
2. REST: exchange ticket via auth/SSO resource → backend session token.
3. REST: fetch pilot profile, static data, virtual goods, loadouts.
4. REST: request a battle/session → backend allocates a game server, returns
   its WebSocket address + a join token.
5. Connect Plane 2 WebSocket to that game server; UE4 replication runs the match.
6. REST: post-match results, progression, leaderboards; watchdog heartbeats.

Each numbered step maps to specific `Vk*Resource` classes — see the REST doc.
This lifecycle is the **re-implementation target**: a server must satisfy steps
2–6 to make the game playable again.
