#!/usr/bin/env python3
"""
EVE: Valkyrie - Warzone — minimal private backend (MVP, clean-room).

Implemented from the interface documentation in docs/ (networking/01-14,
reimpl/01-02). No game code is reused. Goal: serve the documented contract so
the shipped client can boot -> login -> bootstrap a pilot -> request a match.

Covers (per reimpl/01-mvp-server-guide.md):
  - POST /oauth/token            (SSO: Basic 'valkyrieClient', mint HS256 JWT)
  - clients / signup             (bootstrap fingerprint -> id/href/wallet)
  - accounts (v2.0)              (-> pilot_uri)
  - pilots?pilot_id=             (pilot object + HATEOAS *_uri graph)
  - staticdata GetFileList       (files[] manifest)
  - sessionrequests / sessions   (matchmaking -> session)
  - battleservers                (server registration / allocation)
  - everything else              (envelope-wrapped permissive stub + logged)

Every response is wrapped in the documented envelope:
  { "uri","verb","status","message","content": {...} }   (docs/networking/13)

Runs HTTPS on a configurable port (default 8443; use 443 on a host with root).
All requests are logged to logs/requests.log — this is the "oracle" harness:
point the real client at it and watch what it sends / where it 404s.
"""
import base64, hashlib, hmac, json, ssl, time, os, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("VK_PORT", "8443"))
JWT_SECRET = os.environ.get("VK_JWT_SECRET", "valkyrie-preservation-dev-key").encode()
LOG = open(os.path.join(HERE, "logs", "requests.log"), "a", buffering=1)

# Base URL the client will see for HATEOAS links. On a real deploy this is the
# redirected VGS host; for self-test it's our own host:port.
BASE = os.environ.get("VK_BASE", f"https://localhost:{PORT}")

def log(*a):
    line = " ".join(str(x) for x in a)
    LOG.write(f"{time.strftime('%H:%M:%S')} {line}\n")
    print(line, flush=True)

