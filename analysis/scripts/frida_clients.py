#!/usr/bin/env python3
"""
frida_clients.py — live instrumentation of the shipped client's POST /clients
(VkClientResource) completion path, to learn why it loops instead of advancing.

Clean-room: hooks the locally-held binary by RVA (addresses from docs/networking/16,
recovered by our own disassembly). Logs only control-flow/branch facts — no
copyrighted bytes. Distil findings into docs as prose.

RVAs (image base 0x140000000) — CORRECTED 2026-05-23. The earlier values
(0xb7d70 etc.) were WRONG: they dropped the leading 0x2 of the 0x20b… RVA, so the
hooks landed at base+0xb7d70 (VA 0x1400b7d70, cold) and never fired. The functions
are at absolute VA 0x1420…; subtract image base 0x140000000 to get the RVA:
  0x20b7d70  /clients response-completion handler entry   (VA 0x1420b7d70)
  0x20b85a8  the success gate: cmp dword [r15+0x14], -1    (VA 0x1420b85a8; r15+0x14 = parsed client_id)
  0x20b7b40  transport-failure helper (null/!bWasSuccessful response path) (VA 0x1420b7b40)
  0x20845d0  pilot_uri continuation builder (runs only on success) (VA 0x1420845d0)
  0x2038010  JSON-parse entry                              (VA 0x142038010)

Usage: python analysis/scripts/frida_clients.py   (then launch the game via Steam)
Runs ~180s, attaching as soon as the process appears, logging every hit.
"""
import frida, time, sys

NAME = "EVE Valkyrie - Warzone.exe"
JS = r"""
var base = Process.getModuleByName("EVE Valkyrie - Warzone.exe").base;
send("base=" + base);
// CONTROL: hook a guaranteed-hot system export to prove Frida interception works.
var recvFn = null;
try { recvFn = Module.getGlobalExportByName("recv"); } catch(e){}
if (!recvFn) { try { recvFn = Process.getModuleByName("ws2_32.dll").getExportByName("recv"); } catch(e){} }
if (recvFn) {
  var rc = 0;
  Interceptor.attach(recvFn, { onEnter: function(){ rc++; if (rc<=3 || rc%200===0) send("CONTROL recv #" + rc); } });
  send("hooked recv (control)");
} else send("could not hook recv");
// Parser: log EVERY call (capped), dump readable args, to see if 0x38010 fires at all.
var pc = 0;
try {
  Interceptor.attach(base.add(0x2038010), { onEnter: function () {
    pc++;
    if (pc > 40) return;
    var c = this.context, s = "";
    [["rcx",c.rcx],["rdx",c.rdx],["r8",c.r8]].forEach(function(kv){
      try { var w = kv[1].readUtf16String(50); if (w && /[A-Za-z_{]/.test(w)) s += " "+kv[0]+"w='"+w+"'"; } catch(e){}
      try { var pp = kv[1].readPointer(); var w2 = pp.readUtf16String(50); if (w2 && /[A-Za-z_{]/.test(w2)) s += " "+kv[0]+"*w='"+w2+"'"; } catch(e){}
    });
    send("PARSE#" + pc + s);
  }});
  send("hooked parser 0x2038010 (all calls, capped 40)");
} catch (e) { send("HOOK FAIL parser: " + e); }

// /clients completion handler — the decisive hook. The UE4 completion delegate
// signature is Method(this, FHttpRequestPtr Request, FHttpResponsePtr Response,
// bool bWasSuccessful), so Win64 regs are rcx=this, rdx=Request, r8=Response,
// r9=bWasSuccessful. Last run proved the handler ENTERS with a non-null Response
// but EXITS before the body parse (state stays 1, client_id stays -1) — so the
// decisive bit is bWasSuccessful (r9) and which early-exit branch is taken.
try {
  var hVA = base.add(0x20b7d70);
  Interceptor.attach(hVA, { onEnter: function () {
    var c = this.context;
    var resp = c.r8;
    // SAFE: bWasSuccessful is the 4th arg, sitting in r9 (low byte). Pure
    // register read — NO dereference, NO calling vtable functions (the earlier
    // "probe vtable slots by calling them" crashed the game with a jump to 0x0).
    var bWasSuccessful = c.r9.and(0xff).toInt32();
    var respState = resp.isNull() ? "NULL" : "non-null";
    this.self = c.rcx;
    send("CLIENTS-COMPLETE enter: this=" + c.rcx + " Response=" + resp +
         " (" + respState + ") bWasSuccessful=" + bWasSuccessful);
  }, onLeave: function () {
    try { send("CLIENTS-COMPLETE leave: state[+0xa0]=" + this.self.add(0xa0).readInt() +
                " client_id[+0x14]=" + this.self.add(0x14).readInt() +
                " pilot_id[+0x18]=" + this.self.add(0x18).readInt()); } catch (e) {}
  }});
  send("hooked /clients completion 0x20b7d70 (now logs bWasSuccessful)");
} catch (e) { send("HOOK FAIL completion: " + e); }

// success gate + registered + transport-fail markers. ONLY this proven-safe set
// (run 1 hooked exactly these and ran clean). The four tail hooks tried earlier
// (0x20b87a7/869b/86e2/8736) crashed the game deterministically — one is not an
// instruction boundary, so Frida's inline patch corrupted the handler. Removed.
// We don't need them: run 1 already showed the body is never parsed and the gate
// is never reached; the only missing bit is bWasSuccessful (the safe r9 read).
[["GATE 0x20b85a8 (cmp client_id,-1)", 0x20b85a8],
 ["REGISTERED 0x20b85e3", 0x20b85e3],
 ["TRANSPORT-FAIL 0x20b7b40", 0x20b7b40],
 ["CONTINUATION 0x20845d0 (pilot_uri load)", 0x20845d0]].forEach(function (kv) {
  try {
    var hit = 0;
    Interceptor.attach(base.add(kv[1]), { onEnter: function () {
      hit++; if (hit <= 5 || hit % 50 === 0) send("HIT " + kv[0] + " #" + hit);
    }});
    send("hooked " + kv[0]);
  } catch (e) { send("HOOK FAIL " + kv[0] + ": " + e); }
});
"""

