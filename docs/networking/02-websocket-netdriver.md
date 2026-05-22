---
doc: net-websocket
title: WebSocket Replication Transport
summary: Realtime gameplay uses UE4's HTML5Networking WebSocketNetDriver over libwebsockets (TCP), not the default UDP IpNetDriver.
keywords: [websocket, netdriver, replication, libwebsockets, html5networking, ue4, transport, gameplay, rpc]
status: draft
updated: 2026-05-22
evidence: [E1, E2, E5]
---

# WebSocket Replication Transport

## What it is

Realtime in-match networking (actor replication, RPCs, movement) is carried by
Unreal Engine 4's **`WebSocketNetDriver`** from the
`Engine/Plugins/Experimental/HTML5Networking` plugin, implemented over
**libwebsockets**. Evidence (E1/E2): embedded source paths for
`WebSocketNetDriver.cpp`, `WebsocketConnection.cpp`, `WebSocket.cpp`, plus
libwebsockets handshake strings (`Sec-WebSocket-Key`, `Upgrade: websocket`,
`Sec-WebSocket-Protocol: %s`, `Sec-WebSocket-Version: %d`).

## Why it matters (and is unusual)

UE4 games normally replicate over **UDP** via `IpNetDriver`. EVE Valkyrie
instead uses **WebSockets over TCP**. Implications for a server re-impl:

- The game server must speak the WebSocket protocol (HTTP Upgrade handshake
  then framed messages), not raw UDP packets.
- Reliability/ordering come from TCP; UE4's own reliability layer rides on top.
- A re-implemented dedicated server can reuse UE 4.14's HTML5Networking driver
  directly (engine-stock, E5) — the proprietary part is only *which* driver is
  configured and any custom handshake/subprotocol string.

## UE4 replication model carried inside (E5 — engine-stock)

Inside the WebSocket byte stream, UE4 framing is standard for 4.14:
- **Connection** → **Control channel** (channel 0) handshake: `NMT_Hello`,
  `NMT_Challenge`, `NMT_Login`, `NMT_Welcome`, `NMT_Join` control messages.
- **Actor channels** carry property replication + RPC "bunches".
- **Packages/GUIDs**: the client and server must agree on the loaded map and
  package versions; mismatches are rejected at the control-channel handshake.

These are documented UE 4.14 behaviours; reuse the public engine to satisfy them.

## Vk-specific seams to determine (open questions)

- The **`Sec-WebSocket-Protocol`** subprotocol string the client requests (must
  be echoed by the server to complete the handshake).
- WebSocket path/URL the client connects to (provided by
  `VkBattleServerResource`, Plane 1 — see `01-rest-backend.md`).
- Whether the WS uses TLS (`wss://`) or plain `ws://`, and on what port.
- Any pre-login app-level token check layered on UE4's `NMT_Login` (e.g. the
  backend join token from battle-server allocation).
- Whether replication uses `Iris`/custom serialization — unlikely in 4.14;
  expect stock `FArchive`/`FBitWriter` bunching.

## Bridge from Plane 1

The match flow is: REST allocates a battle server (`VkBattleServerResource`) →
client receives a server address + join token → client opens the WebSocket
NetDriver connection to that address → UE4 control-channel login (carrying the
token) → replication begins. Confirming the token's placement in the handshake
is the single most important capture target for restoring multiplayer.
