#include "MicMMS.h"
/*------------------- Information Program -------------------*/
//  MicMMS version 2.0.3  (Version code)
/*----------------------------------------------------------*/

/*------------------- Data list -------------------*/
// MicMMS aaa("WiFi_name", "Password", "Mqtt_server", Mqtt_port,"/Department/Process/","Machine_number", 1, Serial1,"IP_Address","Gate_way","Subnet_mask","Version_coding");
/*-------------------------------------------------*/

// MicMMS aaa("NHT-IIoT-GD-2", "natmms22", "10.128.16.200", 1883,"/nht/gd/","ic05r", 1, Serial1,"10.128.56.14","10.128.56.1","255.255.254.0","2.0.3");
MicMMS aaa("MIC_Iot", "Micdev@2024", "broker.hivemq.com", 1883,"/mic/demo1/","no_21", 1, Serial1,"192.168.0.100","192.168.0.1","255.255.255.0","2.0.3"); //MIC are test

void setup() {
  aaa.init();
  aaa.callAPI();
  aaa.start();
}

void loop() {
  aaa.run();
}


