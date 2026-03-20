import cv2
import os
import sys
import time
import json
import numpy as np
from datetime import datetime, timedelta
from dynamsoft_barcode_reader_bundle import *

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def imwrite(path, img):
    """cv2.imwrite unicode-ohutu asendus Windows jaoks."""
    ext = os.path.splitext(path)[1]
    _, buf = cv2.imencode(ext, img)
    with open(path, 'wb') as f:
        f.write(buf.tobytes())
from helpers import RTSPStreamReader, is_green_screen, measure_global_change

# --- KONFIGURATSIOON ---
# STREAM_URL = "rtsp://172.17.37.81:8554/rulaad"
# STREAM_URL = "rtsp://172.17.37.81:8554/salami"
# STREAM_URL = "rtsp://172.17.37.81:8554/veis"
STREAM_URL = "rtsp://172.17.37.81:8554/kalkun"
# STREAM_URL = "rtsp://172.17.37.81:8554/empty"
# STREAM_URL = "rtsp://172.17.37.81:8554/false_alarm"


MOTION_THRESHOLD = 10.0
CAPTURE_DELAY = 2.5
DYNAMSOFT_LICENSE = "t0084YQEAAIUx4hU4EqEOu9FaT9GprNtmXmbGA7IcvmG7V7l1yrR4WjV1JWPPrLuJoJN4HXVvqroIag2MeSFUJlbpkh0vhl8/Nrk3lffN1GzB7BvBtkl5"
DEBUG_MODE = True  
capture_date = datetime(2026, 2, 14)

# Initsialiseerimine
LicenseManager.init_license(DYNAMSOFT_LICENSE)
router = CaptureVisionRouter()
_orig_dir = os.getcwd()
os.chdir(os.path.join(_PROJECT_ROOT, "config"))
err_code, err_msg = router.init_settings_from_file("minimal_template.json")
os.chdir(_orig_dir)
if err_code != EnumErrorCode.EC_OK:
    print(f"Failed to load JSON settings from file: {err_msg}")
    exit()

with open(os.path.join(_PROJECT_ROOT, "config", "barcode_data.json"), 'r') as f:
    barcode_data = json.load(f)

folder_name = os.path.join(_PROJECT_ROOT, "andmed", STREAM_URL.split('/')[-1])
os.makedirs(folder_name, exist_ok=True)

stream = RTSPStreamReader(STREAM_URL)
time.sleep(2)

# --- Olekumuutujad ---
total_triggers = 0
started = False
green_cooldown = False
motion_triggered = False
trigger_time = 0
cycle_start_time = 0
current_product = None # we maintain a "current product", if a given frame does not have barcode, we proceed with last ean
required_keys = ["rois", "date_area", "label1_below", "label2_above", "product_area_between"]

print(f"Ühendatud vooga {STREAM_URL}. Ootan rohelist märguannet...")

