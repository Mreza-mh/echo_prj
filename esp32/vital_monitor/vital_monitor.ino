#include <Wire.h>  // i2c library
#include <WiFi.h>  // wifi library
#include <ESPmDNS.h>  // resolve MQTT_BROKER_HOST -> IP via mDNS
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
// روش اول: IP ثابت (اگر لپ‌تاپ همیشه همین IP رو داره، سریع‌تر و بدون وابستگی به mDNS)
// اگر IP عوض شد یا اینجا خالی/اشتباه بود، خودکار fallback به mDNS با MQTT_BROKER_HOST می‌شود
const char* MQTT_BROKER_STATIC_IP = "172.28.43.84";

// روش دوم (fallback): نام لپ‌تاپ روی mDNS — بدون پسوند .local
const char* MQTT_BROKER_HOST = "DESKTOP-I889UM3";

char MQTT_BROKER[16]; // در setup() پر می‌شود (یا از IP ثابت، یا از resolve با mDNS)
const int MQTT_PORT = 1883;
const char* DEVICE_ID = "ESP32_001";

char CMD_TOPIC[50]; //devices/ESP32_001/cmd  come from frontend
char DATA_TOPIC[50]; //devices/ESP32_001/data  send to frontend

// ==================== Objects ====================
MAX30105 sensor;
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient); //run mqtt obj in wifi obj

// ==================== State ====================
bool measuring = false; // now
bool sensorReady = false; // init == 
int patientId = 0;
uint32_t lastPublish = 0; //last time publish data
uint32_t measureStartMs = 0; //start time of measure

const uint32_t PUBLISH_INTERVAL_MS = 2000; //publish data every 2 seconds


const uint32_t MAX_SESSION_MS = 150000; //150 seconds بیشترین زمان مجاز برای اندازه گیری  120+30=150 
//  چراغ سر همین یکم دیتر خاموش میشه

const uint32_t MQTT_LOST_STOP_MS = 20000; // if mqtt is lost, stop the measure after 20 seconds
uint32_t mqttLostSince = 0;  // from when mqtt is lost?

// ==================== Heart Rate Variables ====================
// IBI (Inter Beat Interval): BPM = 60000 / IBI (between two zaraban)

const byte IBI_SIZE = 8;          // آخرین 8 ضربان
uint16_t ibis[IBI_SIZE];          //  IBI ها 
byte ibiSpot = 0;                 // buffer index
byte ibiCount = 0;                // چند مقدار معتبر داخل آرایه داریم
long lastBeat = 0;                // زمان آخرین ضربان
long lastValidBeat = 0;           // زمان اخرین ضربان نمعتبر
float beatsPerMinute = 0;         // لحظه ای  BPM
int beatAvg = 0;                  // median-based BPM 
long lastIRValue = 0;             // last LED IR value

// valid interval range: 300ms..1500ms  =>  40..200 BPM   
// ELSE => NOISE 
const uint16_t IBI_MIN_MS = 300;
const uint16_t IBI_MAX_MS = 1500;

const byte IBI_MIN_REPORT = 2; // تا وقتی 2 ضربان نداشته باشیم خروجی نده (سریع‌تر از 3، پایدارتر از 1)

int lastGoodHR = 0; // last trusted average
uint32_t lastGoodAt = 0; 
const long FINGER_IR_THRESHOLD = 50000; // ir کمتر از این یعنی انگشت روی سنسور نیست

const uint32_t BEAT_STALE_MS = 3500; // 3.5 ثانیه ضربان معتبری نداشتیم همه ریست

const uint32_t GOOD_HR_HOLD_MS = 15000; // تا 15 ثانیه مقدار اخر نگه میداریم البت هاینو تو فرانت هم هندل کردم که نشون بده داره نمیگیره 

const uint32_t FINGER_OFF_DEBOUNCE_MS = 500; // اگر بیشتر از نیم ث بود بگو انگشت رفت
uint32_t irLowSince = 0;   // ir از کی اومده پایین
bool fingerOn = false;

