import socket
import json
import datetime
import os
import requests 
from flask import Flask, jsonify, request, render_template
from flask_socketio import SocketIO, emit
from pymongo import MongoClient

# --- CONFIGURACIÓN GENERAL ---
UDP_IP = "0.0.0.0"       # Escuchar todo el tráfico entrante
UDP_PORT = 5005          # Puerto del Rakwireless
MONGO_URI = 'mongodb://localhost:27017/'
DB_NAME = 'invernadero_db'

# --- CONFIGURACIÓN IA (OPENROUTER) ---
# Leemos la clave del sistema operativo para seguridad
API_KEY = os.environ.get('OPENROUTER_API_KEY') 
URL_API_IA = "https://openrouter.ai/api/v1/chat/completions"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secreto_iot_agronomo_master'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# --- BASE DE DATOS ---
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    col_mediciones = db['mediciones_iot']
    col_ia = db['historial_ia']
    print("✅ MongoDB Conectado")
except Exception as e:
    print(f"❌ Error Mongo: {e}")

# --- CEREBRO IA: DEEPSEEK CONTEXTUAL ---
def consultar_deepseek(t, h, l, pregunta_usuario=None):
    """
    Consulta a la IA. Si hay 'pregunta_usuario', responde eso usando los datos como contexto.
    Si no, da un reporte general.
    """
    if not API_KEY:
        return "⚠️ Error: Falta configurar OPENROUTER_API_KEY en Linux."

    prompt_system = "Eres un ingeniero agrónomo experto en invernaderos automatizados y IoT."
    
    # Construcción inteligente del Prompt
    if pregunta_usuario and pregunta_usuario.strip() != "":
        # MODO CHATBOT: Responde la duda específica del usuario
        prompt_user = f"""
        DATOS EN TIEMPO REAL:
        - Temperatura: {t}°C
        - Humedad: {h}%
        - Luz: {l} Lux
        
        USUARIO PREGUNTA: "{pregunta_usuario}"
        
        INSTRUCCIONES: Responde a la pregunta del usuario. Usa los datos del sensor como contexto para justificar tu respuesta. Sé breve y técnico.
        """
    else:
        # MODO REPORTE: Diagnóstico automático
        prompt_user = f"""
        Analiza estos datos actuales: T:{t}°C, H:{h}%, L:{l} Lux.
        Dame un diagnóstico breve del estado del cultivo y una acción recomendada.
        """

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek/deepseek-chat", # Modelo económico y potente
        "messages": [
            {"role": "system", "content": prompt_system},
            {"role": "user", "content": prompt_user}
        ],
        "temperature": 0.7,
        "max_tokens": 200
    }

    try:
        print(f"🤖 Consultando IA (Modo: {'Chat' if pregunta_usuario else 'Reporte'})...")
        response = requests.post(URL_API_IA, headers=headers, json=payload, timeout=15)
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"Error OpenRouter: {response.text}"
    except Exception as e:
        return f"Error de conexión IA: {e}"

# --- RUTAS ---

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
    """
    Recibe la petición del botón web/app.
    Puede incluir JSON: {"pregunta": "¿Debo regar?"}
    """
    try:
        # 1. Obtener pregunta (si existe)
        cuerpo = request.json or {}
        pregunta = cuerpo.get('pregunta', "")

        # 2. Obtener datos reales
        ultimo = col_mediciones.find_one(sort=[('_id', -1)])
        if not ultimo:
            return jsonify({"consejo": "No hay datos de sensores para analizar."})
            
        t = ultimo.get('t', 0)
        h = ultimo.get('h', 0)
        l = ultimo.get('l', 0)

        # 3. Consultar IA
        consejo = consultar_deepseek(t, h, l, pregunta)
        
        # 4. Auditoría
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
        socketio.emit('nuevo_dato_sensor', data)
        return jsonify({"status": "ok"})
    except: return jsonify({"status": "error"}), 500

# --- SERVIDOR UDP ---
def escuchar_sensores_udp():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((UDP_IP, UDP_PORT))
        print(f"📡 UDP Escuchando en puerto {UDP_PORT}")
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
            # CORRECCIÓN CRÍTICA OBJECTID
            d_json['_id'] = str(d_json['_id'])
            
            socketio.emit('nuevo_dato_sensor', d_json)
            socketio.sleep(0.01)
        except: socketio.sleep(1)

if __name__ == '__main__':
    socketio.start_background_task(target=escuchar_sensores_udp)
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
