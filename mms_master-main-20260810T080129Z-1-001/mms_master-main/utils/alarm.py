import utils.constant as constant
import pandas as pd
import os
from pathlib import Path
import sys
import pymssql
import datetime
from influxdb import InfluxDBClient
import datetime
import time
from dotenv import load_dotenv,set_key

class PREPARE:

    def __init__(self,server,database,user_login,password,table,table_columns,table_log,table_columns_log,
                 influx_server,influx_database,influx_user_login,influx_password,influx_port,
                 column_names,mqtt_topic,initial_db):
        
        self.server = server
        self.database = database
        self.user_login = user_login
        self.password = password
        self.table = table
        self.table_columns = table_columns
        self.table_log = table_log
        self.table_columns_log = table_columns_log

        self.influx_server = influx_server
        self.influx_database = influx_database
        self.influx_user_login = influx_user_login
        self.influx_password = influx_password
        self.influx_port = influx_port

        self.column_names = column_names
        self.mqtt_topic = mqtt_topic
        self.initial_db = initial_db

        self.df_insert = None
        self.df_influx = None
        self.df_sql = None
        self.newest_time = None

    def stamp_time(self):
        now = datetime.datetime.now()
        print("\nHi this is job run at -- %s"%(now.strftime("%Y-%m-%d %H:%M:%S")))

    def error_msg(self,process,msg,e):
        result = {"status":constant.STATUS_ERROR,"process":process,"message":msg,"error":e}

        try:
            self.log_to_db(result)
            sys.exit()
        except Exception as e:
            self.info_msg(self.error_msg.__name__,e)
            sys.exit()
            
    def info_msg(self,process,msg):
        result = {"status":constant.STATUS_INFO,"process":process,"message":msg,"error":"-"}
        print(result)

    def ok_msg(self,process):
        result = {"status":constant.STATUS_OK,"process":process,"message":"program running done","error":"-"}
        try:
            self.log_to_db(result)
            print(result)
        except Exception as e:
            self.error_msg(self.ok_msg.__name__,'cannot ok msg to log',e)
    
    def conn_sql(self):
        try:
            cnxn = pymssql.connect(self.server, self.user_login, self.password, self.database)
            cursor = cnxn.cursor()
            return cnxn,cursor
        except Exception as e:
            self.info_msg(self.conn_sql.__name__,e)
            sys.exit()

    def log_to_db(self,result):
        cnxn,cursor=self.conn_sql()
        try:
            cursor.execute(f"""
                INSERT INTO [{self.database}].[dbo].[{self.table_log}] 
                values(
                    getdate(), 
                    '{result["status"]}', 
                    '{result["process"]}', 
                    '{result["message"]}', 
                    '{str(result["error"]).replace("'",'"')}'
                    )
                    """
                )
            cnxn.commit()
            cursor.close()
        except Exception as e:
            self.info_msg(self.log_to_db.__name__,e)
            sys.exit()
 
class MC_ALARM(PREPARE):
    def __init__(self,server,database,user_login,password,table,table_columns,table_log,table_columns_log,
                 influx_server,influx_database,influx_user_login,influx_password,influx_port,
                 column_names,mqtt_topic,initial_db):
        super().__init__(server,database,user_login,password,table,table_columns,table_log,table_columns_log,
                         influx_server,influx_database,influx_user_login,influx_password,influx_port,
                         column_names,mqtt_topic,initial_db)        

    def query_influx(self) :
        try:
            result_lists = []
            client = InfluxDBClient(self.influx_server, self.influx_port, self.influx_user_login,self.influx_password, self.influx_database)
            mqtt_topic_value = list(str(self.mqtt_topic).split(","))
            for i in range(len(mqtt_topic_value)):
                query = f"select time,status,topic from mqtt_consumer where topic ='{mqtt_topic_value[i]}' order by time desc limit 20"
                result = client.query(query)
                result_df = pd.DataFrame(result.get_points())
                result_lists.append(result_df)
            query_influx = pd.concat(result_lists, ignore_index=True)

            query_influx["time"] =   pd.to_datetime(query_influx["time"]).dt.tz_convert(None)
            query_influx["time"] = query_influx["time"] + pd.DateOffset(hours=7)    
            query_influx["time"] = query_influx['time'].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S'))
            env_path = Path('utils/.env')
            load_dotenv(dotenv_path=env_path,override=True)
            last_event = str(os.environ["ALARM_TIME"])

            if not query_influx.empty :
                if last_event !='':
                    new_query_influx = query_influx[query_influx.time > last_event]
                    if not new_query_influx.empty:
                        self.df_influx = new_query_influx
                        self.newest_time = self.df_influx.head(1)['time'].values[0]
                else:
                    self.df_influx = query_influx
                    self.newest_time = self.df_influx.head(1)['time'].values[0]
            else:
                self.df_influx = None
                self.info_msg(self.query_influx.__name__,"influxdb data is emply")         

        except Exception as e:
            self.error_msg(self.query_influx.__name__,"cannot query influxdb",e)
      
    def edit_col(self):
        try:
            df = self.df_influx.copy()
            df_split = df['topic'].str.split('/', expand=True)
            df['mc_no'] = df_split[3].values
            df['process'] = df_split[2].values
            df.drop(columns=['topic'],inplace=True)
            df.rename(columns = {'time':'occurred'}, inplace = True)
            df.rename(columns={'status': 'alarm'}, inplace=True)
            self.df_insert = df
 
        except Exception as e:
            self.error_msg(self.edit_col.__name__,"cannot edit dataframe data",e)

    def df_to_db(self):
            #connect to db
            mcstatus_list = ['occurred','alarm','mc_no','process']
            cnxn,cursor = self.conn_sql()
            try:
                if not self.df_insert is None:  
                    df = self.df_insert
                    for index, row in df.iterrows():
                        value = None
                        for i in range(len(mcstatus_list)):
                            address = mcstatus_list[i]
                            if value == None:
                                value = ",'"+str(row[address])+"'"
                            else:
                                value = value+",'"+str(row[address])+"'"
                        insert_string = f"""
                        INSERT INTO [{self.database}].[dbo].[{self.table}] 
                        values(
                            getdate()
                            {value}
                            )
                            """
                        cursor.execute(insert_string)
                        cnxn.commit()
                    cursor.close()
                    self.df_insert = None
                    # update time
                    env_path = Path('utils/.env')
                    load_dotenv(dotenv_path=env_path,override=True)
                    set_key(env_path, "ALARM_TIME", str(self.newest_time))
                    
                    self.info_msg(self.df_to_db.__name__,f"insert data successfully")     
            except Exception as e:
                print('error: '+str(e))
                self.error_msg(self.df_to_db.__name__,"cannot insert df to sql",e)

    def run(self):
        self.stamp_time()
        if self.initial_db == 'True':
            self.query_influx()
            if self.df_influx is not None:
                self.edit_col()
                time.sleep(1)
                print(self.df_insert)
                self.df_to_db()
                self.ok_msg(self.df_to_db.__name__)
        else:
            print("db is not initial yet")

if __name__ == "__main__":    
    print("must be run with main")