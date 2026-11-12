import psutil
from typing import List, Dict, Any, Optional

# System-critical processes on Windows/Linux that should never be killed
PROTECTED_PROCESS_NAMES = {
    "system", "system idle process", "registry", "smss.exe", "csrss.exe", 
    "wininit.exe", "services.exe", "lsass.exe", "winlogon.exe", "svchost.exe",
    "init", "kthreadd", "systemd"
}

PROTECTED_PIDS = {0, 4}

class ProcessManager:
    """
    Manages process discovery, filtering ('Hog Hunter'), and safe termination.
    """
    @staticmethod
    def get_processes(
        sort_by: str = "memory",
        limit: int = 50,
        search_query: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Retrieves a snapshot of active processes with CPU and Memory utilization.
        """
        procs: List[Dict[str, Any]] = []
        search_query = search_query.strip().lower()

        # Iterate over processes non-blockingly
        for p in psutil.process_iter(['pid', 'name', 'username', 'status', 'num_threads']):
            try:
                info = p.info
                pid = info.get('pid')
                name = info.get('name') or "Unknown"

                # Filter by search query if specified
                if search_query:
                    if search_query not in name.lower() and str(pid) != search_query:
                        continue

                # Query memory
                try:
                    mem_info = p.memory_info()
                    mem_rss_mb = round(mem_info.rss / (1024 * 1024), 1)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    mem_rss_mb = 0.0

                # Query non-blocking CPU percent
                try:
                    cpu_pct = round(p.cpu_percent(interval=None), 1)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    cpu_pct = 0.0

                # Is this a protected system process?
                is_system = (
                    pid in PROTECTED_PIDS or 
                    name.lower() in PROTECTED_PROCESS_NAMES
                )

                procs.append({
                    "pid": pid,
                    "name": name,
                    "cpu_percent": cpu_pct,
                    "memory_mb": mem_rss_mb,
                    "username": info.get('username') or "N/A",
                    "status": info.get('status') or "unknown",
                    "threads": info.get('num_threads') or 0,
                    "is_protected": is_system
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Sort results
        if sort_by == "cpu":
            procs.sort(key=lambda x: x["cpu_percent"], reverse=True)
        elif sort_by == "name":
            procs.sort(key=lambda x: x["name"].lower())
        else: # default "memory"
            procs.sort(key=lambda x: x["memory_mb"], reverse=True)

        return procs[:limit]

    @staticmethod
    def terminate_process(pid: int) -> Dict[str, Any]:
        """
        Safely attempts to terminate a process by PID.
        Guards against terminating system-critical processes.
        """
        if pid in PROTECTED_PIDS:
            return {"success": False, "message": f"PID {pid} is a protected core system process."}

        try:
            proc = psutil.Process(pid)
            name = proc.name()

            if name.lower() in PROTECTED_PROCESS_NAMES:
                return {"success": False, "message": f"Process '{name}' is protected and cannot be killed."}

            proc.terminate()
            gone, alive = psutil.wait_procs([proc], timeout=1.5)
            if alive:
                proc.kill() # Force kill if terminate didn't exit in time

            return {"success": True, "message": f"Process '{name}' (PID {pid}) terminated successfully."}

        except psutil.NoSuchProcess:
            return {"success": False, "message": f"Process PID {pid} is no longer running."}
        except psutil.AccessDenied:
            return {"success": False, "message": f"Permission denied to terminate PID {pid} (Run as Administrator)."}
        except Exception as e:
            return {"success": False, "message": f"Error terminating process: {str(e)}"}

