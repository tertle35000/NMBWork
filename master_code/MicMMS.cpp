/*------------------- Information Program -------------------*/
//  MicMMS version 2.1.1   (Version code)
/*----------------------------------------------------------*/

#include "HardwareSerial.h"
#include "esp_system.h"
#include "MicMMS.h"
#include "config.h"

MicMMS::MicMMS(const char* ssid, const char* password, const char* mqtt_server, int mqtt_port, const char* dp_name, const char* mac_no, int slaveId, HardwareSerial& serialPort, const char* ip_address, const char* gateway_address, const char* subnet_mask, const char* vrs_code)
  : wifiClient(), mqttClient(wifiClient), ssid(ssid), password(password), mqtt_server(mqtt_server), mqtt_port(mqtt_port), dp_name(dp_name), mac_no(mac_no), slaveId(slaveId), serialPort(serialPort), modbus(slaveId, serialPort, 0), vrs_code(vrs_code) {
  ip.fromString(ip_address);
  gateway.fromString(gateway_address);
  subnet.fromString(subnet_mask);
}

void MicMMS::setupWiFi() {
  int MinRSSI = -85;
  int bestNetworkIndex = -1;
  unsigned long startAttemptTime = millis();

  WiFi.disconnect(true);  // delete old config
  WiFi.mode(WIFI_OFF);
  delay(SaveDisconnectTime);  // 1000ms seems to work in most cases, may depend on AP
  WiFi.mode(WIFI_STA);

  Serial.println("Scanning for WiFi networks...");
  int n = WiFi.scanNetworks();  // WiFi.scanNetworks will return the number of networks found
  if (n == 0) {
    Serial.println("no networks found");
    return;
  }
  // } else {
  //   Serial.printf("%d networks found:\n", n);
  //   for (int i = 0; i < n; ++i) {
  //     // Print SSID and RSSI for each network found
  //     // Serial.printf("%d: %s, Signal: %d dBm, BSSID: %s, Channel: %d\n", i + 1, WiFi.SSID(i).c_str(), WiFi.RSSI(i), WiFi.BSSIDstr(i).c_str(), WiFi.channel(i));
  //   }
  // }
  // Find the network with the best RSSI value
  for (int j = 0; j < n; ++j) {
    if (WiFi.SSID(j) == ssid) {
      int rssi = WiFi.RSSI(j);
      if (rssi > MinRSSI) {
        MinRSSI = rssi;
        bestNetworkIndex = j;
      }
    }
  }
  // Connect to the network with the best RSSI value
  if (bestNetworkIndex != -1) {
    Serial.printf("Best AP Connection:%s, Signal: %d dBm, BSSID: %s, Channel: %d\n", WiFi.SSID(bestNetworkIndex).c_str(), WiFi.RSSI(bestNetworkIndex), WiFi.BSSIDstr(bestNetworkIndex).c_str(), WiFi.channel(bestNetworkIndex));
    
    // [เพิ่ม] กำหนด DNS Server เพื่อให้บอร์ดหา IP ของ broker.hivemq.com เจอ
    IPAddress primaryDNS(8, 8, 8, 8); 
    IPAddress secondaryDNS(8, 8, 4, 4);
 
    // Connect to the selected AP
    WiFi.config(ip, gateway, subnet, primaryDNS, secondaryDNS); // [แก้ไข] แนบ DNS เข้าไปด้วย
    WiFi.begin(ssid, password, 0, WiFi.BSSID(bestNetworkIndex));

    while (WiFi.status() != WL_CONNECTED) {
      // printf("WiFi status is %d\n", WiFi.status());
      Serial.println("Connecting WiFi Fail,Restarting...");
      digitalWrite(Pinled2, HIGH);
      delay(100);
      digitalWrite(Pinled2, LOW);
      delay(1000);
      if ((millis() - startAttemptTime) >= 15000) {  // Check WiFi.status() 15s
        WiFi.reconnect();
        WiFi.begin(ssid, password, 0, WiFi.BSSID(bestNetworkIndex));
        startAttemptTime = millis();
      }
    }
    if ((WiFi.status() == WL_CONNECTED)) {
      Serial.println("Connected to WiFi Completed");
      digitalWrite(Pinled2, HIGH);
    }
  } else {
    digitalWrite(Pinled2, HIGH);
    delay(100);
    digitalWrite(Pinled2, LOW);
    delay(500);
    Serial.println("No known networks found");
  }
}

void MicMMS::reconnect() {
  char topic_sub[30];
  strcpy(topic_sub, topic_pub_1);
  strcat(topic_sub, dp_name);
  strcat(topic_sub, mac_no);

  if (!mqttClient.connected()) {
    Serial.println("Attempting MQTT connection...");
    String clientId = "ESP32Client_";
    clientId += mac_no;
    clientId += String(random(0xffff), HEX);  // ESP32Client_mc_no0xa12f the "0xa12f" is random number form "HEX"
    if (mqttClient.connect(clientId.c_str())) {
      Serial.println("Connected to MQTT Broker");
      digitalWrite(Pinled1, LOW);  // Broker connected!!
      /*----- Subscribe data return from server -----*/
      mqttClient.subscribe(topic_sub);
    } else {
      printf("Failed with state %d\n", mqttClient.state());
      if (mqttClient.state() == -2) {
        digitalWrite(Pinled1, HIGH);  // Broker don't connection
      }
      delay(1000);
    }
  }
}

