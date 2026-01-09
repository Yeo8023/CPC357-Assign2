# 🛡️ IOT-Based Intruder Detection System

A smart security system that uses facial recognition to detect intruders and alerts through hardware buzzer and **Google Cloud Platform (GCP)** logging.

## 📋 Features

- **Real-time Face Recognition** - Identifies authorized users vs intruders
- **Hardware Integration** - PIR motion sensor + buzzer alarm on ESP32 microcontroller
- **Cloud Logging** - Stores events and intruder photos in **Google Cloud (Firestore & Storage)**
- **Web Dashboard** - Real-time monitoring via **Cloud Run**
- **Smart Alerts** - Welcome beep for authorized users, loud alarm for intruders

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
- Laptop/PC with webcam

## 💻 Software Requirements

- Python 3.8 or higher
- Arduino IDE (for microcontroller)
- **Google Cloud Platform (GCP)** Account

## 🚀 Quick Setup

### 1. Check Your Python Version

Run this command to check your installed version:
```bash
python --version
# Output Example: Python 3.10.6
```
> **Important:** Note your version (e.g., `3.9`, `3.10`, `3.11`) as you will need to download the matching wheel in Step 3.

### 2. Create Virtual Environment (Recommended)

To avoid conflicts, create a virtual environment:

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

**For Windows users**, you must install `dlib` manually first (it requires C++ tools otherwise).

1.  **Download the correct wheel:**
    Go to the [Dlib Repository](https://github.com/z-mahmud22/Dlib_Windows_Python3.x/releases) and download the `.whl` file matching your Python version:
    *   `cp39` → Python 3.9
    *   `cp310` → Python 3.10 (*Recommended*)
    *   `cp311` → Python 3.11

    *Save the file inside this project folder.*

2.  **Install the wheel:**
    ```bash
    # Example for Python 3.10 (Update filename if yours is different)
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
    *   **Cloud Storage**: Search for "Cloud Storage" and create a bucket (Project ID as name recommended).
4.  **Get Credentials**:
    *   Navigate to **IAM & Admin** → **Service Accounts**.
    *   Click **Create Service Account** -> Name it "iot-gateway".
    *   **Grant Roles**: Add `Cloud Datastore User` and `Storage Object Admin`.
    *   Click the created account → **Keys** tab → **Add Key** → **Create new key (JSON)**.
    *   Rename the downloaded file to `serviceAccountKey.json` and place it in this project root.

### 5. Configure Arduino

1. Open `arduinocode.ino` in Arduino IDE
2. Select board: **Tools → Board → ESP32 Arduino → Cytron Maker Feather AIoT S3**
3. Select your COM port: **Tools → Port → COMX**
4. Upload the code to the microcontroller

### 6. Add Known Faces

1. Create a `known_faces` folder in the project root
2. Add photos of authorized people (one face per image)
3. Name files: `PersonName.jpg` or `PersonName1.jpg`, `PersonName2.jpg`
   - Tip: Multiple photos per person improves recognition

### 7. Update COM Port

Edit `security_gateway.py` line 15:
```python
SERIAL_PORT = "COM3"  # Change to your microcontroller's COM port
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
streamlit run dashboard.py
```
Access at: http://localhost:8501

**Option B: Deploy to Google Cloud Run**
To host clearly on the web (as per Technical Report):
1.  Push this code to GitHub.
2.  Go to [Google Cloud Console - Cloud Run](https://console.cloud.google.com/run).
3.  Click **Create Service**.
4.  Select **"Continuously deploy from a source repository"** and connect your GitHub.
5.  Allow unauthenticated invocations (Public access).
6.  Click **Create**.

**Live Demo**: [Click Here to View Dashboard](https://security-dashboard-432472007208.asia-southeast1.run.app/)

## 📖 How It Works

1. **PIR sensor detects motion** → Arduino sends "MOTION" signal to Python
2. **Camera captures image** → Python performs face recognition
3. **If authorized** → Welcome beep plays, logs to Firestore
4. **If intruder** → Loud alarm plays, saves photo, uploads to Cloud Storage
5. **View logs** → Cloud Dashboard shows all events and evidence

## 📁 Project Structure

```
IOT-Based-Intruder-Detection-System/
├── arduinocode.ino              # Microcontroller code
├── security_gateway.py          # Main detection system (Edge)
├── dashboard.py                 # Web dashboard (Cloud/App)
├── Dockerfile                   # Cloud Run container config
├── requirements.txt             # Project dependencies
├── requirements_dashboard.txt   # Optimized Cloud dependencies
├── serviceAccountKey.json       # Firebase credentials
├── dlib-19.22.99-cp310-*.whl    # Facial recognition wheel
├── known_faces/                 # Authorized people photos
├── intruders/                   # Captured intruder photos
└── .gitignore                   # Git configuration
```

## 🎛️ Configuration

Edit `security_gateway.py` to customize:

- `SERIAL_PORT` - Arduino COM port (line 15)
- `TOLERANCE` - Face recognition sensitivity (line 23, lower = stricter)
- `PREVIEW_DURATION_SECONDS` - Camera preview time (line 27)

## ❓ Troubleshooting

**Camera not opening?**
- Make sure no other application is using the camera
- Try running as administrator

**Arduino not connecting?**
- Check COM port in Device Manager
- Install CP210x USB driver if needed

**Face recognition not working?**
- Ensure good lighting in photos and detection
- Add 2-3 photos per person from different angles
- Adjust `TOLERANCE` value (0.4-0.6 range)

## 📝 License

This project is for educational purposes: CPC357 Project

## 👥 Group Members

| Name | Matric No. |
| :--- | :--- |
| **Lim Yong Jun** | 164598 |
| **Yeo Din Song** | 163369 |
