package com.daniel.invernadero

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
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

    // ⚠️ REEMPLAZAR CON TU IP ELÁSTICA DE AWS
    private val BASE_URL = "http://54.XX.XX.XX:5000/"

    private lateinit var api: ApiService
    private lateinit var tvTemp: TextView
    private lateinit var etMensaje: TextInputEditText

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Vincular Vistas
        tvTemp = findViewById(R.id.tvTemp)
        etMensaje = findViewById(R.id.etMensaje)
        val btnActualizar = findViewById<Button>(R.id.btnActualizar)
        val btnEnviar = findViewById<Button>(R.id.btnEnviar)

        // Configurar Retrofit
        try {
            val retrofit = Retrofit.Builder()
                .baseUrl(BASE_URL)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
            api = retrofit.create(ApiService::class.java)
        } catch (e: Exception) {
            Toast.makeText(this, "Error config URL", Toast.LENGTH_LONG).show()
        }

        // Listeners
        btnActualizar.setOnClickListener { cargarDatosServidor() }
        btnEnviar.setOnClickListener { enviarDatosServidor() }
    }

    private fun cargarDatosServidor() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val historial = api.obtenerHistorial()
                withContext(Dispatchers.Main) {
                    if (historial.isNotEmpty()) {
                        val dato = historial[0] // El más reciente

                        // Parseo seguro
                        val t = if (dato.has("t")) dato.get("t").asString else "--"
                        val h = if (dato.has("h")) dato.get("h").asString else "--"
                        val l = if (dato.has("l")) dato.get("l").asString else "--"

                        tvTemp.text = "Temp: $t °C\nHumedad: $h %\nLuz: $l Lux"
                        Toast.makeText(applicationContext, "Datos recibidos ✅", Toast.LENGTH_SHORT).show()
                    } else {
                        tvTemp.text = "No hay datos en el servidor"
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    tvTemp.text = "Error de conexión"
                    Toast.makeText(applicationContext, "Fallo: ${e.message}", Toast.LENGTH_LONG).show()
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

        CoroutineScope(Dispatchers.IO).launch {
            try {
                // Crear JSON Manual
                val json = JsonObject()
                json.addProperty("tipo", "reporte_manual")
                json.addProperty("observacion", mensaje)
                json.addProperty("usuario", "Operario Android")

                val respuesta = api.enviarReporte(json)

                withContext(Dispatchers.Main) {
                    Toast.makeText(applicationContext, "Reporte Enviado 📤", Toast.LENGTH_SHORT).show()
                    etMensaje.text?.clear()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(applicationContext, "Error envío: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }
}