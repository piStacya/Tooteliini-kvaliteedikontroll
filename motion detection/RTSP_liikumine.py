import cv2
import os
import time
import numpy as np
import matplotlib.pyplot as plt
import threading


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

"""
Liikumise tuvastamine ja viivitusega salvestamine.

Eesmärk: Tuvastada konveieril liikumine, oodata pildi stabiliseerumist ja salvestada kaader.
"""

# --- KONFIGURATSIOON ---
# STREAM_URL = "rtsp://172.17.37.81:8554/salami"
# STREAM_URL = "rtsp://172.17.37.81:8554/veis"
# STREAM_URL = "rtsp://172.17.37.81:8554/kalkun"
STREAM_URL = "rtsp://172.17.37.81:8554/rulaad"
# STREAM_URL = "rtsp://172.17.37.81:8554/empty"
# STREAM_URL = "rtsp://172.17.37.81:8554/false_alarm"

MOTION_THRESHOLD = 15.0  # Lävend, millest suurem muutus loetakse liikumiseks
CAPTURE_DELAY = 3      # Sekundid, mida oodatakse peale liikumise algust enne pildi tegemist

# Kausta loomine
folder_name = STREAM_URL.split('/')[-1]
os.makedirs(folder_name, exist_ok=True)

def is_green_screen(frame):
    """ Tuvastab rohelise märguande (eelmise ülesande lahendus). """
    if frame is None: return False
    small = cv2.resize(frame, (64, 64))
    avg_color = np.mean(small, axis=(0, 1))
    return avg_color[1] > 200 and avg_color[0] < 50 and avg_color[2] < 50

# --- Muutuse mõõtmine ---
def measure_change(f1, f2):
    """
    Arvutab kahe kaadri vahelise erinevuse.
    Sinu ülesanne: 
    1. Mõõda funktsiooni täitmise aega.
    2. Testi arvutuse kiirust: kas piltide muutmine halltoonidesse ja väiksemaks annab olulist võitu?
    3. Arvuta MAE (Mean Absolute Error), MSE või mõni muu ise välja mõeldud erinevuse või liikumise mõõdik
    4. Prindi välja kulunud aeg ja tagasta arvutatud skoor.
    """
    t_start = time.perf_counter()

    # Halltoonidesse (3 kanalist 1 -> kiirem arvutus)
    g1 = cv2.cvtColor(f1, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(f2, cv2.COLOR_BGR2GRAY)

    # Väiksemaks (kiirendab arvutust oluliselt)
    small1 = cv2.resize(g1, (320, 180))
    small2 = cv2.resize(g2, (320, 180))

    # MAE: pikslite absoluuterinevuste keskmine
    score = float(np.mean(cv2.absdiff(small1, small2)))

    elapsed_ms = (time.perf_counter() - t_start) * 1000
    print(f"measure_change: {elapsed_ms:.3f} ms, skoor: {score:.4f}")

    return score

stream = RTSPStreamReader(STREAM_URL)
time.sleep(2)
if not stream.ret:
    print(f"Viga ühendusega: {STREAM_URL}")
    exit()

print(f"Seadistatud: Lävend {MOTION_THRESHOLD}, viivitus {CAPTURE_DELAY}s")

# Logi salvestamine
# loo siin tühjad listid, et talletada info "muutuse graafik üle aja" jaoks ---
change_log = []   # measure_change() väärtused
time_log = []     # vastavad ajahetked (sekundid alates tsükli algusest)


started = False
green_cooldown = False
motion_triggered = False
trigger_time = 0
cycle_start_time = 0
frame_count = 0

try:
    while True:
        # Loeme kaks järjestikust kaadrit
        ret1, frame1 = stream.read()
        time.sleep(0.02) # Väike paus, et kaadrid jõuaksid muutuda
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

            # Liikumise tuvastamine ja ajastus ---
            # 1. Kutsu välja measure_change() ja salvesta tulemus ka listi. salvesta ka ajahetk.
            # 2. Kui muutus ületab MOTION_THRESHOLD ja 'motion_triggered' on False:
            #    - Märgi liikumine tuvastatuks, salvesta hetke aeg 'trigger_time' muutujasse.
            # 3. Kui 'motion_triggered' on True ja 'CAPTURE_DELAY' aeg on täis:
            #    - Salvesta pilt (cv2.imwrite).
            #    - Reseti 'motion_triggered', et oodata järgmist liikumist.
            
            # 1. Mõõda muutus ja logi
            change = measure_change(frame1, frame2)
            change_log.append(change)
            time_log.append(now - cycle_start_time)

            # 2. Tuvasta liikumise algus
            if change > MOTION_THRESHOLD and not motion_triggered:
                print(f">>> Liikumine tuvastatud! (skoor={change:.2f}) Ootan {CAPTURE_DELAY}s...")
                motion_triggered = True
                trigger_time = now

            # 3. Pärast viivitust salvesta pilt
            if motion_triggered and (now - trigger_time) >= CAPTURE_DELAY:
                frame_count += 1
                filename = os.path.join(folder_name, f"frame_{frame_count:04d}.jpg")
                ret_save, frame_save = stream.read()
                if ret_save and frame_save is not None:
                    cv2.imwrite(filename, frame_save)
                    print(f">>> Pilt salvestatud: {filename}")
                motion_triggered = False

finally:
    stream.stop()
    # joonista graafik, kasuta näiteks plt.plot(), plt.axhline()(lävendi jaoks),
    # pane ka nimi ja telgede nimed. salvesta graafik faili
    if change_log:
        plt.figure(figsize=(10, 5))
        plt.plot(time_log, change_log, color='steelblue', linewidth=1.0, label='Kaadrite erinevus (MAE)')
        plt.axhline(y=MOTION_THRESHOLD, color='red', linestyle='--', linewidth=1.5,
                    label=f'Lävend ({MOTION_THRESHOLD})')
        plt.title('Liikumise tuvastamine konveieril')
        plt.xlabel('Aeg (sekundit)')
        plt.ylabel('MAE')
        plt.legend()
        plt.tight_layout()
        plt.savefig('liikumise_graafik_rulaad.png', dpi=150)
        print("Graafik salvestatud: liikumise_graafik.png")
    else:
        print("Andmeid pole — tsükkel ei käivitunud (rohelist kaadrit ei nähtud).")

