package com.daniel.invernadero

import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout
import com.google.android.material.textfield.TextInputEditText
import com.google.gson.JsonObject
import kotlinx.coroutines.*
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

// --- INTERFAZ DE CONEXIÓN CON EL SERVIDOR ---
interface ApiService {
    // 1. Obtener datos de sensores (con truco anti-caché)
    @GET("/api/historial")
    suspend fun obtenerHistorial(@Query("z") aleatorio: Long): List<JsonObject>

    // 2. Enviar reporte manual (Bitácora)
    @POST("/api/movil/data")
    suspend fun enviarReporte(@Body datos: JsonObject): JsonObject

    // 3. Consultar al Cerebro IA
    @POST("/api/ia/consultar")
    suspend fun consultarIA(@Body datos: JsonObject): JsonObject
}

class MainActivity : AppCompatActivity() {

    private val BASE_URL = "http://3.210.134.165:5000/" 

    private lateinit var api: ApiService
    
    // Elementos de la Pantalla
    private lateinit var swipeRefresh: SwipeRefreshLayout
    private lateinit var tvTempVal: TextView
    private lateinit var tvHumVal: TextView
    private lateinit var tvLuxVal: TextView
    
    // Sección IA (Chatbot)
    private lateinit var etPreguntaIA: TextInputEditText
    private lateinit var btnConsultarIA: Button
    private lateinit var tvRespuestaIA: TextView

    // Sección Bitácora (Reporte)
    private lateinit var etMensaje: TextInputEditText
    private lateinit var btnEnviar: Button

    // Control de actualización automática
    private var jobActualizacion: Job? = null
    private val INTERVALO_UPDATE = 5000L // 5 segundos

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // 1. Vincular variables con el diseño XML
        swipeRefresh = findViewById(R.id.swipeRefresh)
        tvTempVal = findViewById(R.id.tvTempVal)
        tvHumVal = findViewById(R.id.tvHumVal)
        tvLuxVal = findViewById(R.id.tvLuxVal)
        
        etPreguntaIA = findViewById(R.id.etPreguntaIA)
        btnConsultarIA = findViewById(R.id.btnConsultarIA)
        tvRespuestaIA = findViewById(R.id.tvRespuestaIA)
        
        etMensaje = findViewById(R.id.etMensaje)
        btnEnviar = findViewById(R.id.btnEnviar)

        // 2. Configurar conexión Retrofit
        try {
            val retrofit = Retrofit.Builder()
                .baseUrl(BASE_URL)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
            api = retrofit.create(ApiService::class.java)
        } catch (e: Exception) {
            Toast.makeText(this, "Error Configuración URL", Toast.LENGTH_LONG).show()
        }

        // 3. Configurar Botones
        swipeRefresh.setOnRefreshListener { cargarDatosUnaVez() }
        
        btnEnviar.setOnClickListener { enviarReporteManual() }
        
        btnConsultarIA.setOnClickListener { 
            val pregunta = etPreguntaIA.text.toString()
            consultarCapatazIA(pregunta) 
        }
    }

    // --- CICLO DE VIDA (Ahorro de batería) ---
    override fun onResume() {
        super.onResume()
        startAutoUpdate() // Empezar a descargar datos al abrir
    }

    override fun onPause() {
        super.onPause()
        stopAutoUpdate() // Parar descargas al salir
    }

    // --- LÓGICA 1: INTELIGENCIA ARTIFICIAL (ROL CAPATAZ) ---
    private fun consultarCapatazIA(pregunta: String) {
        // Bloquear botón para evitar doble clic
        btnConsultarIA.isEnabled = false
        btnConsultarIA.text = "CONSULTANDO..."
        tvRespuestaIA.visibility = View.GONE
        
        CoroutineScope(Dispatchers.IO).launch {
            try {
                // Preparamos el paquete para el servidor
                val json = JsonObject()
                json.addProperty("pregunta", pregunta)
                
                // 🔥 LA CLAVE: Nos identificamos como 'movil' para recibir respuestas cortas
                json.addProperty("origen", "movil") 

                val respuesta = api.consultarIA(json)
                
                withContext(Dispatchers.Main) {
                    if (respuesta.has("consejo")) {
                        tvRespuestaIA.text = "🤖 " + respuesta.get("consejo").asString
                        tvRespuestaIA.visibility = View.VISIBLE
                    } else {
                        Toast.makeText(applicationContext, "Sin respuesta", Toast.LENGTH_SHORT).show()
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(applicationContext, "Error IA: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            } finally {
                withContext(Dispatchers.Main) {
                    btnConsultarIA.isEnabled = true
                    btnConsultarIA.text = "ANALIZAR CONTEXTO"
                }
            }
        }
    }

    // --- LÓGICA 2: SENSORES EN TIEMPO REAL ---
    private fun startAutoUpdate() {
        jobActualizacion?.cancel()
        jobActualizacion = CoroutineScope(Dispatchers.IO).launch {
            while (isActive) {
                cargarDatosBackground()
                delay(INTERVALO_UPDATE)
            }
        }
    }
    
    private fun stopAutoUpdate() {
        jobActualizacion?.cancel()
    }

    private suspend fun cargarDatosBackground() {
        try {
            // Usamos System.currentTimeMillis() para romper el caché
            val historial = api.obtenerHistorial(System.currentTimeMillis())
            withContext(Dispatchers.Main) {
                if (historial.isNotEmpty()) actualizarUI(historial[0])
            }
        } catch (e: Exception) { 
            // Fallo silencioso en background
        }
    }

    private fun cargarDatosUnaVez() {
        swipeRefresh.isRefreshing = true
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val historial = api.obtenerHistorial(System.currentTimeMillis())
                withContext(Dispatchers.Main) {
                    if (historial.isNotEmpty()) actualizarUI(historial[0])
                    swipeRefresh.isRefreshing = false
                    Toast.makeText(applicationContext, "Datos actualizados", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) { 
                    swipeRefresh.isRefreshing = false 
                    Toast.makeText(applicationContext, "Error conexión", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun actualizarUI(dato: JsonObject) {
        val t = if (dato.has("t")) dato.get("t").asString else "--"
        val h = if (dato.has("h")) dato.get("h").asString else "--"
        val l = if (dato.has("l")) dato.get("l").asString else "--"

        tvTempVal.text = t
        tvHumVal.text = h
        tvLuxVal.text = "$l Lx"
    }

    // --- LÓGICA 3: BITÁCORA MANUAL ---
    private fun enviarReporteManual() {
        val mensaje = etMensaje.text.toString()
        if (mensaje.isEmpty()) {
            Toast.makeText(this, "Escribe una observación", Toast.LENGTH_SHORT).show()
            return
        }

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val json = JsonObject()
                json.addProperty("observacion", mensaje)
                json.addProperty("usuario", "Android Operario") // Identidad del reporte
                
                api.enviarReporte(json)
                
                withContext(Dispatchers.Main) {
                    Toast.makeText(applicationContext, "Bitácora guardada ✅", Toast.LENGTH_SHORT).show()
                    etMensaje.text?.clear()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(applicationContext, "Fallo envío", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }
}