def main():
    dev = frida.get_local_device()
    print("waiting for a 'valkyrie' process ...", flush=True)
    pid = None
    deadline = time.time() + 300
    last_dump = 0
    while pid is None and time.time() < deadline:
        procs = dev.enumerate_processes()
        for p in procs:
            n = p.name.lower()
            if "warzone" in n or "valkyrie" in n:   # NOT eveclassic
                pid = p.pid; print("found:", repr(p.name), pid, flush=True); break
        if pid is None and time.time() - last_dump > 5:
            last_dump = time.time()
            cands = [p.name for p in procs if any(s in p.name.lower() for s in ("eve","valk","warz","game"))]
            print(f"[{int(time.time()%1000)}] {len(procs)} procs; candidates: {cands}", flush=True)
        time.sleep(0.2)
    if pid is None:
        print("process never appeared (5 min)", flush=True); return
    print("attaching to pid", pid, flush=True)
    session = dev.attach(pid)
    script = session.create_script(JS)
    # encode-safe print: the console is cp1252 and payloads can carry non-ASCII
    # (URIs, JSON) which otherwise crash the message callback mid-run.
    def _msg(m, d):
        s = str(m.get("payload", m))
        print("MSG:", s.encode("ascii", "replace").decode("ascii"), flush=True)
    script.on("message", _msg)
    script.load()
    print("hooks loaded; logging until process exits or 180s", flush=True)
    end = time.time() + 180
    while time.time() < end:
        try:
            if not any(p.pid == pid for p in dev.enumerate_processes()):
                print("process exited", flush=True); break
        except Exception:
            break
        time.sleep(0.5)

if __name__ == "__main__":
    main()
