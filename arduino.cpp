
#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include <ArduinoJson.h> 
#include "SparkFun_SHTC3.h"
#include "Light_VEML7700.h" 

// --- CONFIGURACIÓN DE RED ---
const char* ssid = "VTR-3288102 5G";
const char* password = "g4wZjph6nkwv";

// --- CONFIGURACIÓN AWS ---
const char* udpAddress = "3.210.134.165"; 
const int udpPort = 5005;

// --- OBJETOS GLOBALES ---
WiFiUDP udp;
SHTC3 mySHTC3;             
Light_VEML7700 VMEL = Light_VEML7700(); 

// Intervalo de envío
unsigned long lastSendTime = 0;
const int interval = 5000; 

void setup() {
  
  Serial.begin(115200);
  time_t timeout = millis();
  while (!Serial) {
    if ((millis() - timeout) < 2000) delay(100);
    else break;
  }

  Serial.println("\n--- Iniciando EcoMind Node V2 ---");


  pinMode(WB_IO2, OUTPUT);
  digitalWrite(WB_IO2, HIGH); 
  delay(300); 

  // 3. Iniciar I2C y Sensores
  Wire.begin(); 
  
  // -- RAK1901 (Temp/Hum) --
  if (mySHTC3.begin() != SHTC3_Status_Nominal) {
    Serial.println("Falló SHTC3 (Temp/Hum).");
  } else {
    Serial.println("SHTC3 Listo.");
  }

  // -- RAK12010 (Luz) --
  
  if (!VMEL.begin()) {
    Serial.println("Sensor de Luz no encontrado (Revisar tornillos).");
  } else {
    Serial.println("VEML7700 Listo (Librería RAK).");
    VMEL.setGain(VEML7700_GAIN_1);
    VMEL.setIntegrationTime(VEML7700_IT_800MS);
    
  
    VMEL.setLowThreshold(10000);
    VMEL.setHighThreshold(20000);
    VMEL.interruptEnable(false); 
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

  // B. Crear JSON 
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
  
  Serial.println("Enviado a AWS");
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
    Serial.println("\nConectado IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nFallo WiFi (Reintentará en loop)");
  }
}
