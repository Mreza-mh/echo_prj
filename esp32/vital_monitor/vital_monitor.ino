#include <Wire.h>  // i2c library
#include <WiFi.h>  // wifi library
#include <PubSubClient.h>  // mqtt library
#include <ArduinoJson.h>  // json library

#include "MAX30105.h"
#include "heartRate.h"

#define I2C_SDA 42 //Serial Data
#define I2C_SCL 41 //Serial Clock

// ==================== WiFi ====================
const char* WIFI_SSID = "Kk";
const char* WIFI_PASSWORD = "11111111";

// ==================== MQTT ====================
const char* MQTT_BROKER = "10.179.144.84";
const int MQTT_PORT = 1883;
const char* DEVICE_ID = "ESP32_001";

char CMD_TOPIC[50]; //devices/ESP32_001/cmd  come from frontend
char DATA_TOPIC[50]; //devices/ESP32_001/data  send to frontend

// ==================== Objects ====================
MAX30105 sensor;
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient); //run mqtt obj in wifi obj

// ==================== State ====================
bool measuring = false;
bool sensorReady = false;
int patientId = 0;
uint32_t lastPublish = 0; //last time publish data
uint32_t measureStartMs = 0; //start time of measure

const uint32_t PUBLISH_INTERVAL_MS = 2000; //publish data every 2 seconds


const uint32_t MAX_SESSION_MS = 150000; //150 seconds بیشترین زمان مجاز برای اندازه گیری  120+30=150 
//  چراغ سر همین یکم دیتر خاموش میشه

const uint32_t MQTT_LOST_STOP_MS = 20000; // if mqtt is lost, stop the measure after 20 seconds
uint32_t mqttLostSince = 0;  // from when mqtt is lost?

// ==================== Heart Rate Variables ====================
// IBI method: store the time BETWEEN beats and take the MEDIAN.
// Median kills noisy/false beats; averaging BPM values does not.
const byte IBI_SIZE = 8;          // last 8 inter-beat intervals (~6-8 seconds of data)
uint16_t ibis[IBI_SIZE];          // inter-beat intervals in ms
byte ibiSpot = 0;                 // ring buffer index
byte ibiCount = 0;                // how many valid intervals collected
long lastBeat = 0;                // زمان آخرین ضربان
long lastValidBeat = 0;           // last beat with a valid interval (noise beats do not count)
float beatsPerMinute = 0;         // instantaneous BPM (for serial debug only)
int beatAvg = 0;                  // median-based BPM (the reported value)
long lastIRValue = 0;             // last LED IR value

// valid interval range: 300ms..1500ms  =>  40..200 BPM
const uint16_t IBI_MIN_MS = 300;
const uint16_t IBI_MAX_MS = 1500;

// start reporting after this many valid intervals (~2-3 seconds).
// median still filters outliers; the value just gets steadier as more beats arrive.
const byte IBI_MIN_REPORT = 3;

int lastGoodHR = 0; // last trusted average
uint32_t lastGoodAt = 0; // when we got it

const long FINGER_IR_THRESHOLD = 50000; // if the IR value is less than this value, the finger is not on the sensor => noise

// if no VALID beat is detected for more than 3500ms, the reading is stale > reset HR state
const uint32_t BEAT_STALE_MS = 3500;

// while the finger is ON, keep sending the last good HR for up to 15s during a dropout.
// the finger-on condition (below) makes sure a removed finger still invalidates fast.
const uint32_t GOOD_HR_HOLD_MS = 15000;

// IR must stay below threshold for 500ms CONTINUOUSLY before we call it "finger off".
// a single low sample (light pressure change) must not wipe the reading.
const uint32_t FINGER_OFF_DEBOUNCE_MS = 500;
uint32_t irLowSince = 0;   // since when IR has been below threshold (0 = it is not)
bool fingerOn = false;     // debounced finger state, used by publishData

// ==================== SENSOR ====================
void setLedSafePower() { //setup led power
  sensor.setPulseAmplitudeRed(0x0A);
  sensor.setPulseAmplitudeIR(0x3F);  // ~12.6mA: stronger IR = cleaner pulse signal = stable beat detection
  sensor.setPulseAmplitudeGreen(0);
}

bool initSensor() { // if sensor is not found, return false else setup led power and return true
  Serial.println("Initializing MAX30102...");
  if (!sensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("MAX30102 NOT FOUND!");
    return false;
  }
  // sampleAverage=8: chip averages 8 raw samples per output -> hardware noise filtering
  // sampleRate=400 / 8 = 50Hz effective, plenty for beat detection
  // pulseWidth=411 + adcRange=16384: max resolution
  sensor.setup(0x3F /*ledBrightness*/, 8 /*sampleAverage*/, 2 /*ledMode: Red+IR*/,
               400 /*sampleRate*/, 411 /*pulseWidth*/, 16384 /*adcRange*/);
  setLedSafePower();
  Serial.println("Sensor READY");
  return true;
}

