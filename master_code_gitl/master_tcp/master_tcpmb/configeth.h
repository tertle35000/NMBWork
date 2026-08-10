#ifndef CONFIGETH_H
#define CONFIGETH_H

/*------------------- Information Program -------------------*/
//  MicMMS version 2.0.3
/*----------------------------------------------------------*/

#define Pinled1 1                // LED for Detected the Publish data
#define Pinled2 2                // LED for Connection Internet
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
char* topic_pub_1 = "data";  // data/dp_name/mac_no
char* topic_pub_2 = "status";
char* topic_pub_3 = "alarm";
char* topic_esp_health = "esp_health";
char* topic_broke_modbus = "mqtt";

/*--------- Timer config ---------*/
// const uint16_t itr_modbus = 500;  // ms   0.1s
const uint16_t itr_fnc_1 = 1000;    // ms   1s
const uint16_t itr_fnc_2 = 1000;    // ms
const uint16_t itr_fnc_3 = 1000;    // ms
const uint16_t itr_esp = 20000;     // ms    20s
const uint16_t itr_network = 5000;  // ms 5s
const uint16_t itr_bro_mod = 5000;  // ms  5s

byte mac[] = { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED };  // MAC address
/*--------- Variable config ---------*/
const uint8_t num_got_data = 180;
uint16_t got_data[num_got_data];

float init_heap;
uint16_t bkr_connect, modb_check;
uint16_t tigger_1 = 1;
int total_data, total_data1, total_data3, Add_convert = 65536;
int16_t total_data2;
String prv_status, status;
String alarm_;
String Wos_ttl;
String Rx_datasub;
unsigned long long prv_time = 0;
unsigned long long prv_time_1 = 0;
unsigned long long prv_time_2 = 0;
uint16_t heap_cnt1, heap_cnt2, heap_cnt3;
float ct_fn1, ct_fn2, ct_fn3, ct_read;
uint16_t ct_read_cnt, ct_fn1_cnt, ct_fn2_cnt, ct_fn3_cnt;

/*--------- Number Time config CPU ---------*/
const uint16_t ct_read_ = 2000;       //2000 microsec
const unsigned int ct_fn1_ = 100000;  //100  ms
const unsigned int ct_fn2_ = 100000;  //100  ms
const unsigned int ct_fn3_ = 100000;  //100  ms

