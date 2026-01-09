import cv2
import face_recognition
import os
import datetime
import time
import serial
import serial.tools.list_ports
import numpy as np
import re

# Cloud Libraries
import firebase_admin
from firebase_admin import credentials, firestore, storage

# --- CONFIGURATION ---
SERIAL_PORT = "COM3"
BAUD_RATE = 9600
KNOWN_FACES_DIR = "known_faces"
INTRUDERS_DIR = "intruders"
GCP_KEY_PATH = "serviceAccountKey.json"
BUCKET_NAME = "intruder-detection-image"
COLLECTION_NAME = "security_logs"

TOLERANCE = 0.5
MODEL = "hog"

# Camera Preview Settings
PREVIEW_DURATION_SECONDS = 2  # How long to show preview before capturing
SHOW_CAPTURED_RESULT = True  # Show the result with detection boxes

# --- GLOBAL VARIABLES ---
db = None
bucket = None
ser = None

# --- INITIALIZATION FUNCTIONS ---

def initialize_gcp():
    """Initializes Google Cloud Firestore and Storage."""
    global db, bucket
    try:
        if not os.path.exists(GCP_KEY_PATH):
            print(f"[ERROR] GCP Key not found at {GCP_KEY_PATH}. Cloud logging detected disabled.")
            return

        cred = credentials.Certificate(GCP_KEY_PATH)
        firebase_admin.initialize_app(cred, {
            'storageBucket': BUCKET_NAME
        })
        db = firestore.client()
        bucket = storage.bucket()
        print("[INFO] Google Cloud Connected Successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to connect to GCP: {e}")

def initialize_serial():
    """Initializes Serial Connection to Microcontroller."""
    global ser
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        # Allow time for arduino reset
        time.sleep(2) 
        print(f"[INFO] Serial Connected on {SERIAL_PORT}")
    except serial.SerialException:
        print(f"[WARNING] Could not connect to {SERIAL_PORT}. Running in Simulated Mode (No Hardware).")
        ser = None

# --- HELPER FUNCTIONS ---

def trigger_buzzer():
    """Sends command to Microcontroller to sound the alarm."""
    if ser:
        try:
            ser.write(b"ALARM_ON\n")
            print("[Sent] ALARM_ON signal to hardware.")
        except Exception as e:
            print(f"[ERROR] Serial write failed: {e}")
    else:
        print("[SIMULATION] Hardware Alarm Triggered (Buzzer ON)")

def trigger_welcome_beep():
    """Sends command to Microcontroller to play welcoming beep for authorized users."""
    if ser:
        try:
            ser.write(b"WELCOME\n")
            print("[Sent] WELCOME signal to hardware - Playing friendly beeps.")
        except Exception as e:
            print(f"[ERROR] Serial write failed: {e}")
    else:
        print("[SIMULATION] Hardware Welcome Beep (Short & Pleasant)")

def upload_image_to_bucket(local_path):
    """Uploads file to GCS and returns public URL."""
    if not bucket:
        return "No Cloud Connection"
    
    try:
        filename = os.path.basename(local_path)
        blob = bucket.blob(filename)
        blob.upload_from_filename(local_path)
        blob.make_public()
        print(f"[CLOUD] Image uploaded: {blob.public_url}")
        return blob.public_url
    except Exception as e:
        print(f"[ERROR] Upload failed: {e}")
        return "Upload Failed"

def log_event_to_firestore(name, status, image_url=None):
    """Logs the security event to Firestore."""
    if not db:
        return

    data = {
        "timestamp": firestore.SERVER_TIMESTAMP,
        "datetime_str": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "unix_timestamp": time.time(),
        "name": name,
        "status": status,
        "device": "Laptop_Gateway"
    }
    if image_url:
        data["image_url"] = image_url

    try:
        db.collection(COLLECTION_NAME).add(data)
        print(f"[CLOUD] Event logged to Firestore: {status} - {name}")
    except Exception as e:
        print(f"[ERROR] Firestore log failed: {e}")

# --- CORE LOGIC ---

