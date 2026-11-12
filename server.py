import asyncio
import os
from contextlib import asynccontextmanager
from typing import Set, Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from engine.telemetry import TelemetryCollector
from engine.process_manager import ProcessManager
from engine.network_probe import NetworkProbe
from engine.diagnostics import SystemDoctor

# Global Singletons
collector = TelemetryCollector()
connected_websockets: Set[WebSocket] = set()

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


# --- WebSocket Streaming ---

@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """
    Subscribes client to real-time, low-overhead system telemetry frames.
    """
    await websocket.accept()
    connected_websockets.add(websocket)
    try:
        # Keep connection open; receive any client commands/pings if needed
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        connected_websockets.discard(websocket)
