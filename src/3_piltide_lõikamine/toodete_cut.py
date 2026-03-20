import cv2
import os
import json
import time
from datetime import datetime, timedelta
from dynamsoft_barcode_reader_bundle import *

# --- KONFIGURATSIOON ---
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INPUT_FOLDER = os.path.join(_PROJECT_ROOT, "andmed", "rulaad", "full_frames")
OUTPUT_SUBFOLDER = "individual_products"
DYNAMSOFT_LICENSE = "t0084YQEAAIUx4hU4EqEOu9FaT9GprNtmXmbGA7IcvmG7V7l1yrR4WjV1JWPPrLuJoJN4HXVvqroIag2MeSFUJlbpkh0vhl8/Nrk3lffN1GzB7BvBtkl5"
capture_date = datetime(2026, 2, 14)

if not os.path.exists(INPUT_FOLDER):
    print(f"Viga: Sisendkausta '{INPUT_FOLDER}' ei eksisteeri.")
    exit()
# Otsime üles kõik pildid
image_files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
image_files.sort()
print(f"Leiti {len(image_files)} pilti töötlemiseks.")

# Loome väljundkausta
output_base = os.path.join(os.path.dirname(INPUT_FOLDER), OUTPUT_SUBFOLDER)
os.makedirs(output_base, exist_ok=True)

# Vastavustabel kausta nime ja EAN koodi vahel
FOLDER_TO_EAN = {
    "rulaad": "4740574008052",
    "kalkun": "4740574090002",
    "veis": "4740574081192",
    "salami": "4740574009820"
}

ean = FOLDER_TO_EAN.get(os.path.basename(os.path.dirname(INPUT_FOLDER)))

with open(os.path.join(_PROJECT_ROOT, "config", "barcode_data.json"), 'r') as f:
    barcode_data = json.load(f)

current_product = barcode_data.get(ean)
current_product["_ean"] = ean
# Kontrollime, et kõik vajalikud lõikeparameetrid on JSON-is olemas
required_keys = ["rois"]
if not all(k in current_product for k in required_keys):
    print("ROIS väli puudub")
    exit()

for filename in image_files:
    file_path = os.path.join(INPUT_FOLDER, filename)
    frame = cv2.imread(file_path)
    if frame is None: continue

    temp_slices = []
    # Lõikame välja 4 pakendit
    for pkg_id, coords in current_product["rois"].items():
        x1, y1 = coords[0]
        x2, y2 = coords[1]
        roi_crop = frame[y1:y2, x1:x2]
        
        # Roteerime 90 kraadi vastupäeva
        rotated = cv2.rotate(roi_crop, cv2.ROTATE_90_COUNTERCLOCKWISE)
        temp_slices.append(rotated)

    # Skaleerime kõik viilud ühtlasele suurusele (võttes aluseks suurima)
    max_h = max(s.shape[0] for s in temp_slices)
    max_w = max(s.shape[1] for s in temp_slices)
    
    base_name = os.path.splitext(filename)[0]
    
    for i, s_img in enumerate(temp_slices):
        final_slice = cv2.resize(s_img, (max_w, max_h))
        slice_filename = f"{base_name}_slice_{i+1}.png"
        cv2.imwrite(os.path.join(output_base, slice_filename), final_slice)
    
    print(filename+"  -> Salvestatud 4 toote pilti.")
print("\nTöö lõpetatud.")