def load_known_faces(directory):
    # Reusing the robust logic from Phase 1
    encodings = []
    names = []
    if not os.path.exists(directory):
        os.makedirs(directory)
        return [], []

    for filename in os.listdir(directory):
        if filename.lower().endswith(('.jpg', '.png', '.jpeg')):
            path = os.path.join(directory, filename)
            try:
                img = cv2.imread(path)
                if img is None: continue
                rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype('uint8')
                face_encs = face_recognition.face_encodings(rgb)
                if face_encs:
                    encodings.append(face_encs[0])
                    # Name Parsing - Remove numerical suffixes
                    basename = os.path.splitext(filename)[0]
                    
                    # First, handle underscore-separated suffixes (e.g., Name_1, Name_2)
                    if "_" in basename:
                         name_part = basename.rsplit('_', 1)[0]
                         suffix = basename.rsplit('_', 1)[1]
                         if suffix.isdigit() or len(suffix) < 3:
                             final_name = name_part
                         else:
                             final_name = basename
                    else:
                        final_name = basename
                    
                    # Second, strip trailing digits directly appended to name (e.g., Name1, Name2, Name3)
                    # Remove all trailing digits from the name
                    final_name = re.sub(r'\d+$', '', final_name).strip()
                    
                    names.append(final_name.title())
            except:
                pass
    return encodings, names

