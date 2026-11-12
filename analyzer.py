import psutil
import re
import sys

def parse_logs(log_file):
    print(f"Parsing logs from {log_file} for ERROR and CRITICAL messages...")
    try:
        with open(log_file, 'r') as f:
            for line in f:
                if 'ERROR' in line or 'CRITICAL' in line:
                    print(line.strip())
    except FileNotFoundError:
        print(f"Log file {log_file} not found.")

def get_system_metrics():
    print("--- System Metrics ---")
    try:
        print(f"CPU Usage: {psutil.cpu_percent(interval=1)}%")
        print(f"Memory Usage: {psutil.virtual_memory().percent}%")
        print(f"Disk Usage: {psutil.disk_usage('/').percent}%")
    except Exception as e:
        print(f"Error fetching system metrics: {e}")
    print("----------------------")

if __name__ == "__main__":
    log_file_path = "sample.log"
    if len(sys.argv) > 1:
        log_file_path = sys.argv[1]
    
    get_system_metrics()
    print("\n--- Log Analysis ---")
    parse_logs(log_file_path)
