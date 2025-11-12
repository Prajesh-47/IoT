import subprocess
import socket
import time
import re
import statistics
import logging

# --- CONFIGURATION ---
GATEWAY_IP = "192.168.127.4"
GATEWAY_MAC = "E4:5F:01:31:2E:62"
DATA_PORT = 5005
BLE_CHAR_HANDLE = "0x0014"
BLE_PAYLOAD = "68656c6c6f"
DATA_PACKET = b"hello"
NUM_TEST_PACKETS = 100
TEST_DELAY = 0.1
# ---------------------

logging.basicConfig(level=logging.INFO)

def test_wifi_ping():
    command = ['ping', '-c', '1', '-W', '2', GATEWAY_IP]
    start_time = time.time()
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3.0)
        if result.returncode != 0:
            return None, False
        match = re.search(r"time=([\d\.]+)\s*ms", result.stdout)
        if match:
            latency = float(match.group(1))
            return latency, True
        else:
            return None, False
    except subprocess.TimeoutExpired:
        return None, False
    except Exception as e:
        return None, False

def test_ble_write():
    start = time.time()
    try:
        proc = subprocess.run(['gatttool', '--char-write-req', '-b', GATEWAY_MAC, '-a', BLE_CHAR_HANDLE, '--value=' + BLE_PAYLOAD], timeout=2, capture_output=True)
        if proc.returncode == 0 and "Attribute can't be written" not in proc.stderr:
            latency = (time.time() - start) * 1000
            return latency, True
        else:
            return None, False
    except Exception as e:
        return None, False
def collect_metrics(protocol, num_packets, test_func):
    latencies = []
    failures = 0
    for i in range(num_packets):
        latency, success = test_func()
        if success:
            latencies.append(latency)
        else:
            failures += 1
        time.sleep(TEST_DELAY)
    if not latencies:
        return 0, None, None, None, None, failures
    total_success = num_packets - failures
    reliability = (total_success / num_packets) * 100
    avg_latency = statistics.mean(latencies)
    min_latency = min(latencies) if latencies else None
    max_latency = max(latencies) if latencies else None
    p95_latency = None
    if latencies:
        p95_latency = statistics.quantiles(latencies, n=100, method='exclusive')[94]
    return reliability, avg_latency, min_latency, max_latency, p95_latency, failures

def send_wifi(data):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2)
    try:
        sock.sendto(data, (GATEWAY_IP, DATA_PORT))
        logging.info(f"[Wi-Fi] Data sent")
    except Exception as e:
        logging.warning(f"[Wi-Fi] Send failed: {e}")
    finally:
        sock.close()

def send_ble(data_hex):
    try:
        proc = subprocess.run(['gatttool', '--char-write-req', '-b', GATEWAY_MAC, '-a', BLE_CHAR_HANDLE, '--value=' + data_hex], timeout=2, capture_output=True)
        if proc.returncode == 0 and "Attribute can't be written" not in proc.stderr:
            logging.info("[BLE] Data sent")
        else:
            logging.warning(f"[BLE] Send failed: {proc.stderr if proc.stderr else 'Unknown error'}")
    except Exception as e:
        logging.warning(f"[BLE] Send failed: {e}")

def main():
    wifi_stats = collect_metrics("wifi", NUM_TEST_PACKETS, test_wifi_ping)
    if wifi_stats[0] > 0:
        print(f"Wi-Fi: {wifi_stats[0]:.2f}% rel, {wifi_stats[1]:.2f} ms avg, {wifi_stats[4]:.2f} ms p95, {wifi_stats[5]} failures")
    else:
        print("Wi-Fi: No successful packets.")

    ble_stats = collect_metrics("ble", NUM_TEST_PACKETS, test_ble_write)
    if ble_stats[0] > 0:
        print(f"BLE: {ble_stats[0]:.2f}% rel, {ble_stats[1]:.2f} ms avg, {ble_stats[4]:.2f} ms p95, {ble_stats[5]} failures")
      else:
        print("BLE: No successful packets.")

    if wifi_stats[0] >= ble_stats[0]:
        selected_protocol = "wifi"
        print("Selected: Wi-Fi")
    else:
        selected_protocol = "ble"
        print("Selected: BLE")

    if selected_protocol == "wifi":
        send_wifi(DATA_PACKET)
    elif selected_protocol == "ble":
        send_ble(BLE_PAYLOAD)
    else:
        print("No protocol works.")

if __name__ == "__main__":
    main()