def process_camera(known_encodings, known_names):
    """
    Opens camera, shows preview for positioning, then captures and analyzes frame.
    Optimized for fast camera initialization.
    """
    print("[ACTION] Opening Camera for Verification...")
    
    # Optimize camera opening speed
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Use DirectShow backend (faster on Windows)
    
    # Set camera properties BEFORE reading frames for faster initialization
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer for instant response
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # Lower resolution = faster opening
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)  # Set explicit FPS
    
    # Check if camera opened
    if not cap.isOpened():
        print("[ERROR] Camera failure - Could not open camera.")
        return
    
    print("[INFO] ✅ Camera Connected Successfully!")
    
    # Warmup: Discard first 3 frames (often dark/slow from camera startup)
    for _ in range(3):
        cap.read()
    
    print("[INFO] Showing preview... Position yourself in frame.")
    print(f"[INFO] Capture will happen in {PREVIEW_DURATION_SECONDS} seconds...")
    
    # Show live preview to let user position themselves
    preview_frames = PREVIEW_DURATION_SECONDS * 20  # 20 fps preview
    frame = None
    
    for i in range(preview_frames):
        ret, temp_frame = cap.read()
        if ret:
            frame = temp_frame
            
            # Add text overlay showing countdown
            display_frame = frame.copy()
            seconds_left = PREVIEW_DURATION_SECONDS - (i // 20)
            if seconds_left > 0:
                text = f"Get Ready! Capturing in {seconds_left}..."
                color = (0, 255, 255)  # Yellow
            else:
                text = "CAPTURING NOW!"
                color = (0, 255, 0)  # Green
            
            # Draw text with background for better visibility
            cv2.rectangle(display_frame, (40, 20), (700, 80), (0, 0, 0), -1)
            cv2.putText(display_frame, text, (50, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
            
            # Show preview window
            cv2.imshow('Security Check - Camera Preview', display_frame)
            cv2.waitKey(1)
        time.sleep(0.05)
    
    print("[INFO] 📸 Capturing frame for analysis...")

    if frame is None:
        print("[ERROR] Could not capture image.")
        cap.release()
        cv2.destroyAllWindows()
        return

    # Process Frame
    print("[INFO] Processing face detection...")
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).astype('uint8')
    face_locs = face_recognition.face_locations(rgb_frame, model=MODEL)
    face_encs = face_recognition.face_encodings(rgb_frame, face_locs)

    if not face_locs:
        print("[RESULT] ⚠️  No face detected in the captured frame.")
        print("[TIP] Next time: Make sure you're visible in the preview window")
        # Show the captured frame for reference
        cv2.imshow('Security Check - No Face Detected', frame)
        cv2.waitKey(3000)
        cap.release()
        cv2.destroyAllWindows()
        return

    any_intruder_detected = False
    log_entries = [] # To store logs (Name, Status)

    # LOOP through all faces found
    for (top, right, bottom, left), encoding in zip(face_locs, face_encs):
        person_name = "Unknown"
        is_intruder_face = True
        
        # Check matches (Best Match Logic)
        distances = face_recognition.face_distance(known_encodings, encoding)
        if len(distances) > 0:
            best_idx = np.argmin(distances)
            if distances[best_idx] < TOLERANCE:
                person_name = known_names[best_idx]
                is_intruder_face = False
        
        # Logic Aggregation
        if is_intruder_face:
            any_intruder_detected = True
        
        log_entries.append((person_name, "Intruder" if is_intruder_face else "Authorized"))

        # --- VISUALIZATION DRAWING (Per Face) ---
        color = (0, 0, 255) if is_intruder_face else (0, 255, 0)
        label = "INTRUDER" if is_intruder_face else person_name
        
        cv2.rectangle(frame, (left, top), (right, bottom), color, 3)
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
        cv2.putText(frame, label, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 2)

    # Show the result for 3 seconds
    cv2.imshow('Security Provision', frame)
    cv2.waitKey(3000) 

    # --- DECISION (Aggregated) ---
    
    # 1. Log EVERYONE seen and trigger appropriate sounds
    authorized_detected = False
    for name, status in log_entries:
         if status == "Authorized":
             print(f"✅ Welcome, {name}!")
             log_event_to_firestore(name, "Authorized")
             authorized_detected = True
         # We delay logging intruders until we decide if we need to save the image
    
    # 2. Play welcome beep for authorized users (only if NO intruders present)
    if authorized_detected and not any_intruder_detected:
        trigger_welcome_beep()

    if any_intruder_detected:
        # Case B: At least one Intruder
        print("🚨 INTRUDER DETECTED! 🚨")
        
        # 1. Hardware Action
        trigger_buzzer()
        
        # 2. Save Image (Group shot if multiple people)
        if not os.path.exists(INTRUDERS_DIR): os.makedirs(INTRUDERS_DIR)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        img_name = f"intruder_{ts}.jpg"
        local_path = os.path.join(INTRUDERS_DIR, img_name)
        cv2.imwrite(local_path, frame)
        print(f"[EVIDENCE] Saved to {local_path}")
        
        # 3. Cloud Upload
        url = upload_image_to_bucket(local_path)
        
        # 4. Log the Intruders (with image)
        for name, status in log_entries:
            if status == "Intruder":
                 log_event_to_firestore("Unknown", "Intruder", url)

    cap.release()
    cv2.destroyAllWindows()
    print("[ACTION] Camera Closed. Returning to Listen Mode.")

# --- MAIN LOOP ---

def main():
    print("--- SMART SECURITY GATEWAY STARTED ---")
    
    # Setup
    initialize_gcp()
    initialize_serial()
    
    # Pre-load faces
    print("[INFO] Loading Face Database...")
    known_encs, known_names = load_known_faces(KNOWN_FACES_DIR)
    print(f"[INFO] {len(known_names)} authorized people loaded.")

    print("\n[LISTENING] Waiting for 'MOTION' signal from Serial...")
    
    while True:
        if ser:
            try:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        print(f"[SERIAL] Received: {line}")
                        if "MOTION" in line:
                            process_camera(known_encs, known_names)
                            # Clear buffer to avoid repeat triggers
                            ser.reset_input_buffer()
            except Exception as e:
                print(f"[ERROR] Serial Loop: {e}")
                time.sleep(1)
        else:
            # Simulation fallback: Manual Input
            cmd = input("[SIMULATION] Type 'm' + Enter to simulate MOTION, or 'q' to quit: ")
            if cmd.lower() == 'm':
                process_camera(known_encs, known_names)
            elif cmd.lower() == 'q':
                break
        
        time.sleep(0.1)

if __name__ == "__main__":
    main()
