#include "MicMMSeth.h"

/*------------------- Information Program -------------------*/
//  MicMMS version 2.0.3 (Version code)
/*----------------------------------------------------------*/

/*------------------- Data list -------------------*/
// MicMMS aaa("WiFi_name", "Password", "Mqtt_server", Mqtt_port,"/Department/Process/","Machine_number","IP_Address_for Box Iot","Gate_way","Subnet_mask","IP_Address_for Rx data","Version_coding");
/*-------------------------------------------------*/
MicMMS aaa("MIC_Iot", "Micdev@2024", "192.168.0.201", 1883,"/mic/test/","mc01r","192.168.0.124","192.168.0.1","255.255.255.0","192.168.3.19","2.0.3"); //MIC are test

void setup() {
  aaa.init();
  aaa.start();
}

void loop() {
  aaa.run();
}
