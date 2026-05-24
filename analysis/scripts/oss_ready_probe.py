#!/usr/bin/env python3
"""
oss_ready_probe.py — observation-only: locate where the natural store-subsystem
attach chain breaks in 2D mode (no forcing).

Chain (from clean-room RE, docs/reimpl/07):
  online/session subsystem ready latch  session+0x870  <- set by 0x1402f0d00
      iff  byte[session+0x858] != 0   (OSS "logged-in / session-valid")
  store-subsystem attach  0x1404f2b50  (sets GameInstance+0x18c0, arms delegates,
      calls store loader)  -- registered by the session pump 0x14036a670 only when
      session+0x870 != 0 AND global byte 0x143851965 (the launch "-vr" flag) AND a
      vtable predicate.
  store-subsystem update/ready callback  0x1404ee230  -> sets GameInstance+0x19d0=1
      (the lone login gate).

This probe READS ONLY (no writes). It reports, on a 2D launch:
  - the value of the candidate "-vr" global 0x143851965 (RVA 0x3851965),
  - whether/when the OSS logged-in byte (+0x858) and ready latch (+0x870) flip,
  - whether the store-attach 0x1404f2b50 is ever reached,
  - whether the +0x19d0 setter 0x1404ee230 is ever reached,
  - the login state enum (+0x890) for correlation.
So we can see exactly which link is missing without changing behaviour.
Usage: python analysis/scripts/oss_ready_probe.py   (then launch via Steam)
"""
import frida, time

JS = r"""
var base = Process.getModuleByName("EVE Valkyrie - Warzone.exe").base;
function rva(p){ try { var d=p.sub(base); if (d.compare(0)>=0 && d.compare(0x4000000)<0) return "vk+0x"+d.toString(16);} catch(e){} return ""+p; }
send("base="+base);

var VRFLAG = base.add(0x3851965);
function vrflag(){ try { return VRFLAG.readU8(); } catch(e){ return "err"; } }
send("[init] -vr-candidate global 0x143851965 = " + vrflag());

var lastB858 = -1, lastB870 = -1, ossCalls = 0;
var attachSeen = false, setterSeen = false;
var lastState = -999, ticks = 0;

// OSS ready setter 0x1402f0d00 — this(rcx); reads +0x858 (logged-in) -> +0x870 (latch)
try {
  Interceptor.attach(base.add(0x2f0d00), { onEnter: function(){
    ossCalls++;
    var oss = this.context.rcx;
    var b858, b870;
    try { b858 = oss.add(0x858).readU8(); } catch(e){ return; }
    try { b870 = oss.add(0x870).readU8(); } catch(e){ b870 = -1; }
    if (b858 !== lastB858 || b870 !== lastB870){
      send("[OSS 0x2f0d00] this="+oss+"  +0x858(loggedIn)="+b858+"  +0x870(readyLatch)="+b870+"  (call#"+ossCalls+")");
      lastB858 = b858; lastB870 = b870;
    }
  }});
  send("hooked OSS-ready-setter 0x2f0d00");
} catch(e){ send("HOOK OSS FAIL: "+e); }

// store-subsystem attach 0x1404f2b50 — does it ever run?
try {
  Interceptor.attach(base.add(0x4f2b50), { onEnter: function(){
    if (!attachSeen){ attachSeen = true; send("[STORE-ATTACH 0x4f2b50] CALLED  this="+this.context.rcx); }
  }});
  send("hooked store-attach 0x4f2b50");
} catch(e){ send("HOOK attach FAIL: "+e); }

// +0x19d0 setter function 0x1404ee230 — does it ever run, and does it set the byte?
try {
  Interceptor.attach(base.add(0x4ee230), { onEnter: function(){
    this.gi = this.context.rcx;     // its 'this' is (or relates to) the subsystem
    if (!setterSeen){ setterSeen = true; send("[19d0-SETTER 0x4ee230] CALLED  this="+this.context.rcx); }
  }});
  send("hooked 19d0-setter 0x4ee230");
} catch(e){ send("HOOK setter FAIL: "+e); }

// login tick driver 0x1406e9200 — correlate state enum
try {
  Interceptor.attach(base.add(0x6e9200), { onEnter: function(){
    var p = this.context.rcx, state;
    try { state = p.add(0x890).readInt(); } catch(e){ return; }
    if (state < 0 || state > 0x10) return;
    ticks++;
    if (state !== lastState){
      send("[login] state "+lastState+" -> "+state+"   vrflag="+vrflag()+"  attachSeen="+attachSeen+"  19d0setterSeen="+setterSeen);
      lastState = state;
    } else if (ticks % 240 === 0){
      send("[login] state="+state+" (still)  vrflag="+vrflag()+"  ossLoggedIn="+lastB858+"  readyLatch="+lastB870+"  attachSeen="+attachSeen+"  19d0setterSeen="+setterSeen);
    }
  }});
  send("hooked login-tick 0x6e9200");
} catch(e){ send("HOOK tick FAIL: "+e); }
"""


def main():
    dev = frida.get_local_device()
    print("waiting for the game ... (launch via Steam now)", flush=True)
    pid = None
    deadline = time.time() + 300
    last = 0
    while pid is None and time.time() < deadline:
        for p in dev.enumerate_processes():
            n = p.name.lower()
            if "warzone" in n or "valkyrie" in n:
                pid = p.pid
                print("found", repr(p.name), pid, flush=True)
                break
        if pid is None and time.time() - last > 5:
            last = time.time(); print("waiting...", flush=True)
        time.sleep(0.2)
    if pid is None:
        print("no process", flush=True); return
    s = dev.attach(pid)
    sc = s.create_script(JS)

    def _msg(m, d):
        print("MSG:", str(m.get("payload", m)).encode("ascii", "replace").decode("ascii"), flush=True)
    sc.on("message", _msg)
    sc.load()
    print("probe loaded; logging 240s or until exit", flush=True)
    end = time.time() + 240
    while time.time() < end:
        try:
            if not any(p.pid == pid for p in dev.enumerate_processes()):
                print("process exited", flush=True); break
        except Exception:
            break
        time.sleep(0.5)


if __name__ == "__main__":
    main()
