#include <Wire.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#include "MAX30105.h"
#include "heartRate.h"

#define I2C_SDA 42
#define I2C_SCL 41

// ==================== WiFi ====================
const char* WIFI_SSID = "Kk";
const char* WIFI_PASSWORD = "11111111";

// ==================== MQTT ====================
const char* MQTT_BROKER = "10.179.144.84";
const int MQTT_PORT = 1883;
const char* DEVICE_ID = "ESP32_001";

char CMD_TOPIC[50];
char DATA_TOPIC[50];

// ==================== Objects ====================
MAX30105 sensor;
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

// ==================== State ====================
bool measuring = false;
bool sensorReady = false;
int patientId = 0;
uint32_t lastPublish = 0;
uint32_t measureStartMs = 0;

// هر ۲ ثانیه یک reading منتشر می‌شود — فرانت هم با همین بازه poll می‌کند تا سینک بمانند
const uint32_t PUBLISH_INTERVAL_MS = 2000;

// session فرانت ۱۲۰ ثانیه است؛ اگر دستور stop به هر دلیلی نرسد
// (قطع WiFi/MQTT، شکست publish در بک‌اند، بستن مرورگر) خود دستگاه
// کمی بعد از آن خاموش می‌شود تا LED هیچ‌وقت روشن نماند
const uint32_t MAX_SESSION_MS = 150000;

// اگر وسط اندازه‌گیری MQTT قطع بماند، نه داده‌ای به سرور می‌رسد و نه stop —
// پس بعد از این مدت قطعی، اندازه‌گیری را خودمان تمام می‌کنیم
const uint32_t MQTT_LOST_STOP_MS = 20000;
uint32_t mqttLostSince = 0;

// ==================== Heart Rate Variables ====================
const byte RATE_SIZE = 4;
byte rates[RATE_SIZE];
byte rateSpot = 0;
long lastBeat = 0;
float beatsPerMinute = 0;
int beatAvg = 0;
long lastIRValue = 0;
uint32_t lastSensorRead = 0;

const long FINGER_IR_THRESHOLD = 50000;

// اگر مدتی هیچ ضربانی تشخیص داده نشود (قفل سیگنال از دست رفته) ولی انگشت هنوز
// روی سنسور باشد، میانگین قدیمی نامعتبر می‌شود تا برای همیشه یک عدد ثابت تکرار نشود.
// کمی بالاتر از سقف مجاز بازه‌ی معتبر BPM (۳۰۰۰ms = ۲۰ ضربان) تا ضربان واقعی کند هم رد نشود
const uint32_t BEAT_STALE_MS = 3500;

// ==================== SENSOR ====================
void setLedSafePower() {
  sensor.setPulseAmplitudeRed(0x0A);
  sensor.setPulseAmplitudeIR(0x1F);
  sensor.setPulseAmplitudeGreen(0);
}

bool initSensor() {
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

void shutdownSensor() {
  sensor.setPulseAmplitudeRed(0);
  sensor.setPulseAmplitudeIR(0);
  sensor.setPulseAmplitudeGreen(0);
  Serial.println("Sensor OFF");
}

// ==================== TEST ====================
// در بوت ۲ ثانیه چراغ روشن می‌شود تا سلامت سنسور معلوم باشد، بعد خاموش.
// همین خاموش‌کردن تضمین می‌کند بعد از ریستِ وسطِ اندازه‌گیری هم LED روشن نماند
// (رجیسترهای MAX30102 با ریست ESP32 پاک نمی‌شوند — تغذیه‌اش جداست)
void testSensorStartup() {
  Serial.println("=== TEST MODE (2s) ===");
  if (initSensor()) {
    delay(2000);
    shutdownSensor();
  }
  Serial.println("=== TEST DONE ===");
}

// ==================== HR STATE ====================
void resetHeartRateState() {
  for (byte i = 0; i < RATE_SIZE; i++) rates[i] = 0;
  rateSpot = 0;
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
  }
  // بافر ضربان‌ها را برای بیمار جدید پاک می‌کنیم تا داده‌ی session قبلی نشت نکند
  resetHeartRateState();
  measuring = true;
  measureStartMs = millis();
  lastPublish = 0;
  Serial.println("START");
}

void stopMeasuring(const char* reason) {
  if (!measuring && !sensorReady) return;
  measuring = false;
  shutdownSensor();
  sensorReady = false;
  Serial.printf("STOP (%s)\n", reason);
}

// ==================== WIFI ====================
bool connectWiFi() {
  Serial.print("Connecting WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 8000) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi OK: " + WiFi.localIP().toString());
    return true;
  }
  Serial.println("\nWiFi FAILED, will keep retrying");
  return false;
}

