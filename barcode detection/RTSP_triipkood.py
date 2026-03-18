import cv2
import os
import json
import time
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Ei ava graafikut aknas, lihtsalt salvestab faili
import matplotlib.pyplot as plt
import threading
from datetime import datetime, timedelta
from dynamsoft_barcode_reader_bundle import *


# ─── DYNAMSOFT SEADISTUS ────────────────────────────────────────────────────
DYNAMSOFT_LICENSE = "t0084YQEAAIUx4hU4EqEOu9FaT9GprNtmXmbGA7IcvmG7V7l1yrR4WjV1JWPPrLuJoJN4HXVvqroIag2MeSFUJlbpkh0vhl8/Nrk3lffN1GzB7BvBtkl5"
LicenseManager.init_license(DYNAMSOFT_LICENSE)

router = CaptureVisionRouter()
template_path = "minimal_template.json"
err_code, err_msg = router.init_settings_from_file(template_path)
if err_code != EnumErrorCode.EC_OK:
    print(f"Malli viga: {err_msg}")
    exit()

# ─── TOOTEANDMEBAAS ─────────────────────────────────────────────────────────
data_path = "barcode_data.json"
with open(data_path, "r", encoding="utf-8") as f:
    product_db = json.load(f)

# Video salvestamise kuupäev (kasutame yl2-st tuttavat kuupäeva)
CAPTURE_DATE = datetime(2026, 2, 14)


# ─── RTSP LUGEJA ────────────────────────────────────────────────────────────
class RTSPStreamReader:
    def __init__(self, url):
        self.cap = cv2.VideoCapture(url)
        self.ret = False
        self.frame = None
        self.running = True
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _update(self):
        while self.running:
            ret, frame = self.cap.read()
            if not self.running: break
            with self.lock:
                self.ret = ret
                self.frame = frame
            if not ret: break

    def read(self):
        with self.lock:
            if self.frame is None: return self.ret, None
            return self.ret, self.frame.copy()

    def stop(self):
        self.running = False
        self.thread.join(timeout=1.0)
        self.cap.release()


# ─── KONFIGURATSIOON ────────────────────────────────────────────────────────
STREAM_URL = "rtsp://172.17.37.81:8554/salami"
# STREAM_URL = "rtsp://172.17.37.81:8554/veis"
# STREAM_URL = "rtsp://172.17.37.81:8554/kalkun"
# STREAM_URL = "rtsp://172.17.37.81:8554/rulaad"
# STREAM_URL = "rtsp://172.17.37.81:8554/empty"
# STREAM_URL = "rtsp://172.17.37.81:8554/false_alarm"

MOTION_THRESHOLD = 15.0
CAPTURE_DELAY = 2.5  # ülesandes nõutud

stream_name = STREAM_URL.split('/')[-1]
folder_name = stream_name  # salvesta otse barcode detection kausta alamkausta (ASCII tee)
os.makedirs(folder_name, exist_ok=True)


# ─── ABIFUNKTSIOONID ────────────────────────────────────────────────────────
def is_green_screen(frame):
    """Tuvastab rohelise märguande (tsükli algus/lõpp)."""
    if frame is None: return False
    small = cv2.resize(frame, (64, 64))
    avg_color = np.mean(small, axis=(0, 1))
    return avg_color[1] > 200 and avg_color[0] < 50 and avg_color[2] < 50