// MQTT callback fuction : payload = data in Json, lehgth = length of the Json file
void MicMMS::callback(char* topic, byte* payload, unsigned int length) {
  // Convert are load String
  char message[length + 1];
  // function for copy string from source variable to insert into destination variable.
  strncpy(message, (char*)payload, length);  // Syntax char *strncpy(char *dest, const char *src, size_t n) Parameter dest, src, n —number char of src that want to Copy
  message[length] = '\0';
  // Serial.println(message);
  Rx_datasub = message;
  // Serial.println(Rx_datasub);
}

void MicMMS::init() {
  std::vector<std::vector<String>> def_tb;
  pinMode(Pinled1, OUTPUT);  //Publish
  pinMode(Pinled2, OUTPUT);  //Connect

  Serial.begin(115200);
  /*---- Pin ESP32S2 for Serial RS232 UART Rx 18, Tx 17 ----*/
  Serial1.begin(115200, SERIAL_8N1, /*rx =*/rsRx, /*tx =*/rsTx);

  setupWiFi();
  Serial.print("MAC address: ");
  Serial.println(WiFi.macAddress());
  Serial.print("IP address IoT Box: ");
  Serial.println(WiFi.localIP());
  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setBufferSize(1024);   // Config the size, in bytes, of the internal send/receive buffer
  mqttClient.setKeepAlive(30);      // Config Keep-alive 30s
  mqttClient.setSocketTimeout(10);  // Config Socket timeout 10s
  mqttClient.setCallback([this](char* topic, byte* payload, unsigned int length) {
    this->callback(topic, payload, length);
  });
  digitalWrite(Pinled2, HIGH);
  init_heap = esp_get_free_heap_size();
  modbus.start();
}

bool MicMMS::publishMessage(char* topic, const char* message) {
  if (mqttClient.publish(topic, message)) {
    digitalWrite(Pinled1, HIGH);
    delay(100);
    digitalWrite(Pinled1, LOW);
    return true;
  } else {
    return false;
  }
}

void MicMMS::run() {
  modbus.poll(got_data, num_got_data);
}

void MicMMS::start() {
  if (ESP32 == 2) {
    Serial.println("Running on ESP32-S2");
    xTaskCreatePinnedToCore(modbus_Task, "Task0", 10000, this, 7, NULL, 0);
    xTaskCreatePinnedToCore(Network_Task, "Task1", 10000, this, 6, NULL, 0);
    xTaskCreatePinnedToCore(func1_Task, "Task2", 10000, this, 5, NULL, 0);
    xTaskCreatePinnedToCore(func2_Task, "Task3", 10000, this, 4, NULL, 0);
    xTaskCreatePinnedToCore(func3_Task, "Task4", 10000, this, 3, NULL, 0);
    xTaskCreatePinnedToCore(broke_modbus_Task, "Task5", 10000, this, 2, NULL, 0);
    xTaskCreatePinnedToCore(esp_Task, "Task6", 10000, this, 1, NULL, 0);
  } else if (ESP32 == 3) {
    Serial.println("Running on ESP32-S3");
    xTaskCreatePinnedToCore(modbus_Task, "Task0", 10000, this, 7, NULL, 0);
    xTaskCreatePinnedToCore(Network_Task, "Task1", 10000, this, 6, NULL, 1);
    xTaskCreatePinnedToCore(func1_Task, "Task2", 10000, this, 5, NULL, 0);
    xTaskCreatePinnedToCore(func2_Task, "Task3", 10000, this, 4, NULL, 0);
    xTaskCreatePinnedToCore(func3_Task, "Task4", 10000, this, 3, NULL, 0);
    xTaskCreatePinnedToCore(broke_modbus_Task, "Task5", 10000, this, 2, NULL, 0);
    xTaskCreatePinnedToCore(esp_Task, "Task6", 10000, this, 1, NULL, 0);
    /*} else if (ESP32 == 4) {
    Serial.println("Running on ESP32-C6");*/
  } else {
    Serial.println("Unknown ESP32 variant");
  }
}

// Sent data from Modbus to table def_tb
void MicMMS::modbus_Task(void* pvParam) {
  while (1) {
    //record raw data to table
    unsigned long long int start = micros();
    for (int i = 0; i < active_tb_rows; i++) {
      def_tb[i][3] = got_data[(def_tb[i][1].toInt()) - 1];
    }
    // for (int i = 43; i < 55; i++) {
    //   Serial.print(got_data[i]);
    //   Serial.print(":");
    // }
    // Serial.println();
    ct_read = micros() - start;
    //interval work loop 550-600 microsec
    vTaskDelay(pdMS_TO_TICKS(itr_modbus));  //loop get value every 100 sec
  }
}

