import os
from pathlib import Path
from dotenv import load_dotenv
from utils.data import DATA
try:
    env_path = Path('.env')
    load_dotenv(dotenv_path=env_path,override=True)
    influx_to_sqlserver = DATA(
        server=os.getenv('SERVER'),
        database=os.getenv('DATABASE'),
        user_login=os.getenv('USER_LOGIN'),
        password=os.getenv('PASSWORD'),
        table=os.getenv('TABLE_1'),
        table_columns=os.getenv('PRODUCTION_COLUMN_NAMES'),
        table_log=os.getenv('TABLE_LOG_1'),
        table_columns_log=os.getenv('TABLE_COLUMNS_LOG'),
        influx_server=os.getenv('INFLUX_SERVER'),
        influx_database=os.getenv('INFLUX_DATABASE'),
        influx_user_login=os.getenv('INFLUX_USER_LOGIN'),
        influx_password=os.getenv('INFLUX_PASSWORD'),
        influx_port=int(os.getenv('INFLUX_PORT')),
        influx_measurement=os.getenv('INFLUX_MEASUREMENT'),
        column_names=os.getenv('PRODUCTION_COLUMN_NAMES'),
        mqtt_topic=os.getenv('MQTT_TOPIC_1'),
        initial_db=os.getenv('INIT_DB'),
        calculate_function=os.getenv('CALCULATE_FUNCTION'),
        calculate_factor=os.getenv('CALCULATE_FACTOR')
    )
    influx_to_sqlserver.run()

except Exception as e:
    print(e)
    