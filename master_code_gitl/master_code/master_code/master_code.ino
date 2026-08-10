#include "MicMMS.h"
/*------------------- Information Program -------------------*/
//  MicMMS version 2.0.3   (Version code)
/*----------------------------------------------------------*/

/*------------------- Data list -------------------*/
// MicMMS aaa("WiFi_name", "Password", "Mqtt_server", Mqtt_port,"/Department/Process/","Machine_number", 1, Serial1,"IP_Address","Gate_way","Subnet_mask","Version_coding");
/*-------------------------------------------------*/
MicMMS aaa("MIC_Iot", "Micdev@2024", "192.168.0.201", 1883,"/mst/demo/","mc01", 1, Serial1,"192.168.0.100","192.168.0.1","255.255.255.0","2.0.3");

void setup() {
  aaa.init();
  aaa.start();
}
  
void loop() {
  aaa.run();
}
