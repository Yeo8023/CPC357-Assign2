# 🛡️ IOT-Based Intruder Detection System

A smart security system that uses facial recognition to detect intruders, control a physical gate (Servo), and alerts through hardware buzzer and **Google Cloud Platform (GCP)** logging.

## 📋 Features

- **Real-time Face Recognition** - Identifies specific authorized users ("Yeo Din Song", "Lim Yong Jun") vs intruders.
- **Dual-Response Hardware** - 
    - **Authorized**: Opens Gate (Servo 90°) + Welcome Chime.
    - **Intruder**: Locks Gate (Servo 0°) + Loud Alarm.
- **Cloud Logging** - Stores events and intruder photos in **Google Cloud (Firestore & Storage)**.
- **Secure Dashboard** - Password-protected web dashboard hosted on **Cloud Run**.
- **Smart Alerts** - Welcome beep for authorized users, loud alarm for intruders.

## 🌍 SDG 11 Impact Analysis

**Goal 11: Sustainable Cities and Communities**
*Target 11.7: Provide universal access to safe, inclusive and accessible, green and public spaces.*

This project directly contributes to Smart City safety by:
1.  **Automated Surveillance**: Reducing the need for manual guarding of public/private spaces using 24/7 IoT monitoring.
2.  **Crime Deterrence**: Immediate localized alarms (Buzzer) and cloud evidence storage deter unauthorized access.
3.  **Data-Driven Security**: The centralized dashboard allows security personnel to monitor multiple entry points remotely, ensuring efficient resource allocation for urban safety.

## 🔧 Hardware Requirements

- Maker Feather AIoT S3 (ESP32-S3) microcontroller
- PIR Motion Sensor (connected to GPIO 4)
- Passive Buzzer (connected to GPIO 39)
- **Micro Servo Motor (SG90) (connected to GPIO 14)**
- Laptop/PC with webcam

## 💻 Software Requirements

- Python 3.10 (Recommended)
- Arduino IDE (for microcontroller)
- **Google Cloud Platform (GCP)** Account

## 🚀 Quick Setup

### 1. Check Your Python Version

Run this command to check your installed version:
```bash
python --version
# Output Example: Python 3.10.6
```
> **Important:** Note your version. You will need to download the matching `dlib` wheel in Step 3.

### 2. Create Virtual Environment (Recommended)

To avoid conflict, create a virtual environment:

```bash
# 1. Navigate to project
cd IOT-Based-Intruder-Detection-System

# 2. Create environment
python -m venv venv

# 3. Activate it (Run one):
# Windows (CMD):        venv\Scripts\activate
# Windows (PowerShell): .\venv\Scripts\Activate
# Mac / Linux:          source venv/bin/activate
```

### 3. Install Python Dependencies

**For Windows users**, you must install `dlib` manually first.

1.  **Download the correct wheel:**
    Go to the [Dlib Repository](https://github.com/z-mahmud22/Dlib_Windows_Python3.x/releases) and download the `.whl` file matching your Python version (e.g., `cp310` for Python 3.10).
    *Save the file inside this project folder.*

2.  **Install the wheel:**
    ```bash
    # Example for Python 3.10
    pip install dlib-19.22.99-cp310-cp310-win_amd64.whl
    ```

3.  **Install remaining dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### 4. Setup Google Cloud Platform (GCP)

1.  Access the [Google Cloud Console](https://console.cloud.google.com/).
2.  **Create a Project**: Select "New Project" and give it a name.
3.  **Enable Services**:
    *   **Firestore**: Search for "Firestore", select "Native Mode", and create a database.
    *   **Cloud Storage**: Search for "Cloud Storage" and create a bucket.
4.  **Get Credentials**:
    *   Navigate to **IAM & Admin** → **Service Accounts**.
    *   Create account "iot-gateway".
    *   **Grant Roles**: `Cloud Datastore User`, `Storage Object Admin`.
    *   **Keys** tab → **Add Key** → **Create new key (JSON)**.
    *   Rename to `serviceAccountKey.json` and place in this project root.

### 5. Configure Arduino

1. Open `arduinocode/arduinocode.ino` in Arduino IDE.
2. Select board: **Tools → Board → ESP32 Arduino → Cytron Maker Feather AIoT S3**.
3. Select your COM port: **Tools → Port → COMx**.
4. **Install Library**: Search for **ESP32Servo** in Library Manager and install it.
5. Upload the code.

### 6. Add Known Faces

1. Create a `known_faces` folder in the project root.
2. Add photos of authorized people:
   - **Required Names**: `Yeo Din Song.jpg`, `Lim Yong Jun.jpg`.
   - *Note: Only these specific names will trigger the "Authorized" (Gate Open) response.*

### 7. Update COM Port

Edit `security_gateway.py` line 15:
```python
SERIAL_PORT = "COM7"  # Change to your microcontroller's COM port
```

## ▶️ Running the System

### 1. Start Security Gateway (The "Edge" Brain)
This runs on your laptop and connects to the microcontroller.

```bash
python security_gateway.py
```

### 2. View the Dashboard (The "Cloud" View)

**Option A: Run Locally**
```bash
python -m streamlit run dashboard.py
```
*   **Login Password**: `admin123`
*   Access at: http://localhost:8501

**Option B: Deploy to Google Cloud Run**
1.  Push code to GitHub.
2.  Create Cloud Run Service connected to GitHub.
3.  Grant `Cloud Datastore User` and `Storage Object Viewer` permissions to the Cloud Run Service Account.
4.  See detailed steps in `deployment_guide.md`.

**Live Demo**: [Click Here to View Dashboard](https://security-dashboard-432472007208.asia-southeast1.run.app/)

## 📖 How It Works

1. **PIR sensor detects motion** → Arduino sends "MOTION" signal to Python.
2. **Camera captures image** → Python performs face recognition.
3. **If Authorized** (Yeo Din Song / Lim Yong Jun):
   - Gateway sends **'A'**.
   - **Servo rotates 90° (Gate Open)**.
   - Welcome Chime plays.
   - Logs to Firestore.
4. **If Intruder/Unknown**:
   - Gateway sends **'I'**.
   - **Servo stays at 0° (Gate Locked)**.
   - Loud Alarm plays.
   - Photo saved & uploaded to Cloud Storage.
5. **View logs** → Cloud Dashboard (Password Protected) shows events & evidence.

## 📁 Project Structure

```
IOT-Based-Intruder-Detection-System/
├── arduinocode/
│   └── arduinocode.ino          # Microcontroller code (ESP32 + Servo)
├── security_gateway.py          # Main detection system (Edge)
├── dashboard.py                 # Password-protected Web dashboard
├── Dockerfile                   # Cloud Run configuration
├── requirements.txt             # Project dependencies
├── serviceAccountKey.json       # Firebase credentials (local only)
├── known_faces/                 # Authorized people photos
├── intruders/                   # Captured intruder photos
└── README.md                    # This documentation
```

## 📝 License

This project is for educational purposes: CPC357 Project

## 👥 Group Members

| Name | Matric No. |
| :--- | :--- |
| **Lim Yong Jun** | 164598 |
| **Yeo Din Song** | 163369 |
