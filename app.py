import socket
import json
import datetime
import os
import requests # Librería para consumir la API de OpenRouter
from flask import Flask, jsonify, request, render_template
from flask_socketio import SocketIO, emit
from pymongo import MongoClient

# --- CONFIGURACIÓN DE RED Y BASE DE DATOS ---
UDP_IP = "0.0.0.0"       # Escuchar en todas las interfaces de AWS
UDP_PORT = 5005          # Puerto para recibir datos del Rakwireless
MONGO_URI = 'mongodb://localhost:27017/'
DB_NAME = 'invernadero_db'

# --- CONFIGURACIÓN IA (OPENROUTER) ---
# Leemos la variable de entorno del sistema Linux (Seguridad)
API_KEY = os.environ.get('OPENROUTER_API_KEY') 
URL_API_IA = "https://openrouter.ai/api/v1/chat/completions"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secreto_iot_agronomo_v2'
# async_mode='threading' es el más compatible para scripts sencillos
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# --- CONEXIÓN MONGODB ---
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    col_mediciones = db['mediciones_iot']
    col_ia = db['historial_ia'] # Colección para auditoría de consejos
    print("✅ MongoDB Conectado Exitosamente")
except Exception as e:
    print(f"❌ Error Crítico Mongo: {e}")

# --- FUNCIÓN CEREBRO: CONSULTAR IA ---
def consultar_deepseek(t, h, l):
    """
    Envía los datos a OpenRouter (DeepSeek V3) y retorna un consejo breve.
    """
    if not API_KEY:
        return "⚠️ Error: No se configuró OPENROUTER_API_KEY en el sistema."

    # Prompt de Ingeniería (Contexto Experto)
    prompt_system = "Eres un ingeniero agrónomo experto en invernaderos automatizados. Sé conciso."
    prompt_user = f"""
    Analiza las condiciones actuales:
    - Temperatura: {t}°C
    - Humedad: {h}%
    - Luz: {l} Lux
    
    Responde en MÁXIMO 2 oraciones:
    1. Diagnóstico breve.
    2. Acción inmediata recomendada.
    """

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek/deepseek-chat", # ID del modelo en OpenRouter
        "messages": [
            {"role": "system", "content": prompt_system},
            {"role": "user", "content": prompt_user}
        ],
        "temperature": 0.6, # Creatividad equilibrada
        "max_tokens": 150
    }

    try:
        print("🤖 Consultando a OpenRouter...")
        response = requests.post(URL_API_IA, headers=headers, json=payload, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            # Extraer el texto de la respuesta
            consejo = data['choices'][0]['message']['content']
            return consejo
        else:
            print(f"Error API IA: {response.text}")
            return "Error al conectar con la IA."
            
    except Exception as e:
        print(f"Excepción IA: {e}")
        return "Fallo de conexión externa."

# --- RUTAS HTTP (API REST & WEB) ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/historial', methods=['GET'])
def obtener_historial():
    """
    Devuelve los últimos 5 registros para la App Android.
    """
    try:
        cursor = col_mediciones.find().sort('_id', -1).limit(5)
        registros = list(cursor)
        # Limpieza de objetos Mongo para JSON
        for reg in registros:
            reg['_id'] = str(reg['_id'])
            if 'timestamp' in reg: reg['timestamp'] = str(reg['timestamp'])
        return jsonify(registros)
    except: return jsonify([])

@app.route('/api/ia/consultar', methods=['POST'])
def trigger_ia():
    """
    Endpoint que activa la consulta a la IA (Botón en Web/App).
    """
    try:
        # 1. Buscar último dato REAL del sensor
        ultimo_dato = col_mediciones.find_one(sort=[('_id', -1)])
        
        if not ultimo_dato:
            return jsonify({"consejo": "No hay datos de sensores para analizar."})
            
        t = ultimo_dato.get('t', 0)
        h = ultimo_dato.get('h', 0)
        l = ultimo_dato.get('l', 0)

        # 2. Llamar a OpenRouter
        consejo = consultar_deepseek(t, h, l)
        
        # 3. Guardar auditoría
        col_ia.insert_one({
            "fecha": str(datetime.datetime.now()),
            "inputs": {"t": t, "h": h, "l": l},
            "respuesta": consejo
        })

        # 4. Responder
        return jsonify({
            "status": "success",
            "consejo": consejo,
            "referencia": f"{t}°C / {h}%"
        })

    except Exception as e:
        return jsonify({"consejo": f"Error interno: {e}"})

@app.route('/api/movil/data', methods=['POST'])
def recibir_movil():
    """
    Recibe reportes manuales desde Android.
    """
    try:
        data = request.json
        data['timestamp'] = str(datetime.datetime.now())
        data['origen'] = 'android_app'
        
        col_mediciones.insert_one(data)
        
        # Corrección ObjectId
        data['_id'] = str(data['_id'])
        
        socketio.emit('nuevo_dato_sensor', data)
        return jsonify({"status": "ok"})
    except: return jsonify({"status": "error"}), 500

# --- SERVIDOR UDP (RECEPCIÓN SENSORES) ---
def escuchar_sensores_udp():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sock.bind((UDP_IP, UDP_PORT))
        print(f"📡 UDP Escuchando en puerto {UDP_PORT}...")
    except Exception as e:
        print(f"⚠️ Error binding UDP: {e}")
        return

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            msg = data.decode('utf-8')
            
            # Parseo resiliente
            try:
                d_json = json.loads(msg)
            except:
                d_json = {"raw": msg}
            
            d_json['timestamp'] = str(datetime.datetime.now())
            d_json['origen_ip'] = addr[0]
            
            # Guardar en Mongo
            col_mediciones.insert_one(d_json)
            
            # CORRECCIÓN IMPORTANTE: Convertir ObjectId a String
            d_json['_id'] = str(d_json['_id'])
            
            # Emitir a WebSockets
            socketio.emit('nuevo_dato_sensor', d_json)
            
            socketio.sleep(0.01) # Ceder control a otros hilos
        except Exception as e:
            print(f"Error loop UDP: {e}")
            socketio.sleep(1)

# --- ARRANQUE ---
if __name__ == '__main__':
    # Tarea de fondo para UDP
    socketio.start_background_task(target=escuchar_sensores_udp)
    
    print("🚀 Servidor EcoMind Iniciado en puerto 5000")
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
