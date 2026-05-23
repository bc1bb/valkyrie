#!/usr/bin/env python3
"""Start the backend in a thread and exercise the documented contract in-process.
Avoids shell backgrounding (sandbox kills detached listeners)."""
import threading, time, ssl, json, os, urllib.request, importlib.util, sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("vksrv", os.path.join(HERE, "server.py"))
srv = importlib.util.module_from_spec(spec); spec.loader.exec_module(srv)

t = threading.Thread(target=srv.main, daemon=True); t.start()
time.sleep(1.5)

# client trusts our local CA
ctx = ssl.create_default_context(cafile=os.path.join(HERE, "certs", "ca.crt"))
ctx.check_hostname = False  # we hit localhost; SANs cover the real hosts

def req(method, path, data=None, auth=None, raw=False):
    url = f"https://localhost:{srv.PORT}{path}"
    r = urllib.request.Request(url, method=method,
        data=(data.encode() if isinstance(data,str) else data))
    if auth: r.add_header("Authorization", auth)
    try:
        with urllib.request.urlopen(r, context=ctx, timeout=5) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

P=lambda *a: print("  ",*a)
ok=0; fail=0
def check(name, cond, detail=""):
    global ok,fail
    print(("PASS " if cond else "FAIL ")+name+("  "+detail if detail else ""))
    ok+=cond; fail+=(not cond)

print("=== Valkyrie local backend — contract self-test ===")
# 1 SSO 401
c,_ = req("POST","/oauth/token",data="x=1")
check("SSO rejects missing Basic auth (401)", c==401, f"got {c}")
# 2 SSO token
c,b = req("POST","/oauth/token",data="grant_type=steam_ticket&steam_ticket=abc&intellectual_property=VALKYRIE",auth="Basic dmFsa3lyaWVDbGllbnQ6")
d=json.loads(b) if c==200 else {}
check("SSO mints bearer JWT", c==200 and d.get("token_type")=="bearer" and d.get("access_token","").count(".")==2,
      f"type={d.get('token_type')} segs={d.get('access_token','').count('.')+1}")
# 3 accounts -> pilot_uri
c,b = req("GET","/v2.0/valkyrie/accounts/",auth="Bearer "+d.get("access_token","x"))
e=json.loads(b); check("accounts: envelope + pilot_uri",
      set(["uri","verb","status","content"]).issubset(e) and "pilot_uri" in e["content"],
      e["content"].get("pilot_uri",""))
# 4 pilot HATEOAS
c,b = req("GET","/v1.0/valkyrie/pilots?pilot_id=1")
pc=json.loads(b)["content"]; links=[k for k in pc if k.endswith("_uri")]
check("pilot: id+callsign+balance+links", pc.get("pilot_id")==1 and "balance" in pc and len(links)>=15,
      f"{len(links)} *_uri links, balance={pc['balance']}")
# 5 staticdata
c,b = req("GET","/v1.0/valkyrie/staticdata/GetFileList")
sc=json.loads(b)["content"]; check("staticdata: files[]+branch+build",
      "files" in sc and "branch_name" in sc and "build_number" in sc, str(sc))
# 6 battleservers
c,b = req("POST","/v1.0/valkyrie/battleservers",data="{}")
bc=json.loads(b)["content"]; check("battleservers: battleServerUri (Plane1->2)",
      bc.get("battleServerUri","").startswith("ws://"), bc.get("battleServerUri",""))
# 7 sessionrequests
c,b = req("POST","/v1.0/valkyrie/sessionrequests",data="{}")
check("sessionrequests -> session", json.loads(b)["content"].get("is_joinable")==True)
# 8 unknown resource -> permissive stub
c,b = req("GET","/v1.0/valkyrie/leaderboards/hero")
check("unknown resource -> 200 envelope stub", c==200 and "content" in json.loads(b))
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
