#ifndef CONFIG_H
#define CONFIG_H
/*------------------- Information Program -------------------*/
//  MicMMS version 2.1.1   (Version code)
/*----------------------------------------------------------*/

#define Pinled1 1                // LED for Detected the Publish data
#define Pinled2 2                // LED for Connection Internet
#define rsRx 18                  // Pin for Serial RS232/RS485 UART Rx 18
#define rsTx 17                  // Pin for Serial RS232/RS485 UART Tx 17
#define SaveDisconnectTime 1000  // Time in ms for save disconnection

#if CONFIG_IDF_TARGET_ESP32
#define ESP32  1
#elif CONFIG_IDF_TARGET_ESP32S2
#define ESP32  2
#elif CONFIG_IDF_TARGET_ESP32S3
#define ESP32  3
#elif CONFIG_IDF_TARGET_ESP32C6
#define ESP32  4
#else
#define ESP32  5
#endif

/*--------- Topics to Publish MQTT Broker ---------*/
char* topic_pub_1 = "data";  //data/mic/test/a001
char* topic_pub_2 = "status";
char* topic_pub_3 = "alarm";
char* topic_esp_health = "esp_health";
char* topic_broke_modbus = "mqtt";
//  char* topic_sub_1 = "sub_1";

/*--------- Timer config ---------*/
const uint16_t itr_modbus = 100;    // ms   0.1s
const uint16_t itr_fnc_1 = 1000;    // ms   1s
const uint16_t itr_fnc_2 = 1000;    // ms
const uint16_t itr_fnc_3 = 1000;    // ms
const uint16_t itr_esp = 20000;     // ms  20s
const uint16_t itr_network = 5000;  // ms  5s
const uint16_t itr_bro_mod = 5000;  // ms

/*--------- Variable config ---------*/
const uint8_t num_got_data = 180;
uint16_t got_data[num_got_data];
int count_mb_check = 0;  // Check the receipt of data from GOT

float init_heap;
uint16_t bkr_connect, modb_check;
uint16_t tigger_1 = 1;
int total_data, Add_convert = 65536;
String prv_status, status;
String prv_alarm, alarm_;
String Lot_ttl;
String Rx_datasub;
String api_version = "1";  // Config version (separate from firmware vrs_code), persisted in LittleFS "/api_version.txt"
unsigned long long prv_time = 0;
unsigned long long prv_time_1 = 0;
unsigned long long prv_time_2 = 0;
uint16_t heap_cnt1, heap_cnt2, heap_cnt3;
float ct_fn1, ct_fn2, ct_fn3, ct_read;
uint16_t ct_read_cnt, ct_fn1_cnt, ct_fn2_cnt, ct_fn3_cnt;
/*--------- Number Time config CPU ---------*/
const uint16_t ct_read_ = 400;        //400 microsec
const unsigned int ct_fn1_ = 100000;  //100  ms
const unsigned int ct_fn2_ = 100000;  //100 ms
const unsigned int ct_fn3_ = 100000;  //100 ms

/*--------- Dynamic Array Config ---------*/
// config ทั้งหมด (def_tb) มาจาก server ผ่าน MicMMS::callAPI() เท่านั้น ไม่มี default ฝังในเฟิร์มแวร์อีกต่อไป
#define MAX_DEF_TB_ROWS 250
int active_tb_rows = 0;  // ตั้งค่าจริงใน callAPI() หลังโหลด config จาก API หรือ cache ใน LittleFS

std::vector<int> modbus_check_list;
String def_tb[MAX_DEF_TB_ROWS][5];  // name||address||type||value||prv_value

#endif