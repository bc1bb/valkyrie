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
- **Connection** → **Control channel** (channel 0) handshake (below).
- **Actor channels** carry property replication + RPC "bunches".
- **Packages/GUIDs**: the client and server must agree on the loaded map and
  package versions; mismatches are rejected at the control-channel handshake.

### Control-channel handshake (UE 4.14, engine-stock)

Control-message types **confirmed present in the binary (E2):** `NMT_Login`,
`NMT_Failure`, `NMT_JoinSplit`, `NMT_NetGUIDAssign`, `NMT_DebugText`, plus
`Hello`/`Challenge`/`Welcome` and `NetworkVersion`/`EngineNetworkVersion`/
`GameNetworkVersion`. The full stock 4.14 sequence (E5) a re-impl server must
speak:

```
client → server : NMT_Hello   (IsLittleEndian, RemoteNetworkVersion)
server          : validate version → on mismatch NMT_Upgrade/NMT_Failure
                  (=> ENetworkFailure::OutdatedClient/Server, 09-*)
server → client : NMT_Challenge (nonce string)
client → server : NMT_Login    (challenge response, request URL/options,
                                 UniqueNetId from OnlineSubsystemVk, + join token)
server          : auth/capacity OK?
server → client : NMT_Welcome  (map/gamemode/redirect)  | NMT_Failure
client           : load map; NMT_Netspeed; then
client → server : NMT_Join      (or NMT_JoinSplit for splitscreen)
server          : spawn player; NMT_NetGUIDAssign for object-ref GUIDs
```

- **Version gate:** `EngineNetworkVersion` + `GameNetworkVersion` must match
  (UE 4.14.3 / CL 3195953, `engine/01-*`) or the handshake aborts.
- **Battle connection auth (E2/E5):** the battle connection is initiated via
  `ConnectToBattle` / `eOnConnectingToServer_Event`. The app-level join
  authorization is layered on UE4's `NMT_Login` — the join credential (the
  backend-issued JWT/session token from `03-*`/`06-*`) rides in the login
  options / connect-URL of the WebSocket connect. The **exact wire layout** of
  the join token still needs a capture (E4) or deeper struct RE.
  > **Correction (2026-05-23):** an earlier draft here claimed a Valkyrie
  > "capability-token" system from the strings `CapTokenTBS`/`AuthTokenTBE`/
  > `CapTokenSeq`/etc. **That was a false positive.** Those are the `setct-*`/
  > `setAttr-*` **SET (Secure Electronic Transaction) ASN.1 OID names** built
  > into statically-linked **OpenSSL**'s object table (164 `setct-` + the full
  > `setAttr-` set are present, e.g. `setct-PANData`, `setct-OIData`) — a
  > linking artifact, *not* game code. No evidence of a bespoke CapToken system
  > remains; treat the join auth as the standard backend token over `NMT_Login`.
- Everything else is documented UE 4.14 behaviour; a re-impl built on the same
  engine inherits it. Reuse the public engine to satisfy the handshake.

## Vk-specific seams to determine (open questions)

- The **`Sec-WebSocket-Protocol`** subprotocol: **no game-specific subprotocol
  name string exists** in the binary (E2 — searched all strings; only
  libwebsockets internals + `Sec-WebSocket-Protocol: ` with a `%s`/empty value
  appear). So the UE4 HTML5Networking driver registers an **empty/default
  subprotocol** (libwebsockets `lws_protocols` with no/`""` name). A
  re-implemented server therefore does **not** need to match a specific
  subprotocol value — accept the handshake without requiring one. (Verify the
  exact on-wire header with a capture if strict, but the contract is "no
  specific subprotocol".)
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