uint32_t lastWifiRetry = 0;

void ensureWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  if (millis() - lastWifiRetry < 10000) return;
  lastWifiRetry = millis();
  Serial.println("WiFi reconnecting...");
  WiFi.reconnect();
}

// ==================== MQTT ====================
void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (int i = 0; i < length; i++) msg += (char)payload[i];

  StaticJsonDocument<200> doc;
  if (deserializeJson(doc, msg)) return;

  const char* action = doc["action"];
  if (!action) return;

  if (strcmp(action, "start") == 0) {
    startMeasuring(doc["patient_id"] | 0);
  } else if (strcmp(action, "stop") == 0) {
    stopMeasuring("cmd");
  }
}

uint32_t lastMqttAttempt = 0;

void connectMqtt() {
  if (mqtt.connected()) return;

  // هر تلاشِ ناموفق اتصال، حلقه را به اندازه socket timeout بلاک می‌کند و
  // نمونه‌برداری ۲۰ms ضربان را خراب می‌کند؛ پس وسط اندازه‌گیری کمتر تلاش می‌کنیم
  uint32_t retryInterval = measuring ? 5000 : 2000;
  if (millis() - lastMqttAttempt < retryInterval) return;
  lastMqttAttempt = millis();

  Serial.print("Connecting MQTT...");
  if (mqtt.connect(DEVICE_ID)) {
    Serial.println("OK");
    mqtt.subscribe(CMD_TOPIC);
  } else {
    Serial.println("Fail");
  }
}

// ==================== SENSOR LOGIC ====================
void updateSensor() {
  if (millis() - lastSensorRead < 20) return;
  lastSensorRead = millis();

  lastIRValue = sensor.getIR();

  if (checkForBeat(lastIRValue)) {
    long delta = millis() - lastBeat;
    lastBeat = millis();
    beatsPerMinute = 60 / (delta / 1000.0);

    if (beatsPerMinute > 20 && beatsPerMinute < 255) {
      rates[rateSpot++] = (byte)beatsPerMinute;
      rateSpot %= RATE_SIZE;
      beatAvg = 0;
      for (byte i = 0; i < RATE_SIZE; i++) beatAvg += rates[i];
      beatAvg /= RATE_SIZE;
    }
  }

  // انگشت برداشته شده یا مدتی است هیچ ضربانی تشخیص داده نشده — در هر دو حالت
  // عدد را نامعتبر می‌کنیم تا یک میانگین کهنه برای همیشه گزارش نشود
  bool fingerOff = lastIRValue < FINGER_IR_THRESHOLD;
  bool beatStale = lastBeat != 0 && millis() - lastBeat > BEAT_STALE_MS;
  if (fingerOff || beatStale) {
    beatAvg = 0;
    beatsPerMinute = 0;
  }
}

void publishData() {
  StaticJsonDocument<128> doc;
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
// تضمین می‌کند سنسور فقط در بازه‌ی یک session روشن باشد، حتی اگر stop گم شود
void enforceSafetyStop() {
  if (!measuring) {
    mqttLostSince = 0;
    return;
  }

  if (millis() - measureStartMs > MAX_SESSION_MS) {
    stopMeasuring("session timeout");
    return;
  }

  if (mqtt.connected()) {
    mqttLostSince = 0;
  } else {
    if (mqttLostSince == 0) mqttLostSince = millis();
    else if (millis() - mqttLostSince > MQTT_LOST_STOP_MS) {
      stopMeasuring("mqtt lost");
    }
  }
}

// ==================== SETUP ====================
void setup() {
  Serial.begin(115200);
  Wire.begin(I2C_SDA, I2C_SCL);

  testSensorStartup();

  snprintf(CMD_TOPIC, sizeof(CMD_TOPIC), "devices/%s/cmd", DEVICE_ID);
  snprintf(DATA_TOPIC, sizeof(DATA_TOPIC), "devices/%s/data", DEVICE_ID);

  connectWiFi();
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt.setCallback(onMqttMessage);
  // پیش‌فرض ۱۵ ثانیه است. مقدار ۲ ثانیه‌ی قبلی زیادی سخت‌گیرانه بود: درست بعد از
  // بالا آمدن وای‌فای گاهی هندشیک اول کندتر از ۲ ثانیه طول می‌کشد و به‌جای موفق
  // شدن، fail و retry می‌شد — همین باعث تأخیر در اولین پاسخ می‌شد. ۵ ثانیه هم
  // جلوی فریز طولانیِ حلقه را می‌گیرد و هم برای هندشیک عادی کافی است
  mqtt.setSocketTimeout(5);
  connectMqtt();
  Serial.println("READY...");
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
