import utils.constant as constant
import pandas as pd
import os
from pathlib import Path
import sys
import pymssql
import json
import datetime
from influxdb import InfluxDBClient
import time
from dotenv import load_dotenv,set_key

class PREPARE:

    def __init__(self,server,database,user_login,password,table,table_columns,table_log,table_columns_log,
                 influx_server,influx_database,influx_user_login,influx_password,influx_port,influx_measurement,
                 column_names,mqtt_topic,initial_db,calculate_function,calculate_factor):
        
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
        self.influx_measurement = influx_measurement

        self.column_names = column_names
        self.mqtt_topic = mqtt_topic
        self.initial_db = initial_db
        self.calculate_function = calculate_function
        self.calculate_factor = calculate_factor

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
 
class DATA(PREPARE):
    def __init__(self,server,database,user_login,password,table,table_columns,table_log,table_columns_log,
                 influx_server,influx_database,influx_user_login,influx_password,influx_port,influx_measurement,
                 column_names,mqtt_topic,initial_db,calculate_function,calculate_factor):
        super().__init__(server,database,user_login,password,table,table_columns,table_log,table_columns_log,
                         influx_server,influx_database,influx_user_login,influx_password,influx_port,influx_measurement,
                         column_names,mqtt_topic,initial_db,calculate_function,calculate_factor)        

    def calculate1(self) :
        try:
            result_lists = []
            client = InfluxDBClient(self.influx_server, self.influx_port, self.influx_user_login,self.influx_password, self.influx_database)
            mqtt_topic_value = list(str(self.mqtt_topic).split(","))
        
            for i in range(len(mqtt_topic_value)):
                query = f"select time,topic,{self.column_names} from {self.influx_measurement} where topic = '{mqtt_topic_value[i]}' order by time desc limit 1"
                result = client.query(query)
                if list(result):
                    result = list(result)[0][0]
                    result_lists.append(result)
                    result_df = pd.DataFrame.from_dict(result_lists)
            self.df_influx = result_df

        except Exception as e:
            self.error_msg(self.calculate1.__name__,"cannot query influxdb",e)
      
    def calculate2(self) :
        try:
            client = InfluxDBClient(self.influx_server, self.influx_port, self.influx_user_login,self.influx_password, self.influx_database)
            mqtt_topic_value = list(str(self.mqtt_topic).split(","))
            now = datetime.datetime.now()
            current_time_epoch = int(time.time()) * 1000 *1000 *1000
            one_hour_ago = now - datetime.timedelta(hours=1)
            previous_time_epoch = int(one_hour_ago.timestamp()) * 1000 *1000 *1000
            print(f"prev:{previous_time_epoch}")
            print(f"current:{current_time_epoch}")
            ##############################################################################
            for i in range(len(mqtt_topic_value)):
                query = f"select time,topic,{self.column_names} from {self.influx_measurement} where topic = '{mqtt_topic_value[i]}' and time >= {previous_time_epoch} and time < {current_time_epoch} "
                result = client.query(query)
                df_result = pd.DataFrame(result.get_points())
                if not df_result.empty:
                    df_result = df_result.sort_values(by='time',ascending=False)
                    df_result = df_result.fillna(0)
                    columns = self.calculate_factor.split(',')
                    df_result['combine_1'] = df_result[columns].fillna('').astype(str).apply(''.join, axis=1)
                    df_result['group_index'] = (df_result['combine_1'] != df_result['combine_1'].shift()).cumsum()
                    df_result['combine_2'] = df_result['combine_1'].astype(str) + df_result['group_index'].astype(str)
                    df_result['rank'] = df_result.groupby('combine_2').cumcount() + 1
                    df_result = df_result[(df_result['rank'] == 2) | (df_result['rank'] == 1)].drop(columns=['rank'])
                    df_result = df_result.drop_duplicates(subset=['combine_2'],keep='last')
                    df_result = df_result.sort_values(by='time',ascending=True)

                self.df_influx = pd.concat([self.df_influx,df_result],ignore_index=True)

        except Exception as e:
            self.error_msg(self.calculate2.__name__,"cannot query influxdb",e)

    def calculate3(self) :
        try:
            result_lists = []
            client = InfluxDBClient(self.influx_server, self.influx_port, self.influx_user_login,self.influx_password, self.influx_database)
            mqtt_topic_value = list(str(self.mqtt_topic).split(","))
            for i in range(len(mqtt_topic_value)):
                query = f"select time,topic,{self.column_names} from {self.influx_measurement} where topic = '{mqtt_topic_value[i]}' order by time desc limit 100"
                result = client.query(query)
                result_df = pd.DataFrame(result.get_points())
                result_lists.append(result_df)
            query_influx = pd.concat(result_lists, ignore_index=True)   
        
            env_path = Path('utils/.env')
            load_dotenv(dotenv_path=env_path,override=True)
            last_event = str(os.environ["SIDELAP_TIME"])
 
            if not query_influx.empty :
                if last_event !='':
                    new_query_influx = query_influx[query_influx.time > last_event] #filter
                    if not new_query_influx.empty:
                        self.df_influx = new_query_influx
                        self.newest_time = self.df_influx.head(1)['time'].values[0]
                else:
                    self.df_influx = query_influx # no filter
                    self.newest_time = self.df_influx.head(1)['time'].values[0]

            else:
                self.df_influx = None
                self.info_msg(self.query_influx.__name__,"influxdb data is emply")
        
        except Exception as e:
            self.error_msg(self.calculate3.__name__,"cannot query influxdb",e)

    def calculate4(self) :
        try:
            client = InfluxDBClient(self.influx_server, self.influx_port, self.influx_user_login,self.influx_password, self.influx_database)
            mqtt_topic_value = list(str(self.mqtt_topic).split(","))
            now = datetime.datetime.now()
            current_time_epoch = int(time.time()) * 1000 *1000 *1000
            one_hour_ago = now - datetime.timedelta(hours=1)
            previous_time_epoch = int(one_hour_ago.timestamp()) * 1000 *1000 *1000
            print(f"prev:{previous_time_epoch}")
            print(f"current:{current_time_epoch}")
            ##############################################################################
            for i in range(len(mqtt_topic_value)):
                query = f"select time,topic,{self.column_names} from {self.influx_measurement} where topic = '{mqtt_topic_value[i]}' and time >= {previous_time_epoch} and time < {current_time_epoch} "
                result = client.query(query)
                df_result = pd.DataFrame(result.get_points())
                if not df_result.empty:
                    df_result = df_result.sort_values(by='time',ascending=False)
                    df_result = df_result.fillna(0)
                    columns = self.calculate_factor.split(',')
                    df_result['combine_1'] = df_result[columns].fillna('').astype(str).apply(''.join, axis=1)
                    df_result['group_index'] = (df_result['combine_1'] != df_result['combine_1'].shift()).cumsum()
                    df_result['combine_2'] = df_result['combine_1'].astype(str) + df_result['group_index'].astype(str)
                    df_result['rank'] = df_result.groupby('combine_2').cumcount() + 1
                    df_result = df_result[(df_result['rank'] == 1) | (df_result['rank'] == 1)].drop(columns=['rank'])

                    df_result = df_result.drop_duplicates(subset=['combine_2'],keep='last')
                    df_result = df_result.sort_values(by='time',ascending=True)
                    
                self.df_influx = pd.concat([self.df_influx,df_result],ignore_index=True)

        except Exception as e:
            self.error_msg(self.calculate4.__name__,"cannot query influxdb",e)

    def edit_col(self):
        try:
            df = self.df_influx.copy()
            df_split = df['topic'].str.split('/', expand=True)
            df['mc_no'] = df_split[3].values
            df['process'] = df_split[2].values
            df.drop(columns=['topic'],inplace=True)
            df.rename(columns = {'time':'occurred'}, inplace = True)
            df["occurred"] =   pd.to_datetime(df["occurred"]).dt.tz_convert(None)
            df["occurred"] = df["occurred"] + pd.DateOffset(hours=7)    
            df["occurred"] = df['occurred'].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
            df.fillna(0,inplace=True)
            self.df_insert = df
        except Exception as e:
            self.error_msg(self.edit_col.__name__,"cannot edit dataframe data",e)

    def df_to_db(self):
        init_list = ['mc_no','process']
        insert_db_value = self.column_names.split(",")
        col_list = init_list+insert_db_value

        if self.calculate_function =="3":
            col_list.append("occurred")

        cnxn,cursor = self.conn_sql()
        try:
            df = self.df_insert
            for index, row in df.iterrows():
                value = None
                for i in range(len(col_list)):
                    address = col_list[i]
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
                time.sleep(0.02)
            cursor.close()
            self.df_insert = None
            # update time
            if self.calculate_function =="3":
                env_path = Path('utils/.env')        
                load_dotenv(dotenv_path=env_path,override=True)
                set_key(env_path, "SIDELAP_TIME", str(self.newest_time))

            self.info_msg(self.df_to_db.__name__,f"insert data successfully")     
        except Exception as e:
            print('error: '+str(e))
            self.error_msg(self.df_to_db.__name__,"cannot insert df to sql",e)

    def run(self):
        self.stamp_time()
        if self.initial_db == 'True':
            if self.calculate_function == '1':
                self.calculate1()
            elif self.calculate_function == '2':
                self.calculate2()
            elif self.calculate_function == '3':
                self.calculate3()
            elif self.calculate_function == '4':
                self.calculate4()
            else :self.calculate1()

            if not self.df_influx.empty:
                self.edit_col()
                time.sleep(1)
                self.df_to_db()
                self.ok_msg(self.df_to_db.__name__)
        else:
            print("db is not initial yet")

if __name__ == "__main__":
    print("must be run with main")
