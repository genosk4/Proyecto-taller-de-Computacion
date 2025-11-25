/**
 * EcoMind IoT Node - Rakwireless (ESP32 Core)
 * Corregido para ArduinoJson v7 y Errores de Compilación
 */

#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include <ArduinoJson.h> // Versión 7.x
#include "SparkFun_SHTC3.h"
#include "Adafruit_VEML7700.h"

// --- CONFIGURACIÓN DE RED ---
const char* ssid = "VTR-3288102";
const char* password = "g4wZjph6nkwv";

// --- CONFIGURACIÓN AWS ---
// Asegúrate de que esta sea tu IP ELÁSTICA actual
const char* udpAddress = "3.210.134.165"; 
const int udpPort = 5005;

// --- OBJETOS GLOBALES ---
WiFiUDP udp;
SHTC3 mySHTC3;               // Sensor RAK1901
Adafruit_VEML7700 vem = Adafruit_VEML7700(); // Sensor Luz

// Intervalo de envío (5 segundos)
unsigned long lastSendTime = 0;
const int interval = 5000; 

bool sensorLuzActivo = false; // Bandera de seguridad

void setup() {
  Serial.begin(115200);
  // Esperar un poco a que el monitor serie arranque, pero con timeout
  // para no bloquear el chip si no está conectado al PC
  unsigned long startWait = millis();
  while (!Serial && millis() - startWait < 3000) delay(10); 

  // 1. Iniciar Sensores I2C
  Wire.begin(); 
  
  Serial.println("\n--- Iniciando EcoMind Node ---");
  
  // RAK1901 (SHTC3)
  if (mySHTC3.begin() != SHTC3_Status_Nominal) {
    Serial.println("❌ Falló SHTC3 (Temp/Hum). Revisar conexión física.");
  } else {
    Serial.println("✅ SHTC3 Listo.");
  }

  // VEM7700 (Luz)
  // Intentamos iniciar. Si falla, el código sigue pero avisando.
  if (!vem.begin()) {
  Serial.println("❌ Falló VEML7700 (Luz). Revisar conexión física.");
  sensorLuzActivo = false; // Marcar como inactivo
} else {
  Serial.println("✅ VEML7700 Listo.");
  vem.setGain(VEML7700_GAIN_1);
  vem.setIntegrationTime(VEML7700_IT_800MS);
  sensorLuzActivo = true; // Marcar como activo
}
  // 2. Conectar WiFi
  connectWiFi();
}

void loop() {
  // Verificar WiFi y reconectar si se cayó
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  // Enviar datos cada X tiempo
  if (millis() - lastSendTime > interval) {
    lastSendTime = millis();
    enviarDatos();
  }
}

void enviarDatos() {
  // A. Leer Sensores
  mySHTC3.update(); // Pedir nueva lectura al hardware
  
  float temp = mySHTC3.toDegC();
  float hum = mySHTC3.toPercent();
  float lux = 0.0;

  if (sensorLuzActivo) {
   lux = vem.readLux();
} else {
   lux = -1.0; // Valor centinela para indicar error en la gráfica
}

  // B. Crear JSON (Sintaxis ArduinoJson v7)
  // Ya no usamos StaticJsonDocument<200>, el sistema ajusta la memoria solo.
  JsonDocument doc;
  
  doc["t"] = ((int)(temp * 100)) / 100.0; // Redondear 2 decimales
  doc["h"] = ((int)(hum * 100)) / 100.0;
  doc["l"] = lux;
  doc["device_id"] = "rak_nodo_01";
  
  // Serializar a String
  String jsonString;
  serializeJson(doc, jsonString);

  // C. Enviar UDP a AWS
  Serial.print("📤 Enviando a AWS: ");
  Serial.println(jsonString);

  udp.beginPacket(udpAddress, udpPort);
  // print() es más seguro que write() para strings en ESP32 UDP
  udp.print(jsonString); 
  udp.endPacket();
}

void connectWiFi() {
  Serial.print("Conectando a WiFi: ");
  Serial.println(ssid);
  
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
    Serial.println("\n❌ Error conectando WiFi. Reintentando en breve...");
  }
}