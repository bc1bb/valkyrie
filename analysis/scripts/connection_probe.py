#!/usr/bin/env python3
"""
connection_probe.py — find what makes the post-registration login fail.
Safe Frida (function-entry hooks + Thread.backtrace + ws2_32 export hooks only;
NO vtable calls, NO mid-function patches — those crashed the game earlier).

Hooks:
  - connect / WSAConnect: log every outbound socket (does the client open a NEW
    connection in the post-registration "connecting" phase? earlier connect_trace
    ran BEFORE /clients was fixed, so the client never reached this phase).
  - CONN-FAILURE delegate handler 0x1404735f0 (RVA 0x4735f0): the "Network failure"
    UI handler. On fire, dump a backtrace -> reveals who BROADCAST the failure.
  - CONN-SUCCESS delegate handler 0x140474140 (RVA 0x474140): the success pair.
"""
import frida, time

NAME = "EVE Valkyrie - Warzone.exe"
JS = r"""
var base = Process.getModuleByName("EVE Valkyrie - Warzone.exe").base;
send("base=" + base);
function ipport(sa){
  try {
    var fam = sa.add(0).readU16();
    var port = (sa.add(2).readU8()<<8) | sa.add(3).readU8();
    if (fam === 2) { var b=sa.add(4); return b.readU8()+"."+b.add(1).readU8()+"."+b.add(2).readU8()+"."+b.add(3).readU8()+":"+port; }
    return "fam"+fam+" port"+port;
  } catch(e){ return "(parse err)"; }
}
["connect","WSAConnect"].forEach(function(name){
  try { var f=Module.getGlobalExportByName(name);
    Interceptor.attach(f,{onEnter:function(a){ send("CONNECT "+name+" -> "+ipport(a[1])); }});
    send("hooked "+name);
  } catch(e){ send("no "+name); }
});
function fmt(a){ var r=a.sub(base); return (r.compare(ptr(0))>0 && r.compare(ptr(0x5000000))<0) ? "vk+0x"+r.toString(16) : a.toString(); }
function hookDelegate(rva,label){
  try {
    Interceptor.attach(base.add(rva),{ onEnter:function(){
      var bt=[];
      try { bt=Thread.backtrace(this.context,Backtracer.ACCURATE).slice(0,14).map(fmt); } catch(e){ bt=["(bt err "+e+")"]; }
      send(label+" FIRED  bt: "+bt.join(" "));
    }});
    send("hooked "+label+" @ vk+0x"+rva.toString(16));
  } catch(e){ send("hook fail "+label+": "+e); }
}
hookDelegate(0x4735f0,"CONN-FAILURE");
hookDelegate(0x474140,"CONN-SUCCESS");
try { var rc=0; Interceptor.attach(Module.getGlobalExportByName("recv"),{onEnter:function(){rc++;if(rc<=2)send("recv#"+rc);}}); send("hooked recv (control)"); } catch(e){}
"""

def main():
    dev = frida.get_local_device()
    print("waiting for game...", flush=True)
    pid = None; deadline = time.time() + 300; last = 0
    while pid is None and time.time() < deadline:
        for p in dev.enumerate_processes():
            n = p.name.lower()
            if "warzone" in n or "valkyrie" in n:
                pid = p.pid; print("found", p.name, pid, flush=True); break
        if pid is None and time.time()-last > 5: last=time.time(); print("waiting...", flush=True)
        time.sleep(0.2)
    if pid is None: print("no process", flush=True); return
    s = dev.attach(pid)
    sc = s.create_script(JS)
    def _msg(m,d): print("MSG:", str(m.get("payload", m)).encode("ascii","replace").decode("ascii"), flush=True)
    sc.on("message", _msg); sc.load()
    print("hooks loaded; logging 200s or until exit", flush=True)
    end = time.time()+200
    while time.time() < end:
        try:
            if not any(p.pid==pid for p in dev.enumerate_processes()): print("process exited", flush=True); break
        except Exception: break
        time.sleep(0.5)

if __name__ == "__main__":
    main()
