import socket
import json
import datetime
import os
import requests
from flask import Flask, jsonify, request, render_template
from flask_socketio import SocketIO, emit
from pymongo import MongoClient
from werkzeug.serving import WSGIRequestHandler

# Clase para filtrar logs de la terminal y ocultar el ruido de socket.io
class FiltroLogs(WSGIRequestHandler):
    def log_request(self, code='-', size='-'):
        if 'socket.io' in self.path:
            return
        super().log_request(code, size)

# Configuracion de red y base de datos
UDP_IP = "0.0.0.0"
UDP_PORT = 5005
MONGO_URI = 'mongodb://localhost:27017/'
DB_NAME = 'invernadero_db'

# Configuracion de la API de IA
API_KEY = os.environ.get('OPENROUTER_API_KEY')
URL_API_IA = "https://openrouter.ai/api/v1/chat/completions"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secreto_iot_agronomo_master'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Conexion a MongoDB
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    col_mediciones = db['mediciones_iot']
    col_ia = db['historial_ia']
    print("MongoDB Conectado")
except Exception as e:
    print(f"Error Mongo: {e}")

# Funcion para consultar a la IA
def consultar_deepseek(t, h, l, pregunta_usuario=None):
    if not API_KEY:
        return "Error: Falta configurar OPENROUTER_API_KEY en Linux."

    prompt_system = "Eres un ingeniero agrónomo experto en invernaderos automatizados y IoT."

    if pregunta_usuario and pregunta_usuario.strip() != "":
        # Modo Chatbot: Responde la duda especifica del usuario
        prompt_user = f"""
        DATOS EN TIEMPO REAL:
        - Temperatura: {t} C
        - Humedad: {h} %
        - Luz: {l} Lux

        USUARIO PREGUNTA: "{pregunta_usuario}"

        INSTRUCCIONES: Responde a la pregunta del usuario usando los datos del sensor como contexto.
        Tu respuesta debe ser concisa y no exceder los 400 tokens.
        """
    else:
        # Modo Reporte: Diagnostico automatico
        prompt_user = f"""
        Analiza estos datos actuales: T:{t} C, H:{h} %, L:{l} Lux.
        Dame un diagnostico del estado del cultivo y acciones recomendadas.
        Asegurate de que la respuesta sea breve y directa (max 400 tokens).
        """

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # Volvemos al modelo V3 estandar (deepseek-chat) manteniendo el limite de tokens
    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": prompt_system},
            {"role": "user", "content": prompt_user}
        ],
        "temperature": 0.7,
        "max_tokens": 400
    }

    try:
        print(f"Consultando IA (Modelo: V3 Standard | Modo: {'Chat' if pregunta_usuario else 'Reporte'})...")
        response = requests.post(URL_API_IA, headers=headers, json=payload, timeout=20)

        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"Error OpenRouter: {response.text}"
    except Exception as e:
        return f"Error de conexion IA: {e}"

# Rutas del servidor

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/historial', methods=['GET'])
def obtener_historial():
    try:
        cursor = col_mediciones.find().sort('_id', -1).limit(5)
        registros = list(cursor)
        for reg in registros:
            reg['_id'] = str(reg['_id'])
            if 'timestamp' in reg: reg['timestamp'] = str(reg['timestamp'])
        return jsonify(registros)
    except: return jsonify([])

@app.route('/api/ia/consultar', methods=['POST'])
def trigger_ia():
    try:
        cuerpo = request.json or {}
        pregunta = cuerpo.get('pregunta', "")

        ultimo = col_mediciones.find_one(sort=[('_id', -1)])
        if not ultimo:
            return jsonify({"consejo": "No hay datos de sensores para analizar."})

        t = ultimo.get('t', 0)
        h = ultimo.get('h', 0)
        l = ultimo.get('l', 0)

        consejo = consultar_deepseek(t, h, l, pregunta)

        col_ia.insert_one({
            "fecha": str(datetime.datetime.now()),
            "inputs": {"t": t, "h": h, "l": l},
            "pregunta": pregunta,
            "respuesta": consejo
        })

        return jsonify({"status": "success", "consejo": consejo})

    except Exception as e:
        return jsonify({"consejo": f"Error interno: {e}"})

@app.route('/api/movil/data', methods=['POST'])
def recibir_movil():
    try:
        data = request.json
        data['timestamp'] = str(datetime.datetime.now())
        data['origen'] = 'android'
        col_mediciones.insert_one(data)
        data['_id'] = str(data['_id'])

        print(f"Reporte Movil Recibido: {data.get('observacion', 'Sin texto')}")

        socketio.emit('nuevo_dato_sensor', data)
        return jsonify({"status": "ok"})
    except: return jsonify({"status": "error"}), 500

# Servidor UDP para recibir datos del hardware
def escuchar_sensores_udp():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((UDP_IP, UDP_PORT))
        print(f"UDP Escuchando en puerto {UDP_PORT}")
    except: return

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            msg = data.decode('utf-8')
            try: d_json = json.loads(msg)
            except: d_json = {"raw": msg}

            d_json['timestamp'] = str(datetime.datetime.now())
            d_json['origen_ip'] = addr[0]

            col_mediciones.insert_one(d_json)
            d_json['_id'] = str(d_json['_id'])

            print(f"Sensor: T:{d_json.get('t')} H:{d_json.get('h')} L:{d_json.get('l')}")

            socketio.emit('nuevo_dato_sensor', d_json)
            socketio.sleep(0.01)
        except: socketio.sleep(1)

if __name__ == '__main__':
    socketio.start_background_task(target=escuchar_sensores_udp)

    print("Servidor AgroSense Iniciado")

    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True, request_handler=FiltroLogs)