void MicMMS::Network_Task(void* pvParam) {
  MicMMS* instance = (MicMMS*)pvParam;

  while (1) {
    /*-------- Check Mqtt Client alive --------*/
    instance->mqttClient.loop();
    /*-------- Check Internet & Server MQTT --------*/
    if ((WiFi.status() != WL_CONNECTED)) {
      digitalWrite(Pinled2, HIGH);
      delay(100);
      digitalWrite(Pinled2, LOW);
      instance->setupWiFi();
    }
    if (!(instance->mqttClient.connected())) {
      instance->reconnect();
    }
    vTaskDelay(pdMS_TO_TICKS(itr_network));  //loop get value every 5 sec
  }
}

// Data productions part
void MicMMS::func1_Task(void* pvParam) {
  MicMMS* instance = (MicMMS*)pvParam;
  MicMMS* dpName = (MicMMS*)(pvParam);
  MicMMS* macNo = (MicMMS*)(pvParam);
  char topic_pub[30];
  strcpy(topic_pub, topic_pub_1);
  strcat(topic_pub, dpName->dp_name);
  strcat(topic_pub, macNo->mac_no);

  while (1) {
    unsigned long long int start = micros();
    bool change_1 = false;

    StaticJsonDocument<300> json_1;  // size = 30*topic [avg]
    // check data change
    for (int i = 0; i < active_tb_rows; i++) {
      if (def_tb[i][2] == "3" || def_tb[i][2] == "4") {
        if (def_tb[i][3] != def_tb[i][4]) {
          change_1 = true;
          break;
        }
      }
    }

    if (change_1 == true) {  // data change !!!
      /*----------------- rssi value -----------------*/
      json_1["rssi"] = (float)WiFi.RSSI();

      /*----------------- Production data -----------------*/
      for (int j = 0; j < (active_tb_rows); j++) {
        /*----------- Production data type a normal -----------*/
        if (def_tb[j][2] == "3") {
          json_1[String(def_tb[j][0])] = (def_tb[j][3]).toInt();
        }
        /*----------- Production data type over value 65535 -----------*/
        if (def_tb[j][2] == "4") {
          total_data = (def_tb[j][3]).toFloat() + ((def_tb[j + 1][3]).toFloat() * Add_convert);
          json_1[String(def_tb[j][0])] = total_data;
          j++;
        }
        /*----------------- Lot Number -----------------*/
        if (def_tb[j][2] == "5") {
          if (def_tb[j][3].toInt() != 0) {
            String hex_ = String((def_tb[j][3]).toInt(), HEX);  //convert data to HEX and define -> String
            String fristPart = hex_.substring(2, 4);            // Split data
            String secondPart = hex_.substring(0, 2);
            long ascii_1 = strtol(fristPart.c_str(), NULL, 16);  //convert data HEX to DEC
            long ascii_2 = strtol(secondPart.c_str(), NULL, 16);
            //Lot_num = String(ascii_1) + String(ascii_2);
            //json_1[String(def_tb[m][0])] = Lot_num.toInt();  //Tx DEC to MQTT type json file
            String Lot_num = String(char(ascii_1)) + String(char(ascii_2));
            /*if((ascii_1 ==32) && (ascii_2 == 32)) {
              Lot_ttl = "-";
            }*/
            Lot_ttl += Lot_num;
          }
        }
      }
      json_1["lot"] = Lot_ttl;

      /*----------------- Publish data -----------------*/
      String json_topic1;
      serializeJson(json_1, json_topic1);
      // instance->publishMessage(mcNo->mc_no, json_topic1.c_str());
      instance->publishMessage(topic_pub, json_topic1.c_str());
      Serial.println(json_topic1);
      for (int k = 0; k < active_tb_rows; k++) {
        if (def_tb[k][2] == "3" || def_tb[k][2] == "4" || def_tb[k][2] == "5") {
          def_tb[k][4] = def_tb[k][3];
          if (def_tb[k][2] == "5") {
            if (def_tb[k][3].toInt() != 0) {
              Lot_ttl = '\0';
            }
          }
        }
      }
      ct_fn1 = micros() - start;
    }
    //interval work loop 120-150 ms
    vTaskDelay(pdMS_TO_TICKS(itr_fnc_1));  //check every 1 sec
  }
}

