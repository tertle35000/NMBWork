#ifndef MICMMS_H
#define MICMMS_H
/*------------------- Information Program -------------------*/
//  MicMMS version 2.1.1   (Version code)
/*----------------------------------------------------------*/

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include "ModbusRtu.h"
#include <vector>
#include <ArduinoJson.h>
// ---- เพิ่มไลบรารี 2 ตัวนี้เข้ามาใหม่ ----
#include <LittleFS.h>
#include <HTTPClient.h>
// ----------------------------------

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
  PubSubClient mqttClient;

  int slaveId;
  HardwareSerial& serialPort;
  Modbus modbus;

  IPAddress ip;
  IPAddress ip_c;
  IPAddress gateway;
  IPAddress subnet;
public:
  MicMMS(const char* ssid, const char* password, const char* mqtt_server, int mqtt_port, const char* dp_name, const char* mac_no, int slaveId, HardwareSerial& serialPort, const char* ip_address, const char* gateway_address, const char* subnet_mask, const char* vrs_code);
  void setupWiFi();
  void reconnect();
  void callback(char* topic, byte* payload, unsigned int length);
  void init();
  bool publishMessage(char* topic, const char* message);
  void run();
  void start();
  void callAPI(); // ---- เพิ่มการประกาศฟังก์ชันใหม่ตรงนี้ ----
private:
  // parse JSON { "api_version": N, "data": [...] } -> def_tb/active_tb_rows, เซ็ต outApiVersion, คืน false ถ้า parse ไม่ผ่าน
  bool loadDefTbFromJson(const String& jsonPayload, long& outApiVersion);
public:
  static void modbus_Task(void* pvParam);
  static void Network_Task(void* pvParam);
  static void func1_Task(void* pvParam);
  static void func2_Task(void* pvParam);
  static void func3_Task(void* pvParam);
  static void broke_modbus_Task(void* pvParam);
  static void esp_Task(void* pvParam);
};

#endif