---
doc: net-anticheat
title: Anti-Cheat & Integrity Posture
summary: No dedicated client anti-cheat (no EAC/BattlEye/PunkBuster) — only Steam VAC (passive) + engine-stock integrity (NetChecksum, NMT_SecurityViolation) + server-authoritative gameplay + backend token/ticket validation. Good news: a private server is not blocked by kernel-level anti-cheat.
keywords: [anticheat, anti-cheat, integrity, vac, eac, battleye, netchecksum, securityviolation, server-authoritative, steam ticket, security, preservation]
status: draft
updated: 2026-05-22
evidence: [E1, E2]
---

# Anti-Cheat & Integrity Posture

What protects match integrity, and what a private server must (not) deal with.

## No dedicated client anti-cheat (E1/E2)

Searched the binary + shipped DLLs: **no EasyAntiCheat, BattlEye, PunkBuster,
GameGuard, Xigncode, or Denuvo** — neither product strings nor AC client DLLs.
So there is **no kernel-mode / always-on anti-cheat** to defeat or integrate.
**Preservation implication:** a re-implemented server (and DNS/host redirection)
is **not** blocked or detected by an active anti-cheat layer — a major plus.

## What integrity it does rely on

1. **Server-authoritative gameplay** (the primary defense, `08-*`): clients
   *request* actions (`ServerMove`, `ServerStartFire`); the server resolves
   movement/hits. A faithful re-impl server keeps authority and is cheat-resistant
   by construction.
2. **Steam VAC** (`VAC`, E2): Valve Anti-Cheat is **passive and Steam-managed**
   — it scans for known cheat signatures client-side and is orthogonal to the
   game backend. It does not gate connecting to a private server and needs no
   server-side integration. (Only relevant on the Steam build.)
3. **Engine-stock net integrity** (E2): `NetChecksumMismatch` (UE4 package/
   version checksum — rejects mismatched content at the control-channel
   handshake, `02-*`) and `NMT_SecurityViolation` (UE4 control-message for
   malformed/illegal bunches). These are version/format guards, not behavioral
   anti-cheat.
4. **Backend credential validation**: the `steam_ticket` OAuth grant (`03-*`)
   lets the backend validate a real Steam session ticket via Steamworks
   server APIs; the Oculus grant validates the Oculus identity. A re-impl SSO can
   validate or stub these (it controls its own policy, `13-*`).

## Re-implementation guidance

- No anti-cheat bypass is needed; do **not** ship or emulate EAC/BattlEye.
- Keep the dedicated server **authoritative** for gameplay to retain integrity.
- Match the **network version** (UE 4.14.3 / CL 3195953, `engine/01-*`) so
  `NetChecksum`/handshake checks pass.
- Ticket validation can be permissive in a private/preservation context (the
  player base is trusted); tighten only if desired.

## Open questions

- Whether the backend strictly enforced Steam ticket validity (vs. trusting the
  client) — affects how permissive a re-impl SSO can be. Confirm by capture if a
  stricter posture is wanted.
