#ifndef MICMMSETH_H
#define MICMMSETH_H

/*------------------- Information Program -------------------*/
//  MicMMS version 2.0.3
/*----------------------------------------------------------*/

#include <Arduino.h>
#include <WiFi.h>
#include <SPI.h>
#include <EthernetENC.h>
#include <ModbusEthernet.h>
#include <PubSubClient.h>
#include <vector>
#include <ArduinoJson.h>
#include <stdlib.h>

class MicMMS {
private:
  const char* ssid;
  const char* password;
  const char* mqtt_server;
  int mqtt_port;
  const char* dp_name;
  const char* mac_no;
  const char* vrs_code;

  WiFiClient wifiClient;
  ModbusEthernet modbus;
  EthernetServer server = EthernetServer(502);
  PubSubClient mqttClient;

  IPAddress ip;
  IPAddress ip1;
  IPAddress gateway;
  IPAddress subnet;
public:
  MicMMS(const char* ssid, const char* password, const char* mqtt_server, int mqtt_port, const char* dp_name, const char* mac_no, const char* ip_address, const char* gateway_address, const char* subnet_mask, const char* ip_address1, const char* vrs_code);
  void setupWiFi();
  void init();
  void reconnect();
  bool publishMessage(char* topic, const char* message);
  void callback(char* topic, byte* payload, unsigned int length);
  void run();
  void start();
  // static void modbus_Task(void* pvParam);
  static void Network_Task(void* pvParam);
  static void func1_Task(void* pvParam);
  static void func2_Task(void* pvParam);
  static void func3_Task(void* pvParam);
  static void broke_modbus_Task(void* pvParam);
  static void esp_Task(void* pvParam);
};

#endif