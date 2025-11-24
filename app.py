import socket
import threading
import json
import datetime
from flask import Flask, jsonify, request
from flask_socketio import SocketIO
from pymongo import MongoClient

# --- CONFIGURACIÓN ---
UDP_IP = "0.0.0.0"       # Escuchar en todas las interfaces
UDP_PORT = 5005          # Puerto definido en AWS Security Group
MONGO_URI = 'mongodb://localhost:27017/'
DB_NAME = 'invernadero_db'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key_segura'
# cors_allowed_origins="*" permite que tu App Android y Web se conecten sin bloqueos
socketio = SocketIO(app, cors_allowed_origins="*")

# --- BASE DE DATOS ---
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    col_mediciones = db['mediciones_iot']
    print("✅ Conexión a MongoDB exitosa")
except Exception as e:
    print(f"❌ Error MongoDB: {e}")

# --- LÓGICA UDP (HILO SEPARADO) ---
def escuchar_sensores_udp():
    """
    Esta función corre en segundo plano. Escucha paquetes UDP del Rakwireless,
    los guarda en Mongo y los retransmite por WebSockets.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    print(f"📡 Servidor UDP escuchando en el puerto {UDP_PORT}...")

    while True:
        try:
            # Buffer de 1024 bytes es suficiente para texto corto
            data, addr = sock.recvfrom(1024)
            mensaje_raw = data.decode('utf-8')
            print(f"📥 Dato recibido de {addr}: {mensaje_raw}")

            # 1. Parseo de datos (Asumiremos formato JSON: {"t":25, "h":60, "l":100})
            # Si el sensor manda texto plano, aquí haríamos el split.
            try:
                datos_json = json.loads(mensaje_raw)
            except json.JSONDecodeError:
                # Fallback por si envías texto plano tipo "25.5,60.2"
                print("⚠️ No es JSON válido, guardando como raw")
                datos_json = {"raw": mensaje_raw}

            # 2. Agregar Timestamp y IP origen
            datos_json['timestamp'] = datetime.datetime.now()
            datos_json['origen_ip'] = addr[0]

            # 3. Guardar en MongoDB
            col_mediciones.insert_one(datos_json)

            # 4. Convertir ObjectId a string para que no falle el WebSocket
            datos_json['_id'] = str(datos_json['_id'])
            datos_json['timestamp'] = str(datos_json['timestamp'])

            # 5. REAL-TIME: Enviar a la Web y Móvil conectados
            socketio.emit('nuevo_dato_sensor', datos_json)
            
            # --- AQUÍ INTEGRARÍAMOS DEEPSEEK LUEGO ---
            # if datos_json.get('t', 0) > 30:
            #     consultar_ia(datos_json)

        except Exception as e:
            print(f"Error en loop UDP: {e}")

# --- RUTAS WEB (HTTP) ---
@app.route('/')
def index():
    return "<h1>Servidor EcoMind Activo</h1><p>Escuchando UDP en puerto 5005</p>"

@app.route('/api/historial', methods=['GET'])
def obtener_historial():
    # Retorna los últimos 10 registros para llenar las gráficas al abrir la app
    registros = list(col_mediciones.find().sort('_id', -1).limit(10))
    # Limpieza de objetos no serializables
    for reg in registros:
        reg['_id'] = str(reg['_id'])
        reg['timestamp'] = str(reg['timestamp'])
    return jsonify(registros)

# --- INICIO ---
if __name__ == '__main__':
    # Iniciamos el hilo UDP antes que el servidor web
    hilo_udp = threading.Thread(target=escuchar_sensores_udp)
    hilo_udp.daemon = True # Si se cierra la app, se cierra el hilo
    hilo_udp.start()

    # Iniciamos Flask con SocketIO
    print("🚀 Iniciando Servidor Web...")
    socketio.run(app, host='0.0.0.0', port=5000)