# Engineering & Portfolio Development Guidelines

## 1. Project Philosophy & Architecture
- **Simplicity + Technical Depth**: When suggesting or architecting projects, ensure the elevator pitch is immediately intuitive for recruiters and end-users, while the backend implements deep systems concepts (concurrency, hardware telemetry, networking, or data pipelines).
- **Practical Usability**: Prioritize tools with daily utility for the user and the broader developer/tech community over mock toy clones.
- **Frontend-Heavy & App-Centric UI**: Build polished, reactive interfaces (modern dark mode, glassmorphism, responsive data visualizations) that provide desktop-app ergonomics served with zero-configuration launchers.

## 2. Systems & Hardware Engineering Guardrails
- **OS Sensor Boundary Checks**: When parsing hardware sensors (e.g., `psutil.sensors_battery()`), guard against OS-specific overflow values (such as `0xFFFFFFFF` / 4294967295 on Windows) with realistic upper bounds.
- **Cross-Platform Latency Tests**: Prefer non-elevated TCP socket handshake timings over ICMP ping utilities to avoid permission failures across environments.
- **Guarded Process Management**: Always whitelist and block termination of core OS PIDs (0, 4) and critical system processes (`csrss.exe`, `smss.exe`, `services.exe`, etc.).
- **Python Test Invocation**: Always execute test suites via `python -m pytest` to guarantee root workspace inclusion in `sys.path`.
