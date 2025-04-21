package com.example.collectdata

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.net.TrafficStats
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.annotation.RequiresApi
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.collectdata.ui.theme.CollectDataTheme
import kotlinx.coroutines.delay
import java.io.BufferedWriter
import java.io.File
import java.io.FileWriter
import java.io.IOException
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale
import org.eclipse.paho.client.mqttv3.MqttClient
import org.eclipse.paho.client.mqttv3.MqttConnectOptions
import org.eclipse.paho.client.mqttv3.MqttException
import org.eclipse.paho.client.mqttv3.MqttMessage
import android.net.NetworkCapabilities
import android.net.ConnectivityManager



fun isNetworkAvailable(context: Context): Boolean {
    val connectivityManager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
    val activeNetwork = connectivityManager.activeNetwork
    val capabilities = connectivityManager.getNetworkCapabilities(activeNetwork)

    return capabilities?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true ||
            capabilities?.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) == true
}



object MqttService {
    private var mqttClient: MqttClient? = null
    private val brokerUrl = "tcp://194.57.103.203:1883"
    private val topic = "vehicule"

    // Connect to the MQTT broker
    fun connect() {
        try {
            mqttClient = MqttClient(brokerUrl, MqttClient.generateClientId())
            val options = MqttConnectOptions()
            options.isCleanSession = true
            mqttClient?.connect(options)
        } catch (e: MqttException) {
            e.printStackTrace()
        }
    }

    // Publish data to MQTT
    fun publish(messageContent: String) {
        try {
            if (mqttClient != null && mqttClient!!.isConnected) {
                val message = MqttMessage(messageContent.toByteArray())
                message.qos = 1 // Quality of service level 1 (At least once delivery)
                mqttClient!!.publish(topic, message)
            }
        } catch (e: MqttException) {
            e.printStackTrace()
        }
    }

    // Disconnect from MQTT
    fun disconnect() {
        try {
            mqttClient?.let {
                if (it.isConnected) {
                    it.disconnect()
                }
            }
        } catch (e: MqttException) {
            e.printStackTrace()
        }
    }
}


class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        val context: Context = this
        MqttService.connect()
        enableEdgeToEdge()
        setContent {
            CollectDataTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
                    MeasurementScreen(
                        modifier = Modifier.padding(innerPadding),
                        sensorManager = getSystemService(SENSOR_SERVICE) as SensorManager,
                        locationManager = getSystemService(LOCATION_SERVICE) as LocationManager,
                        context = context
                    )
                }
            }
        }
    }
}


@RequiresApi(Build.VERSION_CODES.O)
fun writeDataToCsv(locationData: String, accelerometerData: String, speedData: String, context: Context ) {
    val mqttService = MqttService

    val currentDateTime = LocalDateTime.now()
    val formatter = DateTimeFormatter.ofPattern("yyyyMMdd")

    // Format the date-time
    val formattedDateTime = currentDateTime.format(formatter)

    val dir: File? = context.getExternalFilesDir(Environment.DIRECTORY_DOCUMENTS)
    val fileName = "sensor_data_$formattedDateTime.csv"
    //val path: String? = context.filesDir.absolutePath // Use the appropriate path
    val file = File(dir, fileName)

    try {
        if (!file.exists()) {
            file.createNewFile()
            // Add headers to the CSV file
            val writer = BufferedWriter(FileWriter(file))
            writer.write("Location-lat,Location-long,Speed,Accelerometer-X,Accelerometer-Y,Accelerometer-Z\n")
            writer.close()
        }

        // Append data to the CSV file
        val writer = BufferedWriter(FileWriter(file, true))
        writer.write("$locationData, $speedData, $accelerometerData\n")
        writer.close()
        if (isNetworkAvailable(context)) {
            val message = "X: Accelerometer-X, Y: Accelerometer-Y, Z: Accelerometer-Z"
            mqttService.publish(message)
        }
    } catch (e: IOException) {
        e.printStackTrace()
    }
}

