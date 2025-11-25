# --- IMPORTACIONES ---
import socket
import json
import datetime
# Eliminamos 'threading' nativo y usamos el de la librería
from flask import Flask, jsonify, request, render_template
from flask_socketio import SocketIO, emit

# --- CONFIGURACIÓN ---
UDP_IP = "0.0.0.0"
UDP_PORT = 5005
MONGO_URI = 'mongodb://localhost:27017/'
DB_NAME = 'invernadero_db'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key_segura'

# IMPORTANTE: async_mode='eventlet' (o 'threading' si no tienes eventlet)
# Esto fuerza a que los mensajes fluyan
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading') 

from pymongo import MongoClient

# --- BASE DE DATOS ---
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    col_mediciones = db['mediciones_iot']
    print("✅ Conexión a MongoDB exitosa")
except Exception as e:
    print(f"❌ Error MongoDB: {e}")

# --- LÓGICA UDP ---
def escuchar_sensores_udp():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Evita error de puerto ocupado
    try:
        sock.bind((UDP_IP, UDP_PORT))
    except Exception as e:
        print(f"⚠️ Puerto ocupado: {e}")
        return

    print(f"📡 Servidor UDP escuchando en el puerto {UDP_PORT}...")

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            mensaje_raw = data.decode('utf-8')
            print(f"📥 Recibido: {mensaje_raw}") # Log para debug

            # Parseo
            try:
                datos_json = json.loads(mensaje_raw)
            except:
                datos_json = {"raw": mensaje_raw}

            # Enriquecer dato
            datos_json['timestamp'] = str(datetime.datetime.now())
            
            # Guardar en Mongo (Opcional por ahora si da error)
            # col_mediciones.insert_one(datos_json)

            # --- LA PARTE MÁGICA ---
            # socketio.emit envía el dato A TODOS los navegadores conectados
            socketio.emit('nuevo_dato_sensor', datos_json)
            
            # Pequeña pausa para no saturar CPU
            socketio.sleep(0.01) 

        except Exception as e:
            print(f"Error Loop: {e}")

# --- RUTAS ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/historial', methods=['GET'])
def obtener_historial():
    return jsonify([]) # Placeholder

@app.route('/api/movil/data', methods=['POST'])
def recibir_datos_movil():
    data = request.json
    print(f"📱 Móvil: {data}")
    socketio.emit('nuevo_dato_sensor', data) # Reenviar a la web
    return jsonify({"status": "ok"})

# --- INICIO CORREGIDO ---
if __name__ == '__main__':
    # En lugar de threading.Thread, usamos esto:
    socketio.start_background_task(target=escuchar_sensores_udp)
    
    print("🚀 Iniciando Servidor Web...")
    # allow_unsafe_werkzeug=True permite correr en entornos de desarrollo sin bloqueo
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)