// Status part
void MicMMS::func2_Task(void* pvParam) {
  MicMMS* instance = (MicMMS*)pvParam;
  MicMMS* dpName = (MicMMS*)(pvParam);
  MicMMS* macNo = (MicMMS*)(pvParam);
  char topic_pub[30];
  strcpy(topic_pub, topic_pub_2);
  strcat(topic_pub, dpName->dp_name);
  strcat(topic_pub, macNo->mac_no);

  while (1) {
    unsigned long long int start = micros();
    bool data_check1 = false;
    uint8_t count_data1 = 0;
    for (int i = 0; i < active_tb_rows; i++) {
      if (def_tb[i][2] == "1") {    //type status
        if (def_tb[i][3] == "1") {  //value to register(number)
          count_data1++;            //count_data1 = 1
        }
      }
    }

    if (count_data1 == 1) {  // condition to protection from many value
      data_check1 = true;
    } else {
      data_check1 = false;
      count_data1 = 0;
    }

    StaticJsonDocument<300> json_2;
    if (data_check1 == true) {  // data change and only one!!
      for (int i = 0; i < active_tb_rows; i++) {
        if (def_tb[i][2] == "1") {
          if (def_tb[i][3] == "1") {
            status = def_tb[i][0];
            json_2["status"] = status;
          }
        }
      }
    }
    /*----------- Publish data -----------*/
    if (status != prv_status) {
      String json_topic2;
      serializeJson(json_2, json_topic2);
      instance->publishMessage(topic_pub, json_topic2.c_str());
      prv_status = status;
      ct_fn2 = micros() - start;
    }
    //interval work loop 100-120 ms
    vTaskDelay(pdMS_TO_TICKS(itr_fnc_2));
  }
}

// Alarm part
void MicMMS::func3_Task(void* pvParam) {
  MicMMS* instance = (MicMMS*)pvParam;
  MicMMS* dpName = (MicMMS*)(pvParam);
  MicMMS* macNo = (MicMMS*)(pvParam);
  char topic_pub[30];
  strcpy(topic_pub, topic_pub_3);
  strcat(topic_pub, dpName->dp_name);
  strcat(topic_pub, macNo->mac_no);

  while (1) {
    unsigned long long int start = micros();
    StaticJsonDocument<300> json_3;

    /*------- alarm list and Publish data -------*/
    for (int i = 0; i < active_tb_rows; i++) {
      if (def_tb[i][2] == "2") {
        if (def_tb[i][3] == "1" && def_tb[i][4] == "") {
          alarm_ = def_tb[i][0];
          json_3["status"] = alarm_;
          String json_topic3;
          serializeJson(json_3, json_topic3);
          instance->publishMessage(topic_pub, json_topic3.c_str());
          Serial.println(json_topic3);
          def_tb[i][4] = def_tb[i][3];
          ct_fn3 = micros() - start;
        }
        if (def_tb[i][3] == "1" && def_tb[i][4] == "0") {
          alarm_ = def_tb[i][0];
          json_3["status"] = alarm_;
          String json_topic3;
          serializeJson(json_3, json_topic3);
          instance->publishMessage(topic_pub, json_topic3.c_str());
          Serial.println(json_topic3);
          def_tb[i][4] = def_tb[i][3];
          ct_fn3 = micros() - start;
        }
        if (def_tb[i][3] == "0" && def_tb[i][4] == "1") {
          alarm_ = def_tb[i][0];
          json_3["status"] = alarm_ + "_";
          String json_topic3;
          serializeJson(json_3, json_topic3);
          instance->publishMessage(topic_pub, json_topic3.c_str());
          Serial.println(json_topic3);
          def_tb[i][4] = def_tb[i][3];
          ct_fn3 = micros() - start;
        }
      }
    }
    //interval work loop 100-150 ms
    vTaskDelay(pdMS_TO_TICKS(itr_fnc_3));
  }
}

//Check version code, modbus and Broker alive
void MicMMS::broke_modbus_Task(void* pvParam) {
  MicMMS* instance = (MicMMS*)pvParam;
  MicMMS* dpName = (MicMMS*)(pvParam);
  MicMMS* macNo = (MicMMS*)(pvParam);
  MicMMS* vrs_Code = (MicMMS*)(pvParam);

  char topic_pub[30];
  strcpy(topic_pub, topic_broke_modbus);
  strcat(topic_pub, dpName->dp_name);
  strcat(topic_pub, macNo->mac_no);

  while (1) {
    unsigned long long int start = millis();
    StaticJsonDocument<200> json_4;
    String json_topic4;
    if (instance->mqttClient.connected()) {
      bkr_connect = 1;
    } else {
      bkr_connect = 0;
    }
    modbus_check_list.push_back(def_tb[0][3].toInt());                                             // Add data modbus detected to vector for count follow cycel func
    if (((bkr_connect == 1) && (tigger_1 == 1)) || ((start - prv_time_1) >= (5 * (60 * 1000)))) {  // Use tigger = 1 for Publish first time And Publish data every 5 mins.
      int get_count_total = modbus_check_list.size();
      int count_zero = std::count(modbus_check_list.begin(), modbus_check_list.end(), 0);
      int count_one = std::count(modbus_check_list.begin(), modbus_check_list.end(), 1);
      float prc_ofzero = (float)((count_zero / get_count_total) * 100);
      float prc_ofone = (float)((count_one / get_count_total) * 100);
      if (prc_ofzero == 100.00 || prc_ofone == 100.00) {
        modb_check = 0;
        count_mb_check++;
      } else {
        modb_check = 1;
        count_mb_check = 0;
      }
      modbus_check_list.clear();
      json_4["mac_id"] = WiFi.macAddress();
      json_4["broker"] = bkr_connect;
      json_4["modbus"] = modb_check;           // Modbus Ethernet
      json_4["version"] = vrs_Code->vrs_code;  // code version
      json_4["api_version"] = api_version;     // config version (LittleFS "/api_version.txt")
      serializeJson(json_4, json_topic4);
      instance->publishMessage(topic_pub, json_topic4.c_str());
      Serial.println(json_topic4);
      prv_time_1 = start;
      tigger_1 = 0;  // End use tigger forever until Start program again.
      if (count_mb_check == 3) {
        count_mb_check = 0;
        Serial.println("Restarting in 1 seconds");
        delay(1000);
        digitalWrite(Pinled1, HIGH);
        digitalWrite(Pinled2, HIGH);
        delay(100);
        digitalWrite(Pinled1, LOW);
        digitalWrite(Pinled2, LOW);
        ESP.restart();
      }
    }
    vTaskDelay(pdMS_TO_TICKS(itr_bro_mod));
  }
}

