import socket
import json
import datetime
import requests # Preparado para futura integración con IA
from flask import Flask, jsonify, request, render_template
from flask_socketio import SocketIO, emit
from pymongo import MongoClient

# --- CONFIGURACIÓN ---
UDP_IP = "0.0.0.0"       # Escuchar en todas las interfaces
UDP_PORT = 5005          # Puerto para el Rakwireless
MONGO_URI = 'mongodb://localhost:27017/'
DB_NAME = 'invernadero_db'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secreto_seguro_iot'

# Configuración de WebSockets (async_mode='threading' es compatible con todo)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# --- BASE DE DATOS MONGODB ---
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    col_mediciones = db['mediciones_iot'] # Colección principal
    print("✅ Conexión a MongoDB exitosa")
except Exception as e:
    print(f"❌ Error conectando a MongoDB: {e}")

# --- LÓGICA UDP (HILO EN SEGUNDO PLANO) ---
def escuchar_sensores_udp():
    """
    Escucha datos del hardware Rakwireless y los guarda/retransmite.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Esta línea evita el error "Address already in use" al reiniciar
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sock.bind((UDP_IP, UDP_PORT))
        print(f"📡 Servidor UDP activo en puerto {UDP_PORT}...")
    except Exception as e:
        print(f"⚠️ Error al abrir puerto UDP: {e}")
        return

    while True:
        try:
            # Recibir datos (Buffer 1024 bytes)
            data, addr = sock.recvfrom(1024)
            mensaje_raw = data.decode('utf-8')
            
            # Log en consola para ver qué llega
            print(f"📥 Recibido desde {addr[0]}: {mensaje_raw}")

            # 1. Parsear JSON
            try:
                datos_json = json.loads(mensaje_raw)
            except json.JSONDecodeError:
                # Si llega basura o texto plano, lo envolvemos
                datos_json = {"raw": mensaje_raw, "error_parseo": True}

            # 2. Enriquecer datos (Agregar fecha y origen)
            datos_json['timestamp'] = str(datetime.datetime.now())
            datos_json['origen_ip'] = addr[0]

            # 3. GUARDAR EN MONGODB (CRÍTICO PARA LA APP ANDROID)
            col_mediciones.insert_one(datos_json)

            # 4. --- CORRECCIÓN DEL ERROR DE OBJECTID ---
            # MongoDB agrega un campo '_id' que no es texto.
            # Debemos convertirlo a string ANTES de enviarlo por WebSocket.
            datos_json['_id'] = str(datos_json['_id'])
            # -------------------------------------------

            # 5. Enviar a Dashboard Web en Tiempo Real
            socketio.emit('nuevo_dato_sensor', datos_json)
            
            # Pequeña pausa para no saturar la CPU
            socketio.sleep(0.01)

        except Exception as e:
            print(f"⚠️ Error en bucle UDP: {e}")
            socketio.sleep(1) # Esperar un poco antes de reintentar si falla

# --- RUTAS WEB (HTTP) ---

@app.route('/')
def index():
    # Carga el archivo templates/index.html
    return render_template('index.html')

@app.route('/api/historial', methods=['GET'])
def obtener_historial():
    """
    Ruta consumida por la App Android para ver datos.
    """
    try:
        # Traer los últimos 5 registros, del más nuevo al más viejo
        cursor = col_mediciones.find().sort('_id', -1).limit(5)
        registros = list(cursor)

        # Limpiar los objetos de Mongo para que sean JSON válido
        for reg in registros:
            reg['_id'] = str(reg['_id'])
            # Aseguramos que timestamp sea string por si acaso
            if 'timestamp' in reg:
                reg['timestamp'] = str(reg['timestamp'])

        return jsonify(registros)
    except Exception as e:
        print(f"Error historial: {e}")
        return jsonify([])

@app.route('/api/movil/data', methods=['POST'])
def recibir_datos_movil():
    """
    Recibe reportes manuales desde la App Android.
    """
    try:
        data = request.json
        print(f"📱 Reporte Móvil: {data}")
        
        # Agregar timestamp
        data['timestamp'] = str(datetime.datetime.now())
        data['origen'] = 'app_android'
        
        # Guardar y Emitir
        col_mediciones.insert_one(data)
        
        # Corrección ID
        data['_id'] = str(data['_id'])
        
        # Avisar a la web que llegó un reporte manual
        socketio.emit('nuevo_dato_sensor', data)
        
        return jsonify({"status": "recibido"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- INICIO DEL SERVIDOR ---
if __name__ == '__main__':
    # Iniciar el hilo UDP como tarea de fondo gestionada por SocketIO
    socketio.start_background_task(target=escuchar_sensores_udp)
    
    print("🚀 Servidor EcoMind Iniciado. Presiona Ctrl+C para salir.")
    # host='0.0.0.0' es obligatorio para AWS
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)