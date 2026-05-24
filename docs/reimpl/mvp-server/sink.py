#!/usr/bin/env python3
"""
sink.py — tiny logging HTTP/TCP sink for the local sidecar ports the client/game
may expect (watchdog 127.0.0.1:8080, battle-server reg localhost:10080) and any
other port passed on argv. Accepts a connection, logs peer + first bytes, returns
a permissive HTTP 200. Used to discover/​satisfy "connection refused" targets
during live client bring-up. Clean-room: logs only what the client sends locally.
"""
import socket, threading, sys, time, os
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = open(os.path.join(HERE, "logs", "sink.log"), "a", buffering=1)
def log(*a): LOG.write(time.strftime("%H:%M:%S ")+" ".join(map(str,a))+"\n"); print(*a, flush=True)

def serve(port):
    s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try: s.bind(("0.0.0.0", port)); s.listen(16)
    except OSError as e: log(f"[:{port}] bind failed {e}"); return
    log(f"[:{port}] listening")
    while True:
        c, a = s.accept()
        threading.Thread(target=handle, args=(c, a, port), daemon=True).start()

HOLD_PORTS = {26000, 26001, 26002}  # server-speaks-first persistent channels: keep open, just log

def handle(c, a, port):
    if port in HOLD_PORTS:
        log(f"[:{port}] CONNECT from {a} (HOLD: keeping open, logging inbound)")
        try:
            c.settimeout(120.0)
            while True:
                d = c.recv(4096)
                if not d:
                    log(f"[:{port}] peer {a} closed"); break
                log(f"[:{port}] recv {len(d)}B: {d[:200]!r}")
        except Exception as e:
            log(f"[:{port}] hold-end {a}: {e}")
        finally:
            try: c.close()
            except Exception: pass
        return
    try:
        c.settimeout(2.0)
        data = b""
        try: data = c.recv(4096)
        except Exception: pass
        log(f"[:{port}] CONNECT from {a} first={data[:300]!r}")
        body = b'{"status":"ok"}'
        c.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: %d\r\nConnection: close\r\n\r\n%b" % (len(body), body))
    except Exception as e: log(f"[:{port}] err {e}")
    finally:
        try: c.close()
        except Exception: pass

if __name__ == "__main__":
    ports = [int(x) for x in sys.argv[1:]] or [8080, 10080]
    for p in ports: threading.Thread(target=serve, args=(p,), daemon=True).start()
    while True: time.sleep(3600)