// Detect ESP status
void MicMMS::esp_Task(void* pvParam) {
  MicMMS* instance = (MicMMS*)pvParam;
  MicMMS* dpName = (MicMMS*)(pvParam);
  MicMMS* macNo = (MicMMS*)(pvParam);

  char topic_pub[30];
  strcpy(topic_pub, topic_esp_health);
  strcat(topic_pub, dpName->dp_name);
  strcat(topic_pub, macNo->mac_no);
  //strcpy(topic_pub, mcNo->mc_no);
  //strcat(topic_pub, topic_esp_health);

  while (1) {
    unsigned long long int start = millis();
    StaticJsonDocument<200> json_5;
    String json_topic5;
    float use_heap = (1 - (esp_get_free_heap_size() / init_heap)) * 100;
    // check heap
    if (use_heap >= 20.0 && use_heap <= 40.0) {
      heap_cnt1++;
    } else if (use_heap > 40.0 && use_heap <= 60.0) {
      heap_cnt2++;
    } else if (use_heap > 60.0) {
      heap_cnt3++;
    }
    // check cpu
    float read_over = ((ct_read / ct_read_) - 1) * 100;
    if (read_over > 80) {
      ct_read_cnt++;
    }
    float fnc1_over = ((ct_fn1 / ct_fn1_) - 1) * 100;
    if (fnc1_over > 80) {
      ct_fn1_cnt++;
    }
    float fnc2_over = ((ct_fn2 / ct_fn2_) - 1) * 100;
    if (fnc2_over > 80) {
      ct_fn2_cnt++;
    }
    float fnc3_over = ((ct_fn3 / ct_fn3_) - 1) * 100;
    if (fnc3_over > 80) {
      ct_fn3_cnt++;
    }

    if (start - prv_time >= (12 * (60 * (60 * 1000)))) {  // 12hr
      json_5["mem_use"] = use_heap;
      json_5["mem_cnt1"] = heap_cnt1;
      json_5["mem_cnt2"] = heap_cnt2;
      json_5["mem_cnt3"] = heap_cnt3;
      json_5["cpu_fn0"] = ct_read_cnt;
      json_5["cpu_fn1"] = ct_fn1_cnt;
      json_5["cpu_fn2"] = ct_fn2_cnt;
      json_5["cpu_fn3"] = ct_fn3_cnt;

      serializeJson(json_5, json_topic5);
      instance->publishMessage(topic_pub, json_topic5.c_str());
      Serial.println(json_topic5);
      prv_time = start;
      heap_cnt1 = 0;
      heap_cnt2 = 0;
      heap_cnt3 = 0;
      ct_read_cnt = 0;
      ct_fn1_cnt = 0;
      ct_fn2_cnt = 0;
      ct_fn3_cnt = 0;
    }
    ct_read = 0;
    ct_fn1 = 0;
    ct_fn2 = 0;
    ct_fn3 = 0;
    vTaskDelay(pdMS_TO_TICKS(itr_esp));
  }
}

//========================================================================  Dynamic Config Function   =================================================================== //

