import os
from pathlib import Path
from dotenv import load_dotenv
from utils.mc_status import MC_STATUS
try:
    env_path = Path('.env')
    load_dotenv(dotenv_path=env_path,override=True)
    mc_status_to_sqlserver = MC_STATUS(
        server=os.getenv('SERVER'),
        database=os.getenv('DATABASE'),
        user_login=os.getenv('USER_LOGIN'),
        password=os.getenv('PASSWORD'),
        table=os.getenv('TABLE_2'),
        table_columns=os.getenv('PRODUCTION_COLUMN_NAMES'),
        table_log=os.getenv('TABLE_LOG_2'),
        table_columns_log=os.getenv('TABLE_COLUMNS_LOG'),
        influx_server=os.getenv('INFLUX_SERVER'),
        influx_database=os.getenv('INFLUX_DATABASE'),
        influx_user_login=os.getenv('INFLUX_USER_LOGIN'),
        influx_password=os.getenv('INFLUX_PASSWORD'),
        influx_port=int(os.getenv('INFLUX_PORT')),
        column_names=os.getenv('MCSTATUS_TABLE_COLUMNS'),
        mqtt_topic=os.getenv('MQTT_TOPIC_2'),
        initial_db=os.getenv('INIT_DB'))
    mc_status_to_sqlserver.run()

except Exception as e:
    print(e)
    