void shutdownSensor() { //shutdown led power
  sensor.setPulseAmplitudeRed(0);
  sensor.setPulseAmplitudeIR(0);
  sensor.setPulseAmplitudeGreen(0);
  Serial.println("Sensor OFF");
}

// ==================== TEST ====================

void testSensorStartup() {
  Serial.println("=== TEST MODE (2s) ===");
  if (initSensor()) { // if sensor is found, delay 2 seconds and shutdown sensor
    delay(2000);
    shutdownSensor();
  }
  Serial.println("=== TEST DONE ===");
}

// ==================== HR STATE ====================
void resetHeartRateState() {
  for (byte i = 0; i < IBI_SIZE; i++) ibis[i] = 0;
  ibiSpot = 0;
  ibiCount = 0;
  lastBeat = 0;
  lastValidBeat = 0;
  beatsPerMinute = 0;
  beatAvg = 0;
  lastIRValue = 0;
}

// median of the collected intervals (robust: one bad beat cannot shift it)
uint16_t medianIBI() {
  uint16_t sorted[IBI_SIZE];
  for (byte i = 0; i < ibiCount; i++) sorted[i] = ibis[i];
  for (byte i = 1; i < ibiCount; i++) {          // insertion sort, max 8 items
    uint16_t key = sorted[i];
    int8_t j = i - 1;
    while (j >= 0 && sorted[j] > key) { sorted[j + 1] = sorted[j]; j--; }
    sorted[j + 1] = key;
  }
  if (ibiCount % 2) return sorted[ibiCount / 2];
  return (sorted[ibiCount / 2 - 1] + sorted[ibiCount / 2]) / 2;
}

void startMeasuring(int pid) {
  patientId = pid;
  if (!sensorReady) sensorReady = initSensor();
  if (!sensorReady) {
    Serial.println("START FAILED: sensor not found");
    return;
  } // else => sensorReady 
  resetHeartRateState(); // reset heart rate state
  lastGoodHR = 0; // new session, forget last patient's value
  lastGoodAt = 0;
  fingerOn = false; // new session, re-detect the finger from scratch
  irLowSince = 0;
  measuring = true;
  measureStartMs = millis();
  lastPublish = 0;
  Serial.println("START");
}

void stopMeasuring(const char* reason) {
  if (!measuring && !sensorReady) return; // stope
  measuring = false;
  shutdownSensor(); // 0 0 0
  sensorReady = false;
  Serial.printf("STOP (%s)\n", reason);
}

// ==================== WIFI ====================
bool connectWiFi() {
  Serial.print("Connecting WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD); // req for connect 

  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 8000) {
    delay(500);
    Serial.print(".");
  } // delay 8 seconds for try to connect

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi OK: " + WiFi.localIP().toString());
    return true;
  }
  Serial.println("\nWiFi FAILED, will keep retrying");
  return false;
}

uint32_t lastWifiRetry = 0;

void ensureWiFi() { // ensure wifi is connected
  if (WiFi.status() == WL_CONNECTED) return;
  if (millis() - lastWifiRetry < 10000) return; // 10 seconds for try to connect again 
  lastWifiRetry = millis();
  Serial.println("WiFi reconnecting...");
  WiFi.reconnect();
}

// ==================== MQTT ====================

// {
//     "action":"start",
//     "patient_id":15
// } 
// onMqttMessage(
//     "devices/ESP32_001/cmd",
//     payload,
//     35
// );
void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  String msg; // convert ASCII payload to string
  for (int i = 0; i < length; i++) msg += (char)payload[i];

  StaticJsonDocument<200> doc;
  if (deserializeJson(doc, msg)) return; // DECODE JSON // if json is not valid, return

  const char* action = doc["action"]; // get action from json
  if (!action) return;

  if (strcmp(action, "start") == 0) {
    startMeasuring(doc["patient_id"] | 0);
  } else if (strcmp(action, "stop") == 0) {
    stopMeasuring("cmd");
  }
}

uint32_t lastMqttAttempt = 0; // last time mqtt attempt

void connectMqtt() {
  if (mqtt.connected()) return;

  uint32_t retryInterval = measuring ? 5000 : 2000; // 5 seconds for measuring, 2 seconds for not measuring  if mqtt is lost, we have more time to reconnect
  if (millis() - lastMqttAttempt < retryInterval) return; // if last mqtt attempt is less than retry interval, return
  lastMqttAttempt = millis(); // update last mqtt attempt

  Serial.print("Connecting MQTT...");
  if (mqtt.connect(DEVICE_ID)) { // connect to mqtt
    Serial.println("OK");
    mqtt.subscribe(CMD_TOPIC); // subscribe to cmd topic if message come send to onMqttMessage()
  } else {
    Serial.println("Fail");
  }
}

