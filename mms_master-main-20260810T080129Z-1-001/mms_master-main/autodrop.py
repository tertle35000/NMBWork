from influxdb import InfluxDBClient
import dotenv
import os
import time
def drop_mqtt_consumer():
    # client = InfluxDBClient(host='192.168.0.160', port=8086, username='admin', password='admin', database='influx')
    time.sleep(120)
    client = InfluxDBClient(os.environ["INFLUX_SERVER"], os.environ["INFLUX_PORT"], os.environ["INFLUX_USER_LOGIN"], os.environ["INFLUX_PASSWORD"], os.environ["INFLUX_DATABASE"])
    client.query('DROP MEASUREMENT mqtt_consumer')
    print("Dropped measurement mqtt_consumer")
    client.close()

if __name__ == "__main__":
    dotenv_file = dotenv.find_dotenv()
    dotenv.load_dotenv(dotenv_file,override=True)
    drop_mqtt_consumer()
