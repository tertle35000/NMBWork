# master_mst
This is MMS project for Master code for RS232(Master).

## Getting started

- v.1.0.0 The default code version.
- v.2.0.0 Revise software to can run auto following Microcontroller chip between the ESP32S2 and ESP32S3.
- v.2.0.1  Add hard reset WiFi in setupWiFi() because the WiFi driver is hold down so impact on SMM-001 can't reconnect WiFi.
- V.2.0.2  Add WiFi.reconnect() for the wireless network bug.
- V.2.0.3  Add mqttClient Setting the KeepAlive and setSocketTimeout for pingreq to related the Mqtt server.
- V.2.0.3  Add setBufferSize set the MQTT_MAX_MESSAGE_SIZE, mqttClient Setting the KeepAlive and setSocketTimeout for pingreq to related the Mqtt server.

## Target board

- MIC-Smart (SMM-001,SMM-002(ESP32S2),SMM-002A(ESP32S3))

## Read serial

- RS232

## Data config .ino

MicMMS aaa("WiFi_name", "Password", "BSSID", "Mqtt_server", Mqtt_port,"/Department/Process/","Machine_number", 1, Serial1,"IP_Address","Gate_way","Subnet_mask","Version_coding");

## config.h

/_----- SMM-001 ----_/

- Pinled1 41 // LED for Detected the Publish data
- Pinled2 42 // LED for Connection Interne

/_----- SMM-002(ESP32S2) and SMM-002A(EPS32S3) ----_/

- Pinled1 1 // LED for Detected the Publish data
- Pinled2 2 // LED for Connection Internet

/_----- Pin Tx and Rx ----_/
- rsRx 18                  // Pin for Serial RS232/RS485 UART Rx 18
- rsTx 17                  // Pin for Serial RS232/RS485 UART Tx 17

/_--------- Topics to Publish MQTT Broker ---------_

- Example: data/mic/test/a001, alarm/mic/test/a001
- char\* topic_pub_1 = "data";
- char\* topic_pub_2 = "status";
- char\* topic_pub_3 = "alarm";
- char\* topic_esp_health = "esp_health";
- char\* topic_broke_modbus = "mqtt";

## Config PubSubClient in MMS . cpp lib
-   mqttClient.setBufferSize(1024);   // Config the size, in bytes, of the internal send/receive buffer
-   mqttClient.setKeepAlive(30);      // Config Keep-alive 30s
-   mqttClient.setSocketTimeout(10);  // Config Socket timeout 10s

## function

- init (Setup System)
- start (Main Operating System)
- run (read mudbus)

## Usage

```c
#include "MicMMS.h"

/*-------------------  Fill data at file .ino (Data config) -------------------*/
// MicMMS aaa("WiFi_name", "Password", "Mqtt_server", Mqtt_port,"/Department/Process/","Machine_number", 1, Serial1,"IP_Address","Gate_way","Subnet_mask", "Version_coding");
/*----------------------------------------------------------------------------*/
MicMMS aaa("MIC_Iot", "Micdev@2024", "192.168.0.201", 1883, "/mic/test/", "a001", 1, Serial1, "192.168.0.100", "192.168.0.1", "255.255.255.0", "2.0.3"); //MIC are test

void setup() {
  aaa.init();
  aaa.start();
}

void loop() {
  aaa.run();
}
```

## The WiFi connection cannot be checked.

As follows

- WiFi_Name
- Password_WiFi
- IP Address IIoT Box, Gateway, Subnet mask, It should be in the correct LAN band of the system.
- RSSI WiFi signal quality is required!! Not lower than -85 dBm

## The MQTT Broker server cannot be connected.

"Data cannot be sent to the MQTT Server" should be validated. As follows

- IP Address Mqtt_server
- Mqtt_port Must be: 1883
- IP Address IIoT Box is required!! Unique If you have more than 1 IIoT Box
- WiFi signal quality issues

## The Modbus connection cannot be checked.
As follows

- Pins for RS232/RS485 UART Tx, RX series correctly defined at the IIoT Box
- Set "Slave ID" to GOT and IoT Gateway the wrong match!!
- Wire RS232 mistask!!
