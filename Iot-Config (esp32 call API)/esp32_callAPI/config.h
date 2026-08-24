#ifndef CONFIG_H
#define CONFIG_H
/*------------------- Information Program -------------------*/
//  MicMMS version 2.0.3  (Version code)
/*----------------------------------------------------------*/

#define Pinled1 1      // LED for Detected the Publish data
#define Pinled2 2      // LED for Connection Internet
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
char* topic_pub_1 = "data";  //data/nht/gd/ic02r
char* topic_pub_2 = "status";
char* topic_pub_3 = "alarm";
char* topic_esp_health = "esp_health";
char* topic_broke_modbus = "mqtt";

/*--------- Timer config ---------*/
const uint16_t itr_modbus = 100;  // ms   0.1s
const uint16_t itr_fnc_1 = 1000;  // ms   1s
const uint16_t itr_fnc_2 = 1000;  // ms
const uint16_t itr_fnc_3 = 1000;  // ms
const uint16_t itr_esp = 20000;   // ms    20s
const uint16_t itr_network = 5000;   // ms  5s
const uint16_t itr_bro_mod = 5000;  // ms  5s

/*--------- Variable config ---------*/
const uint8_t num_got_data = 150;
uint16_t got_data[num_got_data];
float init_heap;
uint16_t bkr_connect, modb_check;
uint16_t query_check1, query_check2;
uint16_t query_temp1, query_temp2, tigger_1 = 1;
int total_data, Add_convert = 65536;
String prv_status, status;
String prv_alarm, alarm_;
String Lot_ttl;
String Rx_datasub;
unsigned long long prv_time = 0;
unsigned long long prv_time_1 = 0;
unsigned long long prv_time_2 = 0;
uint16_t heap_cnt1, heap_cnt2, heap_cnt3;
float ct_fn1, ct_fn2, ct_fn3, ct_read;
uint16_t ct_read_cnt, ct_fn1_cnt, ct_fn2_cnt, ct_fn3_cnt;
/*--------- Number Time config CPU ---------*/
const uint16_t ct_read_ = 400;             //400 microsec
const unsigned int ct_fn1_ = 100000;      //100  ms 
const unsigned int ct_fn2_ = 100000;     //100 ms
const unsigned int ct_fn3_ = 100000;    //100 ms


/*--------- Dynamic Array Config ---------*/
#define MAX_DEF_TB_ROWS 50
int active_tb_rows = 20; // จำนวนข้อมูลเริ่มต้นจาก Default (มี 20 บรรทัด)

//////////////////////////////////// I/C M/A (BORE , RACEWAY , FINISH) ////////////////////////////////////////
String def_tb[MAX_DEF_TB_ROWS][5] = {
/*------ name||address||type||value||prv_value ------*/
/*------- type for separate detail of data -------*/
{ "RUN", "1", "1", "", "" },      //Status1
  { "STOP", "2", "1", "", "" },     //Status2
  { "ALARM", "3", "1", "", "" },    //Status3
  { "Alarm1", "11", "2", "", "" },  //Status4
  { "Alarm2", "12", "2", "", "" },  //Status5
  { "Alarm3", "13", "2", "", "" },  //Status6
  { "Alarm4", "14", "2", "", "" },  //Status7
  { "Alarm5", "15", "2", "", "" },  //Status8
  { "data1", "21", "3", "", "" },   //Data production
  { "data2", "22", "3", "", "" },
  { "data3", "23", "3", "", "" },
  { "data4", "24", "3", "", "" },
  { "data5", "25", "3", "", "" },
  { "lot", "31", "4", "", "" },
  { "lot", "32", "4", "", "" },
  { "lot", "33", "4", "", "" },
  { "lot", "34", "4", "", "" },
  { "mod", "35", "5", "", "" },
  { "mod", "36", "5", "", "" },
  { "mod", "37", "5", "", "" }
};

#endif