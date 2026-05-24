#!/usr/bin/env python3
"""
staticdata_probe.py (v4) — read the static-data resource state directly.

Established by disassembly: the GetFileList completion is 0x14209b550 (RVA
0x209b550). rcx/r15 = the FVKStaticDataResource `this`. It SUCCEEDS (gate
[rbp+0x88]-[rbp+0xb4] > 0 = 26-0) and hands the 26-file list to a listener at
[this+0x20] (vtable methods +0x38/+0x48/+0x68). The resource tracks per-file
download state in an int32 array: data=[this+0xd0], count=[this+0xd8], all reset
to -1 (0xffffffff) at GetFileList. The wall is that "all files complete" never
fires -> stays on DOWNLOADING -> 30s timeout.

This probe (SAFE: entry hook + memory reads only, no patching):
  - Hooks 0x209b550. onEnter saves this(=rcx) and rbp(=rsp-0x118) and the Response.
    onLeave reads [rbp+0x88] (valid file count) and [rbp+0xb4] to confirm the
    success gate LIVE, and resolves the listener method addresses
    ([[this+0x20]] vtable +0x38/+0x48/+0x68) as RVAs to disassemble next.
  - Then polls the per-file state array every 2s and prints a histogram of state
    values (how many files are -1 / 0 / other) -> shows whether downloads ever
    reach "done" and where the aggregation stalls.
Usage: python analysis/scripts/staticdata_probe.py   (then relaunch via Steam)
"""
import frida, time

JS = r"""
var base = Process.getModuleByName("EVE Valkyrie - Warzone.exe").base;
var modEnd = base.add(Process.getModuleByName("EVE Valkyrie - Warzone.exe").size);
send("base=" + base);
function rva(p){ try { if (p.compare(base)>=0 && p.compare(modEnd)<0) return "vk+0x"+p.sub(base).toString(16); } catch(e){} return ""+p; }

var RES = null;          // the FVKStaticDataResource this-ptr
var polling = false;

function dumpStates(tag){
  if (RES === null) return;
  try {
    var data = RES.add(0xd0).readPointer();
    var count = RES.add(0xd8).readInt();
    if (count < 0 || count > 200) { send(tag+" state: count="+count+" (bad)"); return; }
    var hist = {};
    var sample = [];
    for (var i=0;i<count;i++){
      var v = data.add(i*4).readU32();
      var key = (v===0xffffffff)?"-1":(""+v);
      hist[key] = (hist[key]||0)+1;
      if (i<8) sample.push(v===0xffffffff?-1:v);
    }
    send(tag+" per-file states: count="+count+" hist="+JSON.stringify(hist)+" sample8="+JSON.stringify(sample));
  } catch(e){ send(tag+" state read err: "+e); }
}

try {
  Interceptor.attach(base.add(0x209b550), { onEnter: function(){
    this.res = this.context.rcx;
    this.rbp = this.context.rsp.sub(0x118);
    this.resp = this.context.r8;
    send("GFL-complete ENTER  this="+this.res+"  Response="+(this.resp.isNull()?"NULL":this.resp)+"  (respObj=" + (function(){try{return this.resp.readPointer();}catch(e){return "?";}}).call(this) + ")");
  }, onLeave: function(){
    RES = this.res;
    try {
      var fc = this.rbp.add(0x88).readInt();
      var b  = this.rbp.add(0xb4).readInt();
      send("GFL-complete LEAVE  validFiles[rbp+0x88]="+fc+"  [rbp+0xb4]="+b+"  => successGate="+((!this.resp.isNull() && (fc-b)>0)?"PASS(1)":"FAIL(0)"));
    } catch(e){ send("rbp read err: "+e); }
    // resolve listener vtable methods
    try {
      var listener = this.res.add(0x20).readPointer();
      send("listener[this+0x20]="+listener);
      if (!listener.isNull()){
        var vt = listener.readPointer();
        send("  listener vtbl="+rva(vt)+"  +0x38="+rva(vt.add(0x38).readPointer())+"  +0x48="+rva(vt.add(0x48).readPointer())+"  +0x68="+rva(vt.add(0x68).readPointer()));
      }
    } catch(e){ send("listener resolve err: "+e); }
    // resource fields of interest
    try { send("res+0x30="+this.res.add(0x30).readInt()+"  res+0xd8(filecount)="+this.res.add(0xd8).readInt()); } catch(e){}
    dumpStates("LEAVE");
    if (!polling){ polling = true; var n=0;
      var id = setInterval(function(){ n++; dumpStates("POLL#"+n); if (n>=20){ clearInterval(id); } }, 2000);
    }
  }});
  send("hooked GFL-complete 0x209b550");
} catch(e){ send("HOOK FAIL: "+e); }
try { var rc=0; Interceptor.attach(Module.getGlobalExportByName("recv"),{onEnter:function(){rc++; if(rc<=2) send("CONTROL recv #"+rc);}}); }catch(e){}
"""

def main():
    dev = frida.get_local_device()
    print("waiting for the game ...", flush=True)
    pid = None; deadline = time.time() + 300; last = 0
    while pid is None and time.time() < deadline:
        for p in dev.enumerate_processes():
            n = p.name.lower()
            if "warzone" in n or "valkyrie" in n:
                pid = p.pid; print("found", repr(p.name), pid, flush=True); break
        if pid is None and time.time()-last > 5: last=time.time(); print("waiting...", flush=True)
        time.sleep(0.2)
    if pid is None: print("no process", flush=True); return
    s = dev.attach(pid); sc = s.create_script(JS)
    def _msg(m, d): print("MSG:", str(m.get("payload", m)).encode("ascii","replace").decode("ascii"), flush=True)
    sc.on("message", _msg); sc.load()
    print("probe loaded; logging 180s or until exit", flush=True)
    end = time.time() + 180
    while time.time() < end:
        try:
            if not any(p.pid == pid for p in dev.enumerate_processes()): print("process exited", flush=True); break
        except Exception: break
        time.sleep(0.5)

if __name__ == "__main__":
    main()