// Parse JSON payload รูปแบบ { "api_version": N, "data": [ {Name, Address, Type}, ... ] } เข้า def_tb/active_tb_rows
// ใช้ร่วมกันทั้งตอนโหลดจาก API สด ๆ และตอน fallback จาก cache "/config.json" (โครงสร้างไฟล์เดียวกัน)
// outApiVersion จะถูกตั้งค่าเป็น api_version ที่อ่านได้ (-1 ถ้าไม่มีฟิลด์นี้), คืน false ถ้า parse ไม่ผ่าน
bool MicMMS::loadDefTbFromJson(const String& jsonPayload, long& outApiVersion) {
  // 4096 = พื้นที่ parse ผลลัพธ์ JSON หลังแตกเป็น object/array แล้ว (ไม่ใช่ขนาด jsonPayload ดิบตรง ๆ
  // เพราะ ArduinoJson เก็บ string ซ้ำ + overhead ต่อ key-value pair เพิ่มด้วย ดังนั้น jsonPayload ดิบ
  // ที่ parse ผ่านได้จริงจะเล็กกว่า 4096 byte เสมอ) — ค่านี้ผูกกับ callAPI() ที่รันบน stack ของ
  // setup()/loop() task (default ~8192 byte) เช็คระยะขอบจาก Serial log "callAPI stack remaining"
  // ด้านล่างทุกครั้งหลัง flash ใหม่ ถ้าเหลือน้อยเกินไปให้ลดตัวเลขนี้ลง
  StaticJsonDocument<4096> doc;
  DeserializationError error = deserializeJson(doc, jsonPayload);

  if (error || !doc.is<JsonObject>() || !doc["data"].is<JsonArray>()) {
    return false;
  }

  outApiVersion = doc["api_version"] | -1L;

  JsonArray array = doc["data"].as<JsonArray>();
  int row = 0;
  for (JsonObject item : array) {
    if (row >= MAX_DEF_TB_ROWS) break;  // ป้องกันการล้น Array
    def_tb[row][0] = item["Name"].as<String>();
    def_tb[row][1] = item["Address"].as<String>();
    def_tb[row][2] = item["Type"].as<String>();
    def_tb[row][3] = "";
    def_tb[row][4] = "";
    row++;
  }
  active_tb_rows = row;  // อัปเดตจำนวนแถวปัจจุบัน
  return true;
}