bool freshHrReady = false; // اولین HR معتبر session آماده شد؛ نباید منتظر تیک بعدی publish بمانیم

// ==================== SENSOR ====================
void setLedSafePower() { //setup led power
  sensor.setPulseAmplitudeRed(0x0A);
  sensor.setPulseAmplitudeIR(0x3F);  
  sensor.setPulseAmplitudeGreen(0);
}

bool initSensor() { 
  Serial.println("Initializing MAX30102...");
  if (!sensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("MAX30102 NOT FOUND!");
    return false;
  }

  sensor.setup(0x3F /*ledBrightness*/, 8 /*sampleAverage mean 8 ta*/, 2 /*ledMode: Red+IR*/,
               400 /*sampleRate in s => 400/8=50Hz 50in 1s */, 411 /*pulseWidth for degat*/, 16384 /*adcRange for signal*/);
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
  Serial.println("=== TEST MODE ===");
  if (initSensor()) { // if sensor is found, shutdown right away (no need to wait 2s here)
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

// median of the collected intervals (one bad beat cannot shift it)
uint16_t medianIBI() {
  uint16_t sorted[IBI_SIZE];
  for (byte i = 0; i < ibiCount; i++) sorted[i] = ibis[i]; // copy
  for (byte i = 1; i < ibiCount; i++) {          // insertion sort, max 8 items
    uint16_t key = sorted[i];
    int8_t j = i - 1;
    while (j >= 0 && sorted[j] > key) { sorted[j + 1] = sorted[j]; j--; }
    sorted[j + 1] = key;
  }
  if (ibiCount % 2) return sorted[ibiCount / 2]; // فرد 
  return (sorted[ibiCount / 2 - 1] + sorted[ibiCount / 2]) / 2; // زوج میانگین دوتا وسطی
}

void startMeasuring(int pid) {
  patientId = pid;
  if (!sensorReady) sensorReady = initSensor();
  if (!sensorReady) {
    Serial.println("START FAILED: sensor not found");
    return;
  } // else => sensorReady 
  resetHeartRateState(); // reset
  lastGoodHR = 0; // new session, forget last patient's value
  lastGoodAt = 0;
  fingerOn = false; // new session, re-detect the finger from scratch
  irLowSince = 0;
  measuring = true; // مهم
  measureStartMs = millis();
  lastPublish = 0;
  Serial.println("START");
}

void stopMeasuring(const char* reason) {
  if (!measuring && !sensorReady) return; // stope
  measuring = false;
  shutdownSensor(); // 0 0 0
  sensorReady = false; // مهم
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

// تست سریع: آیا IP ثابت روی پورت MQTT جواب می‌دهد؟ (بدون نیاز به resolve)
bool staticIpReachable() {
  WiFiClient testClient;
  bool ok = testClient.connect(MQTT_BROKER_STATIC_IP, MQTT_PORT, 1500); // 1.5s timeout
  testClient.stop();
  return ok;
}

// آی‌پی لپ‌تاپ را با mDNS پیدا می‌کند (fallback وقتی IP ثابت کار نکند)
bool resolveBrokerHostViaMDNS() {
  if (!MDNS.begin("esp32-vital")) {
    Serial.println("mDNS init failed");
    return false;
  }
  IPAddress ip = MDNS.queryHost(MQTT_BROKER_HOST, 5000);
  if (ip == IPAddress(0, 0, 0, 0)) {
    Serial.printf("mDNS: %s.local peyda nashod\n", MQTT_BROKER_HOST);
    return false;
  }
  snprintf(MQTT_BROKER, sizeof(MQTT_BROKER), "%s", ip.toString().c_str());
  Serial.printf("mDNS: %s.local -> %s\n", MQTT_BROKER_HOST, MQTT_BROKER);
  return true;
}

// روش اول IP ثابت، اگر جواب نداد روش دوم mDNS
bool resolveBrokerHost() {
  Serial.printf("Testing static IP %s:%d ...\n", MQTT_BROKER_STATIC_IP, MQTT_PORT);
  if (staticIpReachable()) {
    snprintf(MQTT_BROKER, sizeof(MQTT_BROKER), "%s", MQTT_BROKER_STATIC_IP);
    Serial.printf("Static IP OK -> %s\n", MQTT_BROKER);
    return true;
  }
  Serial.println("Static IP javab nadad, mDNS emtehan mishavad...");
  return resolveBrokerHostViaMDNS();
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
  if (mqtt.connected()) return; // وصلیم ؟

  uint32_t retryInterval = measuring ? 5000 : 2000; // 5 seconds for measuring, 2 seconds for not measuring درگیر نکنیم اگر توی اندازه گییر هستیم 
  if (millis() - lastMqttAttempt < retryInterval) return; // جلوگیری از لوپ
  lastMqttAttempt = millis(); // update last mqtt attempt

  Serial.print("Connecting MQTT...");
  if (mqtt.connect(DEVICE_ID)) { // connect to mqtt
    Serial.println("OK");
    mqtt.subscribe(CMD_TOPIC); 
    Serial.println("Fail");
  }
}

//  SENSOR LOGIC  avg of last 4 heart beat
void updateSensor() { // update loop
  sensor.check(); // read max FIFO

  while (sensor.available()) { 
    lastIRValue = sensor.getFIFOIR();

    if (checkForBeat(lastIRValue)) { //  heart beat detected import.SparkFun
      long delta = millis() - lastBeat;    // time between last beat and current beat
      lastBeat = millis();
      beatsPerMinute = 60000.0 / delta;    // debug 

      // بازه برای چلوگیری از نویز   فاصله ضربان ها نباید از یه انداز کم یا زیاد باشه 
      if (delta >= IBI_MIN_MS && delta <= IBI_MAX_MS && lastValidBeat != 0) {
        ibis[ibiSpot++] = (uint16_t)delta; // میریزیم تو ارایه 
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

  if (lastIRValue >= FINGER_IR_THRESHOLD) { // finger hast 
    irLowSince = 0;
    fingerOn = true;
  } else { // finger nist
    if (irLowSince == 0) irLowSince = millis();
    if (millis() - irLowSince > FINGER_OFF_DEBOUNCE_MS) fingerOn = false; // تندی فالز نکنیم 
  }

  bool beatStale = lastValidBeat != 0 && millis() - lastValidBeat > BEAT_STALE_MS; //  3500ms
  if (!fingerOn || beatStale) { // 3.5 ث ضربان معتبر نداریم یا انگشت نیست 
    resetHeartRateState(); 
  }
}

// send data to laravel 
void publishData() { 
  StaticJsonDocument<128> doc; // create JSON
  doc["patient_id"] = patientId;
  doc["device_id"]  = DEVICE_ID;

  // یه هذت بیت معتر داریم و ازش بیشتر از 15 ث نگذشته
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
  // از شروع بیشتر از 150 گذشته
  if (millis() - measureStartMs > MAX_SESSION_MS) { 
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

  while (!resolveBrokerHost()) {
    Serial.println("Retrying broker resolve in 2s...");
    delay(2000);
  }

  mqtt.setServer(MQTT_BROKER, MQTT_PORT); // set mqtt server
  mqtt.setCallback(onMqttMessage); // set mqtt callback   if message come run onMqttMessage()
  mqtt.setSocketTimeout(1); // short timeout
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






// START
// IR=0 | BPM=0.00 | AVG=0
// IR=0 | BPM=0.00 | AVG=0
// IR=72011 | BPM=0.00 | AVG=0
// IR=72185 | BPM=0.00 | AVG=0
// IR=72301 | BPM=1.98 | AVG=0
// IR=72397 | BPM=62.31 | AVG=65
