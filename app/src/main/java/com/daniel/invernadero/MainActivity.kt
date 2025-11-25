package com.daniel.invernadero // <--- NO OLVIDES TU PAQUETE

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout
import com.google.android.material.textfield.TextInputEditText
import com.google.gson.JsonObject
import kotlinx.coroutines.* // Importante para el ciclo automático
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

// --- INTERFAZ API ---
interface ApiService {
    // Agregamos @Query("z") para enviar un número basura que rompa el caché
    @GET("/api/historial")
    suspend fun obtenerHistorial(@Query("z") aleatorio: Long): List<JsonObject>

    @POST("/api/movil/data")
    suspend fun enviarReporte(@Body datos: JsonObject): JsonObject
}

class MainActivity : AppCompatActivity() {

    // ⚠️ REVISA TU IP
    private val BASE_URL = "http://3.210.134.165:5000/"

    private lateinit var api: ApiService
    private lateinit var swipeRefresh: SwipeRefreshLayout
    private lateinit var tvTempVal: TextView
    private lateinit var tvHumVal: TextView
    private lateinit var tvLuxVal: TextView
    private lateinit var etMensaje: TextInputEditText
    private lateinit var btnEnviar: Button

    // Control del Auto-Update
    private var jobActualizacion: Job? = null
    private val INTERVALO_UPDATE = 5000L // 5 segundos

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
            Toast.makeText(this, "Error URL", Toast.LENGTH_SHORT).show()
        }

        // Listener manual (por si acaso)
        swipeRefresh.setOnRefreshListener {
            cargarDatosUnaVez()
        }

        // Configurar botón enviar
        btnEnviar.setOnClickListener { enviarDatosServidor() }
    }

    // --- CICLO DE VIDA (MAGIA AUTOMÁTICA) ---

    override fun onResume() {
        super.onResume()
        startAutoUpdate() // Empezar a actualizar cuando abres la app
    }

    override fun onPause() {
        super.onPause()
        stopAutoUpdate() // Dejar de actualizar si sales (ahorra batería/datos)
    }

    private fun startAutoUpdate() {
        jobActualizacion?.cancel()

        jobActualizacion = CoroutineScope(Dispatchers.IO).launch {
            while (isActive) {
                // Log para debug (Míralo en Logcat de Android Studio)
                android.util.Log.d("EcoMind", "Pidiendo datos nuevos...")

                cargarDatosBackground()

                // Espera 3 segundos (un poco más rápido para pruebas)
                delay(3000L)
            }
        }
    }

    private fun stopAutoUpdate() {
        jobActualizacion?.cancel()
    }

    // --- FUNCIONES DE CARGA ---

    private suspend fun cargarDatosBackground() {
        try {
            val historial = api.obtenerHistorial(System.currentTimeMillis())
            withContext(Dispatchers.Main) {
                if (historial.isNotEmpty()) {
                    val dato = historial[0]
                    actualizarUI(dato)
                }
            }
        } catch (e: Exception) {
            // En modo automático fallamos en silencio para no llenar de Toasts
            e.printStackTrace()
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
                    Toast.makeText(applicationContext, "Actualizado", Toast.LENGTH_SHORT).show()
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
        // Extraer valores con seguridad
        val t = if (dato.has("t")) dato.get("t").asString else "--"
        val h = if (dato.has("h")) dato.get("h").asString else "--"
        val l = if (dato.has("l")) dato.get("l").asString else "--"

        tvTempVal.text = t
        tvHumVal.text = h
        tvLuxVal.text = "$l Lx"

        // --- AGREGAMOS FEEDBACK VISUAL ---
        // Usamos el timestamp del servidor si existe, o la hora actual del celular
        val horaServidor = if (dato.has("timestamp")) {
            // Intentamos limpiar el formato de fecha feo de Python
            dato.get("timestamp").asString.substring(11, 19) // Toma solo HH:MM:SS
        } else {
            // Hora local si no viene del server
            android.text.format.DateFormat.format("HH:mm:ss", java.util.Date())
        }

        // Un pequeño Toast (mensaje flotante) discreto para confirmar recepción
        // Opcional: Si te molesta que salga cada 5 seg, comenta esta línea
        //Toast.makeText(applicationContext, "Recibido: $horaServidor", Toast.LENGTH_SHORT).show()
    }

    // ... (Mantén tu función enviarDatosServidor igual) ...
    private fun enviarDatosServidor() {
        // ... (Tu código de enviar anterior) ...
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
                    Toast.makeText(applicationContext, "Enviado", Toast.LENGTH_SHORT).show()
                    etMensaje.text?.clear()
                }
            } catch (e: Exception) { }
        }
    }
}