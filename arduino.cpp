/**
 * EcoMind IoT Node - Rakwireless (ESP32 Core RAK11200)
 * Integración Final: WiFi UDP + SHTC3 + VEML7700 (RAK Library)
 */

#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include <ArduinoJson.h> // Versión 7
#include "SparkFun_SHTC3.h"
#include "Light_VEML7700.h" // La librería que tú probaste y funciona

// --- CONFIGURACIÓN DE RED ---
const char* ssid = "VTR-3288102 5G";
const char* password = "g4wZjph6nkwv";

// --- CONFIGURACIÓN AWS ---
const char* udpAddress = "3.210.134.165"; 
const int udpPort = 5005;

// --- OBJETOS GLOBALES ---
WiFiUDP udp;
SHTC3 mySHTC3;                // Temp y Humedad
Light_VEML7700 VMEL = Light_VEML7700(); // Sensor de Luz (RAK)

// Intervalo de envío
unsigned long lastSendTime = 0;
const int interval = 5000; 

void setup() {
  // 1. Iniciar Consola
  Serial.begin(115200);
  time_t timeout = millis();
  while (!Serial) {
    if ((millis() - timeout) < 2000) delay(100);
    else break;
  }

  Serial.println("\n--- Iniciando EcoMind Node V2 ---");

  // 2. ACTIVAR ENERGÍA DE SENSORES (¡LA CLAVE QUE FALTABA!)
  // En WisBlock, el pin WB_IO2 alimenta los slots de sensores.
  pinMode(WB_IO2, OUTPUT);
  digitalWrite(WB_IO2, HIGH); 
  delay(300); // Esperar a que la electricidad se estabilice

  // 3. Iniciar I2C y Sensores
  Wire.begin(); 
  
  // -- RAK1901 (Temp/Hum) --
  if (mySHTC3.begin() != SHTC3_Status_Nominal) {
    Serial.println("❌ Falló SHTC3 (Temp/Hum).");
  } else {
    Serial.println("✅ SHTC3 Listo.");
  }

  // -- RAK12010 (Luz) --
  // Usamos la lógica de tu ejemplo funcional
  if (!VMEL.begin()) {
    Serial.println("❌ Sensor de Luz no encontrado (Revisar tornillos).");
  } else {
    Serial.println("✅ VEML7700 Listo (Librería RAK).");
    VMEL.setGain(VEML7700_GAIN_1);
    VMEL.setIntegrationTime(VEML7700_IT_800MS);
    
    // Configuración extra del ejemplo para estabilidad
    VMEL.setLowThreshold(10000);
    VMEL.setHighThreshold(20000);
    VMEL.interruptEnable(false); // No necesitamos interrupciones físicas ahora
  }

  // 4. Conectar WiFi
  connectWiFi();
}

void loop() {
  // Reconexión automática WiFi
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  // Timer no bloqueante (5 segundos)
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
  
  // Lectura del sensor de luz con la nueva librería
  float lux = VMEL.readLux();

  // Debug local
  Serial.print("T:"); Serial.print(temp);
  Serial.print(" H:"); Serial.print(hum);
  Serial.print(" L:"); Serial.println(lux);

  // B. Crear JSON (ArduinoJson v7)
  JsonDocument doc;
  
  doc["t"] = ((int)(temp * 100)) / 100.0;
  doc["h"] = ((int)(hum * 100)) / 100.0;
  
  // Protección por si el sensor da lecturas raras al inicio
  if (lux < 0) lux = 0; 
  doc["l"] = lux;
  
  doc["device_id"] = "rak_nodo_01";
  
  String jsonString;
  serializeJson(doc, jsonString);

  // C. Enviar UDP a AWS
  udp.beginPacket(udpAddress, udpPort);
  udp.print(jsonString); 
  udp.endPacket();
  
  Serial.println("📤 Enviado a AWS");
}

void connectWiFi() {
  Serial.print("Conectando WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  
  int intentos = 0;
  while (WiFi.status() != WL_CONNECTED && intentos < 10) {
    delay(500);
    Serial.print(".");
    intentos++;
  }
  
  if(WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ Conectado IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n⚠️ Fallo WiFi (Reintentará en loop)");
  }
}
