import asyncio
import os
import random
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Set, Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine.telemetry import TelemetryCollector
from engine.process_manager import ProcessManager
from engine.network_probe import NetworkProbe
from engine.diagnostics import SystemDoctor
from engine.pdf_report import PDFReportGenerator

# Global Singletons
collector = TelemetryCollector()
connected_websockets: Set[WebSocket] = set()

# Distributed Multi-Device Fleet Routing
room_dashboards: Dict[str, Set[WebSocket]] = {}
room_agents: Dict[str, WebSocket] = {}
room_latest_telemetry: Dict[str, Dict[str, Any]] = {}

# Asynchronous Background Broadcast Task
async def telemetry_broadcast_loop():
    """
    Background worker that samples system metrics every 1.0 second
    and broadcasts non-blocking JSON frames to all connected WebSocket clients.
    """
    while True:
        try:
            if connected_websockets:
                # Collect telemetry
                telemetry_data = collector.collect()
                
                # Fast process snapshot for health calculation
                top_procs = ProcessManager.get_processes(sort_by="cpu", limit=5)
                health = SystemDoctor.evaluate(telemetry_data, top_procs)

                # Broadcast payload
                payload = {
                    "type": "telemetry_tick",
                    "timestamp": telemetry_data["timestamp"],
                    "uptime": telemetry_data["uptime_formatted"],
                    "cpu": telemetry_data["cpu"],
                    "memory": telemetry_data["memory"],
                    "io": telemetry_data["io"],
                    "battery": telemetry_data["battery"],
                    "health": {
                        "score": health["health_score"],
                        "status": health["status_text"],
                        "color": health["status_color"]
                    }
                }

                # Push to all active WebSockets
                disconnected = set()
                for ws in list(connected_websockets):
                    try:
                        await ws.send_json(payload)
                    except Exception:
                        disconnected.add(ws)

                # Clean up stale connections
                for ws in disconnected:
                    connected_websockets.discard(ws)

        except Exception as e:
            print(f"[Telemetry Broadcast Error] {e}")

        await asyncio.sleep(1.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Launch background broadcaster
    task = asyncio.create_task(telemetry_broadcast_loop())
    yield
    # Shutdown: Cancel background task
    task.cancel()


# FastAPI App Initialization
app = FastAPI(
    title="SysPulse Telemetry & System Diagnostics Station",
    description="Real-time OS telemetry, process manager, and hardware diagnostics platform.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for cross-device & web accessibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Mount Static directory
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root():
    """Serve the single-page application dashboard."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "SysPulse Backend is Running. UI index.html not yet initialized."}


@app.get("/download/agent.py")
async def download_agent_py():
    """Download the standalone single-file client agent script."""
    agent_path = os.path.join(STATIC_DIR, "agent.py")
    if not os.path.exists(agent_path):
        agent_path = os.path.join(BASE_DIR, "agent.py")
    return FileResponse(agent_path, filename="agent.py", media_type="text/x-python")


@app.get("/download/agent.bat")
async def download_agent_bat(pin: str = "482-901", hub: str = ""):
    """Generate a 1-click Windows launcher batch script for the agent."""
    bat_content = f"""@echo off
title SysPulse Telemetry Agent
color 0b
echo ===================================================
echo     SysPulse Remote Hardware Telemetry Agent
echo ===================================================
echo Device Pairing PIN: {pin}
echo Connecting to Hub: {hub or 'Current Cloud Hub'}
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python is not installed or not in PATH!
    echo Please install Python from https://python.org or Microsoft Store.
    pause
    exit /b 1
)

echo [*] Checking dependencies (psutil, websockets)...
python -m pip install psutil websockets --quiet

echo [*] Downloading latest agent script...
curl -s -O "{hub}/download/agent.py" || powershell -Command "Invoke-WebRequest -Uri '{hub}/download/agent.py' -OutFile 'agent.py'"

echo [*] Starting telemetry stream...
python agent.py --pin {pin} --hub "{hub}"
pause
"""
    return Response(
        content=bat_content,
        media_type="application/x-bat",
        headers={"Content-Disposition": f'attachment; filename="syspulse_agent_{pin}.bat"'}
    )


# --- REST API Endpoints ---

@app.get("/api/system")
async def get_system_spec():
    """Get static hardware and OS specifications."""
    return collector.system_info


@app.get("/api/snapshot")
async def get_full_snapshot():
    """Returns a complete system snapshot including hardware, processes, and health."""
    telemetry = collector.collect()
    procs = ProcessManager.get_processes(sort_by="memory", limit=20)
    health = SystemDoctor.evaluate(telemetry, procs)
    interfaces = NetworkProbe.get_interfaces()
    latency = NetworkProbe.measure_latency()

    return {
        "telemetry": telemetry,
        "health": health,
        "processes": procs,
        "network": {
            "interfaces": interfaces,
            "latency_ms": latency
        }
    }


@app.get("/api/processes")
async def get_processes(
    sort_by: str = Query("memory", pattern="^(memory|cpu|name)$"),
    limit: int = Query(50, ge=5, le=200),
    search: str = Query("", max_length=50)
):
    """Retrieve active processes with filtering and sorting."""
    return ProcessManager.get_processes(sort_by=sort_by, limit=limit, search_query=search)


@app.post("/api/processes/{pid}/kill")
async def terminate_process(pid: int):
    """Safely terminate a rogue or high-resource process."""
    result = ProcessManager.terminate_process(pid)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@app.get("/api/network/connections")
async def get_network_connections(limit: int = Query(50, ge=5, le=150)):
    """Retrieve active internet sockets."""
    return NetworkProbe.get_active_connections(limit=limit)


@app.get("/api/network/latency")
async def get_network_latency():
    """Measures live TCP handshake ping latency."""
    latency = NetworkProbe.measure_latency()
    return {"latency_ms": latency}


@app.get("/api/diagnostics/health")
async def get_health_evaluation():
    """Compute current system health score and actionable advice."""
    telemetry = collector.collect()
    top_procs = ProcessManager.get_processes(sort_by="cpu", limit=10)
    return SystemDoctor.evaluate(telemetry, top_procs)


@app.get("/api/diagnostics/cache")
async def get_cache_info():
    """Get purgeable user temporary cache details."""
    return SystemDoctor.get_cache_summary()


@app.post("/api/diagnostics/clean")
async def clean_temp_cache():
    """Safely purge unlocked files from the user temp cache."""
    return SystemDoctor.clean_cache()


@app.get("/api/reports/pdf")
async def get_pdf_report():
    """Generates and downloads a vectorized executive PDF diagnostic audit report."""
    telemetry = collector.collect()
    procs = ProcessManager.get_processes(sort_by="memory", limit=20)
    health = SystemDoctor.evaluate(telemetry, procs)
    network_data = {
        "interfaces": NetworkProbe.get_interfaces(),
        "latency_ms": NetworkProbe.measure_latency()
    }

    pdf_buffer = PDFReportGenerator.generate(telemetry, health, procs, network_data)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"syspulse_audit_report_{timestamp}.pdf"

    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@app.get("/api/device/new-pin")
async def generate_pairing_pin():
    """Generates a unique 6-digit device pairing PIN."""
    pin = f"{random.randint(100, 999)}-{random.randint(100, 999)}"
    return {"pin": pin}


@app.get("/api/device/{pin}/status")
async def get_device_status(pin: str):
    """Check if remote agent for a given PIN is actively connected."""
    is_online = pin in room_agents
    return {
        "pin": pin,
        "online": is_online,
        "connected_dashboards": len(room_dashboards.get(pin, set())),
        "has_cached_telemetry": pin in room_latest_telemetry
    }


# --- WebSocket Streaming ---

@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """
    Subscribes client to real-time local system telemetry frames (standalone mode).
    """
    await websocket.accept()
    connected_websockets.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        connected_websockets.discard(websocket)


@app.websocket("/ws/agent/{pin}")
async def websocket_agent_endpoint(websocket: WebSocket, pin: str):
    """
    Ingests live telemetry stream from remote client agent.
    Relays frames in real-time to paired dashboards.
    """
    await websocket.accept()
    room_agents[pin] = websocket
    print(f"[SysPulse Hub] Agent connected with Device PIN: {pin}")

    # Notify connected dashboards that agent came online
    dashboards = room_dashboards.get(pin, set())
    for d in list(dashboards):
        try:
            await d.send_json({"type": "agent_status", "status": "online", "pin": pin})
        except Exception:
            pass

    try:
        while True:
            frame = await websocket.receive_json()
            room_latest_telemetry[pin] = frame

            # Broadcast to all dashboards monitoring this PIN
            dashboards = room_dashboards.get(pin, set())
            disconnected = set()
            for d in list(dashboards):
                try:
                    await d.send_json(frame)
                except Exception:
                    disconnected.add(d)

            for d in disconnected:
                dashboards.discard(d)

    except WebSocketDisconnect:
        pass
    finally:
        room_agents.pop(pin, None)
        print(f"[SysPulse Hub] Agent disconnected for Device PIN: {pin}")
        # Notify dashboards of offline state
        dashboards = room_dashboards.get(pin, set())
        for d in list(dashboards):
            try:
                await d.send_json({"type": "agent_status", "status": "offline", "pin": pin})
            except Exception:
                pass


@app.websocket("/ws/dashboard/{pin}")
async def websocket_dashboard_endpoint(websocket: WebSocket, pin: str):
    """
    Subscribes a browser dashboard to a specific remote agent device stream.
    """
    await websocket.accept()
    if pin not in room_dashboards:
        room_dashboards[pin] = set()
    room_dashboards[pin].add(websocket)

    # Immediately push status & cached telemetry if available
    is_online = pin in room_agents
    await websocket.send_json({"type": "agent_status", "status": "online" if is_online else "waiting", "pin": pin})

    if pin in room_latest_telemetry:
        await websocket.send_json(room_latest_telemetry[pin])

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if pin in room_dashboards:
            room_dashboards[pin].discard(websocket)
            if not room_dashboards[pin]:
                room_dashboards.pop(pin, None)
