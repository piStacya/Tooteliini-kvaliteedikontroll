import cv2
import os
import json
import time
from datetime import datetime, timedelta
from dynamsoft_barcode_reader_bundle import *

# Dynamsoft Litsents
DYNAMSOFT_LICENSE = "t0084YQEAAIUx4hU4EqEOu9FaT9GprNtmXmbGA7IcvmG7V7l1yrR4WjV1JWPPrLuJoJN4HXVvqroIag2MeSFUJlbpkh0vhl8/Nrk3lffN1GzB7BvBtkl5"
LicenseManager.init_license(DYNAMSOFT_LICENSE)

# Initsialiseerime triipkoodi lugeja (Router), sätime seaded nii nagu Demo alusel otsustasime
router = CaptureVisionRouter()

template_path = "minimal_template.json"
if not os.path.exists(template_path):
    print(f"Error: Could not find the JSON template at '{template_path}'")
    exit()

err_code, err_msg = router.init_settings_from_file(template_path)
if err_code != EnumErrorCode.EC_OK:
    print(f"Failed to load JSON settings from file: {err_msg}")
    exit()

    

# --- ÜLESANNE 2.1: JSON Andmete lugemine ---
# Meil on fail 'barcode_data.json', kus on info toodete kohta.
data_path = os.path.join(os.path.dirname(__file__), "barcode_data.json")
with open(data_path, "r", encoding="utf-8") as json_file:
    product_db = json.load(json_file)

# Märgime video salvestamise ajaks päeva, mil see tegelikult lindistati 14.02.2026  
capture_date = datetime(2026, 2, 14)

folder_path = "../rulaad" 
file_prefix = "motion_capture_"
files = sorted([f for f in os.listdir(folder_path) if f.startswith(file_prefix) and f.endswith(".jpg")])

print(f"Töötlen tooteid kuupäevaga: {capture_date.strftime('%d.%m.%Y')}")

for filename in files:
    full_path = os.path.join(folder_path, filename)
    start_time = time.perf_counter()
    result = router.capture(full_path, "ReadBarcodes_Default")
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    items = result.get_items() if result is not None else None

    
    if not items:
        print(f"[{filename}] ({elapsed_ms:.1f} ms) Triipkoodi ei leitud.")
        continue

    for item in items:
        if item.get_type() == EnumCapturedResultItemType.CRIT_BARCODE:
            ean = item.get_text()
            
            # --- ÜLESANNE 2.2: Toote otsing ja säilivusaeg ---
            # Sinu ülesanne on:
            # 1. Otsida 'product_db' sõnastikust toodet EAN koodi järgi.
            # 2. Kui toode leiti, võta selle 'name' ja 'expiry_duration' (päevades).
            # 3. Arvuta säilivusaeg: capture_date + expiry_duration.
            # 4. Prindi välja tulemus viisakalt.
            
            product = product_db.get(ean)
            if product:
                product_name = product.get("name") or product.get("ITEMNAME", "Tundmatu toode")
                expiry_duration = product.get("expiry_duration")
                if expiry_duration is None:
                    expiry_duration = product.get("BESTBEFOREDAYS")

                expiry_date = capture_date + timedelta(days=expiry_duration)
                print(
                    f"[{filename}] ({elapsed_ms:.1f} ms) TOODE: {product_name} | "
                    f"SÄILIB KUNI: {expiry_date.strftime('%d.%m.%Y')}"
                )
            else:
                print(f"[{filename}] ({elapsed_ms:.1f} ms) EAN {ean} ei leitud tooteandmebaasist.")