String def_tb[][5] = {
  /*------ name||address||type||value||prv_value ------*/
  /*------- type for separate detail of data -------*/
  { "SET UP", "1", "1", "", "" },  //Status Data
  { "WAIT QC", "2", "1", "", "" },
  { "MACHINE MANTE", "3", "1", "", "" },
  { "PLAN STOP", "4", "1", "", "" },
  { "WAIT PART", "5", "1", "", "" },
  { "MACHINE_RUN", "6", "2", "", "" },
  { "MACHINE_Alarm", "7", "2", "", "" },
  { "NO-WORK", "21", "3", "", "" },
  { "C1-HOPPER EMPTY", "22", "3", "", "" },
  { "C2-HOPPER EMPTY", "23", "3", "", "" },
  { "C3-HOPPER EMPTY", "24", "3", "", "" },
  { "C4-HOPPER EMPTY", "25", "3", "", "" },
  { "C5-HOPPER EMPTY", "26", "3", "", "" },
  { "C1-HOPPER EMPTY(3ball)", "27", "3", "", "" },
  { "C2-HOPPER EMPTY(3ball)", "28", "3", "", "" },
  { "C3-HOPPER EMPTY(3ball)", "29", "3", "", "" },
  { "LOT QTY.COMPLETED.", "30", "3", "", "" },
  { "TRAY QTY.COMPLETED.", "31", "3", "", "" },
  { "R.P.SAMPLE QTY.COMPLETED.", "32", "3", "", "" },
  { "D1 RTNR EMPTY", "33", "3", "", "" },
  { "D2 RTNR EMPTY", "34", "3", "", "" },
  { "D1 RTNR WAIT", "35", "3", "", "" },
  { "D2 RTNR WAIT", "36", "3", "", "" },
  { "AIR LOW PRESSURE", "37", "3", "", "" },
  { "EMG.STOP", "38", "3", "", "" },
  { "STATION ERROR", "39", "3", "", "" },
  { "SERVO &INDEX ERROR", "40", "3", "", "" },
  { "CAMAERA CHECK NG", "41", "3", "", "" },
  { "BALL CHECK NG", "42", "3", "", "" },
  { "RETAINER NG", "43", "3", "", "" },
  { "REMNANTS", "44", "3", "", "" },
  { "C1-SUPPLY ERROR", "45", "3", "", "" },
  { "C2-SUPPLY ERROR", "46", "3", "", "" },
  { "C3-SUPPLY ERROR", "47", "3", "", "" },
  { "D1 SUPPLY W-CHECK ERROR", "48", "3", "", "" },
  { "D2 SUPPLY W-CHECK ERROR", "49", "3", "", "" },
  { "W.TRANSFER W-CHECK ERROR", "50", "3", "", "" },
  { "C1-EMPTY", "51", "3", "", "" },
  { "C2-EMPTY", "52", "3", "", "" },
  { "C3-EMPTY", "53", "3", "", "" },
  { "C4-EMPTY", "54", "3", "", "" },
  { "C5-EMPTY", "55", "3", "", "" },
  { "D1 NO-RETAINER", "56", "3", "", "" },
  { "D1 VACUUM MISS", "57", "3", "", "" },
  { "D2 NO-RETAINER", "58", "3", "", "" },
  { "D2 VACUUM MISS", "59", "3", "", "" },
  { "WATING FOR STATION", "60", "3", "", "" },
  { "D1 CHECK CABLE SIGNAL NG", "61", "3", "", "" },
  { "EJECT CHECK CABLE SIGNAL NG", "62", "3", "", "" },
  { "NO WORK IR , OR", "63", "3", "", "" },
  { "BRG MIX PART", "64", "3", "", "" },
  { "CABLE WORK CHUCK NG", "65", "3", "", "" },
  { "COUNTER NG YIELD OVER", "66", "3", "", "" },
  { "STATION NG YIELD OVER", "67", "3", "", "" },
  { "MAIN INDEX CYCLE OVER", "68", "3", "", "" },
  { "PRE P.WORK TAKE UP", "69", "3", "", "" },
  { "MAIN P.WORK TAKE UP", "70", "3", "", "" },
  { "C1-EMPTY(3ball)", "71", "3", "", "" },
  { "C2-EMPTY(3ball)", "72", "3", "", "" },
  { "C3-EMPTY(3ball)", "73", "3", "", "" },
  { "WORK SUPP. CYCLE OVER", "74", "3", "", "" },
  { "C1/C2(C1) B.SUPP CYCLE OVER", "75", "3", "", "" },
  { "C3(C2) B.SUPP CYCLE OVER", "76", "3", "", "" },
  { "C4/C5(C3) B.SUPP CYCLE OVER", "77", "3", "", "" },
  { "O/R HOLD CYCLE OVER", "78", "3", "", "" },
  { "PRE B.SEPA CYCLE OVER", "79", "3", "", "" },
  { "B.SEPA CYCLE OVER", "80", "3", "", "" },
  { "CAMERA CHECK CYCLE OVER", "81", "3", "", "" },
  { "SEPA CHECK CYCLE OVER", "82", "3", "", "" },
  { "SD1/D2 SUPP CYCLE OVER", "83", "3", "", "" },
  { "W.TRNSFER CYCLE OVER", "84", "3", "", "" },
  { "PRE PRESS CYCLE OVER", "85", "3", "", "" },
  { "MAIN PRESS CYCLE OVER", "86", "3", "", "" },
  { "EJECT CYCLE OVER", "87", "3", "", "" },
  { "REM.CHECK CYCLE OVER", "88", "3", "", "" },
  { "UNIT CAM,RTN,CYCLE OVER", "89", "3", "", "" },
  { "CAM,RTN,NO JUDGE", "90", "3", "", "" },
  { "CAM,RTN,ERROR", "91", "3", "", "" },
  { "CAM,RTN,NO TRIGER", "92", "3", "", "" },
  { "W.TRNS SIGNAL GAUGE TROUBLE", "93", "3", "", "" },
  { "EJECT SIGNAL GAUGE TROUBLE", "94", "3", "", "" },
  { "W.TRNS D1 CONT NG", "95", "3", "", "" },
  { "PRE P.RTNR CONT NG", "96", "3", "", "" },
  { "MAIN P.RTNR CONT NG", "97", "3", "", "" },
  { "EJECT CALK CONT NG", "98", "3", "", "" },
  { "PRE PRESS CLEARANCE CONT.NG", "99", "3", "", "" },
  { "MAIN PRESS CLEARANCE CONT.NG", "100", "3", "", "" },
  { "PRE PRESS SENSOR ERROR", "101", "3", "", "" },
  { "B.SEPA MTR ERROR", "102", "3", "", "" },
  { "LIFTER SERVO ERROR", "103", "3", "", "" },
  { "PRE P.SERVO ERROR", "104", "3", "", "" },
  { "MAIN P.SERVO ERROR", "105", "3", "", "" },
  { "OK FULL PART TRAY", "106", "3", "", "" },
  { "MAIN PRESS SENSOR ERROR", "107", "3", "", "" },
  { "D1/D2 RTNR WAIT", "108", "3", "", "" },
  { "LOT OVER", "109", "3", "", "" },
  { "BALL CHECK1 NG", "110", "3", "", "" },
  { "BALL CHECK2 NG", "111", "3", "", "" },
  { "NO-RETAINER", "112", "3", "", "" },
  { "WATING FOR SENSOR", "113", "3", "", "" },
  { "CABLE SIGNAL NG", "114", "3", "", "" },
  { "RETAINER DOUBLE", "115", "3", "", "" },
  { "RETAINER D1 EMPTY", "116", "3", "", "" },
  { "RETAINER D2 EMPTY", "117", "3", "", "" },
  { "RETAINER EMPTY", "118", "3", "", "" },
  { "ball_c1_ok", "133", "4", "", "" },
  { "ball_c2_ok", "134", "4", "", "" },
  { "ball_c3_ok", "135", "4", "", "" },
  { "ball_c4_ok", "136", "4", "", "" },
  { "ball_c5_ok", "137", "4", "", "" },
  { "ball_c1_ng", "138", "4", "", "" },
  { "ball_c2_ng", "139", "4", "", "" },
  { "ball_c3_ng", "140", "4", "", "" },
  { "ball_c4_ng", "141", "4", "", "" },
  { "ball_c5_ng", "142", "4", "", "" },
  { "ball_c1_remain", "143", "5", "", "" },
  { "ball_c1_remain1", "144", "5", "", "" },
  { "ball_c2_remain", "145", "5", "", "" },
  { "ball_c2_remain1", "146", "5", "", "" },
  { "ball_c3_remain", "147", "5", "", "" },
  { "ball_c3_remain1", "148", "5", "", "" },
  { "ball_c4_remain", "149", "5", "", "" },
  { "ball_c4_remain1", "150", "5", "", "" },
  { "ball_c5_remain", "151", "5", "", "" },
  { "ball_c5_remain1", "152", "5", "", "" },
  { "ball_gauge_c1", "153", "6", "", "" },
  { "ball_gauge_c2", "154", "6", "", "" },
  { "ball_gauge_c3", "155", "6", "", "" },
  { "ball_gauge_c4", "156", "6", "", "" },
  { "ball_gauge_c5", "157", "6", "", "" },
  { "rtnr_ok", "158", "4", "", "" },
  { "rtnr_ng", "159", "4", "", "" },
  { "ball_sepa_ng", "160", "4", "", "" },
  { "ball_shot_ng", "161", "4", "", "" },
  { "production_daily_ok", "162", "4", "", "" },
  { "production_daily_ng", "163", "4", "", "" },
  { "average_cycle_time", "164", "7", "", "" },
  { "ball_use_brg", "165", "4", "", "" },
  { "wos_no", "130", "8", "", "" },  //wos Number
  { "wos_no1", "131", "8", "", "" },
  { "wos_no2", "132", "8", "", "" },

};

#endif