#!/usr/bin/env python3
"""
Dual-listener launcher for the AgentShield backend.

Serves BOTH:
  *  HTTP  :8000  ->  dashboard + Next.js proxy + tap-only phone page (unchanged)
  *  HTTPS :8443  ->  PHONE VOICE URL. Self-signed cert makes the page a
                      "secure context", which is the ONLY way the browser lets
                      the Web Speech mic work over Wi-Fi (getUserMedia /
                      SpeechRecognition refuse plain-http LAN IPs).

Why two ports instead of flipping 8000 to https-only:
  The Next.js dashboard handlers call http://localhost:8000. Switching 8000 to
  https would break the dashboard's polling. Keeping 8000 as HTTP and adding a
  dedicated 8443 HTTPS listener lets voice work over Wi-Fi with zero disruption.

Usage (from backend/):
    python run_dual.py
    -> http://localhost:8000  (dashboard backend)
    -> https://10.203.252.92:8443/phone  (voice phone page)
    -> http://10.203.252.92:8000/phone    (tap-only phone page)

On the phone, Chrome will warn about the self-signed cert the first time:
    Advanced -> Proceed to 10.203.252.92 (unsafe).
After that the page runs as a secure context and the mic is grantable.

MP vs threads: multiprocessing keeps two real uvicorn processes (one per port),
so each handles signals cleanly and the dashboard behaves exactly as before.
"""

import multiprocessing as mp
import os


# Resolve cert/key relative to this file so launch dir doesn't matter.
_BASE = os.path.dirname(os.path.abspath(__file__))
_CERT = os.path.join(_BASE, "certs", "cert.pem")
_KEY = os.path.join(_BASE, "certs", "key.pem")

HOST = "0.0.0.0"       # reachable from the phone over Wi-Fi AND localhost
HTTP_PORT = 8000
HTTPS_PORT = 8443


def run_http():
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=HTTP_PORT, log_level="info")


def run_https():
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=HTTPS_PORT, log_level="info",
                ssl_certfile=_CERT, ssl_keyfile=_KEY)


def main():
    mp.set_start_method("spawn", force=True)
    procs = [mp.Process(target=run_http, daemon=True),
             mp.Process(target=run_https, daemon=True)]
    for p in procs:
        p.start()
    print(f"[dual] http  :{HTTP_PORT}  https:{HTTPS_PORT}  (live)")
    try:
        for p in procs:
            p.join()
    except KeyboardInterrupt:
        for p in procs:
            p.terminate()


if __name__ == "__main__":
    main()