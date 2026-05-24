#!/usr/bin/env python3
"""
clients_stalker.py — Stalker-trace the /clients completion handler (0x20b7d70)
to see its ACTUAL executed call sequence on a live completion.

Why Stalker (not Interceptor): the static model (docs/networking/16) keeps
mismatching live behaviour — the handler enters with a non-null Response but
exits without hitting ANY instrumented point (parse/gate/transport-fail/etc.).
Inline hooks at guessed mid-function addresses also crashed the game (Frida
patches original bytes). Stalker JITs a *copy* of the code and records what runs
WITHOUT patching the original — safe, and it shows the real branch path.

Approach: on entry to 0x20b7d70, follow the current thread capturing CALL events;
on leave, unfollow and dump the in-order list of call targets that land inside
the game module (as RVAs). That reveals exactly which subroutines the handler
invokes (status getter? body parser 0x2038010? error helper 0x20b7b40? the
pilot_uri continuation 0x20845d0?) and therefore where it diverges.

Clean-room: logs only RVAs/control-flow of the locally-held binary; no bytes.
Usage: python analysis/scripts/clients_stalker.py   (then launch via Steam)
"""
import frida, time

NAME = "EVE Valkyrie - Warzone.exe"
JS = r"""
var mod = Process.getModuleByName("EVE Valkyrie - Warzone.exe");
var base = mod.base, modEnd = base.add(mod.size);
send("base=" + base + " size=0x" + mod.size.toString(16));

function inMod(p){ return p.compare(base) >= 0 && p.compare(modEnd) < 0; }
function rva(p){ return "0x" + p.sub(base).toString(16); }

// Stalker the /clients completion handler's own execution.
var handler = base.add(0x20b7d70);
Interceptor.attach(handler, {
  onEnter: function () {
    this.calls = [];
    var calls = this.calls;
    this.tid = Process.getCurrentThreadId();
    send("STALK begin: handler entered, following tid " + this.tid);
    Stalker.follow(this.tid, {
      events: { call: true },
      onReceive: function (events) {
        var rows = Stalker.parse(events, { annotate: true, stringify: false });
        for (var i = 0; i < rows.length; i++) {
          var r = rows[i];
          if (r[0] === 'call') {
            var to = ptr(r[2]);
            if (inMod(to)) {
              var s = rva(to);
              // collapse immediate repeats to keep the list readable
              if (calls.length === 0 || calls[calls.length - 1] !== s) calls.push(s);
            }
          }
        }
      }
    });
  },
  onLeave: function () {
    try { Stalker.unfollow(this.tid); Stalker.flush(); } catch (e) {}
    var c = this.calls || [];
    send("STALK end: " + c.length + " in-module calls; first 150 (RVA, in order):");
    send("CALLS " + c.slice(0, 150).join(" "));
  }
});
send("hooked + will stalk /clients completion 0x20b7d70");

// control: prove interception works
try {
  var recvFn = Module.getGlobalExportByName("recv");
  var rc = 0;
  Interceptor.attach(recvFn, { onEnter: function () { rc++; if (rc <= 2) send("CONTROL recv #" + rc); } });
} catch (e) {}
"""

def main():
    dev = frida.get_local_device()
    print("waiting for a 'valkyrie' process ...", flush=True)
    pid = None
    deadline = time.time() + 300
    last = 0
    while pid is None and time.time() < deadline:
        procs = dev.enumerate_processes()
        for p in procs:
            n = p.name.lower()
            if "warzone" in n or "valkyrie" in n:
                pid = p.pid; print("found:", repr(p.name), pid, flush=True); break
        if pid is None and time.time() - last > 5:
            last = time.time(); print(f"[{int(time.time()%1000)}] waiting...", flush=True)
        time.sleep(0.2)
    if pid is None:
        print("process never appeared (5 min)", flush=True); return
    print("attaching to pid", pid, flush=True)
    session = dev.attach(pid)
    script = session.create_script(JS)
    def _msg(m, d):
        s = str(m.get("payload", m))
        print("MSG:", s.encode("ascii", "replace").decode("ascii"), flush=True)
    script.on("message", _msg)
    script.load()
    print("stalker hook loaded; logging until process exits or 180s", flush=True)
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
