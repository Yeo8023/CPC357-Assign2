// --- PIN CONFIGURATION ---
const int pirPin = 4;       // PIR Sensor Data Pin
const int buzzerPin = 39;   // Buzzer Signal Pin

// --- STATE MANAGEMENT ---
bool motionDetectedBefore = false;
unsigned long lastMotionTime = 0;
const unsigned long COOLDOWN_PERIOD = 5000;   // 5 seconds cooldown to prevent spam
const unsigned long BUZZER_DURATION = 5000;   // 5 seconds buzzer duration (LOUDER & LONGER)
unsigned long buzzerStartTime = 0;
bool buzzerActive = false;
bool alarmOverride = false;  // For remote control from Python

// --- BUZZER SETTINGS ---
// INTRUDER ALARM (MAXIMUM LOUDNESS)
const int BUZZER_FREQ_HIGH = 4000;  // Very high frequency (Hz) - Maximum loudness for passive buzzers
const int BUZZER_FREQ_LOW = 3000;   // High frequency for alternating siren effect
const unsigned long SIREN_INTERVAL = 200;  // Alternate frequency every 200ms (faster = more urgent)
unsigned long lastSirenToggle = 0;
bool sirenHighTone = true;

// WELCOME BEEP (Short & Pleasant)
const int WELCOME_FREQ = 2000;      // Pleasant mid-high frequency (louder than before)
const int WELCOME_BEEP_DURATION = 150;  // Each beep lasts 150ms
const int WELCOME_BEEP_GAP = 100;   // Gap between beeps
const int WELCOME_BEEP_COUNT = 2;   // Number of beeps (2 quick beeps)

// Welcome beep state machine
enum WelcomeState { WELCOME_IDLE, WELCOME_BEEP, WELCOME_GAP };
WelcomeState welcomeState = WELCOME_IDLE;
int welcomeBeepCounter = 0;
unsigned long welcomeBeepTimer = 0;

void setup() {
  Serial.begin(9600);           // Must match Python's BAUD_RATE (9600)
  
  // Configure Pins
  pinMode(pirPin, INPUT);       // Read from PIR sensor
  pinMode(buzzerPin, OUTPUT);   // Write to buzzer
  
  // Start in silence
  noTone(buzzerPin);
  digitalWrite(buzzerPin, LOW);
  
  Serial.println("SYSTEM READY: Waiting for motion...");
}

void loop() {
  // --- 1. CHECK FOR SERIAL COMMANDS FROM PYTHON ---
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command == "ALARM_ON") {
      // Python gateway detected intruder - activate LOUD alarm
      Serial.println("[ACK] ALARM_ON received - Activating LOUD buzzer for 5 seconds");
      alarmOverride = true;
      buzzerActive = true;
      buzzerStartTime = millis();
      lastSirenToggle = millis();
      sirenHighTone = true;
      welcomeState = WELCOME_IDLE;  // Cancel any welcome beep
      tone(buzzerPin, BUZZER_FREQ_HIGH);  // Start with high frequency
    }
    else if (command == "WELCOME") {
      // Python gateway detected authorized user - play welcoming beeps
      Serial.println("[ACK] WELCOME received - Playing friendly beeps");
      welcomeState = WELCOME_BEEP;
      welcomeBeepCounter = 0;
      welcomeBeepTimer = millis();
      tone(buzzerPin, WELCOME_FREQ);  // Start first beep
    }
    else if (command == "ALARM_OFF") {
      // Optional: Allow Python to turn off alarm
      Serial.println("[ACK] ALARM_OFF received");
      alarmOverride = false;
      buzzerActive = false;
      welcomeState = WELCOME_IDLE;
      noTone(buzzerPin);
    }
  }

  // --- 2. READ PIR SENSOR ---
  int motionState = digitalRead(pirPin);
  unsigned long currentTime = millis();

  // --- 3. MOTION DETECTION LOGIC ---
  if (motionState == HIGH && !motionDetectedBefore) {
    // Motion detected for the first time (rising edge)
    
    // Check cooldown period to prevent repeated triggers
    if ((currentTime - lastMotionTime) > COOLDOWN_PERIOD) {
      Serial.println("MOTION");  // *** CRITICAL: Send signal to Python ***
      Serial.println("[DEBUG] Motion Detected! -> Notifying Python Gateway");
      
      motionDetectedBefore = true;
      lastMotionTime = currentTime;
    }
  } 
  else if (motionState == LOW && motionDetectedBefore) {
    // Motion stopped (falling edge)
    motionDetectedBefore = false;
    Serial.println("[DEBUG] Motion ended - Back to monitoring");
  }

  // --- 4. INTRUDER ALARM CONTROL (Siren Effect & Auto-timeout) ---
  if (buzzerActive) {
    // Create alternating siren effect for louder/more noticeable alarm
    if ((currentTime - lastSirenToggle) > SIREN_INTERVAL) {
      sirenHighTone = !sirenHighTone;
      if (sirenHighTone) {
        tone(buzzerPin, BUZZER_FREQ_HIGH);  // High pitch
      } else {
        tone(buzzerPin, BUZZER_FREQ_LOW);   // Low pitch
      }
      lastSirenToggle = currentTime;
    }
    
    // Auto turn off buzzer after 5 seconds duration
    if ((currentTime - buzzerStartTime) > BUZZER_DURATION) {
      noTone(buzzerPin);
      buzzerActive = false;
      alarmOverride = false;
      Serial.println("[DEBUG] LOUD Buzzer ended after 5 seconds");
    }
  }

  // --- 5. WELCOME BEEP CONTROL (State Machine for Short Beeps) ---
  if (welcomeState != WELCOME_IDLE) {
    switch (welcomeState) {
      case WELCOME_BEEP:
        // Playing a beep
        if ((currentTime - welcomeBeepTimer) >= WELCOME_BEEP_DURATION) {
          noTone(buzzerPin);  // Stop beep
          welcomeBeepCounter++;
          
          if (welcomeBeepCounter >= WELCOME_BEEP_COUNT) {
            // All beeps done
            welcomeState = WELCOME_IDLE;
            Serial.println("[DEBUG] Welcome beeps complete");
          } else {
            // Move to gap between beeps
            welcomeState = WELCOME_GAP;
            welcomeBeepTimer = currentTime;
          }
        }
        break;
        
      case WELCOME_GAP:
        // Gap between beeps
        if ((currentTime - welcomeBeepTimer) >= WELCOME_BEEP_GAP) {
          // Start next beep
          tone(buzzerPin, WELCOME_FREQ);
          welcomeState = WELCOME_BEEP;
          welcomeBeepTimer = currentTime;
        }
        break;
        
      default:
        break;
    }
  }

  // Small delay for stability
  delay(100); 
}