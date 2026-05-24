import frida, time
dev = frida.get_local_device()
pid = next((p.pid for p in dev.enumerate_processes() if 'warzone' in p.name.lower()), None)
print('pid', pid, flush=True)
if pid is None: raise SystemExit('no game process')
s = dev.attach(pid)
js = '''
function hookExp(name){ try { var f = Module.getGlobalExportByName(name); var n=0;
  Interceptor.attach(f,{onEnter:function(){ n++; if(n<=2) send("HIT "+name+" #"+n); }});
  send("hooked "+name); } catch(e){ send("no "+name); } }
["WSARecv","recv","InternetReadFile","InternetReadFileExW","HttpSendRequestW","HttpSendRequestA","WinHttpReceiveResponse","WinHttpReadData"].forEach(hookExp);
'''
sc = s.create_script(js)
sc.on('message', lambda m,d: print('MSG', m.get('payload', m), flush=True))
sc.load()
print('hooks set', flush=True)
time.sleep(15)
print('done', flush=True)
