# ⚡ SysPulse

> **Your computer's personal mission control.**  
> A sleek, dark-mode desktop dashboard that shows you exactly what your hardware is doing in real-time, hunts down runaway apps, and keeps your system running fast.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Modern_Async_Backend-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![WebSockets](https://img.shields.io/badge/WebSockets-Real--time_Streaming-green.svg)](https://websockets.readthedocs.io)
[![Tests](https://img.shields.io/badge/Pytest-100%25_Passing-brightgreen.svg?logo=pytest&logoColor=white)](https://pytest.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 💡 Why SysPulse?

Have you ever had your laptop fans start screaming, your battery drop faster than expected, or a mystery app freeze your screen?

Traditional task managers can be clunky, boring, and overwhelming. **SysPulse** turns your computer's health into a beautiful, cyberpunk-inspired control center. Just run one command, and your browser opens to a live, animated station showing everything happening inside your machine.

---

## ✨ Features You'll Actually Use

### 1. 📊 Live Hardware Dashboard
- **Per-Core CPU Matrix:** Watch all your processor cores work in real-time.
- **Live Speedometers:** Instant download/upload speeds and disk read/write rates.
- **Battery & Power Insights:** Accurate charge percentages, power draw status, and realistic runtime estimates.
- **Smooth 60 FPS Charts:** Streaming graphs that show CPU and memory trends as they happen.

### 2. 🎯 "Hog Hunter" (Smart Process Manager)
- Tired of games or browser tabs freezing your system?
- Quickly search, sort, and find apps hogging your RAM or CPU.
- **Safe 1-Click Terminate:** Safely close rogue apps right from the dashboard without worrying about crashing your operating system (system-critical processes are protected).

### 3. 🌐 Network Radar
- **Active Sockets:** See which background apps are actively talking to the internet.
- **Live Ping & Latency:** Real-time test of your Wi-Fi or Ethernet connection quality without complex command-line tools.
- **Adapter Details:** Instant view of your IP address, MAC address, and connection speed.

### 4. 🩺 System Doctor & 1-Click Cleaner
- **System Health Score (0–100%):** A single composite score telling you whether your PC is running optimally or needs attention.
- **Smart Advice:** Friendly alerts like *"Chrome has 12 background tabs consuming 1.2 GB"* or *"Disk C: is running low on space"*.
- **Quick Cache Cleaner:** Scans and safely wipes temporary junk files with a single click to free up disk space.
- **📄 Downloadable Executive PDF Report:** Generates and downloads a clean, vectorized PDF diagnostic report summarizing system specs, health findings, disk allocation, and top active processes.

---

## 🚀 Quickstart (Get Running in 30 Seconds)

### Step 1: Clone the Repository
```bash
git clone https://github.com/itz-shreya14/syspulse.git
cd syspulse
```

### Step 2: Set Up Virtual Environment & Install
```bash
# Create and activate environment
python -m venv venv

# On Windows:
.\venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### Step 3: Launch SysPulse!
```bash
python run.py
```
> 🎉 **That's it!** A browser window will automatically pop open at `http://127.0.0.1:8000/` with your live dashboard.

---

## 🌐 Distributed Cloud Hub & Remote Device Monitoring

Want to monitor your laptop from your phone or let a friend monitor their PC? SysPulse operates as a distributed observability hub:

### 1. Deploy the Web Hub to Render (Free)
SysPulse includes a pre-configured `render.yaml` blueprint. Link your GitHub repository (`itz-shreya14/syspulse`) on [Render.com](https://render.com) as a **Web Service** or Blueprint. It will auto-detect `render.yaml` and deploy in 2 minutes!

### 2. Pair Any Remote Computer in Seconds
1. Open your cloud dashboard URL (e.g. `https://syspulse-hub.onrender.com`).
2. Click **"Pair Device"** in the top header to generate a unique 6-digit PIN (e.g., `482-901`).
3. On the computer you want to monitor, run the lightweight agent:
   ```bash
   python agent.py --pin 482-901 --hub https://your-hub.onrender.com
   ```
4. **Instant Telemetry:** The cloud dashboard lights up immediately and streams the remote computer's per-core CPU loads, battery curves, and active processes in real time!

---

## 🛠️ How It Works (Under the Hood)

SysPulse is built with an emphasis on **low overhead (<0.5% CPU)** and clean engineering:

- **The Brain (Python & FastAPI):** Gathers hardware stats directly from the operating system using `psutil` and socket probes.
- **Live Broadcast (WebSockets):** Instead of refreshing the page or spamming the server, the backend pushes metrics every second over a single open WebSocket connection.
- **The Look (Tailwind CSS & Chart.js):** A lightweight single-page web app with zero bulky frameworks or Node.js dependencies—served straight out of Python.

---

## 🧪 Automated Testing

Everything in SysPulse is tested to ensure zero crashes:
```bash
python -m pytest -v
```
All route tests, health checks, and data models pass with a **100% success rate**.

---

## 💼 For Recruiters & Engineers

If you are evaluating this project for software engineering, systems, or backend roles:
- **Language & Stack:** Python 3.10+, FastAPI, WebSockets, `psutil`, Pytest, Chart.js.
- **Engineering Highlights:**
  - Asynchronous event loop (`asyncio`) for non-blocking sub-second telemetry broadcasting.
  - Rate-differential algorithms calculating real-time throughput ($\Delta \text{bytes} / \Delta t$).
  - Safe process management with kernel PID protection.
  - Clean cross-platform latency measurement via TCP handshakes without elevated ICMP permissions.

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
