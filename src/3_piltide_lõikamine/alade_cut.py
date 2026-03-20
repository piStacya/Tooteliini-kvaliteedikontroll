import cv2
import os
import json
from datetime import datetime

# --- KONFIGURATSIOON ---
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
capture_date = datetime(2026, 2, 14)
INPUT_FOLDER = os.path.join(_PROJECT_ROOT, "andmed", "salami", "full_frames")
if not os.path.exists(INPUT_FOLDER):
    print(f"Viga: Sisendkausta '{INPUT_FOLDER}' ei eksisteeri.")
    exit()
image_files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
image_files.sort()

# Alamkaustad erinevatele aladele
SUBS = ["individual_products", "date", "label1", "label2", "product_area"]
# Loome kõik vajalikud kaustad
base_path = os.path.dirname(INPUT_FOLDER)
for sub in SUBS:
    os.makedirs(os.path.join(base_path, sub), exist_ok=True)

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
required_keys = ["rois", "date_area", "label1_below", "label2_above", "product_area_between"]
if not all(k in current_product for k in required_keys):
    print(f"Viga: Tootel {current_product.get('_ean')} puuduvad vajalikud ROI koordinaadid.")
    exit()

for filename in image_files:
    base_name = os.path.splitext(filename)[0]
    file_path = os.path.join(INPUT_FOLDER, filename)
    frame = cv2.imread(file_path)
    if frame is None: continue

    temp_slices = []
    # 1. Samm: Pakendite väljalõikamine ja ettevalmistus
    for pkg_id, coords in current_product["rois"].items():
        x1, y1 = coords[0]
        x2, y2 = coords[1]
        roi_crop = frame[y1:y2, x1:x2]
        rotated = cv2.rotate(roi_crop, cv2.ROTATE_90_COUNTERCLOCKWISE)
        temp_slices.append(rotated)

    max_h = max(s.shape[0] for s in temp_slices)
    max_w = max(s.shape[1] for s in temp_slices)

    # 2. Samm: Detailne tükeldamine (Slicing)
    for i, s_img in enumerate(temp_slices):
        s_idx = i + 1
        # Skaleerime ühtseks
        s_img = cv2.resize(s_img, (max_w, max_h))
        
        # Salvestame individuaalse toote
        cv2.imwrite(os.path.join(base_path, "individual_products", f"{base_name}_s{s_idx}.png"), s_img)

        # Kuupäeva ala
        dx1, dy1 = current_product["date_area"][0]
        dx2, dy2 = current_product["date_area"][1]
        date_crop = s_img[dy1:dy2, dx1:dx2]
        if date_crop.size > 0:
            cv2.imwrite(os.path.join(base_path, "date", f"{base_name}_s{s_idx}_date.png"), date_crop)

        # Alumine silt (Label 1)
        l1_crop = s_img[current_product["label1_below"]:, :]
        if l1_crop.size > 0:
            cv2.imwrite(os.path.join(base_path, "label1", f"{base_name}_s{s_idx}_l1.png"), l1_crop)

        # Ülemine silt (Label 2)
        l2_crop = s_img[:current_product["label2_above"], :]
        if l2_crop.size > 0:
            cv2.imwrite(os.path.join(base_path, "label2", f"{base_name}_s{s_idx}_l2.png"), l2_crop)

        # Toote sisu ala (Product area)
        py1, py2 = current_product["product_area_between"]
        prod_crop = s_img[py1:py2, :]
        if prod_crop.size > 0:
            cv2.imwrite(os.path.join(base_path, "product_area", f"{base_name}_s{s_idx}_prod.png"), prod_crop)

    print(filename+"  -> Tükeldatud ja salvestatud detailid.")

print("\nKõik pildid töödeldud.")