void MicMMS::callAPI() {
  const uint32_t freeHeapBefore = ESP.getFreeHeap();
  const uint32_t minFreeHeapBefore = ESP.getMinFreeHeap();
  const uint32_t stackWatermarkBefore = uxTaskGetStackHighWaterMark(NULL);

  Serial.println("--- Start Dynamic Config Flow ---");

  if (!LittleFS.begin(true)) {
    Serial.println("Error: LittleFS Mount Failed");
    return;
  }

  // --- Load/Init api_version (config version, separate from firmware vrs_code) ---
  if (LittleFS.exists("/api_version.txt")) {
    File apiVerFile = LittleFS.open("/api_version.txt", "r");
    if (apiVerFile) {
      api_version = apiVerFile.readString();
      api_version.trim();  // ตัดเว้นวรรคส่วนเกิน
      apiVerFile.close();
    }
  } else {
    api_version = "1";
    File apiVerFile = LittleFS.open("/api_version.txt", "w");
    if (apiVerFile) {
      apiVerFile.print(api_version);
      apiVerFile.close();
    }
  }
  Serial.printf("api_version loaded: %s\n", api_version.c_str());

  // --- Config มาจาก server ทั้งหมด ไม่มี default ฝังในเฟิร์มแวร์อีกต่อไป: เรียก API ทุกครั้งที่บูต ---
  bool loaded = false;
  long localApiVersion = api_version.toInt();

  // dp_name รูปแบบ "/Department/Process/" เช่น "/mic/demo1/" -> department="mic", process="demo1"
  String dpPath = String(dp_name);
  if (dpPath.startsWith("/")) dpPath.remove(0, 1);
  if (dpPath.endsWith("/")) dpPath.remove(dpPath.length() - 1, 1);
  int slashIdx = dpPath.indexOf('/');
  String department = (slashIdx >= 0) ? dpPath.substring(0, slashIdx) : dpPath;
  String process = (slashIdx >= 0) ? dpPath.substring(slashIdx + 1) : "";
  String currentDpKey = department + "/" + process;  // เช่น "mic/demo1"
  Serial.printf("Department: %s | Process: %s\n", department.c_str(), process.c_str());

  // --- เช็คว่า cache ที่มีอยู่ (ถ้ามี) เป็นของ department/process เดียวกับตอนนี้หรือไม่ ---
  // กันกรณีย้ายกล่องไปอีก process แล้ว cache/เลข version เก่าของ process เดิม (ที่อาจสูงกว่า) มาบัง
  // ทำให้ ESP32 เข้าใจผิดว่า "server ไม่มีอะไรใหม่" ทั้งที่จริง ๆ ต้องดึง config ของ process ใหม่มาแทนที่
  String cachedDpKey = "";
  if (LittleFS.exists("/dp_name.txt")) {
    File dpFile = LittleFS.open("/dp_name.txt", "r");
    if (dpFile) {
      cachedDpKey = dpFile.readString();
      cachedDpKey.trim();
      dpFile.close();
    }
  }
  // หมายเหตุ: ถ้ายังไม่เคยมี /dp_name.txt เลย (cachedDpKey == "") ให้ถือว่า "ไม่รู้ว่า cache เดิมเป็นของ
  // process ไหน" แล้วบังคับ dpChanged = true ไปเลย (ไม่ใช่ปล่อยผ่านว่าเหมือนเดิม) เพราะ /dp_name.txt จะถูกเขียน
  // ก็ต่อเมื่อเข้าเงื่อนไขนี้เท่านั้น -- ถ้าปล่อยผ่านจะกลายเป็นไก่กับไข่: ไม่มีไฟล์ทำให้ไม่ trigger, ไม่ trigger ทำให้ไม่มีไฟล์ตลอดไป
  bool dpChanged = (cachedDpKey != currentDpKey);
  if (dpChanged) {
    if (cachedDpKey.length() == 0) {
      Serial.println("No previous department/process record found (/dp_name.txt missing), forcing config refresh to establish baseline.");
    } else {
      Serial.printf("Department/Process changed (cached: %s -> current: %s). Forcing config refresh regardless of api_version.\n",
                    cachedDpKey.c_str(), currentDpKey.c_str());
    }
  }

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;

    // *** ใส่ URL ของ FastAPI ตรงนี้ครับ ***
    String apiUrl = "http://192.168.0.204:8000/api/config/" + department + "/" + process + "?mac=" + WiFi.macAddress();
    Serial.printf("API URL: %s\n", apiUrl.c_str());

    // เชื่อมรอบแรกไม่ติด (เน็ตสะดุด/server ช้าชั่วคราว) ให้ลองซ้ำอีก 1 ครั้งก่อนค่อยถือว่า fail จริง
    const int maxAttempts = 2;
    int httpCode = -1;
    for (int attempt = 1; attempt <= maxAttempts; attempt++) {
      http.begin(apiUrl);
      httpCode = http.GET();
      Serial.printf("API HTTP code (attempt %d/%d): %d\n", attempt, maxAttempts, httpCode);
      if (httpCode == HTTP_CODE_OK) break;
      http.end();
      if (attempt < maxAttempts) {
        Serial.println("API call failed, retrying once more...");
        delay(1000);  // เว้นจังหวะก่อน retry กันยิงรัว ๆ ตอนเน็ต/server กำลังสะดุด
      }
    }

    if (httpCode == HTTP_CODE_OK) {
      String payload = http.getString();
      http.end();  // ปิด connection ตรงนี้ (เคสอื่น ๆ ที่ล้มเหลว loop retry ข้างบนปิดให้แล้วทุกครั้ง)
      long remoteApiVersion = -1;
      if (loadDefTbFromJson(payload, remoteApiVersion)) {
        Serial.printf("API Success. Active rows: %d | Server api_version: %ld | Local api_version: %ld\n",
                      active_tb_rows, remoteApiVersion, localApiVersion);

        // เซฟลง LittleFS (cache + เลขเวอร์ชัน + dp_name) เมื่อ server มีเวอร์ชันใหม่กว่าที่มีอยู่
        // หรือย้าย department/process มา (dpChanged) ไม่ว่าเลข version จะสูงกว่าหรือไม่ก็ตาม
        // *** สำคัญ: ทุกครั้งที่แก้ data ในไฟล์ config บนเซิร์ฟเวอร์ ต้อง bump "api_version" ขึ้นด้วยเสมอ
        //     ไม่งั้น cache ใน LittleFS (ที่ใช้ fallback ตอน WiFi/API ล่ม) จะไม่ถูกอัปเดตตามของใหม่ ***
        if (dpChanged || remoteApiVersion > localApiVersion) {
          Serial.println(dpChanged ? "Department/Process changed, updating LittleFS cache..."
                                    : "New config version from server, updating LittleFS cache...");
          api_version = String(remoteApiVersion);
          File verFile = LittleFS.open("/api_version.txt", "w");
          if (verFile) {
            verFile.print(api_version);
            verFile.close();
          }
          File dpFile = LittleFS.open("/dp_name.txt", "w");
          if (dpFile) {
            dpFile.print(currentDpKey);
            dpFile.close();
          }
          File f = LittleFS.open("/config.json", "w");
          if (f) {
            f.print(payload);
            f.close();
          }
          // payload ที่เพิ่ง parse ใส่ def_tb ไปแล้วตรงกับ config.json ที่เพิ่งเซฟพอดี ใช้ต่อได้เลย
          loaded = true;
        } else {
          // Version ไม่ใหม่กว่า -> ไม่แตะ cache และ "ไม่เชื่อ" payload สดที่เพิ่ง parse ไปแล้วด้วย
          // (ต่อให้เนื้อหาจริงจะเปลี่ยนไปจากที่ควรเป็นก็ตาม) ต้องโหลด def_tb จาก config.json ที่ cache ไว้แทน
          // เพื่อให้ "version เท่าเดิม = ค่าที่ใช้งานจริงใน RAM ก็ต้องเท่าเดิม" ตาม Dynamic Config Flow ที่ออกแบบไว้
          Serial.println("Config version not newer than local; reloading def_tb from existing LittleFS cache...");
          if (LittleFS.exists("/config.json")) {
            File f = LittleFS.open("/config.json", "r");
            if (f) {
              String cached = f.readString();
              f.close();
              long cachedApiVersion = -1;
              if (loadDefTbFromJson(cached, cachedApiVersion)) {
                Serial.printf("Loaded from cache. Active rows: %d | Cached api_version: %ld\n", active_tb_rows, cachedApiVersion);
                loaded = true;
              } else {
                Serial.println("Error: Failed to parse cached config.json");
              }
            }
          }
          if (!loaded) {
            // Edge case: ยังไม่เคยมี cache มาก่อนเลย (เช่น boot แรกสุดที่ server เริ่มต้นด้วย version เท่ากับ
            // default ในเครื่อง) ไม่มีอะไรให้ fallback -> ใช้ payload สดที่เพิ่ง fetch ไปก่อน (ดีกว่าไม่มีอะไรเลย)
            // และเซฟเป็น cache ตั้งต้นไว้เลย เพื่อไม่ให้ค้างสถานะไม่มี cache ซ้ำอีกในบูตถัดไป
            Serial.println("No existing cache found; bootstrapping cache from live payload instead.");
            if (loadDefTbFromJson(payload, remoteApiVersion)) {
              api_version = String(remoteApiVersion);
              File verFile = LittleFS.open("/api_version.txt", "w");
              if (verFile) {
                verFile.print(api_version);
                verFile.close();
              }
              File dpFile = LittleFS.open("/dp_name.txt", "w");
              if (dpFile) {
                dpFile.print(currentDpKey);
                dpFile.close();
              }
              File f = LittleFS.open("/config.json", "w");
              if (f) {
                f.print(payload);
                f.close();
              }
              loaded = true;
            }
          }
        }
      } else {
        Serial.println("Error: Failed to parse API JSON payload");
      }
    } else {
      Serial.println("API Call Failed!");
    }
  } else {
    Serial.println("Error: WiFi not connected. Cannot call API.");
  }

  if (!loaded && dpChanged) {
    // Cache ที่มีอยู่เป็นของ department/process เดิม (ก่อนย้ายกล่อง) ห้ามใช้ผิด process โดยเด็ดขาด
    // ยอมไม่มี config ดีกว่าเอา address/type ของ process อื่นมาใช้งานผิด ๆ
    Serial.println("Error: Department/Process changed but no successful API fetch yet; refusing to fall back to previous process's cache.");
  } else if (!loaded) {
    Serial.println("Loading fallback config from LittleFS cache...");
    if (LittleFS.exists("/config.json")) {
      File f = LittleFS.open("/config.json", "r");
      if (f) {
        String cached = f.readString();
        f.close();
        long cachedApiVersion = -1;
        if (loadDefTbFromJson(cached, cachedApiVersion)) {
          Serial.printf("Fallback Load Success. Active rows: %d | Cached api_version: %ld\n", active_tb_rows, cachedApiVersion);
          loaded = true;
        } else {
          Serial.println("Error: Failed to parse cached config.json");
        }
      }
    } else {
      Serial.println("Error: No cached config.json available.");
    }
  }

  if (!loaded) {
    Serial.println("Error: No config loaded (API failed and no cache). active_tb_rows = 0");
  }

  // --- เพิ่มโค้ดพรินต์ตรวจสอบตรงนี้ ---
  Serial.println("--- Current def_tb in RAM ---");
  for (int i = 0; i < active_tb_rows; i++) {
    Serial.printf("Row %02d | Name: %-10s | Addr: %-4s | Type: %s\n", 
                  i + 1, 
                  def_tb[i][0].c_str(), 
                  def_tb[i][1].c_str(), 
                  def_tb[i][2].c_str());
  }
  // --------------------------------

  const uint32_t freeHeapAfter = ESP.getFreeHeap();
  const uint32_t minFreeHeapAfter = ESP.getMinFreeHeap();
  const uint32_t stackWatermarkAfter = uxTaskGetStackHighWaterMark(NULL);
  const uint32_t heapUsedAfter = freeHeapBefore > freeHeapAfter
                                   ? freeHeapBefore - freeHeapAfter
                                   : 0;
  const uint32_t peakHeapUsed = minFreeHeapBefore > minFreeHeapAfter
                                  ? minFreeHeapBefore - minFreeHeapAfter
                                  : 0;
  const uint32_t additionalStackUsed = stackWatermarkBefore > stackWatermarkAfter
                                        ? (stackWatermarkBefore - stackWatermarkAfter) * sizeof(StackType_t)
                                        : 0;

  Serial.printf("callAPI heap retained: %u bytes\n", heapUsedAfter);
  Serial.printf("callAPI peak heap use: %u bytes\n", peakHeapUsed);
  Serial.printf("callAPI additional stack use: %u bytes\n", additionalStackUsed);
  Serial.printf("callAPI free heap after: %u bytes\n", freeHeapAfter);
  Serial.printf("callAPI minimum free heap: %u bytes\n", minFreeHeapAfter);
  // ค่านี้คือระยะขอบ stack ที่เหลือ "แย่ที่สุดเท่าที่เคยเหลือ" ของ task นี้ตั้งแต่เริ่มรัน (ไม่ใช่แค่ตอน
  // callAPI() นี้อย่างเดียว) ถ้าเลขนี้ใกล้ 0 แปลว่า StaticJsonDocument<4096> ใน loadDefTbFromJson()
  // เสี่ยง stack overflow ให้ลดขนาดลง (ดูคอมเมนต์ที่ตัวแปร doc)
  Serial.printf("callAPI stack remaining (worst-case since boot): %u bytes\n", stackWatermarkAfter * sizeof(StackType_t));
  Serial.println("--- End Dynamic Config Flow ---");
}