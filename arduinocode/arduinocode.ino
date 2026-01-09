const int pirPin = 4;       // PIR Sensor Data Pin
const int buzzerPin = 39;   // Buzzer Signal Pin
const int servoPin = 14;    // Servo Motor Pin

// --- LIBRARIES ---
#include <ESP32Servo.h>

// --- OBJECTS ---
Servo gateServo;

// --- STATE MANAGEMENT ---
bool motionDetectedBefore = false;
unsigned long lastMotionTime = 0;
const unsigned long COOLDOWN_PERIOD = 5000;   // 5 seconds cooldown

// Buzzer & Alarm State
const unsigned long BUZZER_DURATION = 5000;   // 5 seconds buzzer duration
unsigned long buzzerStartTime = 0;
bool buzzerActive = false;
bool alarmOverride = false;  // For remote control

// Servo State
const unsigned long GATE_OPEN_DURATION = 5000; // 5 seconds to keep gate open
unsigned long gateOpenTime = 0;
bool isGateOpen = false;

// --- BUZZER SETTINGS ---
// INTRUDER ALARM
const int BUZZER_FREQ_HIGH = 4000;
const int BUZZER_FREQ_LOW = 3000;
const unsigned long SIREN_INTERVAL = 200;
unsigned long lastSirenToggle = 0;
bool sirenHighTone = true;

// WELCOME BEEP
const int WELCOME_FREQ = 2000;
const int WELCOME_BEEP_DURATION = 150;
const int WELCOME_BEEP_GAP = 100;
const int WELCOME_BEEP_COUNT = 2;

// Welcome beep state machine
enum WelcomeState { WELCOME_IDLE, WELCOME_BEEP, WELCOME_GAP };
WelcomeState welcomeState = WELCOME_IDLE;
int welcomeBeepCounter = 0;
unsigned long welcomeBeepTimer = 0;

void setup() {
  Serial.begin(9600);           // Match Python's BAUD_RATE
  
  // Configure Pins
  pinMode(pirPin, INPUT);
  pinMode(buzzerPin, OUTPUT);
  
  // Servo Setup
  gateServo.attach(servoPin);
  gateServo.write(0); // Ensure gate is closed (0 degrees) directly on startup
  
  // Start in silence
  noTone(buzzerPin);
  digitalWrite(buzzerPin, LOW);
  
  Serial.println("SYSTEM READY: Waiting for motion...");
}

void loop() {
  unsigned long currentTime = millis();

  // --- 1. CHECK FOR SERIAL COMMANDS FROM PYTHON ---
  if (Serial.available() > 0) {
    char command = Serial.read(); // Read single character
    
    // Ignore newline/whitespace characters
    if (command == '\n' || command == '\r' || command == ' ') {
      // Do nothing
    }
    else if (command == 'I') {
      // INTRUDER -> Lock Gate & Alarm
      Serial.println("[ACK] 'I' received - INTRUDER! Locking Gate & Alarm.");
      
      // 1. Lock Gate
      gateServo.write(0); 
      isGateOpen = false;

      // 2. Activate Alarm
      alarmOverride = true;
      buzzerActive = true;
      buzzerStartTime = currentTime;
      lastSirenToggle = currentTime;
      sirenHighTone = true;
      welcomeState = WELCOME_IDLE; // Cancel welcome, prioritize alarm
      tone(buzzerPin, BUZZER_FREQ_HIGH);
    }
    else if (command == 'A') {
      // AUTHORIZED -> Open Gate & Welcome
      Serial.println("[ACK] 'A' received - Authorized. Opening Gate.");

      // 1. Open Gate
      gateServo.write(90);
      isGateOpen = true;
      gateOpenTime = currentTime;

      // 2. Play Welcome Chime
      // Only start if not already playing or alarming
      if (!alarmOverride) {
          welcomeState = WELCOME_BEEP;
          welcomeBeepCounter = 0;
          welcomeBeepTimer = currentTime;
          tone(buzzerPin, WELCOME_FREQ);
      }
    }
  }

  // --- 2. GATE AUTO-CLOSE LOGIC ---
  if (isGateOpen) {
    if ((currentTime - gateOpenTime) > GATE_OPEN_DURATION) {
      Serial.println("[INFO] Auto-closing gate.");
      gateServo.write(0);
      isGateOpen = false;
    }
  }

  // --- 3. READ PIR SENSOR ---
  int motionState = digitalRead(pirPin);

  // --- 4. MOTION DETECTION LOGIC ---
  if (motionState == HIGH && !motionDetectedBefore) {
    if ((currentTime - lastMotionTime) > COOLDOWN_PERIOD) {
      Serial.println("MOTION");  // Signal to Python
      Serial.println("[DEBUG] Motion Detected!");
      motionDetectedBefore = true;
      lastMotionTime = currentTime;
    }
  } 
  else if (motionState == LOW && motionDetectedBefore) {
    motionDetectedBefore = false;
  }

  // --- 5. INTRUDER ALARM CONTROL ---
  if (buzzerActive) {
    if ((currentTime - lastSirenToggle) > SIREN_INTERVAL) {
      sirenHighTone = !sirenHighTone;
      if (sirenHighTone) tone(buzzerPin, BUZZER_FREQ_HIGH);
      else tone(buzzerPin, BUZZER_FREQ_LOW);
      lastSirenToggle = currentTime;
    }
    
    if ((currentTime - buzzerStartTime) > BUZZER_DURATION) {
      noTone(buzzerPin);
      buzzerActive = false;
      alarmOverride = false;
      Serial.println("[DEBUG] Alarm ended.");
    }
  }

  // --- 6. WELCOME BEEP CONTROL ---
  if (welcomeState != WELCOME_IDLE) {
    switch (welcomeState) {
      case WELCOME_BEEP:
        if ((currentTime - welcomeBeepTimer) >= WELCOME_BEEP_DURATION) {
          noTone(buzzerPin);
          welcomeBeepCounter++;
          if (welcomeBeepCounter >= WELCOME_BEEP_COUNT) {
            welcomeState = WELCOME_IDLE;
          } else {
            welcomeState = WELCOME_GAP;
            welcomeBeepTimer = currentTime;
          }
        }
        break;
      case WELCOME_GAP:
        if ((currentTime - welcomeBeepTimer) >= WELCOME_BEEP_GAP) {
          tone(buzzerPin, WELCOME_FREQ);
          welcomeState = WELCOME_BEEP;
          welcomeBeepTimer = currentTime;
        }
        break;
    }
  }

  delay(50); // Small delay
}