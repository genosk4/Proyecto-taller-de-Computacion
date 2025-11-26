package com.daniel.invernadero // <--- ⚠️ IMPORTANTE: MANTÉN TU PAQUETE

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

// --- INTERFAZ API CON CHATBOT ---
interface ApiService {
    @GET("/api/historial")
    suspend fun obtenerHistorial(@Query("z") aleatorio: Long): List<JsonObject>

    @POST("/api/movil/data")
    suspend fun enviarReporte(@Body datos: JsonObject): JsonObject

    // Nueva ruta para la IA
    @POST("/api/ia/consultar")
    suspend fun consultarIA(@Body datos: JsonObject): JsonObject
}

class MainActivity : AppCompatActivity() {

    // ⚠️ TU IP DE AWS (Asegúrate que sea la correcta)
    private val BASE_URL = "http://52.22.205.161:5000/"

    private lateinit var api: ApiService

    // UI Elements
    private lateinit var swipeRefresh: SwipeRefreshLayout
    private lateinit var tvTempVal: TextView
    private lateinit var tvHumVal: TextView
    private lateinit var tvLuxVal: TextView

    // Sección IA
    private lateinit var etPreguntaIA: TextInputEditText
    private lateinit var btnConsultarIA: Button
    private lateinit var tvRespuestaIA: TextView

    // Sección Reporte
    private lateinit var etMensaje: TextInputEditText
    private lateinit var btnEnviar: Button

    // Auto-Update
    private var jobActualizacion: Job? = null
    private val INTERVALO_UPDATE = 5000L

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Vincular Vistas
        swipeRefresh = findViewById(R.id.swipeRefresh)
        tvTempVal = findViewById(R.id.tvTempVal)
        tvHumVal = findViewById(R.id.tvHumVal)
        tvLuxVal = findViewById(R.id.tvLuxVal)

        etPreguntaIA = findViewById(R.id.etPreguntaIA)
        btnConsultarIA = findViewById(R.id.btnConsultarIA)
        tvRespuestaIA = findViewById(R.id.tvRespuestaIA)

        etMensaje = findViewById(R.id.etMensaje)
        btnEnviar = findViewById(R.id.btnEnviar)

        // Configurar Retrofit
        try {
            val retrofit = Retrofit.Builder()
                .baseUrl(BASE_URL)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
            api = retrofit.create(ApiService::class.java)
        } catch (e: Exception) {
            Toast.makeText(this, "Error URL", Toast.LENGTH_SHORT).show()
        }

        // Listeners
        swipeRefresh.setOnRefreshListener { cargarDatosUnaVez() }
        btnEnviar.setOnClickListener { enviarReporteManual() }

        // --- NUEVO LISTENER BOTÓN IA ---
        btnConsultarIA.setOnClickListener {
            val pregunta = etPreguntaIA.text.toString()
            consultarAgronomoIA(pregunta)
        }
    }

    override fun onResume() {
        super.onResume()
        startAutoUpdate()
    }

    override fun onPause() {
        super.onPause()
        stopAutoUpdate()
    }

    // --- LÓGICA CHATBOT IA ---
    private fun consultarAgronomoIA(pregunta: String) {
        // Bloquear UI para evitar doble click
        btnConsultarIA.isEnabled = false
        btnConsultarIA.text = "ANALIZANDO..."
        tvRespuestaIA.visibility = View.GONE

        CoroutineScope(Dispatchers.IO).launch {
            try {
                // Crear JSON {"pregunta": "..."}
                val json = JsonObject()
                json.addProperty("pregunta", pregunta) // Si va vacío, el servidor dará reporte general

                val respuesta = api.consultarIA(json)

                withContext(Dispatchers.Main) {
                    if (respuesta.has("consejo")) {
                        tvRespuestaIA.text = "🤖 " + respuesta.get("consejo").asString
                        tvRespuestaIA.visibility = View.VISIBLE
                    } else {
                        Toast.makeText(applicationContext, "Sin respuesta de IA", Toast.LENGTH_SHORT).show()
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

    // --- LÓGICA DE ACTUALIZACIÓN SENSORES ---
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
            val historial = api.obtenerHistorial(System.currentTimeMillis())
            withContext(Dispatchers.Main) {
                if (historial.isNotEmpty()) actualizarUI(historial[0])
            }
        } catch (e: Exception) { }
    }

    private fun cargarDatosUnaVez() {
        swipeRefresh.isRefreshing = true
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val historial = api.obtenerHistorial(System.currentTimeMillis())
                withContext(Dispatchers.Main) {
                    if (historial.isNotEmpty()) actualizarUI(historial[0])
                    swipeRefresh.isRefreshing = false
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) { swipeRefresh.isRefreshing = false }
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

    private fun enviarReporteManual() {
        val mensaje = etMensaje.text.toString()
        if (mensaje.isEmpty()) return

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val json = JsonObject()
                json.addProperty("tipo", "reporte_manual")
                json.addProperty("observacion", mensaje)
                json.addProperty("usuario", "Android")
                api.enviarReporte(json)
                withContext(Dispatchers.Main) {
                    Toast.makeText(applicationContext, "Reporte Enviado", Toast.LENGTH_SHORT).show()
                    etMensaje.text?.clear()
                }
            } catch (e: Exception) { }
        }
    }
}