def measure_change(f1, f2):
    """Arvutab kahe kaadri MAE halltoonides väiksemas resolutsioonis."""
    g1 = cv2.cvtColor(cv2.resize(f1, (320, 180)), cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(cv2.resize(f2, (320, 180)), cv2.COLOR_BGR2GRAY)
    return float(np.mean(cv2.absdiff(g1, g2)))


def read_barcode(image_path):
    """
    Loeb triipkoodi pildifailist.
    Tagastab (koodid, aeg_ms) kus koodid on list tekstidest.
    """
    t_start = time.perf_counter()
    result = router.capture(image_path, "ReadBarcodes_Default")
    elapsed_ms = (time.perf_counter() - t_start) * 1000

    barcodes = []
    if result:
        for item in result.get_items():
            if item.get_type() == EnumCapturedResultItemType.CRIT_BARCODE:
                barcodes.append(item.get_text())

    return barcodes, elapsed_ms


def lookup_product(ean):
    """
    Otsib toote andmebaasist EAN koodi järgi.
    Tagastab (toote_nimi, säilivusaeg_kuupäev) või (None, None) kui ei leita.
    """
    product = product_db.get(ean)
    if not product:
        return None, None
    name = product.get("ITEMNAME") or product.get("name", "Tundmatu toode")
    days = product.get("BESTBEFOREDAYS") or product.get("expiry_duration", 0)
    expiry = CAPTURE_DATE + timedelta(days=days)
    return name, expiry


# ─── STATISTIKA MUUTUJAD ────────────────────────────────────────────────────
total_tacts = 0          # mitu korda liikumine tuvastati ja pilt tehti
barcode_successes = 0    # mitu korda leiti triipkood
barcode_times = []       # triipkoodi lugemise ajad (ms)
barcode_counts = []      # mitu triipkoodi ühel pildil leiti

# ─── LOGI GRAAFIKU JAOKS ────────────────────────────────────────────────────
change_log = []
time_log = []


# ─── PEAPROGRAM ─────────────────────────────────────────────────────────────
stream = RTSPStreamReader(STREAM_URL)
time.sleep(2)
if not stream.ret:
    print(f"Viga ühendusega: {STREAM_URL}")
    exit()

print(f"Seadistatud: Lävend {MOTION_THRESHOLD}, viivitus {CAPTURE_DELAY}s")

started = False
green_cooldown = False
motion_triggered = False
trigger_time = 0
cycle_start_time = 0
frame_count = 0

try:
    while True:
        ret1, frame1 = stream.read()
        time.sleep(0.02)
        ret2, frame2 = stream.read()

        if not ret1 or not ret2: break

        now = time.time()
        current_is_green = is_green_screen(frame2)

        if not started:
            if current_is_green:
                print(">>> Alustame tsüklit!")
                started = True
                green_cooldown = True
                cycle_start_time = now
        else:
            if not current_is_green:
                green_cooldown = False

            if current_is_green and not green_cooldown:
                print(">>> Lõpetame tsükli.")
                break

            # Liikumise mõõtmine ja logimine
            change = measure_change(frame1, frame2)
            change_log.append(change)
            time_log.append(now - cycle_start_time)

            # Liikumise alguse tuvastamine
            if change > MOTION_THRESHOLD and not motion_triggered:
                motion_triggered = True
                trigger_time = now
                elapsed = now - cycle_start_time
                print(f"  Liikumine tuvastatud {elapsed:.2f}s juures (MAE={change:.2f})")

            # Pärast 2.5s viivitust: salvesta pilt ja loe triipkood
            if motion_triggered and (now - trigger_time) >= CAPTURE_DELAY:
                frame_count += 1
                elapsed = trigger_time - cycle_start_time  # aeg video algusest
                filename = os.path.join(folder_name, f"frame_{frame_count:04d}.jpg")

                ret_save, frame_save = stream.read()
                if ret_save and frame_save is not None:
                    cv2.imwrite(filename, frame_save)

                total_tacts += 1

                # ── Triipkoodi lugemine ──────────────────────────────────
                barcodes, bc_time = read_barcode(filename)
                barcode_times.append(bc_time)
                barcode_counts.append(len(barcodes))

                print(f"\n[Takt {total_tacts}] Aeg: {elapsed:.2f}s | Triipkoodi lugemine: {bc_time:.1f} ms")

                if barcodes:
                    barcode_successes += 1
                    for ean in barcodes:
                        name, expiry = lookup_product(ean)
                        if name:
                            print(f"  EAN: {ean} | Toode: {name} | Säilib kuni: {expiry.strftime('%d.%m.%Y')}")
                        else:
                            print(f"  EAN: {ean} | Toode: tundmatu andmebaasist")
                else:
                    print(f"  Triipkoodi ei leitud.")

                motion_triggered = False

finally:
    stream.stop()

    # ── Statistika ──────────────────────────────────────────────────────────
    print("\n" + "="*50)
    print("STATISTIKA")
    print("="*50)
    if total_tacts > 0:
        rate = barcode_successes / total_tacts * 100
        print(f"Tuvastusmäär:   {barcode_successes}/{total_tacts} ({rate:.1f}%)")
    if barcode_times:
        print(f"Jõudlus:        keskmine {sum(barcode_times)/len(barcode_times):.1f} ms, "
              f"max {max(barcode_times):.1f} ms")
    if barcode_counts:
        avg_count = sum(barcode_counts) / len(barcode_counts)
        print(f"Maht:           keskmiselt {avg_count:.1f} triipkoodi pildi kohta")
    print("="*50)

    # ── Graafik ─────────────────────────────────────────────────────────────
    if change_log:
        stream_name = STREAM_URL.split('/')[-1]
        plt.figure(figsize=(10, 5))
        plt.plot(time_log, change_log, color='steelblue', linewidth=1.0, label='Kaadrite erinevus (MAE)')
        plt.axhline(y=MOTION_THRESHOLD, color='red', linestyle='--', linewidth=1.5,
                    label=f'Lävend ({MOTION_THRESHOLD})')
        plt.title(f'Liikumise tuvastamine - {stream_name}')
        plt.xlabel('Aeg (sekundit)')
        plt.ylabel('MAE')
        plt.legend()
        plt.tight_layout()
        graf_path = f"liikumise_graafik_{stream_name}.png"
        plt.savefig(graf_path, dpi=150)
        plt.close()
        print(f"Graafik salvestatud: {graf_path}")
    else:
        print("Andmeid pole — tsükkel ei käivitunud.")
