/*------------------- Information Program -------------------*/
//  MicMMS version 2.0.3   (Version code)
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
    // WiFi.config(ip, gateway, subnet);
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
  //std::vector<std::vector<String>> def_tb;
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
    instance->printHeap();
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
    json_4["mac_id"] = WiFi.macAddress();
    json_4["broker"] = bkr_connect;

    query_check1 = instance->modbus.getInCnt();   //Get input messages counter value and return input messages counter
    query_check2 = instance->modbus.getOutCnt();  //Get transmitted messages counter value and return transmitted messages counter
    // printf("query_check1 : %d,query_temp1 : %d,query_check2 : %d,query_temp2 : %d\n", query_check1, query_temp1, query_check2, query_temp2);

    if ((start - prv_time_2) >= 5000) {  //Check data from GOT evert 5s
      if ((query_check1 == query_temp1) && (query_check2 == query_temp2)) {
        modb_check = 0;
      } else {
        modb_check = 1;
      }
      prv_time_2 = start;
      query_temp1 = query_check1;
      query_temp2 = query_check2;
    }
    json_4["modbus"] = modb_check;
    json_4["version"] = vrs_Code->vrs_code;  // code version

    if (((bkr_connect == 1) && (tigger_1 == 1)) || ((start - prv_time_1) >= (5 * (60 * 1000)))) {  // Use tigger = 1 for Publish first time And Publish data every 5 mins.
      serializeJson(json_4, json_topic4);
      instance->publishMessage(topic_pub, json_topic4.c_str());
      Serial.println(json_topic4);
      prv_time_1 = start;
      tigger_1 = 0;  // End use tigger forever until Start program again.
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

void MicMMS::printHeap() {
    Serial.printf("Free Heap      : %u bytes\n", ESP.getFreeHeap());
    Serial.printf("Min Free Heap  : %u bytes\n", ESP.getMinFreeHeap());
    Serial.printf("Heap Size      : %u bytes\n", ESP.getHeapSize());
}

//========================================================================  Dynamic Config Function   =================================================================== //

void MicMMS::callAPI() {
  Serial.println("--- Start Dynamic Config Flow ---");
  
  if (!LittleFS.begin(true)) {
    Serial.println("Error: LittleFS Mount Failed");
    return;
  }

  bool isVersionMatch = false;
  String currentVersion = String(vrs_code);
  
  // 1. ตรวจสอบเวอร์ชันใน LittleFS
  if (LittleFS.exists("/version.txt")) {
    File vFile = LittleFS.open("/version.txt", "r");
    if (vFile) {
      String fsVersion = vFile.readString();
      fsVersion.trim(); // ตัดเว้นวรรคส่วนเกิน
      vFile.close();
      
      if (fsVersion == currentVersion) {
        isVersionMatch = true;
      }
    }
  }

  // 2. เงื่อนไขตัดสินใจตาม Flowchart
  if (isVersionMatch) {
    Serial.println("Version matched! Calling API...");
    
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      
      // *** ใส่ URL ของ FastAPI ตรงนี้ครับ ***
      String apiUrl = "http://192.168.0.168:8000/api/config?mac=" + WiFi.macAddress(); 
      http.begin(apiUrl);
      
      int httpCode = http.GET();
      Serial.printf("API URL: %s\n", apiUrl.c_str());
      Serial.printf("API HTTP code: %d (%s)\n", httpCode, http.errorToString(httpCode).c_str());
      if (httpCode == HTTP_CODE_OK) {
        String payload = http.getString();
        Serial.println("API Success, Saving to LittleFS...");
        
        // บันทึก JSON ลง LittleFS
        File f = LittleFS.open("/config.json", "w");
        if (f) {
          f.print(payload);
          f.close();
        }
        
        // โหลด JSON เข้าสู่ตัวแปร RAM (def_tb)
        StaticJsonDocument<2048> doc;
        DeserializationError error = deserializeJson(doc, payload);
        
        if (!error && doc.is<JsonArray>()) {
          JsonArray array = doc.as<JsonArray>();
          int row = 0;
          for (JsonObject item : array) {
            if (row >= MAX_DEF_TB_ROWS) break; // ป้องกันการล้น Array
            def_tb[row][0] = item["Name"].as<String>();
            def_tb[row][1] = item["Address"].as<String>();
            def_tb[row][2] = item["Type"].as<String>();
            def_tb[row][3] = "";
            def_tb[row][4] = "";
            row++;
          }
          active_tb_rows = row; // อัปเดตจำนวนแถวปัจจุบัน
          Serial.printf("Load to RAM Success. Active rows: %d\n", active_tb_rows);
        }
      } else {
        Serial.println("API Call Failed! Loading fallback from LittleFS...");
        
        // Fallback: ดึงข้อมูลเก่าที่เคยบันทึกไว้ใน LittleFS ขึ้นมาใช้แทน
        if (LittleFS.exists("/config.json")) {
          File f = LittleFS.open("/config.json", "r");
          if (f) {
            StaticJsonDocument<2048> doc;
            DeserializationError error = deserializeJson(doc, f);
            if (!error && doc.is<JsonArray>()) {
              JsonArray array = doc.as<JsonArray>();
              int row = 0;
              for (JsonObject item : array) {
                if (row >= MAX_DEF_TB_ROWS) break;
                def_tb[row][0] = item["Name"].as<String>();
                def_tb[row][1] = item["Address"].as<String>();
                def_tb[row][2] = item["Type"].as<String>();
                def_tb[row][3] = "";
                def_tb[row][4] = "";
                row++;
              }
              active_tb_rows = row;
              Serial.printf("Fallback Load Success. Active rows: %d\n", active_tb_rows);
            }
            f.close();
          }
        }
      }
      http.end();
    } else {
      Serial.println("Error: WiFi not connected. Cannot call API.");
    }
  } else {
    // กรณีที่เวอร์ชันไม่ตรง (หรือแฟลชบอร์ดครั้งแรก)
    Serial.println("Version NOT matched or First boot. Using config.h (Default)");
    
    // อัปเดตไฟล์เวอร์ชันใหม่ เพื่อให้บูตครั้งหน้าเข้าไปดึง API ได้
    File vFile = LittleFS.open("/version.txt", "w");
    if (vFile) {
      vFile.print(currentVersion);
      vFile.close();
      Serial.println("Version updated in LittleFS.");
    }
    // ตัวแปร active_tb_rows และ def_tb ใน RAM จะใช้ค่า Default เดิมจากที่ตั้งไว้ใน config.h ตามปกติ
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

  Serial.println("--- End Dynamic Config Flow ---");
}