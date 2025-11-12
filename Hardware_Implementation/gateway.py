import subprocess
import socket
import threading
import time
import logging

# --- CONFIGURATION ---
DATA_PORT = 5005
GATEWAY_MAC = "E4:5F:01:31:2E:62"
NODE2_MAC = "E4:5F:01:DE:BA:E7"
BLE_CHAR_HANDLE = "0x0014"
# ---------------------

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

def start_wifi_listener():
    sock = None
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('', DATA_PORT))
            logging.info(f"Wifi listener ready on UDP {DATA_PORT}")
            while True:
                data, addr = sock.recvfrom(1024)
                logging.info(f"[Wi-Fi] {data.decode('utf-8', errors='ignore')} from {addr[0]}")
        except Exception as e:
            logging.error(f"Wi-Fi listener error: {e}")
            if sock:
                sock.close()
            time.sleep(2)

def start_ble_listener():
    logging.info("Starting BLE listener...")
    while True:
        try:
            child = subprocess.Popen(
                ['gatttool', '-I'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            child.stdin.write(f'connect {NODE2_MAC}\n')
            child.stdin.flush()
            logging.info(f"Sent connect to {NODE2_MAC}")

            started = time.time()
            while True:
                if time.time() - started > 10:
                    logging.warning("BLE connection timeout; killing gatttool.")
                    child.terminate()
                    break
                line = child.stdout.readline()
                if not line:
                    break
                if 'Notification' in line or 'Characteristic Write Response' in line:
                    logging.info(f"[BLE] {line.strip()}")
            child.wait()
            time.sleep(2)
        except Exception as e:
            logging.error(f"BLE listener error: {e}")
        time.sleep(2)

t_wifi = threading.Thread(target=start_wifi_listener, daemon=True)
t_wifi.start()

start_ble_listener()

