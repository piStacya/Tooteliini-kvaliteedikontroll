import cv2
import os
import time
from dynamsoft_barcode_reader_bundle import *

# 1. Dynamsoft Litsentsi seadistamine
DYNAMSOFT_LICENSE = "t0084YQEAAIUx4hU4EqEOu9FaT9GprNtmXmbGA7IcvmG7V7l1yrR4WjV1JWPPrLuJoJN4HXVvqroIag2MeSFUJlbpkh0vhl8/Nrk3lffN1GzB7BvBtkl5"
errorCode, errorMsg = LicenseManager.init_license(DYNAMSOFT_LICENSE)
if errorCode != EnumErrorCode.EC_OK:
    print(f"Litsentsi viga: {errorMsg}")

# --- ÜLESANNE 1.1: Seadistamine ---
# TODO: Määra kaust, kus asuvad pildid (nt "kalkun") ja failinime algus (nt "motion_capture_")
folder_path = "../motion detection/rulaad"
file_prefix = "frame_"

if not os.path.exists(folder_path):
    print(f"Viga: Kausta '{folder_path}' ei leitud.")
    exit()

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


# Leiame kõik pildid, mis vastavad prefixile ja lõppevad .jpg-ga
files = [f for f in os.listdir(folder_path) if f.startswith(file_prefix) and f.endswith(".jpg")]
files.sort()

print(f"Töötlen {len(files)} faili kaustas {folder_path}...")

for filename in files:
    full_path = os.path.join(folder_path, filename)
    
    # --- ÜLESANNE 1.2: Triipkoodi tuvastamine ---
    t_start = time.perf_counter()
    result = router.capture(full_path, "ReadBarcodes_Default")
    elapsed_ms = (time.perf_counter() - t_start) * 1000

    barcodes = [item for item in result.get_items()
                if item.get_type() == EnumCapturedResultItemType.CRIT_BARCODE]

    if barcodes:
        texts = ", ".join(item.get_text() for item in barcodes)
        print(f"[{filename}] ({elapsed_ms:.1f} ms) Leitud {len(barcodes)} triipkood: {texts}")
    else:
        print(f"[{filename}] ({elapsed_ms:.1f} ms) Triipkoodi ei leitud.")