import os
import sys
import time
import socket
import webbrowser
import threading
import uvicorn

BANNER = r"""
  ____             ____        _            
 / ___| _   _ ___ |  _ \ _   _| |___  ___   
 \___ \| | | / __|| |_) | | | | / __|/ _ \  
  ___) | |_| \__ \|  __/| |_| | \__ \  __/  
 |____/ \__, |___/|_|    \__,_|_|___/\___|  
        |___/                               
  >> Intelligent System & Hardware Telemetry Station <<
"""

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def open_browser_delayed(url: str, delay: float = 1.2):
    time.sleep(delay)
    print(f"[*] Opening SysPulse Dashboard in your default browser: {url}")
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"[!] Could not automatically open browser: {e}")

def main():
    print(BANNER)
    
    port = 8000
    while is_port_in_use(port):
        port += 1

    url = f"http://127.0.0.1:{port}"
    print(f"[*] Starting SysPulse Telemetry Server...")
    print(f"[*] Dashboard URL: {url}")
    print(f"[*] WebSocket Feed: ws://127.0.0.1:{port}/ws/telemetry")
    print(f"[*] Press CTRL+C to stop the station at any time.\n")

    # Launch browser after server warm up in background thread
    threading.Thread(target=open_browser_delayed, args=(url,), daemon=True).start()

    # Run FastAPI via Uvicorn
    uvicorn.run(
        "server:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False
    )

if __name__ == "__main__":
    main()