# --- JWT (HS256, stdlib) -----------------------------------------------------
def b64u(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
def mint_jwt(sub, scopes):
    hdr = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {"sub": sub, "scope": scopes, "iat": now, "exp": now + 3600,
               "iss": "valkyrie-local"}
    seg = b64u(json.dumps(hdr).encode()) + "." + b64u(json.dumps(payload).encode())
    sig = b64u(hmac.new(JWT_SECRET, seg.encode(), hashlib.sha256).digest())
    return seg + "." + sig

# --- response envelope (docs/networking/13) ----------------------------------
def envelope(content, verb="GET", uri="", status="ok", message="", extra=None):
    env = {"uri": uri, "verb": verb, "status": status, "message": message,
           "content": content}
    if extra:               # auth/signup envelopes also carry token/provider/signup
        env.update(extra)
    return env

# --- canned content objects (shapes from docs/networking/13) -----------------
WALLET = {"currency": "silver", "balance": {"silver": 50000, "gold": 500}}

def account_obj():
    return {"pilot_uri": f"{BASE}/v1.0/valkyrie/pilots?pilot_id=1",
            "npe_completed": True, "eula_signed": True}

def pilot_obj():
    return {
        "pilot_id": 1, "callsign": "Preserved", "pilot_name": "Preserved",
        "gender": "Male", "has_set_gender": True,
        "reputation_rank": 1, "reputation_score": 0,
        "league_score": 0, "balance": WALLET["balance"],
        "eula_signed": True, "npe_completed": True, "npe_skipped": False,
        "heartbeat_seconds": 30,
        # collections (empty but present)
        "hero_ships": [], "implants": [], "applied_pilot_cosmetics": [],
        "hero_cosmetics": [], "applied_hero_cosmetics": [], "challenges": [],
        "loot_capsules": [], "global_events": [], "settings": {},
        # HATEOAS link graph (docs/networking/13)
        "pilots_uri": f"{BASE}/v1.0/valkyrie/pilots?pilot_id=1",
        "friends_uri": f"{BASE}/v1.0/valkyrie/pilots/1/friends",
        "settings_uri": f"{BASE}/v1.0/valkyrie/pilots/1/settings",
        "cosmetics_uri": f"{BASE}/v1.0/valkyrie/pilots/1/cosmetics",
        "hero_upgrades_uri": f"{BASE}/v1.0/valkyrie/pilots/1/hero_upgrades",
        "hero_cosmetics_uri": f"{BASE}/v1.0/valkyrie/pilots/1/hero_cosmetics",
        "applied_hero_cosmetics_uri": f"{BASE}/v1.0/valkyrie/pilots/1/applied_hero_cosmetics",
        "applied_pilot_cosmetics_uri": f"{BASE}/v1.0/valkyrie/pilots/1/applied_pilot_cosmetics",
        "pilot_cosmetic_uri": f"{BASE}/v1.0/valkyrie/pilots/1/pilot_cosmetic",
        "pilot_cosmetic_variant_uri": f"{BASE}/v1.0/valkyrie/pilots/1/pilot_cosmetic_variant",
        "hero_xp_transfer_uri": f"{BASE}/v1.0/valkyrie/pilots/1/hero_xp_transfer",
        "hero_rewards_uri": f"{BASE}/v1.0/valkyrie/pilots/1/hero_rewards",
        "collectibles_uri": f"{BASE}/v1.0/valkyrie/pilots/1/collectibles",
        "challenges_uri": f"{BASE}/v1.0/valkyrie/pilots/1/challenges",
        "training_uri": f"{BASE}/v1.0/valkyrie/pilots/1/training",
        "recall_uri": f"{BASE}/v1.0/valkyrie/pilots/1/recall",
        "eula_uri": f"{BASE}/v1.0/valkyrie/eula",
        "gender_uri": f"{BASE}/v1.0/valkyrie/pilots/1/gender",
        "npe_complete_uri": f"{BASE}/v1.0/valkyrie/pilots/1/npe_complete",
        "invites_uri": f"{BASE}/v1.0/valkyrie/pilots/1/invites",
        "heartbeat_uri": f"{BASE}/v1.0/valkyrie/pilots/1/heartbeat",
    }

def client_obj(build_version="CL 1219446 : LIVE"):
    # /clients (VkClientResource) registration response. CONTRACT (E3, docs 16):
    #  - returned BARE (NOT envelope-wrapped): the client reads these fields at
    #    the response body TOP LEVEL.
    #  - SUCCESS GATE: a numeric top-level `client_id` (client pre-inits it to -1
    #    and only advances/logs "registered" when it parses a number).
    #  - status must NOT be 409 (the incompatible-build gate) and
    #    deprecated_version must be false.
    # client_id MUST be a JSON number (read via TryGetNumberField; gate is
    # client_id != -1). docs/networking/16 §1, instruction-level verified.
    return {"client_id": 1, "pilot_id": 1,
            "pilot_uri": f"{BASE}/live/pilots/1",
            "callsign": "Preserved", "default_region": "us-east-1",
            "deprecated_version": False, "popups": [],
            "heartbeat_seconds": 30,
            "vkpilot": {**WALLET},
            "id": 1, "href": f"{BASE}/live/clients/1", "build_version": build_version,
            **WALLET}

# REAL static-data catalog: the genuine StaticData/*.json files were recovered
# from the client's own shipped pak (VkGame-WindowsNoEditor.pak, uncompressed) via
# analysis/scripts/pak_extract.py into ./staticdata_real/. These are the authentic
# catalog (currencies, ship classes, game modes, maps, cosmetics, etc.) the client
# expects. We serve each verbatim and build the GetFileList manifest from them with
# md5 checksums (md5 confirmed accepted by the client, 2026-05-23).
SD_DIR = os.path.join(HERE, "staticdata_real")
SD_FILES = {}   # relpath (forward slashes) -> raw bytes
for _root, _dirs, _fns in os.walk(SD_DIR):
    for _fn in _fns:
        if _fn.endswith(".json"):
            _full = os.path.join(_root, _fn)
            _rel = os.path.relpath(_full, SD_DIR).replace("\\", "/")
            with open(_full, "rb") as _fh:
                SD_FILES[_rel] = _fh.read()

# Schema.json files are build-time JSON-schema definitions that happen to sit in
# the pak's StaticData/ tree; they are NOT catalog files the client downloads.
# LIVE EVIDENCE (2026-05-23): when the manifest listed all 43 files (26 data + 17
# Schema.json), the client fetched exactly the 26 data files and NEVER requested a
# single Schema.json — yet the static-data resource's "all files complete" never
# fired (it sat on "DOWNLOADING STATIC DATA" then timed out with "A NETWORK ERROR
# HAS OCCURRED"). The 17 unfetched manifest entries left the download set undrained.
# Fix: advertise only the real catalog files in GetFileList (still serve any path
# that is requested). The real backend's manifest would not have listed Schema.json.
SD_MANIFEST = {rel: data for rel, data in SD_FILES.items()
               if os.path.basename(rel).lower() != "schema.json"}

# EXPERIMENT (VK_SD_FORCE_DOWNLOAD): the client gets the GetFileList manifest, finds
# every md5 already matches its local pak copy, downloads NOTHING, and then never
# signals "static-data complete" — it re-requests the manifest after ~heartbeat_seconds
# and times out ("A NETWORK ERROR HAS OCCURRED"). Hypothesis: completion only fires
# after >=1 real download+validate. To force downloads while KEEPING integrity valid,
# append a newline to each served file so its md5 differs from the client's pak copy
# (-> download) but still equals the manifest checksum (-> integrity passes); trailing
# whitespace is harmless to JSON. Toggle with VK_SD_FORCE_DOWNLOAD=1.
SD_FORCE_DL = os.environ.get("VK_SD_FORCE_DOWNLOAD", "") not in ("", "0")
SD_SERVE = {rel: (data + b"\n" if SD_FORCE_DL else data) for rel, data in SD_FILES.items()}
SD_CKSUM = {rel: hashlib.md5(data).hexdigest() for rel, data in SD_SERVE.items()}

def staticdata_obj():   # GetFileList (docs/networking/10,13) — manifest of real files
    # Advertise only the catalog files (NOT Schema.json — see SD_MANIFEST note).
    return {"files": [{"filename": rel,
                       "uri": f"{BASE}/live/staticdata/{rel}",
                       "checksum": SD_CKSUM[rel]}
                      for rel in sorted(SD_MANIFEST)],
            "branch_name": "LIVE", "build_number": "3195953"}

def session_obj():
    return {"session_id": 1, "session_uri": f"{BASE}/v1.0/valkyrie/sessions?session_id=1",
            "max_pilots": 8, "current_players": 0, "max_spectators": 2,
            "current_spectators": 0, "owner_callsign": "Preserved",
            "owner_platform": "steam", "in_progress": False, "is_joinable": True,
            "status": "open", "custom_settings": {}}

def battleserver_obj():
    return {"href": f"{BASE}/v1.0/valkyrie/battleservers/1", "battle_id": 1,
            "public_ip": "127.0.0.1", "port": 7777,
            "battleServerUri": "ws://127.0.0.1:7777",
            "map_unique_name": "map_default", "game_mode_unique_name": "gm_default"}

# --- routing -----------------------------------------------------------------
class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def _send(self, obj, code=200, extra_headers=None):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        cid = self.headers.get("X-Correlation-Id")
        if cid: self.send_header("X-Correlation-Id", cid)  # echo VGS correlation id
        # Close the connection after each response. Python http.server's HTTP/1.1
        # keep-alive framing made the client's HTTP completion arrive as
        # bWasSuccessful==false on /clients (-> retry/reset loop, docs 16). One
        # request per connection is what the client reliably finalizes.
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(body); self.wfile.flush()
            log(f"<-- {code} sent {len(body)}B ok ({self.path})")
        except Exception as e:
            log(f"<-- {code} WRITE FAILED ({self.path}): {e!r}")
        self.close_connection = True

    def _body(self):
        n = int(self.headers.get("Content-Length", "0") or "0")
        return self.rfile.read(n) if n else b""

    def _route(self, method):
        u = urlparse(self.path); path = u.path; q = parse_qs(u.query)
        body = self._body()
        auth = self.headers.get("Authorization", "")
        host = self.headers.get("Host", "")
        log(f"--> {method} {host}{self.path} auth={auth[:24]!r} body={body[:1500]!r}")

        # OAuth token endpoint (docs/networking/03)
        if path.endswith("/oauth/token"):
            # require Basic (client returns 401 without it; we accept any value)
            if not auth.startswith("Basic "):
                self.send_response(401); self.send_header("WWW-Authenticate","Basic")
                self.send_header("Content-Length","0"); self.send_header("Connection","close")
                self.end_headers(); self.close_connection = True; return
            tok = mint_jwt("pilot:1", "valkyrie.userLogin.v1 vgs.valkyrieVirtualStore.v1 vgs.marketAccess.v1")
            return self._send({"access_token": tok, "refresh_token": mint_jwt("refresh:1","refresh"),
                               "token_type": "bearer", "expires_in": 3600})

        # Telemetry / client-event (Epic DataRouter-style): fire-and-forget.
        # Real service returns a bare 2xx, NOT the VGS envelope — don't confuse
        # the client's first backend response with an envelope it can't parse.
        if "client-event" in path or path.endswith("/client-event"):
            self.send_response(204); self.send_header("Content-Length","0")
            self.send_header("Connection","close"); self.end_headers()
            self.close_connection = True; return

        # Client bootstrap / signup (post-SSO): the client POSTs
        # {"token": <our SSO JWT>, "provider": "signup"} to /<env>/auth and
        # expects the auth-context envelope (token/provider/signup) wrapping the
        # pilot object (docs/networking/13 parse-order). Give it the full pilot
        # so it has every HATEOAS link to continue.
        if path.endswith("/auth"):
            scopes = "valkyrie.userLogin.v1 vgs.valkyrieVirtualStore.v1 vgs.marketAccess.v1"
            return self._send(envelope(pilot_obj(), verb=method, uri=BASE+path,
                extra={"token": mint_jwt("session:1", scopes), "provider": "signup", "signup": True}))

        # VGS REST entry-points (docs/networking/14) -> envelope-wrapped
        def env(content): return envelope(content, verb=method, uri=BASE+path)
        if "accounts" in path:        return self._send(env(account_obj()))
        if "pilots" in path:          return self._send(env(pilot_obj()))
        # staticdata GetFileList: BARE (top-level `files` array), NOT enveloped.
        # The parser looks for a top-level `files` array ("No 'files' array in
        # response to GetFileList", docs/networking/10); enveloping hides it ->
        # StaticDataDownloadFailed (login-blocking) -> client retries then DELETEs
        # its /clients registration ("Network error"). Observed live 2026-05-23.
        # static-data FILE content (manifest points here). Serve RAW bytes — NOT
        # enveloped/JSON-rewrapped — so the client's integrity checksum matches the
        # exact bytes (md5 in the manifest). Must precede the manifest check (file
        # paths also contain "staticdata"). rel = everything after "/staticdata/".
        if "/staticdata/" in path:
            rel = path.split("/staticdata/", 1)[1]
            data = SD_SERVE.get(rel)
            if data is None:
                log(f"!! static file NOT FOUND: {rel!r}")
                self.send_response(404); self.send_header("Content-Length", "0")
                self.send_header("Connection", "close"); self.end_headers()
                self.close_connection = True; return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            # EXPERIMENT: the VkResource completion family gates on a non-empty
            # Location response header (proven for /clients @0x1420b7d70; same shape
            # in the sibling completion @0x142090f00 which GetHeader("Location") then
            # skips processing if empty). The static-data GetFileList + per-file
            # download completions may share that gate, leaving the resource "failed"
            # (-> "DOWNLOADING STATIC DATA" never completes -> 30s timeout). Echo a
            # non-empty Location (the file's own URI) on every static-data response.
            self.send_header("Location", f"{BASE}/live/staticdata/{rel}")
            self.send_header("Connection", "close")
            self.end_headers()
            try:
                self.wfile.write(data); self.wfile.flush()
                log(f"<-- 200 sent {len(data)}B static file ({rel})")
            except Exception as e:
                log(f"<-- static file WRITE FAILED ({rel}): {e!r}")
            self.close_connection = True
            return
        if path.endswith("/staticdata") or "GetFileList" in path:
            # See Location note above: send a non-empty Location on the manifest too,
            # in case the GetFileList completion shares the /clients Location gate.
            return self._send(staticdata_obj(),
                              extra_headers={"Location": f"{BASE}/live/staticdata"})
        if "clients" in path or "signup" in path:
            bv = "CL 1219446 : LIVE"
            try: bv = (json.loads(body or b"{}").get("app_info") or {}).get("build_version", bv)
            except Exception: pass
            # BARE, top-level object (NOT envelope-wrapped). The success gate at
            # VkClientResource completion (VA 0x1420b7d70, RVA 0x20b7d70) reads
            # `client_id` with TryGetNumberField at the response body TOP LEVEL and
            # requires client_id != -1 (docs/networking/16, re-verified 2026-05-23).
            # The earlier "enveloped like /auth" change was based on a Frida result
            # later found to be a wrong-RVA bug (base+0xb7d70 instead of +0x20b7d70),
            # so the handler was never actually disproven. client_obj() already has
            # client_id/pilot_id as top-level JSON numbers.
            #
            # CRITICAL: the /clients completion handler (VA 0x1420b7d70) reads the
            # "Location" response header and case-insensitively compares it to the
            # EMPTY string; if Location is empty/absent it skips the body parse
            # entirely (je 0x1420b86d2) and broadcasts FAILURE (state stays 1) ->
            # the client retries forever. Only a NON-EMPTY Location makes it parse
            # the body, read client_id, and succeed. (Verified by Stalker call-trace
            # + disasm 2026-05-23; docs/networking/16 had this backwards.) So we MUST
            # send a non-empty Location (the created client resource URI).
            return self._send(client_obj(bv),
                              extra_headers={"Location": f"{BASE}/live/clients/1"})
        if "sessionrequests" in path: return self._send(env(session_obj()))
        if "sessions" in path:        return self._send(env(session_obj()))
        if "battleservers" in path:   return self._send(env(battleserver_obj()))
        # permissive stub: empty content, 200, logged (client tolerates missing fields)
        return self._send(env({}))

    def do_GET(self):    self._route("GET")
    def do_POST(self):   self._route("POST")
    def do_PUT(self):    self._route("PUT")
    def do_DELETE(self): self._route("DELETE")
    def log_message(self, *a): pass   # we do our own logging

def main():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(os.path.join(HERE, "certs", "server.crt"),
                        os.path.join(HERE, "certs", "server.key"))
    # The shipped client is from 2017 and its TLS stack predates TLS 1.3.
    # Cap the protocol/cipher set so an old client can negotiate. Configurable
    # via VK_TLS_MAX (e.g. "1.2"); default unrestricted for the self-test.
    tls_max = os.environ.get("VK_TLS_MAX", "")
    if tls_max == "1.2":
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        try:
            ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        except ssl.SSLError:
            pass
    # Export TLS session keys so a loopback capture can be decrypted for analysis
    # (diagnosing the /clients loop). VK_KEYLOG=<path>.
    kl = os.environ.get("VK_KEYLOG", "")
    if kl:
        try: ctx.keylog_filename = kl
        except Exception as e: log(f"keylog unavailable: {e}")
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), H)
    srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    log(f"=== Valkyrie local backend on https://0.0.0.0:{PORT} (BASE={BASE}) tls_max={tls_max or 'default'} ===")
    srv.serve_forever()

if __name__ == "__main__":
    main()
