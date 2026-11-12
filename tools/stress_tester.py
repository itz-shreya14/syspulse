"""
SysPulse Demo Stress & Load Generator
Simulates synthetic CPU/Memory spikes to demonstrate real-time telemetry,
Hog Hunter tracking, and dynamic health alerts.
"""
import time
import sys
import argparse
import multiprocessing

def cpu_worker(duration: int):
    end_time = time.time() + duration
    while time.time() < end_time:
        _ = 999999 ** 2

def run_cpu_stress(cores: int = 2, duration: int = 15):
    print(f"[*] Simulating synthetic CPU load across {cores} cores for {duration} seconds...")
    workers = []
    for _ in range(cores):
        p = multiprocessing.Process(target=cpu_worker, args=(duration,))
        p.start()
        workers.append(p)

    for p in workers:
        p.join()
    print("[+] CPU stress test complete.")

def run_memory_stress(mb: int = 400, duration: int = 10):
    print(f"[*] Allocating {mb} MB in RAM for {duration} seconds...")
    try:
        # Allocate bytes in memory
        chunk = bytearray(mb * 1024 * 1024)
        time.sleep(duration)
        del chunk
        print("[+] Memory stress test complete.")
    except MemoryError:
        print("[!] Out of memory.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SysPulse Synthetic Workload Generator")
    parser.add_argument("--cpu", action="store_true", help="Generate synthetic CPU spike")
    parser.add_argument("--memory", action="store_true", help="Generate synthetic RAM spike")
    parser.add_argument("--cores", type=int, default=2, help="Number of worker processes for CPU")
    parser.add_argument("--duration", type=int, default=15, help="Duration in seconds")

    args = parser.parse_args()

    if not args.cpu and not args.memory:
        print("Usage: python tools/stress_tester.py --cpu [--cores 2] [--duration 15]")
        print("   or: python tools/stress_tester.py --memory [--duration 10]")
        sys.exit(0)

    if args.cpu:
        run_cpu_stress(cores=args.cores, duration=args.duration)
    if args.memory:
        run_memory_stress(duration=args.duration)