// ==================== SENSOR LOGIC ==================== avg of last 4 heart beat
void updateSensor() { // update sensor data used in loop
  sensor.check(); // read all new samples from sensor FIFO

  while (sensor.available()) { // process EVERY sample, checkForBeat needs a continuous stream
    lastIRValue = sensor.getFIFOIR();

    if (checkForBeat(lastIRValue)) { // full heart beat detected
      long delta = millis() - lastBeat;    // time between last beat and current beat
      lastBeat = millis();
      beatsPerMinute = 60000.0 / delta;    // instantaneous, debug only

      if (delta >= IBI_MIN_MS && delta <= IBI_MAX_MS && lastValidBeat != 0) {
        // valid interval (40..200 BPM) AND not the first beat after a reset
        ibis[ibiSpot++] = (uint16_t)delta;
        ibiSpot %= IBI_SIZE;
        if (ibiCount < IBI_SIZE) ibiCount++;

        beatAvg = 60000 / medianIBI(); // BPM from the MEDIAN interval

        if (ibiCount >= IBI_MIN_REPORT) { // enough beats => report it (gets steadier as buffer fills)
          lastGoodHR = beatAvg;
          lastGoodAt = millis();
        }
      }
      lastValidBeat = millis(); // any detected beat keeps the stream "fresh"
    }

    sensor.nextSample();
  }

  // debounced finger detection: one low sample is NOT "finger off"
  if (lastIRValue >= FINGER_IR_THRESHOLD) {
    irLowSince = 0;
    fingerOn = true;
  } else {
    if (irLowSince == 0) irLowSince = millis();
    if (millis() - irLowSince > FINGER_OFF_DEBOUNCE_MS) fingerOn = false;
  }

  bool beatStale = lastValidBeat != 0 && millis() - lastValidBeat > BEAT_STALE_MS; // no valid beat for 3500ms
  if (!fingerOn || beatStale) {
    resetHeartRateState(); // full reset so old beats never mix into the next reading
    // note: lastGoodHR / lastGoodAt survive on purpose; publishData holds them while finger is on
  }
}

// send data to laravel 
void publishData() { 
  StaticJsonDocument<128> doc; // create JSON
  doc["patient_id"] = patientId;
  doc["device_id"]  = DEVICE_ID;

  // valid while the finger is on and we had a trusted value in the last 15s.
  // dropouts (missed beats, brief IR dips) keep showing the last good number;
  // actually removing the finger invalidates within ~500ms (debounce) regardless of hold.
  bool valid = fingerOn && lastGoodHR > 0 && millis() - lastGoodAt < GOOD_HR_HOLD_MS;
  doc["hr"]       = valid ? lastGoodHR : -999;
  doc["valid_hr"] = valid;

  char buf[128];
  serializeJson(doc, buf);

  mqtt.publish(DATA_TOPIC, buf);
  Serial.printf("IR=%lu | BPM=%.2f | AVG=%d\n", lastIRValue, beatsPerMinute, beatAvg);
}

// ==================== SAFETY ====================
void enforceSafetyStop() {
  //measuring = true (come start)  = false (come stop) from back
  if (!measuring) {
    mqttLostSince = 0;
    return;
  }

  if (millis() - measureStartMs > MAX_SESSION_MS) { // session timeout  front kharab shod masalan
    stopMeasuring("session timeout");
    return;
  }

  if (mqtt.connected()) {
    mqttLostSince = 0; // no lost so no lost time
  } else {
    if (mqttLostSince == 0) mqttLostSince = millis(); // first lost time 
    else if (millis() - mqttLostSince > MQTT_LOST_STOP_MS) { // more than 20s *** 
      stopMeasuring("mqtt lost");
    }
  }
}

// ==================== SETUP ====================
void setup() {
  Serial.begin(115200); //Baud Rate
  Wire.begin(I2C_SDA, I2C_SCL); // start i2c communication

  testSensorStartup(); // test sensor startup

  snprintf(CMD_TOPIC, sizeof(CMD_TOPIC), "devices/%s/cmd", DEVICE_ID); // devices/ESP32_001/cmd
  snprintf(DATA_TOPIC, sizeof(DATA_TOPIC), "devices/%s/data", DEVICE_ID); // devices/ESP32_001/data

  connectWiFi(); // connect to wifi
  mqtt.setServer(MQTT_BROKER, MQTT_PORT); // set mqtt server
  mqtt.setCallback(onMqttMessage); // set mqtt callback   if message come run onMqttMessage()
  mqtt.setSocketTimeout(1); // short timeout: a lost broker must not freeze the loop (beat detection dies)
  connectMqtt(); // connect to mqtt
  Serial.println("READY..."); // ready to use
}

// ==================== LOOP ====================
void loop() {
  ensureWiFi();
  connectMqtt();
  mqtt.loop();

  enforceSafetyStop();

  if (measuring && sensorReady) {
    updateSensor();

    if (millis() - lastPublish > PUBLISH_INTERVAL_MS) {
      lastPublish = millis();
      publishData();
    }
  }
}
