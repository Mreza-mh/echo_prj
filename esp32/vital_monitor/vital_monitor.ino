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
const byte RATE_SIZE = 4;
byte rates[RATE_SIZE]; // 4 samples of heart rate array for average size=4
byte rateSpot = 0; // index of the current sample
long lastBeat = 0; //زمان آخرین ضربان
float beatsPerMinute = 0; //heart rate in beats per minute(BPM)  calculate by last beat
int beatAvg = 0; // average heart rate
long lastIRValue = 0; // last LED IR value
uint32_t lastSensorRead = 0; // last time sensor read

const long FINGER_IR_THRESHOLD = 50000; // if the IR value is less than this value, the finger is not on the sensor => noise

// if no beat is detected for more than 3500ms, the beat is stale > beatAvg = 0
const uint32_t BEAT_STALE_MS = 3500;

// ==================== SENSOR ====================
void setLedSafePower() { //setup led power
  sensor.setPulseAmplitudeRed(0x0A);
  sensor.setPulseAmplitudeIR(0x1F);
  sensor.setPulseAmplitudeGreen(0);
}

bool initSensor() { // if sensor is not found, return false else setup led power and return true
  Serial.println("Initializing MAX30102...");
  if (!sensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("MAX30102 NOT FOUND!");
    return false;
  }
  sensor.setup();
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
  for (byte i = 0; i < RATE_SIZE; i++) rates[i] = 0;
  rateSpot = 0;  // index of the current sample
  lastBeat = 0; 
  beatsPerMinute = 0; 
  beatAvg = 0; 
  lastIRValue = 0;
}

void startMeasuring(int pid) {
  patientId = pid;
  if (!sensorReady) sensorReady = initSensor();
  if (!sensorReady) {
    Serial.println("START FAILED: sensor not found");
    return;
  } // else => sensorReady 
  resetHeartRateState(); // reset heart rate state
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
  if (millis() - lastSensorRead < 20) return; // sample rate is 2s
  lastSensorRead = millis(); // update last sensor read

  lastIRValue = sensor.getIR(); // get IR value from sensor

  if (checkForBeat(lastIRValue)) { // full heart beat detected
    long delta = millis() - lastBeat;    // time between last beat and current beat
    lastBeat = millis();
    beatsPerMinute = 60 / (delta / 1000.0);

    if (beatsPerMinute > 20 && beatsPerMinute < 255) { // valid heart rate
      rates[rateSpot++] = (byte)beatsPerMinute; // add heart rate to array
      rateSpot %= RATE_SIZE; // update index of the current sample
      beatAvg = 0; // reset beat average
      for (byte i = 0; i < RATE_SIZE; i++) beatAvg += rates[i]; // calculate average heart rate
      beatAvg /= RATE_SIZE; // update beat average
    }
  }


  bool fingerOff = lastIRValue < FINGER_IR_THRESHOLD;
  bool beatStale = lastBeat != 0 && millis() - lastBeat > BEAT_STALE_MS; // if no beat is detected for more than 3500ms, the beat is stale > beatAvg = 0    new data is false ...  !chace 
  if (fingerOff || beatStale) {
    beatAvg = 0;
    beatsPerMinute = 0;
  }
}

// send data to laravel 
void publishData() { 
  StaticJsonDocument<128> doc; // create JSON
  doc["patient_id"] = patientId;
  doc["device_id"]  = DEVICE_ID;

  bool valid = lastIRValue >= FINGER_IR_THRESHOLD && beatAvg > 0;
  doc["hr"]       = valid ? beatAvg : -999;
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
  mqtt.setSocketTimeout(5); // set mqtt socket timeout
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