@Composable
fun MeasurementScreen(modifier: Modifier = Modifier, sensorManager: SensorManager, locationManager: LocationManager, context: Context) {
    var isMeasuring by remember { mutableStateOf(false) }
    var accelerometerData by remember { mutableStateOf("0.0, 0.0, 0.0") }
    var locationData by remember { mutableStateOf("0.0, 0.0") }
    var speedData by remember { mutableStateOf("0.0") }
    var networkUsageData by remember { mutableStateOf("Download: 0 MB, Upload: 0 MB") }
    var temperatureData by remember { mutableStateOf("Temperature: N/A °C") }
    var humidityData by remember { mutableStateOf("Humidity: N/A %") }

    // Gestion de l'accéléromètre, température et humidité
    val sensorListener = remember {
        object : SensorEventListener {
            override fun onSensorChanged(event: SensorEvent?) {
                event?.let {
                    when (it.sensor.type) {
                        Sensor.TYPE_ACCELEROMETER -> {
                            accelerometerData = String.format(
                                Locale.US, "%.2f, %.2f, %.2f",
                                it.values[0], it.values[1], it.values[2]
                            )
                        }
                        Sensor.TYPE_AMBIENT_TEMPERATURE -> {
                            temperatureData = String.format(Locale.US, "Temperature: %.1f °C", it.values[0])
                        }
                        Sensor.TYPE_RELATIVE_HUMIDITY -> {
                            humidityData = String.format(Locale.US, "Humidity: %.1f %%", it.values[0])
                        }
                    }
                }
            }
            override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}
        }
    }

    // Gestion de la localisation et de la vitesse
    val locationListener = remember {
        object : LocationListener {
            override fun onLocationChanged(location: Location) {
                locationData = String.format(
                    Locale.US, "%.6f, %.6f",
                    location.latitude, location.longitude
                )
                speedData = String.format(Locale.US, "%.2f", location.speed)
            }
            override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
            override fun onProviderEnabled(provider: String) {}
            override fun onProviderDisabled(provider: String) {}
        }
    }


    // Effet lancé lorsque la mesure démarre
    LaunchedEffect(isMeasuring) {
        if (isMeasuring) {

            val accelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
            val temperatureSensor = sensorManager.getDefaultSensor(Sensor.TYPE_AMBIENT_TEMPERATURE)
            val humiditySensor = sensorManager.getDefaultSensor(Sensor.TYPE_RELATIVE_HUMIDITY)

            sensorManager.registerListener(sensorListener, accelerometer, SensorManager.SENSOR_DELAY_NORMAL)
            temperatureSensor?.let { sensorManager.registerListener(sensorListener, it, SensorManager.SENSOR_DELAY_NORMAL) }
            humiditySensor?.let { sensorManager.registerListener(sensorListener, it, SensorManager.SENSOR_DELAY_NORMAL) }

            locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 1000L, 0f, locationListener)

            val initialRx = TrafficStats.getTotalRxBytes()
            val initialTx = TrafficStats.getTotalTxBytes()

            while (isMeasuring) {
                delay(500L)

                val currentRx = TrafficStats.getTotalRxBytes()
                val currentTx = TrafficStats.getTotalTxBytes()

                val downloadedMB = (currentRx - initialRx) / (1024.0 * 1024.0)
                val uploadedMB = (currentTx - initialTx) / (1024.0 * 1024.0)

                networkUsageData = String.format(Locale.US, "Download: %.2f MB, Upload: %.2f MB", downloadedMB, uploadedMB)
                writeDataToCsv(
                    locationData,
                    accelerometerData,
                    speedData,
                    context
                )
            }
            sensorManager.unregisterListener(sensorListener)
            locationManager.removeUpdates(locationListener)

        }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(text = "Accéléromètre", style = MaterialTheme.typography.titleMedium)
        Text(text = accelerometerData, modifier = Modifier.padding(8.dp))

        Text(text = "Localisation", style = MaterialTheme.typography.titleMedium)
        Text(text = locationData, modifier = Modifier.padding(8.dp))

        Text(text = "Vitesse", style = MaterialTheme.typography.titleMedium)
        Text(text = speedData, modifier = Modifier.padding(8.dp))

        Text(text = "Température", style = MaterialTheme.typography.titleMedium)
        Text(text = temperatureData, modifier = Modifier.padding(8.dp))

        Text(text = "Humidité", style = MaterialTheme.typography.titleMedium)
        Text(text = humidityData, modifier = Modifier.padding(8.dp))

        Text(text = "Charge du Réseau", style = MaterialTheme.typography.titleMedium)
        Text(text = networkUsageData, modifier = Modifier.padding(8.dp))

        Spacer(modifier = Modifier.height(20.dp))

        if (!isMeasuring) {
            Button(
                onClick = { isMeasuring = true },
                modifier = Modifier.padding(8.dp)
            ) {
                Text("Lancer la mesure")
            }

        } else {
            Button(
                onClick = { isMeasuring = false },
                modifier = Modifier.padding(8.dp)
            ) {
                Text("Arrêter la mesure")
            }

        }
    }
}

//@Preview(showBackground = true)
//@Composable
//fun MeasurementScreenPreview() {
//    CollectDataTheme {
//        MeasurementScreen(sensorManager = null as SensorManager, locationManager = null as LocationManager, context = context)
//    }
//}