try:
    while True:
        loop_start_t = time.perf_counter() #mõõdame kogu töötlemisele minevat aega
        ret1, frame1 = stream.read()
        time.sleep(0.02) # Väike paus, et kaadrid jõuaksid muutuda
        ret2, frame2 = stream.read()
        if not ret1 or not ret2: break

        now = time.time()
        current_is_green = is_green_screen(frame2)
        
        if not started:
            if current_is_green:
                print(">>> Roheline ekraan tuvastatud! Alustame tsüklit.")
                started = True
                green_cooldown = True
        else:
            process_this_frame = False
            if not current_is_green and green_cooldown:
                print(">>> Roheline ekraan lõppes. Alustame monitooringut.")
                green_cooldown = False
                cycle_start_time = now
                total_triggers += 1
                process_this_frame = True
            elif not green_cooldown:
                if current_is_green:
                    print(">>> Järgmine roheline ekraan tuvastatud. Lõpetan tsükli.")
                    break

                # Mõõdame liikumist
                mae = measure_global_change(frame1, frame2)
                if mae > MOTION_THRESHOLD and not motion_triggered:
                    motion_triggered = True
                    trigger_time = now
                    total_triggers += 1

                if motion_triggered and (now - trigger_time >= CAPTURE_DELAY):
                    process_this_frame = True
                    motion_triggered = False

            if process_this_frame:
                elapsed = now - cycle_start_time
                result = router.capture(frame2, "ReadBarcodes_Default")

                items = result.get_items() if result is not None else None
                barcodes = [item.get_text() for item in items or [] if item.get_type() == EnumCapturedResultItemType.CRIT_BARCODE]

                if len(barcodes) > 0:
                    ean = barcodes[0]
                    product = barcode_data.get(ean)
                    if product is None:
                        print(f"[{elapsed:.2f}s] EAN {ean}: tooteinfot ei leitud.")
                        continue 
                    current_product = product.copy()
                    current_product["_ean"] = ean                        
                
                if current_product is None:
                    print("Meil pole tooteinfot. Jätkame...")
                    continue
                
                if not all(k in current_product for k in required_keys):
                    print(f"VIGA: Tooteinfot EAN {current_product.get('_ean')} on puudulik!")
                    continue
                    
                product_name = current_product.get("ITEMNAME", "Tundmatu toode")
                expiry_duration = current_product.get("BESTBEFOREDAYS", 0)
                expiry_date = capture_date + timedelta(days=expiry_duration)
                ean_str = current_product.get("_ean", "Tundmatu")

                # --- Samm 1: Pakendite väljalõikamine, roteerimine, normaliseerimine ---
                temp_slices = []
                for pkg_id, coords in current_product["rois"].items():
                    x1, y1 = coords[0]
                    x2, y2 = coords[1]
                    roi_crop = frame2[y1:y2, x1:x2]
                    rotated = cv2.rotate(roi_crop, cv2.ROTATE_90_COUNTERCLOCKWISE)
                    temp_slices.append(rotated)

                max_h = max(s.shape[0] for s in temp_slices)
                max_w = max(s.shape[1] for s in temp_slices)
                normalized = [cv2.resize(s, (max_w, max_h)) for s in temp_slices]

                time_to_process = time.perf_counter() - loop_start_t

                # --- Samm 3: Tingimuslik salvestamine ---
                if DEBUG_MODE:
                    base_path = folder_name
                    for sub in ["full_frames", "date", "label1", "label2", "product_area"]:
                        os.makedirs(os.path.join(base_path, sub), exist_ok=True)

                    save_start = time.perf_counter()

                    # Täiskaader
                    imwrite(os.path.join(base_path, "full_frames", f"takt_{total_triggers}.png"), frame2)

                    # --- Samm 2: Detailide eraldamine ja salvestamine ---
                    for i, s_img in enumerate(normalized):
                        s_idx = i + 1

                        # Kuupäeva ala
                        dx1, dy1 = current_product["date_area"][0]
                        dx2, dy2 = current_product["date_area"][1]
                        date_crop = s_img[dy1:dy2, dx1:dx2]
                        if date_crop.size > 0:
                            imwrite(os.path.join(base_path, "date", f"takt_{total_triggers}_s{s_idx}_date.png"), date_crop)

                        # Alumine silt (label1)
                        l1_crop = s_img[current_product["label1_below"]:, :]
                        if l1_crop.size > 0:
                            imwrite(os.path.join(base_path, "label1", f"takt_{total_triggers}_s{s_idx}_l1.png"), l1_crop)

                        # Ülemine silt (label2)
                        l2_crop = s_img[:current_product["label2_above"], :]
                        if l2_crop.size > 0:
                            imwrite(os.path.join(base_path, "label2", f"takt_{total_triggers}_s{s_idx}_l2.png"), l2_crop)

                        # Toote sisu ala
                        py1, py2 = current_product["product_area_between"]
                        prod_crop = s_img[py1:py2, :]
                        if prod_crop.size > 0:
                            imwrite(os.path.join(base_path, "product_area", f"takt_{total_triggers}_s{s_idx}_prod.png"), prod_crop)

                    save_time = time.perf_counter() - save_start
                    print(f"  [DEBUG] Salvestamisaeg: {save_time*1000:.1f} ms")

                print("\n -------------------------------------------- \n")
                print(f"Takt {total_triggers}. Liikumine oli tuvastatud {elapsed:.2f}s juures!")
                print(f"Kontekst: EAN {ean_str} | {product_name} | Aegub {expiry_date.strftime('%d.%m.%Y')}")
                print(f"Töötlemisaeg (ilma salvestamiseta): {time_to_process*1000:.1f} ms")

except KeyboardInterrupt:
    print("Peatatud.")
finally:
    stream.stop()
    print("\nTöö lõpetatud.")
