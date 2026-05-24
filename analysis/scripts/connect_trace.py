import frida, time
dev = frida.get_local_device()
print("waiting for game...", flush=True)
pid = None
deadline = time.time() + 240
while pid is None and time.time() < deadline:
    for p in dev.enumerate_processes():
        if "warzone" in p.name.lower() or "valkyrie" in p.name.lower():
            pid = p.pid; break
    time.sleep(0.1)
if pid is None:
    print("no process", flush=True); raise SystemExit
print("attaching", pid, flush=True)
s = dev.attach(pid)
js = r"""
function ipport(sa){
  try {
    var fam = sa.add(0).readU16();
    var port = (sa.add(2).readU8()<<8) | sa.add(3).readU8();
    if (fam === 2) { // AF_INET
      var b = sa.add(4);
      var ip = b.readU8()+"."+b.add(1).readU8()+"."+b.add(2).readU8()+"."+b.add(3).readU8();
      return ip+":"+port;
    }
    return "fam"+fam+" port"+port;
  } catch(e){ return "(parse err "+e+")"; }
}
["connect","WSAConnect"].forEach(function(name){
  try {
    var f = Module.getGlobalExportByName(name);
    Interceptor.attach(f, { onEnter: function(a){ send("CONNECT "+name+" -> "+ipport(a[1])); } });
    send("hooked "+name);
  } catch(e){ send("no "+name+": "+e); }
});
"""
sc = s.create_script(js)
sc.on("message", lambda m, d: print("MSG", m.get("payload", m), flush=True))
sc.load()
print("connect hooks live; relaunch the game now if needed", flush=True)
time.sleep(200)
print("done", flush=True)
