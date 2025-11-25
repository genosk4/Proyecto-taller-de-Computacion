package com.daniel.invernadero// <--- TU PAQUETE

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout
import com.google.android.material.textfield.TextInputEditText
import com.google.gson.JsonObject
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

// --- INTERFAZ API ---
interface ApiService {
    @GET("/api/historial")
    suspend fun obtenerHistorial(): List<JsonObject>

    @POST("/api/movil/data")
    suspend fun enviarReporte(@Body datos: JsonObject): JsonObject
}

class MainActivity : AppCompatActivity() {

    // ⚠️ TU IP DE AWS
    private val BASE_URL = "http://3.210.134.165:5000/"

    private lateinit var api: ApiService

    // UI Elements
    private lateinit var swipeRefresh: SwipeRefreshLayout
    private lateinit var tvTempVal: TextView
    private lateinit var tvHumVal: TextView
    private lateinit var tvLuxVal: TextView
    private lateinit var etMensaje: TextInputEditText
    private lateinit var btnEnviar: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Vincular Vistas
        swipeRefresh = findViewById(R.id.swipeRefresh)
        tvTempVal = findViewById(R.id.tvTempVal)
        tvHumVal = findViewById(R.id.tvHumVal)
        tvLuxVal = findViewById(R.id.tvLuxVal)
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
            Toast.makeText(this, "Error configuración URL", Toast.LENGTH_LONG).show()
        }

        // 1. Configurar Pull-to-Refresh
        swipeRefresh.setOnRefreshListener {
            cargarDatosServidor()
        }

        // Cargar datos al abrir
        cargarDatosServidor()

        // 2. Configurar Botón Enviar
        btnEnviar.setOnClickListener { enviarDatosServidor() }
    }

    private fun cargarDatosServidor() {
        swipeRefresh.isRefreshing = true // Mostrar spinner de carga

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val historial = api.obtenerHistorial()
                withContext(Dispatchers.Main) {
                    if (historial.isNotEmpty()) {
                        val dato = historial[0] // El más reciente

                        // Asignar valores a cada tarjeta
                        tvTempVal.text = if (dato.has("t")) dato.get("t").asString else "--"
                        tvHumVal.text = if (dato.has("h")) dato.get("h").asString else "--"
                        tvLuxVal.text = if (dato.has("l")) "${dato.get("l").asString} Lx" else "--"

                    } else {
                        Toast.makeText(applicationContext, "Sin datos recientes", Toast.LENGTH_SHORT).show()
                    }
                    swipeRefresh.isRefreshing = false // Ocultar spinner
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    swipeRefresh.isRefreshing = false
                    Toast.makeText(applicationContext, "Error de conexión", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun enviarDatosServidor() {
        val mensaje = etMensaje.text.toString()
        if (mensaje.isEmpty()) {
            Toast.makeText(this, "Escribe un reporte primero", Toast.LENGTH_SHORT).show()
            return
        }

        // Feedback visual (deshabilitar botón)
        btnEnviar.isEnabled = false
        btnEnviar.text = "ENVIANDO..."

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val json = JsonObject()
                json.addProperty("tipo", "reporte_manual")
                json.addProperty("observacion", mensaje)
                json.addProperty("usuario", "Android Operario")

                api.enviarReporte(json) // Ignoramos respuesta por simplicidad

                withContext(Dispatchers.Main) {
                    Toast.makeText(applicationContext, "Reporte Enviado", Toast.LENGTH_SHORT).show()
                    etMensaje.text?.clear()
                    btnEnviar.isEnabled = true
                    btnEnviar.text = "ENVIAR REPORTE"
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(applicationContext, "Falló el envío", Toast.LENGTH_SHORT).show()
                    btnEnviar.isEnabled = true
                    btnEnviar.text = "ENVIAR REPORTE"
                }
            }
        }
    }
}