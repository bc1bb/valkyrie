#!/usr/bin/env python3
"""
login_advance_probe.py — confirm the static-data login gate and force it open.

Synthesised from two clean-room RE passes (docs/reimpl/05 + 06):
  - The login object is ticked by 0x1406e9200; its state enum is at login+0x890,
    its per-step timer at login+0x894. State 2 = "DOWNLOADING STATIC DATA".
  - The state-2 handler 0x1406ec6a0 POLLS byte login+0x899 each tick and advances
    only when it is set. That byte is set ONLY by the login completion delegate
    0x1406e5780(login, success) when the static-data subsystem multicast
    (subsystem 0x143ab9858 + 0x270) broadcasts success.
  - The manifest completion 0x14209b550 (this=manager) SUCCEEDS but its listener
    slot (manager+0x20 / +0x30) is reportedly NULL, so the broadcast never fires
    and login+0x899 never flips -> 30s timeout -> "A NETWORK ERROR HAS OCCURRED".

This probe (SAFE: function-entry hooks, memory READS, and a single one-byte WRITE
to a polled state flag — no code execution, no vtable calls from hooks):
  1. Hooks the manifest completion 0x14209b550: reads this(rcx)+0x20/+0x30 to
     verify the manager listener slot live; sets manifestDone.
  2. Hooks the login completion delegate 0x1406e5780: reports if it EVER fires
     naturally (it should not, in the stuck case) and with what success arg.
  3. Hooks the tick driver 0x1406e9200: captures login=rcx, logs state-enum
     transitions and the timer. Once the manifest has completed and we are in
     state 2 with login+0x899 still 0, it WRITES login+0x899=1 ONCE and watches
     whether the next tick advances the state (to 3 = DOWNLOADING STORE DATA).

Set VK_OBSERVE_ONLY=1 to skip the write (pure observation run).
Usage: python analysis/scripts/login_advance_probe.py   (then launch via Steam)
"""
import frida, os, time

OBSERVE_ONLY = os.environ.get("VK_OBSERVE_ONLY", "") not in ("", "0")

JS = r"""
var OBSERVE_ONLY = %s;
var base = Process.getModuleByName("EVE Valkyrie - Warzone.exe").base;
function rva(p){ try { var d=p.sub(base); if (d.compare(0)>=0 && d.compare(0x4000000)<0) return "vk+0x"+d.toString(16);} catch(e){} return ""+p; }
send("base="+base+"  OBSERVE_ONLY="+OBSERVE_ONLY);

var manifestDone = false;
var forced = false;
var login = null;
var gi = null;            // game-instance pointer (rax from 0x1404e6650)
var giForced = false;
var lastState = -999;
var tickCount = 0;

// game-instance accessor 0x1404e6650 — capture its return (the GI pointer)
try {
  Interceptor.attach(base.add(0x4e6650), { onLeave: function(retval){
    if (gi === null && !retval.isNull()){ gi = ptr(retval.toString()); send("[GI] captured game-instance="+gi); }
  }});
  send("hooked GI-accessor 0x4e6650");
} catch(e){ send("HOOK GI FAIL: "+e); }

// 1) manifest completion 0x14209b550 — this(rcx)=manager; read listener slot
try {
  Interceptor.attach(base.add(0x209b550), { onEnter: function(){
    var mgr = this.context.rcx;
    var resp = this.context.r8;
    var l20 = "?", l30 = "?";
    try { l20 = rva(mgr.add(0x20).readPointer()); } catch(e){ l20 = "err:"+e; }
    try { l30 = mgr.add(0x30).readU32(); } catch(e){ l30 = "err:"+e; }
    send("[GFL-complete] this(mgr)="+mgr+"  Response="+(resp.isNull()?"NULL":resp)+"  mgr+0x20(listener)="+l20+"  mgr+0x30(flag)="+l30);
  }, onLeave: function(){ manifestDone = true; send("[GFL-complete] returned; manifestDone=true"); }});
  send("hooked GFL-complete 0x209b550");
} catch(e){ send("HOOK GFL FAIL: "+e); }

// 2) login completion delegate 0x1406e5780 — does it ever fire?
try {
  Interceptor.attach(base.add(0x6e5780), { onEnter: function(){
    send("[login-complete-delegate 0x6e5780] FIRED  arg0(rcx)="+this.context.rcx+"  arg1(rdx/success)="+this.context.rdx);
  }});
  send("hooked login-complete-delegate 0x6e5780");
} catch(e){ send("HOOK delegate FAIL: "+e); }

// 3) tick driver 0x1406e9200 — capture login, log state, force the gate byte
try {
  Interceptor.attach(base.add(0x6e9200), { onEnter: function(){
    var p = this.context.rcx;
    var state, timer, b899;
    try { state = p.add(0x890).readInt(); } catch(e){ return; }
    if (state < 0 || state > 0x10) return;     // not the login object
    login = p;
    tickCount++;
    try { timer = p.add(0x894).readFloat(); } catch(e){ timer = -1; }
    var b899, b89a, b89b, g19d0;
    try { b899 = p.add(0x899).readU8(); } catch(e){ b899 = -1; }
    try { b89a = p.add(0x89a).readU8(); } catch(e){ b89a = -1; }
    try { b89b = p.add(0x89b).readU8(); } catch(e){ b89b = -1; }
    try { g19d0 = (gi===null)?"?":gi.add(0x19d0).readU8(); } catch(e){ g19d0 = "err"; }
    var flags = "b899="+b899+" b89a="+b89a+" b89b="+b89b+" gi19d0="+g19d0;
    if (state !== lastState){
      send("[tick] STATE "+lastState+" -> "+state+"   timer="+timer.toFixed(2)+"  "+flags+"  (login="+login+")");
      lastState = state;
    } else if (tickCount %% 120 === 0){
      send("[tick] state="+state+"  timer="+timer.toFixed(2)+"  "+flags);
    }
    // DECISIVE: force the secondary game-instance gate so state 2 can advance.
    if (!OBSERVE_ONLY && !giForced && state === 2 && gi !== null){
      try {
        if (gi.add(0x19d0).readU8() === 0){
          gi.add(0x19d0).writeU8(1);
          giForced = true;
          send("*** FORCED GameInstance+0x19d0 = 1 (state=2, timer="+timer.toFixed(2)+") ***");
        }
      } catch(e){ send("gi force write err: "+e); }
    }
  }});
  send("hooked tick-driver 0x6e9200");
} catch(e){ send("HOOK tick FAIL: "+e); }
""" % ("true" if OBSERVE_ONLY else "false")


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
