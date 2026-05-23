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

def client_obj():   # /clients response: fingerprint echo + id/href + wallet (docs/networking/14)
    return {"id": 1, "href": f"{BASE}/v1.0/valkyrie/clients/1",
            "client_id": "valkyrieClient", "build_version": "LIVE",
            "os_platform": "WindowsNoEditor", "hmd_type": "Rift", "is_2d": False,
            **WALLET}

def staticdata_obj():   # GetFileList (docs/networking/10,13)
    return {"files": [], "branch_name": "LIVE", "build_number": "3195953"}

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
    def _send(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length", "0") or "0")
        return self.rfile.read(n) if n else b""

    def _route(self, method):
        u = urlparse(self.path); path = u.path; q = parse_qs(u.query)
        body = self._body()
        auth = self.headers.get("Authorization", "")
        log(f"--> {method} {self.path} auth={auth[:24]!r} body={body[:200]!r}")

        # OAuth token endpoint (docs/networking/03)
        if path.endswith("/oauth/token"):
            # require Basic (client returns 401 without it; we accept any value)
            if not auth.startswith("Basic "):
                self.send_response(401); self.send_header("WWW-Authenticate","Basic")
                self.send_header("Content-Length","0"); self.end_headers(); return
            tok = mint_jwt("pilot:1", "valkyrie.userLogin.v1 vgs.valkyrieVirtualStore.v1 vgs.marketAccess.v1")
            return self._send({"access_token": tok, "refresh_token": mint_jwt("refresh:1","refresh"),
                               "token_type": "bearer", "expires_in": 3600})

        # VGS REST entry-points (docs/networking/14) -> envelope-wrapped
        def env(content): return envelope(content, verb=method, uri=BASE+path)
        if "accounts" in path:        return self._send(env(account_obj()))
        if "pilots" in path:          return self._send(env(pilot_obj()))
        if "staticdata" in path or "GetFileList" in path: return self._send(env(staticdata_obj()))
        if "clients" in path or "signup" in path:         return self._send(env(client_obj()))
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
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), H)
    srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    log(f"=== Valkyrie local backend on https://0.0.0.0:{PORT} (BASE={BASE}) ===")
    srv.serve_forever()

if __name__ == "__main__":
    main()
