#!/usr/bin/env python3
"""
oss_login_poll.py — read-only: does the VkGame OnlineSubsystem ever flip its
"session-valid" byte (+0x858)? And is the OSS even ticked?

Background (clean-room RE + prior live probe): the login stalls because
OSS+0x858 (logged-in) is never set, so the ready-latch setter 0x1402f0d00
(sets OSS+0x870 iff +0x858) is never called, so the store load + GameInstance
+0x19d0 never happen. This probe captures every VkGame-OSS instance via its
constructor 0x140359060 and POLLS each one's +0x858/+0x870/+0x98 over the whole
login window, counts ticks of the OSS update 0x1402e4f60, and correlates with the
login state enum. Pure reads; no writes.
Usage: python analysis/scripts/oss_login_poll.py   (then launch via Steam)
"""
import frida, time

JS = r"""
var base = Process.getModuleByName("EVE Valkyrie - Warzone.exe").base;
send("base="+base);

var instances = [];   // captured OSS this-ptrs (as strings, deduped)
var tickCount = 0, lastState = -999, lsticks = 0;
var OSS_VTBL = base.add(0x283da60);   // VkGame OSS vtable

// SAFETY: do NOT hook the OSS constructor 0x140359060 — hooking that early-init
// path crashes the 2017 binary on Frida attach (observed twice). Instead capture
// the OSS pointer from the OSS update/tick 0x1402e4f60 (fires later, safe), by
// scanning its argument registers for a pointer whose vtable == the OSS vtable.
try {
  Interceptor.attach(base.add(0x2e4f60), { onEnter: function(){
    tickCount++;
    if (instances.length >= 2) return;   // already have it
    var regs = [this.context.rcx, this.context.rdx, this.context.r8];
    for (var r=0; r<regs.length; r++){
      var p = regs[r];
      try {
        if (!p.isNull() && p.readPointer().equals(OSS_VTBL)){
          var s = p.toString();
          if (instances.indexOf(s) < 0){ instances.push(s); send("[OSS] captured "+s+" (arg"+r+", vtable match) (#"+instances.length+")"); }
        }
      } catch(e){}
    }
  }});
  send("hooked OSS-tick 0x2e4f60 (vtable-scan capture)");
} catch(e){ send("HOOK osstick FAIL: "+e); }

// +0x858 reflected setter thunk 0x1403aeb70 ("mov byte [rdx+0x858],r8b; ret").
// This is the ONLY writer of the OSS logged-in bool (reflection-invoked on OSS
// login-complete). Does it EVER fire during login, and from where? Leaf fn -> safe.
try {
  Interceptor.attach(base.add(0x3aeb70), { onEnter: function(){
    var obj = this.context.rdx, val = this.context.r8.toInt32() & 0xff;
    var isOss = false;
    try { isOss = obj.readPointer().equals(OSS_VTBL); } catch(e){}
    var bt = Thread.backtrace(this.context, Backtracer.FUZZY).slice(0,6).map(function(a){
      var d; try{ d=a.sub(base); if(d.compare(0)>=0 && d.compare(0x4000000)<0) return "vk+0x"+d.toString(16);}catch(e){} return ""+a; }).join(" <- ");
    send("[+0x858-SETTER] obj="+obj+" val="+val+" ossVtableMatch="+isOss+"  bt: "+bt);
  }});
  send("hooked +0x858-setter 0x3aeb70");
} catch(e){ send("HOOK setter FAIL: "+e); }

// login tick driver 0x1406e9200 — login state for correlation
try {
  Interceptor.attach(base.add(0x6e9200), { onEnter: function(){
    var p = this.context.rcx, st;
    try { st = p.add(0x890).readInt(); } catch(e){ return; }
    if (st < 0 || st > 0x10) return;
    lsticks++;
    if (st !== lastState){ send("[login] state "+lastState+" -> "+st); lastState = st; }
  }});
  send("hooked login-tick 0x6e9200");
} catch(e){ send("HOOK logintick FAIL: "+e); }

// poll captured OSS instances
var last = {};
setInterval(function(){
  for (var i=0;i<instances.length;i++){
    var t = ptr(instances[i]);
    var b858, b870, w98;
    try { b858 = t.add(0x858).readU8(); } catch(e){ b858 = "?"; }
    try { b870 = t.add(0x870).readU8(); } catch(e){ b870 = "?"; }
    try { w98  = t.add(0x98).readU32(); } catch(e){ w98 = "?"; }
    var key = instances[i];
    var cur = b858+"/"+b870+"/"+w98;
    if (last[key] !== cur){
      send("[OSS poll] "+key+"  +0x858(loggedIn)="+b858+"  +0x870(latch)="+b870+"  +0x98="+w98+"  | osstick="+tickCount+" loginstate="+lastState);
      last[key] = cur;
    }
  }
}, 2000);
send("polling every 2s");
"""


def main():
    import ctypes
    dev = frida.get_local_device()
    print("waiting for a STABLE game process (RAM>400MB) ... (launch via Steam now)", flush=True)
    # Attaching during early init crashed the 2017 binary before; wait until the
    # process is sizeable/stable, then attach (past the fragile init window).
    def ram_mb(pid):
        try:
            import subprocess
            out = subprocess.check_output(["powershell", "-NoProfile", "-Command",
                f"(Get-Process -Id {pid} -ErrorAction SilentlyContinue).WorkingSet64"], text=True).strip()
            return int(out)/1e6 if out else 0
        except Exception:
            return 0
    pid = None
    deadline = time.time() + 300
    last = 0
    while pid is None and time.time() < deadline:
        for p in dev.enumerate_processes():
            n = p.name.lower()
            if "warzone" in n or "valkyrie" in n:
                if ram_mb(p.pid) > 400:
                    pid = p.pid
                    print("found stable", repr(p.name), pid, flush=True)
                break
        if pid is None and time.time() - last > 5:
            last = time.time(); print("waiting...", flush=True)
        time.sleep(0.5)
    if pid is None:
        print("no stable process", flush=True); return
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
