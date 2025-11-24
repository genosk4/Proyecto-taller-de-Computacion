/**
 * EcoMind IoT Node - Rakwireless (ESP32 Core)
 * Protocolo: UDP directo a AWS
 * Sensores: SHTC3 (RAK1901) + VEM7700 (Luz)
 */

#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include <ArduinoJson.h> // ¡Instalar librería ArduinoJson!
#include "SparkFun_SHTC3.h"
#include "Adafruit_VEM7700.h"

// --- CONFIGURACIÓN DE RED ---
const char* ssid = "TU_WIFI_NOMBRE";
const char* password = "TU_WIFI_PASSWORD";

// --- CONFIGURACIÓN AWS ---
const char* udpAddress = "TU_IP_ELASTICA_AWS"; // Ej: "54.20.10.15"
const int udpPort = 5005;

// --- OBJETOS GLOBALES ---
WiFiUDP udp;
SHTC3 mySHTC3;             // Sensor RAK1901
Adafruit_VEM7700 vem = Adafruit_VEM7700(); // Sensor Luz

// Intervalo de envío (5 segundos)
unsigned long lastSendTime = 0;
const int interval = 5000; 

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10); // Esperar consola

  // 1. Iniciar Sensores I2C
  Wire.begin(); // Pines por defecto del WisBlock (SDA, SCL)
  
  Serial.println("Iniciando sensores...");
  
  // RAK1901 (SHTC3)
  if (mySHTC3.begin() != SHTC3_Status_Nominal) {
    Serial.println("❌ Falló SHTC3 (Temp/Hum). Revisar conexión.");
  } else {
    Serial.println("✅ SHTC3 Listo.");
  }

  // VEM7700 (Luz)
  if (!vem.begin()) {
    Serial.println("❌ Falló VEM7700 (Luz). Revisar conexión.");
  } else {
    Serial.println("✅ VEM7700 Listo.");
    vem.setGain(VEM7700_GAIN_1);
    vem.setIntegrationTime(VEM7700_IT_800MS);
  }

  // 2. Conectar WiFi
  connectWiFi();
}

void loop() {
  // Verificar WiFi y reconectar si se cayó (Robustez)
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  // Enviar datos cada X tiempo (Multitasking básico sin bloquear)
  if (millis() - lastSendTime > interval) {
    lastSendTime = millis();
    enviarDatos();
  }
}

void enviarDatos() {
  // A. Leer Sensores
  mySHTC3.update();
  float temp = mySHTC3.toDegC();
  float hum = mySHTC3.toPercent();
  float lux = vem.readLux();

  // B. Crear JSON Profesional
  // Calculamos tamaño: un JSON pequeño no requiere mucho buffer
  StaticJsonDocument<200> doc;
  doc["t"] = ((int)(temp * 100)) / 100.0; // Redondear a 2 decimales
  doc["h"] = ((int)(hum * 100)) / 100.0;
  doc["l"] = lux;
  doc["device_id"] = "rak_nodo_01";
  
  // Serializar a String
  char jsonBuffer[200];
  serializeJson(doc, jsonBuffer);

  // C. Enviar UDP a AWS
  Serial.print("Enviando a AWS: ");
  Serial.println(jsonBuffer);

  udp.beginPacket(udpAddress, udpPort);
  udp.write((const uint8_t*)jsonBuffer, strlen(jsonBuffer));
  udp.endPacket();
}

void connectWiFi() {
  Serial.print("Conectando a WiFi...");
  WiFi.begin(ssid, password);
  
  int intentos = 0;
  while (WiFi.status() != WL_CONNECTED && intentos < 20) {
    delay(500);
    Serial.print(".");
    intentos++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi Conectado.");
    Serial.print("IP Local: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n❌ Error conectando WiFi.");
  }
}