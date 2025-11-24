import socket
import json
import time
import random

# PONE AQUÍ LA IP ELÁSTICA DE TU SERVIDOR AWS
IP_SERVIDOR = "3.210.134.165" 
PUERTO = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print(f"Enviando datos a {IP_SERVIDOR}:{PUERTO} (Ctrl+C para parar)")

while True:
    # Simulamos datos del RAK1901 (Temp/Hum) y Sensor de Luz
    temperatura = round(random.uniform(20.0, 35.0), 2)
    humedad = round(random.uniform(40.0, 80.0), 2)
    luz = random.randint(200, 800)

    # Formato JSON
    mensaje = {
        "t": temperatura,
        "h": humedad,
        "l": luz,
        "device_id": "rak_simulado_01"
    }
    
    mensaje_bytes = json.dumps(mensaje).encode('utf-8')
    
    sock.sendto(mensaje_bytes, (IP_SERVIDOR, PUERTO))
    print(f"Enviado: {mensaje}")
    
    time.sleep(5) # Enviar cada 5 segundos
