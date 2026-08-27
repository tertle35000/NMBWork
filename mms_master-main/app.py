import streamlit as st
import os
import time
import pymssql
import json
import pandas as pd
from influxdb import InfluxDBClient
import dotenv
import subprocess

telegraf_path = "/app/telegraf.conf"
ofelia_path = "/app/config.ini"
# path for test streamlit run app.py

# ofelia_path = "./config.ini"
# telegraf_path = "./telegraf.conf"

def update_config_file1(file_path, str_fields):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    with open(file_path, 'w') as file:
        for line in lines:
            if 'json_string_fields' in line:
                new_line = f'  json_string_fields = [{str_fields}]'
                file.write(new_line)
            else:
                file.write(line) 

def update_config_file2(file_path,mqtt_server):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    with open(file_path, 'w') as file:

        for line in lines:
            if 'servers' in line:
                new_line_2 = f'  servers = ["{mqtt_server}:1883"]\n'
                file.write(new_line_2)
            else:
                file.write(line)

def update_config_file3(file_path, str_fields):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    with open(file_path, 'w') as file:
        for line in lines:
            if 'topics' in line:
                new_line = f'  topics = [{str_fields}]\n'
                file.write(new_line)
            else:
                file.write(line) 

def log_sqlserver(st,server,user_login,password,database,table):
        #connect to db
        cnxn = pymssql.connect(server,user_login,password,database)
        cursor = cnxn.cursor(as_dict=True)
        try:
            cursor.execute(f'''SELECT TOP(20) * FROM {table} order by registered desc''')
            data=cursor.fetchall()
            cursor.close()
            if len(data) != 0:
                df=pd.DataFrame(data)
                st.dataframe(df,width=2000)
            else:
                st.error('Error: SQL SERVER NO DATA', icon="❌")
        except Exception as e:
            st.error('Error'+str(e), icon="❌")

def preview_production_sqlserver(server,user_login,password,database,table,mc_no,process):
        #connect to db
        cnxn = pymssql.connect(server,user_login,password,database)
        cursor = cnxn.cursor(as_dict=True)
        # create table
        try:
            a=f'''SELECT TOP(5) * FROM {table} where mc_no = '{mc_no}' and process = '{process}' order by registered desc'''
            cursor.execute(f'''SELECT TOP(5) * FROM {table} where mc_no = '{mc_no}' and process = '{process}' order by registered desc''')
            data=cursor.fetchall()
            cursor.close()
            if len(data) != 0:
                df=pd.DataFrame(data)
                st.dataframe(df,width=1500)
            else:
                st.error('Error: SQL SERVER NO DATA', icon="❌")
        except Exception as e:
            st.error('Error'+str(e), icon="❌")

def preview_influx(st,influx_server,influx_port,influx_user_login,influx_password,influx_database,column_names,mqtt_topic) :
      try:
            client = InfluxDBClient(influx_server,influx_port,influx_user_login,influx_password,influx_database)
            if mqtt_topic.split('/')[0] =='data':
                query1 = f"select time,topic,{column_names} from mqtt_consumer where topic = '{mqtt_topic}' order by time desc limit 5"
                result1 = client.query(query1)
                if list(result1):
                    query_list1 = list(result1)[0]
                    df = pd.DataFrame(query_list1)
                    df.time = pd.to_datetime(df.time).dt.tz_convert('Asia/Bangkok')
                    st.dataframe(df,width=1500)
                else:
                    st.error('Error: influx no data', icon="❌")
            else:
                query2 = f"select time,topic,status from mqtt_consumer where topic = '{mqtt_topic}' order by time desc limit 5"
                result2 = client.query(query2)
                if list(result2):
                    query_list2 = list(result2)[0]
                    df = pd.DataFrame(query_list2)
                    df.time = pd.to_datetime(df.time).dt.tz_convert('Asia/Bangkok')
                    st.dataframe(df,width=1500)
                else:
                    st.error('Error: influx no data', icon="❌")       

      except Exception as e:
          st.error('Error: '+str(e), icon="❌")

def add_column():
    st.header("Add new SQL column")
    old_columns = os.environ["PRODUCTION_TABLE_COLUMNS"]
    init_project = str(os.environ["INIT_PROJECT"])
    project_type_1 = os.environ["PROJECT_TYPE_1"]
    init_db = str(os.environ["INIT_DB"])
    current_columns = str(os.environ["PRODUCTION_COLUMN_NAMES"])

    if project_type_1 == 'PRODUCTION' and init_db == 'True' and init_project == 'True':
        if 'data' not in st.session_state:
            st.session_state.data = []

        with st.form("config_sensor_registry_add"):
            col1,col2 = st.columns(2)
            with col1:
                col1_value = st.text_input("Enter Sensor", key="col1_input")
            with col2:
                col2_options = ["varchar(25)", "float"]
                col2_value = st.selectbox("Select Data type", col2_options, key="col2_select")

            submit_button = st.form_submit_button("Add sensor")
        
        if submit_button:
            if col1_value:
                st.session_state.data.append({"Sensor": col1_value, "DataType": col2_value})    

        if st.session_state.data:
            st.write("Table:")
            df = pd.DataFrame(st.session_state.data)
            delete_checkboxes = []
            with st.form("table_form"):
                for i, row in df.iterrows():
                    col1, col2, col3 = st.columns([3, 3, 1]) 
                    with col1:
                        st.write(row["Sensor"])
                    with col2:
                        st.write(row["DataType"])
                    with col3:
                        delete_checkbox = st.checkbox("Delete", key=f"delete_{i}",label_visibility="collapsed")
                        delete_checkboxes.append(delete_checkbox) 
                
                submit_delete = st.form_submit_button("Delete selected",type="primary")
                
                if submit_delete:
                    st.session_state.data = [row for i, row in enumerate(st.session_state.data) if not delete_checkboxes[i]]
                    st.success("Selected rows deleted successfully.")
                    st.rerun()
                    
    st.text(f"Current columm: {current_columns}")
    submit_new_column = st.button("Confirm new column",key="add_col_button")
    if submit_new_column:
        # edit json_string_fields in telegraf
        init_telegraft_str_col = "status"
        mac_id_col = "mac_id"
        df = pd.DataFrame(st.session_state.data)
        filtered_df = df[df['DataType'] == 'varchar(25)']
        telegraft_str_col = '"' + '","'.join(filtered_df['Sensor'].tolist()) + '"'
        telegraft_str_col = f'"{init_telegraft_str_col}","{mac_id_col}",{telegraft_str_col}'

        new_column = ', '.join(df.apply(lambda row: ' '.join(row), axis=1))  
        add_col_sql(st,os.environ["SERVER"],os.environ["USER_LOGIN"],os.environ["PASSWORD"],os.environ["DATABASE"],os.environ["TABLE_1"],new_column)
        new_production_column = f"{old_columns},{new_column}"
        new_production_column_name = ','.join(df['Sensor'].tolist())
        new_production_column_name = f"{current_columns},{new_production_column_name}"

        update_config_file1(telegraf_path, telegraft_str_col)

        
        os.environ["PRODUCTION_TABLE_COLUMNS"] = str(new_production_column)
        os.environ["PRODUCTION_COLUMN_NAMES"] = str(new_production_column_name)
        dotenv.set_key(dotenv_file,"PRODUCTION_TABLE_COLUMNS",os.environ["PRODUCTION_TABLE_COLUMNS"])
        dotenv.set_key(dotenv_file,"PRODUCTION_COLUMN_NAMES",os.environ["PRODUCTION_COLUMN_NAMES"])

        program_no = str(os.environ["NO"])
        restart_container(f"telegraf_mms{program_no}")
        st.success('Done!', icon="✅")
        time.sleep(0.5)
        st.rerun()
    st.markdown("---")

def add_col_sql(st,server,user_login,password,database,table,new_col):
        cnxn = pymssql.connect(server,user_login,password,database)
        cursor = cnxn.cursor()
        try:
            cursor.execute(f'''ALTER TABLE {table} ADD {new_col}''')
            cnxn.commit()
            cursor.close()
            st.success('ADD NEW COLUMN SUCCESSFULLY!', icon="✅")
        except Exception as e:
            st.error('Error'+str(e), icon="❌")

def dataflow_production_influx():
        st.caption("INFLUXDB")
        type_data = st.radio("Type of data",[os.environ["PREFIX_TOPIC_1"],os.environ["PREFIX_TOPIC_2"],os.environ["PREFIX_TOPIC_3"]],horizontal =True,key="2")
        
        if type_data== os.environ["PREFIX_TOPIC_1"]:
            mqtt_registry = list(str(os.environ["MQTT_TOPIC_1"]).split(","))
        elif type_data== os.environ["PREFIX_TOPIC_2"]:
            mqtt_registry = list(str(os.environ["MQTT_TOPIC_2"]).split(","))
        elif type_data== os.environ["PREFIX_TOPIC_3"]:
            mqtt_registry = list(str(os.environ["MQTT_TOPIC_3"]).split(","))

        preview_influx_selectbox = st.selectbox(
                "mqtt topic",
                mqtt_registry,
                index=None,
                placeholder="select topic...",
                key='preview_influx'
                    )
        if preview_influx_selectbox:
            preview_influx_but = st.button("QUERY",key="preview_influx_but")
            if preview_influx_but:
                preview_influx(st,os.environ["INFLUX_SERVER"],os.environ["INFLUX_PORT"],os.environ["INFLUX_USER_LOGIN"],os.environ["INFLUX_PASSWORD"],os.environ["INFLUX_DATABASE"],os.environ["PRODUCTION_COLUMN_NAMES"],preview_influx_selectbox)
        st.markdown("---")

def dataflow_production_sql():
        st.caption("SQLSERVER")
        type_data = st.radio("Type of data",[os.environ["PREFIX_TOPIC_1"],os.environ["PREFIX_TOPIC_2"],os.environ["PREFIX_TOPIC_3"]],horizontal =True,key="3")

        if type_data== os.environ["PREFIX_TOPIC_1"]:
            mqtt_registry = list(str(os.environ["MQTT_TOPIC_1"]).split(","))
        elif type_data== os.environ["PREFIX_TOPIC_2"]:
            mqtt_registry = list(str(os.environ["MQTT_TOPIC_2"]).split(","))
        elif type_data== os.environ["PREFIX_TOPIC_3"]:
            mqtt_registry = list(str(os.environ["MQTT_TOPIC_3"]).split(","))

        preview_sqlserver_selectbox = st.selectbox(
                "mqtt topic",
                mqtt_registry,
                index=None,
                placeholder="select topic...",
                key='preview_sqlserver'
                    )
        if preview_sqlserver_selectbox:
            preview_sqlserver_but = st.button("QUERY",key="preview_sqlserver_but")
        
            if preview_sqlserver_but:
                mc_no = preview_sqlserver_selectbox.split("/")[3]
                process = preview_sqlserver_selectbox.split("/")[2]
                project_type = preview_sqlserver_selectbox.split("/")[0]

                if project_type == os.environ["PREFIX_TOPIC_1"]:
                    table = os.environ["TABLE_1"]
                elif project_type ==os.environ["PREFIX_TOPIC_2"]:
                    table = os.environ["TABLE_2"]
                elif project_type == os.environ["PREFIX_TOPIC_3"]:
                    table = os.environ["TABLE_3"]   

                preview_production_sqlserver(os.environ["SERVER"],os.environ["USER_LOGIN"],os.environ["PASSWORD"],os.environ["DATABASE"],table,mc_no,process)
        st.markdown("---")

def drop_table(st,server,user_login,password,database,table):
        cnxn = pymssql.connect(server,user_login,password,database)
        cursor = cnxn.cursor()
        try:
            cursor.execute(f'''DROP TABLE {table}''')
            cnxn.commit()
            cursor.close()
            st.success('DROP TABLE SUCCESSFULLY!', icon="✅")
        except Exception as e:
            st.error('Error'+str(e), icon="❌")

def create_table(st,server,user_login,password,database,table,table_columns):
        cnxn = pymssql.connect(server,user_login,password,database)
        cursor = cnxn.cursor()
        try:
            cursor.execute('''
            CREATE TABLE '''+table+''' (
                '''+table_columns+'''
                )
                ''')
            cnxn.commit()
            cursor.close()
            st.success('CREATE TABLE SUCCESSFULLY!', icon="✅")
            return True
        except Exception as e:
            if 'There is already an object named' in str(e):
                st.error('TABLE is already an object named ', icon="❌")
            elif 'Column, parameter, or variable' in str(e):
                st.error('define columns mistake', icon="❌")
            else:
                st.error('Error'+str(e), icon="❌")
            return False

def config_initdb():
        st.header("DB STATUS")
        initial_db_value = os.environ["INIT_DB"]
        if initial_db_value == "False":
            st.error('DB NOT INITIAL', icon="❌")
            st.write("PLEASE CONFIRM CONFIG SETUP BEFORE INITIAL")
            initial_but = st.button("INITIAL DATABASE")
            if initial_but:
                if os.environ["PROJECT_TYPE_1"] == "PRODUCTION":
                    if os.environ["CALCULATE_FUNCTION"] != "3":
                        production_table_columns = os.environ["PRODUCTION_TABLE_COLUMNS"]
                        result_1 = create_table(st,os.environ["SERVER"],os.environ["USER_LOGIN"],os.environ["PASSWORD"],os.environ["DATABASE"],os.environ["TABLE_1"],production_table_columns)
                        result_2 = create_table(st,os.environ["SERVER"],os.environ["USER_LOGIN"],os.environ["PASSWORD"],os.environ["DATABASE"],os.environ["TABLE_LOG_1"],os.environ["TABLE_COLUMNS_LOG"])
                    else:
                        production_table_columns = os.environ["PRODUCTION_TABLE_COLUMNS"]+",occurred datetime"
                        result_1 = create_table(st,os.environ["SERVER"],os.environ["USER_LOGIN"],os.environ["PASSWORD"],os.environ["DATABASE"],os.environ["TABLE_1"],production_table_columns)
                        result_2 = create_table(st,os.environ["SERVER"],os.environ["USER_LOGIN"],os.environ["PASSWORD"],os.environ["DATABASE"],os.environ["TABLE_LOG_1"],os.environ["TABLE_COLUMNS_LOG"])    
                else:
                    result_1,result_2 = False,False
                if os.environ["PROJECT_TYPE_2"] == "MCSTATUS":
                    mcstatus_table_columns = os.environ["MCSTATUS_TABLE_COLUMNS"]
                    result_3 = create_table(st,os.environ["SERVER"],os.environ["USER_LOGIN"],os.environ["PASSWORD"],os.environ["DATABASE"],os.environ["TABLE_2"],mcstatus_table_columns)
                    result_4 = create_table(st,os.environ["SERVER"],os.environ["USER_LOGIN"],os.environ["PASSWORD"],os.environ["DATABASE"],os.environ["TABLE_LOG_2"],os.environ["TABLE_COLUMNS_LOG"])
                else:    
                    result_3,result_4 = False,False

                if os.environ["PROJECT_TYPE_3"] == "ALARMLIST":
                    alarmlist_table_columns = os.environ["ALARMLIST_TABLE_COLUMNS"]
                    result_5 = create_table(st,os.environ["SERVER"],os.environ["USER_LOGIN"],os.environ["PASSWORD"],os.environ["DATABASE"],os.environ["TABLE_3"],alarmlist_table_columns)
                    result_6 = create_table(st,os.environ["SERVER"],os.environ["USER_LOGIN"],os.environ["PASSWORD"],os.environ["DATABASE"],os.environ["TABLE_LOG_3"],os.environ["TABLE_COLUMNS_LOG"])                
                else:    
                    result_5,result_6 = False,False
                # create table monitor
                monitor_tb = "MONITOR_IOT"
                monitor_col = "registered datetime,mc_no varchar(10),process varchar(10),broker varchar(10),modbus varchar(10),mac_id varchar(20)"
                a = create_table(st,os.environ["SERVER"],os.environ["USER_LOGIN"],os.environ["PASSWORD"],os.environ["DATABASE"],table=monitor_tb,table_columns=monitor_col)
                
                results = [result_1,result_2,result_3,result_4,result_5,result_6]
                if not results:
                    st.error('UNKNOWN PROJECT TYPE', icon="❌")
                else:
                    os.environ["INIT_DB"] = "True"
                    dotenv.set_key(dotenv_file,"INIT_DB",os.environ["INIT_DB"])
                    st.success('DB CREATED!', icon="✅")
                    time.sleep(1)
                st.rerun()
        else:
            remove_table_password = st.text_input("PASSWORD","",type="password")
            remove_table = st.button("REMOVE DB",type="primary")
            if remove_table:
                if remove_table_password =="1":
                    project_1 = os.environ["PROJECT_TYPE_1"]
                    project_2 = os.environ["PROJECT_TYPE_2"]
                    project_3 =os.environ["PROJECT_TYPE_3"]
                    if project_1 != "":
                        drop_table(st,os.environ["SERVER"],os.environ["USER_LOGIN"],os.environ["PASSWORD"],os.environ["DATABASE"],os.environ["TABLE_1"])
                        drop_table(st,os.environ["SERVER"],os.environ["USER_LOGIN"],os.environ["PASSWORD"],os.environ["DATABASE"],os.environ["TABLE_LOG_1"])
                    
                    if project_2 != "":
                        drop_table(st,os.environ["SERVER"],os.environ["USER_LOGIN"],os.environ["PASSWORD"],os.environ["DATABASE"],os.environ["TABLE_2"])
                        drop_table(st,os.environ["SERVER"],os.environ["USER_LOGIN"],os.environ["PASSWORD"],os.environ["DATABASE"],os.environ["TABLE_LOG_2"])
                    if project_3 != "":
                        drop_table(st,os.environ["SERVER"],os.environ["USER_LOGIN"],os.environ["PASSWORD"],os.environ["DATABASE"],os.environ["TABLE_3"])
                        drop_table(st,os.environ["SERVER"],os.environ["USER_LOGIN"],os.environ["PASSWORD"],os.environ["DATABASE"],os.environ["TABLE_LOG_3"])

                    drop_table(st,os.environ["SERVER"],os.environ["USER_LOGIN"],os.environ["PASSWORD"],os.environ["DATABASE"],"MONITOR_IOT")

                    os.environ["INIT_DB"] = "False"
                    os.environ["INIT_PROJECT"] = "False"
                    dotenv.set_key(dotenv_file,"INIT_DB",os.environ["INIT_DB"])
                    dotenv.set_key(dotenv_file,"INIT_PROJECT",os.environ["INIT_PROJECT"])
                    st.success('Deleted!', icon="✅")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error('Cannot delete,password mistake!', icon="❌")

def conn_sql(st,server,user_login,password,database):
        try:
            cnxn = pymssql.connect(server,user_login,password,database)
            st.success('SQLSERVER CONNECTED!', icon="✅")
            cnxn.close()
        except Exception as e:
            st.error('Error,Cannot connect sql server :'+str(e), icon="❌")

def config_db_connect(env_headers):
    if env_headers == "SQLSERVER":
        form_name = "config_db_connect_sql"
    elif env_headers == "INFLUXDB":
        form_name = "config_db_connect_influx"

    with st.form(form_name):

        total_env_list = None
        if env_headers == "SQLSERVER":
            total_env_list = sql_server_env_lists = ["SERVER","DATABASE","USER_LOGIN","PASSWORD"]
        elif env_headers == "INFLUXDB":
            total_env_list = influxdb_env_lists = ["INFLUX_SERVER","INFLUX_DATABASE","INFLUX_USER_LOGIN","INFLUX_PASSWORD","INFLUX_PORT","INFLUX_MEASUREMENT"]
        else :
            st.error("don't have the connection")

        if total_env_list is not None:
            st.header(env_headers)
            cols = st.columns(len(total_env_list))
            for j in range(len(total_env_list)):
                param = total_env_list[j]
                if "PASSWORD" in param or "TOKEN" in param:
                    type_value = "password"
                else:
                    type_value = "default"
                os.environ[param] = cols[j].text_input(param,os.environ[param],type=type_value)
                dotenv.set_key(dotenv_file,param,os.environ[param])

            cols = st.columns(2) 

            if env_headers == "SQLSERVER":

                sql_check_but = cols[0].form_submit_button("CONECTION CHECK")
                if sql_check_but:
                    conn_sql(st,os.environ["SERVER"],os.environ["USER_LOGIN"],os.environ["PASSWORD"],os.environ["DATABASE"])

            elif env_headers == "INFLUXDB":
                influx_check_but = cols[0].form_submit_button("CONECTION CHECK")
                if influx_check_but:
                    try:
                        client = InfluxDBClient(os.environ["INFLUX_SERVER"], os.environ["INFLUX_PORT"], os.environ["INFLUX_USER_LOGIN"], os.environ["INFLUX_PASSWORD"], os.environ["INFLUX_DATABASE"])
                        client.ping()
                        st.success('INFLUXDB CONNECTED!', icon="✅")
                    except Exception as e:
                        st.error("Error :"+str(e))
            else:
                st.error('Dont have the connection!', icon="❌")

    st.markdown("---")

def restart_container(container_name):
    try:
        result = subprocess.run(
            ["docker", "restart", container_name], 
            capture_output=True, 
            text=True,
        )
        if result.returncode == 0:
            st.success(f"Successfully restarted {container_name}!")
        else:
            st.error(f"Failed to restart {container_name}: {result.stderr}")

    except subprocess.CalledProcessError as e:
        st.error(f"Failed to restart Telegraf: {e.stderr}")

def config_sensor_registry_add():
    st.header("SENSOR REGISTRY")
    if 'data' not in st.session_state:
        st.session_state.data = []

    with st.form("config_sensor_registry_add"):
        col1,col2 = st.columns(2)
        with col1:
            col1_value = st.text_input("Enter Sensor", key="col1_input")
        with col2:
            col2_options = ["varchar(25)", "float"]
            col2_value = st.selectbox("Select Data type", col2_options, key="col2_select")

        submit_button = st.form_submit_button("Add sensor")
    
    if submit_button:
        if col1_value:
            st.session_state.data.append({"Sensor": col1_value, "DataType": col2_value})    

    if st.session_state.data:
        st.write("Table:")

        df = pd.DataFrame(st.session_state.data)
        delete_checkboxes = []
        with st.form("table_form"):
            for i, row in df.iterrows():
                col1, col2, col3 = st.columns([3, 3, 1]) 
                with col1:
                    st.write(row["Sensor"])
                with col2:
                    st.write(row["DataType"])
                with col3:
                    delete_checkbox = st.checkbox("Delete", key=f"delete_{i}",label_visibility="collapsed")
                    delete_checkboxes.append(delete_checkbox) 
            
            submit_delete = st.form_submit_button("Delete selected",type="primary")
            
            if submit_delete:
                st.session_state.data = [row for i, row in enumerate(st.session_state.data) if not delete_checkboxes[i]]
                st.success("Selected rows deleted successfully.")
                st.rerun()
        init_db = str(os.environ["INIT_DB"])
        if init_db =='False':
            col1,col2 = st.columns(2)
            with col1:
                mqtt_ip = st.text_input("MQTT IP ADDRESS",key="mqtt_ip")
                influx_ip = st.text_input("INFLUX IP ADDRESS",key="influx_ip")
            with col2:
                mqtt_port = st.text_input("MQTT PORT",max_chars=4,placeholder="1883",key="mqtt_port")    
                influx_port = st.text_input("INFLUX PORT",max_chars=4,placeholder="8086",key="influx_port")

            confirm_sensor = st.button("Confirm sensor")
        
            if confirm_sensor:
                if st.session_state.data:
                    init_columns = os.environ["INIT_COLUMNS"]
                    df = pd.DataFrame(st.session_state.data)
                    init_telegraft_str_col = "status"
                    mac_id_col = "mac_id"
                    filtered_df = df[df['DataType'] == 'varchar(25)']
                    telegraft_str_col = '"' + '","'.join(filtered_df['Sensor'].tolist()) + '"'
                    telegraft_str_col = f'"{init_telegraft_str_col}","{mac_id_col}",{telegraft_str_col}'
                    production_column = ', '.join(df.apply(lambda row: ' '.join(row), axis=1))
                    production_column = f"{init_columns},{production_column}"
                    production_column_name = ','.join(df['Sensor'].tolist())
                    update_config_file1(telegraf_path, telegraft_str_col)

                    # edit topic in telegraf
                    telegraft_mqtt_topic = f'"data/{os.environ["DIV"].lower()}/{os.environ["PROCESS"].lower()}/#","alarm/{os.environ["DIV"].lower()}/{os.environ["PROCESS"].lower()}/#","status/{os.environ["DIV"].lower()}/{os.environ["PROCESS"].lower()}/#","mqtt/{os.environ["DIV"].lower()}/{os.environ["PROCESS"].lower()}/#"'
                    print(telegraft_mqtt_topic)
                    update_config_file3(telegraf_path, telegraft_mqtt_topic)

                    os.environ["PRODUCTION_TABLE_COLUMNS"] = str(production_column)
                    os.environ["PRODUCTION_COLUMN_NAMES"] = str(production_column_name)
                    dotenv.set_key(dotenv_file,"PRODUCTION_TABLE_COLUMNS",os.environ["PRODUCTION_TABLE_COLUMNS"])
                    dotenv.set_key(dotenv_file,"PRODUCTION_COLUMN_NAMES",os.environ["PRODUCTION_COLUMN_NAMES"])

                    os.environ['MQTT_BROKER'] = str(mqtt_ip)
                    os.environ['INFLUX_PORT'] = str(influx_port)
                    os.environ['INFLUX_SERVER'] = str(influx_ip)

                    dotenv.set_key(dotenv_file,"MQTT_BROKER",os.environ["MQTT_BROKER"])
                    dotenv.set_key(dotenv_file,"INFLUX_PORT",os.environ["INFLUX_PORT"])
                    dotenv.set_key(dotenv_file,"INFLUX_SERVER",os.environ["INFLUX_SERVER"])

                    update_config_file2(telegraf_path,mqtt_ip)
                    time.sleep(0.5)
                    program_no = str(os.environ["NO"])
                    restart_container(f"telegraf_mms{program_no}")
                    restart_container(f"influxdb_mms{program_no}")
                    st.success('Done!', icon="✅")
                    time.sleep(0.5)
                st.rerun()

def config_mqtt_add():
    st.header("MQTT TOPIC REGISTRY")

    with st.form("config_mqtt_add"):
        div_name =  os.environ["DIV"]
        process_name =  os.environ["PROCESS"]
        project_type_1 = os.environ["PROJECT_TYPE_1"]
        project_type_2 = os.environ["PROJECT_TYPE_2"]
        project_type_3 = os.environ["PROJECT_TYPE_3"]
        prefix_topic_1 = os.environ["PREFIX_TOPIC_1"]
        prefix_topic_2 = os.environ["PREFIX_TOPIC_2"]
        prefix_topic_3 = os.environ["PREFIX_TOPIC_3"]
        mqtt_value = None
    
        mqtt_registry = list(str(os.environ["MQTT_TOPIC"]).split(","))
        col1,col2 = st.columns(2)
        
        with col1:
            add_new_mqtt = st.text_input("Add a new mqtt (topic: machine_no)","",key="add_new_mqtt_input")
            add_new_mqtt_but = st.form_submit_button("Add MQTT", type="secondary")
            add_new_mqtt_ = []
            if add_new_mqtt and add_new_mqtt_but:
                if project_type_1!="":
                    add_new_mqtt1 = prefix_topic_1+"/"+div_name.lower()+"/"+process_name.lower()+"/"+add_new_mqtt.lower()
                else: add_new_mqtt1 = None
                if project_type_2!="":
                    add_new_mqtt2 = prefix_topic_2+"/"+div_name.lower()+"/"+process_name.lower()+"/"+add_new_mqtt.lower()
                else: add_new_mqtt2 = None
                if project_type_3!="":
                    add_new_mqtt3 = prefix_topic_3+"/"+div_name.lower()+"/"+process_name.lower()+"/"+add_new_mqtt.lower()
                else: add_new_mqtt3 = None

                add_new_mqtt_ = [add_new_mqtt1,add_new_mqtt2,add_new_mqtt3]
                if add_new_mqtt1 is None:
                    add_new_mqtt_.remove(add_new_mqtt1)
                if add_new_mqtt2 is None:
                    add_new_mqtt_.remove(add_new_mqtt2) 
                if add_new_mqtt3 is None:
                    add_new_mqtt_.remove(add_new_mqtt3)   

                mqtt_registry+= add_new_mqtt_

                for i in range(len(mqtt_registry)):
                    if mqtt_value == None:
                        mqtt_value = mqtt_registry[i]
                    else:
                        mqtt_value = str(mqtt_value)+","+mqtt_registry[i]

                os.environ["MQTT_TOPIC"] = mqtt_value
                dotenv.set_key(dotenv_file,"MQTT_TOPIC",os.environ["MQTT_TOPIC"])   

                mqtt_1 = None
                mqtt_2 = None
                mqtt_3 = None
                mqtt_4 = None

                mqtt_list = mqtt_value.split(",")

                for i in range(len(mqtt_list)):
                    if mqtt_list[i].split('/')[0] == "data":
                        if mqtt_1==None:
                            mqtt_1 = mqtt_list[i]
                        else:
                            mqtt_1 = str(mqtt_1)+","+mqtt_list[i]
                    elif mqtt_list[i].split('/')[0] == "status":
                        if mqtt_2==None:
                            mqtt_2 = mqtt_list[i]
                        else:
                            mqtt_2 = str(mqtt_2)+","+mqtt_list[i]
                    elif mqtt_list[i].split('/')[0] == "alarm":
                        if mqtt_3==None:
                            mqtt_3 = mqtt_list[i]
                        else:
                            mqtt_3 = str(mqtt_3)+","+mqtt_list[i]      

                if mqtt_1:
                    os.environ["MQTT_TOPIC_1"] = str(mqtt_1)
                    dotenv.set_key(dotenv_file,"MQTT_TOPIC_1",os.environ["MQTT_TOPIC_1"])
                if mqtt_2:
                    os.environ["MQTT_TOPIC_2"] = str(mqtt_2)
                    dotenv.set_key(dotenv_file,"MQTT_TOPIC_2",os.environ["MQTT_TOPIC_2"])
                if mqtt_3:
                    os.environ["MQTT_TOPIC_3"] = str(mqtt_3)
                    dotenv.set_key(dotenv_file,"MQTT_TOPIC_3",os.environ["MQTT_TOPIC_3"])

                mqtt_4 = str(os.environ["MQTT_TOPIC_1"])
                mqtt_4 = mqtt_4.replace('data/', 'mqtt/')
                os.environ["MQTT_TOPIC_4"] = str(mqtt_4)
                dotenv.set_key(dotenv_file,"MQTT_TOPIC_4",os.environ["MQTT_TOPIC_4"])
                
                st.success('Done!', icon="✅")
                time.sleep(0.5)
                st.rerun()

        with col2:
            st.text("PREVIEW ")
            st.text("MQTT TOPIC REGISTRY: "+str(os.environ["MQTT_TOPIC_1"]))
            st.text("MQTT TOPIC REGISTRY: "+str(os.environ["MQTT_TOPIC_2"])) 
            st.text("MQTT TOPIC REGISTRY: "+str(os.environ["MQTT_TOPIC_3"])) 

def config_mqtt_delete():

    with st.form("config_mqtt_delete"):

        mqtt_value = None
        mqtt_registry = list(str(os.environ["MQTT_TOPIC"]).split(","))

        col1, col2 = st.columns(2)

        with col1:
    
            option_mqtt = st.multiselect(
                        'Delete mqtt',
                        mqtt_registry,placeholder="select mqtt...")

            delete_mqtt = st.form_submit_button("Delete MQTT", type="primary")

            if delete_mqtt:
                len_mqtt_registry = len(mqtt_registry)
                len_option_mqtt = len(option_mqtt)
                if len_option_mqtt<len_mqtt_registry:
                    
                    for i in range(len(option_mqtt)):
                        mqtt_registry.remove(option_mqtt[i])

                    for i in range(len(mqtt_registry)):
                        if mqtt_value == None:
                            mqtt_value = mqtt_registry[i]
                        else:
                            mqtt_value = str(mqtt_value)+","+mqtt_registry[i]

                    os.environ["MQTT_TOPIC"] = mqtt_value
                    dotenv.set_key(dotenv_file,"MQTT_TOPIC",os.environ["MQTT_TOPIC"])

                    topics_all = mqtt_value.split(',')
                    data_list = []
                    status_list = []
                    alarm_list = []
                    for topic in topics_all:
                        if 'data' in topic:
                            data_list.append(topic)
                        elif 'status' in topic:
                            status_list.append(topic)
                        elif 'alarm' in topic:
                            alarm_list.append(topic)

                    os.environ["MQTT_TOPIC_1"] = ','.join(data_list)
                    os.environ["MQTT_TOPIC_2"] = ','.join(status_list)
                    os.environ["MQTT_TOPIC_3"] = ','.join(alarm_list)
                    dotenv.set_key(dotenv_file,"MQTT_TOPIC_1",os.environ["MQTT_TOPIC_1"])
                    dotenv.set_key(dotenv_file,"MQTT_TOPIC_2",os.environ["MQTT_TOPIC_2"])
                    dotenv.set_key(dotenv_file,"MQTT_TOPIC_3",os.environ["MQTT_TOPIC_3"])

                    mqtt_4 = str(os.environ["MQTT_TOPIC_1"])
                    mqtt_4 = mqtt_4.replace('data/', 'mqtt/')
                    os.environ["MQTT_TOPIC_4"] = str(mqtt_4)
                    dotenv.set_key(dotenv_file,"MQTT_TOPIC_4",os.environ["MQTT_TOPIC_4"])
                    
                    st.success('Deleted!', icon="✅")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error('Cannot delete,sensor regisry must have at least one!', icon="❌")

    st.markdown("---")

def project_config():

    st.header("Poject Configulation")
    div_name = str(os.environ["DIV"])
    project_name = str(os.environ["PROCESS"])
    table_name_1 = str(os.environ["TABLE_1"])
    table_log_name_1 = str(os.environ["TABLE_LOG_1"])
    table_name_2 = str(os.environ["TABLE_2"])
    table_log_name_2 = str(os.environ["TABLE_LOG_2"])
    table_name_3 = str(os.environ["TABLE_3"])
    table_log_name_3 = str(os.environ["TABLE_LOG_3"])
    init_project = str(os.environ["INIT_PROJECT"])

    with st.form("project_config"):
        col1,col2 = st.columns(2)
        with col1:
            div_name_input = st.text_input('Division Name', div_name,key="div_name_input")
            project_name_input = st.text_input('Process Name', project_name,key="project_name_input")
            production_data= st.checkbox('PRODUCTION DATA')
            mcstatus_data= st.checkbox('STATUS DATA')
            alarmlist_data= st.checkbox('ALARM DATA')

            if str(init_project) == 'True':
                edit_config = st.form_submit_button('EDIT')
                password_edit_text = st.empty()
                password_edit = password_edit_text.text_input("Input password", type="password")

                if password_edit == "1":
                    if edit_config:
                        if production_data:
                            os.environ["DIV"] = str(div_name_input.upper())
                            os.environ["PROCESS"] = str(project_name_input.upper())
                            os.environ["TABLE_1"] = "DATA_PRODUCTION_"+str(project_name_input.upper())
                            os.environ["TABLE_LOG_1"] = "LOG_PRODUCTION_"+str(project_name_input.upper())
                            os.environ["PROJECT_TYPE_1"] = "PRODUCTION"
                        else:
                            os.environ["PROJECT_TYPE_1"] = ""
                            os.environ["TABLE_1"] = ""
                            os.environ["TABLE_LOG_1"] = ""        
                        if mcstatus_data:
                            os.environ["DIV"] = str(div_name_input.upper())
                            os.environ["PROCESS"] = str(project_name_input.upper())
                            os.environ["TABLE_2"] = "DATA_MCSTATUS_"+str(project_name_input.upper())
                            os.environ["TABLE_LOG_2"] = "LOG_MCSTATUS_"+str(project_name_input.upper())
                            os.environ["PROJECT_TYPE_2"] = "MCSTATUS"
                        else:
                            os.environ["PROJECT_TYPE_2"] = ""
                            os.environ["TABLE_2"] = ""
                            os.environ["TABLE_LOG_2"] = ""
                        if alarmlist_data:
                            os.environ["DIV"] = str(div_name_input.upper())
                            os.environ["PROCESS"] = str(project_name_input.upper())
                            os.environ["TABLE_3"] = "DATA_ALARMLIST_"+str(project_name_input.upper())
                            os.environ["TABLE_LOG_3"] = "LOG_ALARMLIST_"+str(project_name_input.upper())
                            os.environ["PROJECT_TYPE_3"] = "ALARMLIST"  
                        else:
                            os.environ["PROJECT_TYPE_3"] = ""
                            os.environ["TABLE_3"] = ""
                            os.environ["TABLE_LOG_3"] = ""

                        os.environ["INIT_PROJECT"] = "True"
                        dotenv.set_key(dotenv_file,"DIV",os.environ["DIV"])
                        dotenv.set_key(dotenv_file,"PROCESS",os.environ["PROCESS"])
                        dotenv.set_key(dotenv_file,"TABLE_1",os.environ["TABLE_1"])
                        dotenv.set_key(dotenv_file,"TABLE_LOG_1",os.environ["TABLE_LOG_1"])
                        dotenv.set_key(dotenv_file,"TABLE_2",os.environ["TABLE_2"])
                        dotenv.set_key(dotenv_file,"TABLE_LOG_2",os.environ["TABLE_LOG_2"])
                        dotenv.set_key(dotenv_file,"TABLE_3",os.environ["TABLE_3"])
                        dotenv.set_key(dotenv_file,"TABLE_LOG_3",os.environ["TABLE_LOG_3"])
                        dotenv.set_key(dotenv_file,"PROJECT_TYPE_1",os.environ["PROJECT_TYPE_1"])
                        dotenv.set_key(dotenv_file,"PROJECT_TYPE_2",os.environ["PROJECT_TYPE_2"])
                        dotenv.set_key(dotenv_file,"PROJECT_TYPE_3",os.environ["PROJECT_TYPE_3"])
                        dotenv.set_key(dotenv_file,"INIT_PROJECT",os.environ["INIT_PROJECT"])
                        st.success('Edit finished', icon="✅")
                        st.rerun()

            else:
                submitted = st.form_submit_button('INITIAL')
                if submitted and str(init_project) !='True':
                    if production_data:
                        os.environ["DIV"] = str(div_name_input.upper())
                        os.environ["PROCESS"] = str(project_name_input.upper())
                        os.environ["TABLE_1"] = "DATA_PRODUCTION_"+str(project_name_input.upper())
                        os.environ["TABLE_LOG_1"] = "LOG_PRODUCTION_"+str(project_name_input.upper())
                        os.environ["PROJECT_TYPE_1"] = "PRODUCTION"
                    else:
                        os.environ["PROJECT_TYPE_1"] = ""
                        os.environ["TABLE_1"] = ""
                        os.environ["TABLE_LOG_1"] = ""        
                    if mcstatus_data:
                        os.environ["DIV"] = str(div_name_input.upper())
                        os.environ["PROCESS"] = str(project_name_input.upper())
                        os.environ["TABLE_2"] = "DATA_MCSTATUS_"+str(project_name_input.upper())
                        os.environ["TABLE_LOG_2"] = "LOG_MCSTATUS_"+str(project_name_input.upper())
                        os.environ["PROJECT_TYPE_2"] = "MCSTATUS"
                    else:
                        os.environ["PROJECT_TYPE_2"] = ""
                        os.environ["TABLE_2"] = ""
                        os.environ["TABLE_LOG_2"] = ""
                    if alarmlist_data:
                        os.environ["DIV"] = str(div_name_input.upper())
                        os.environ["PROCESS"] = str(project_name_input.upper())
                        os.environ["TABLE_3"] = "DATA_ALARMLIS_"+str(project_name_input.upper())
                        os.environ["TABLE_LOG_3"] = "LOG_ALARMLIS_"+str(project_name_input.upper())
                        os.environ["PROJECT_TYPE_3"] = "ALARMLIST"  
                    else:
                        os.environ["PROJECT_TYPE_3"] = ""
                        os.environ["TABLE_3"] = ""
                        os.environ["TABLE_LOG_3"] = ""

                    os.environ["INIT_PROJECT"] = "True"

                    dotenv.set_key(dotenv_file,"DIV",os.environ["DIV"])
                    dotenv.set_key(dotenv_file,"PROCESS",os.environ["PROCESS"])
                    dotenv.set_key(dotenv_file,"TABLE_1",os.environ["TABLE_1"])
                    dotenv.set_key(dotenv_file,"TABLE_LOG_1",os.environ["TABLE_LOG_1"])
                    dotenv.set_key(dotenv_file,"TABLE_2",os.environ["TABLE_2"])
                    dotenv.set_key(dotenv_file,"TABLE_LOG_2",os.environ["TABLE_LOG_2"])
                    dotenv.set_key(dotenv_file,"TABLE_3",os.environ["TABLE_3"])
                    dotenv.set_key(dotenv_file,"TABLE_LOG_3",os.environ["TABLE_LOG_3"])
                    dotenv.set_key(dotenv_file,"PROJECT_TYPE_1",os.environ["PROJECT_TYPE_1"])
                    dotenv.set_key(dotenv_file,"PROJECT_TYPE_2",os.environ["PROJECT_TYPE_2"])
                    dotenv.set_key(dotenv_file,"PROJECT_TYPE_3",os.environ["PROJECT_TYPE_3"])
                    dotenv.set_key(dotenv_file,"INIT_PROJECT",os.environ["INIT_PROJECT"])
                    st.rerun()
        
        with col2:
            st.text("PREVIEW ")
            if production_data:
                st.text("TABLE NAME: "+table_name_1)
                st.text("TABLE LOG NAME: "+table_log_name_1)
            if mcstatus_data:
                st.text("TABLE NAME: "+table_name_2)
                st.text("TABLE LOG NAME: "+table_log_name_2)
            if alarmlist_data:
                st.text("TABLE NAME: "+table_name_3)
                st.text("TABLE LOG NAME: "+table_log_name_3)

def dataflow_test1():
        st.caption("TEST RUN THE PROGRAM")
        test_run_but = st.button("TEST DATA",key="test_run_but1")
        if test_run_but:
            try:
                result = subprocess.check_output(['python', 'main_data.py'])
                st.write(result.decode('UTF-8'))
                st.success('TEST RUN SUCCESS!', icon="✅")
            except Exception as e:
                st.error("Error :"+str(e))
        st.markdown("---")

def dataflow_test2():
        st.caption("TEST RUN THE PROGRAM")
        test_run_but = st.button("TEST STATUS",key="test_run_but2")
        if test_run_but:
            try:
                result = subprocess.check_output(['python', 'main_status.py'])
                st.write(result.decode('UTF-8'))
                st.success('TEST RUN SUCCESS!', icon="✅")
            except Exception as e:
                st.error("Error :"+str(e))
        st.markdown("---")

def dataflow_test3():
        st.caption("TEST RUN THE PROGRAM")
        test_run_but = st.button("TEST ALARM",key="test_run_but3")
        if test_run_but:
            try:
                result = subprocess.check_output(['python', 'main_alarm.py'])
                st.write(result.decode('UTF-8'))
                st.success('TEST RUN SUCCESS!', icon="✅")
            except Exception as e:
                st.error("Error :"+str(e))
        st.markdown("---")

def save_schedule_config(new_config):
    with open(ofelia_path, 'w') as file:
        file.write(new_config)

def schedule_config(schedule_data,schedule_status,schedule_alarm):
    program_no = str(os.environ["NO"])
    calculate_function = str(os.environ["CALCULATE_FUNCTION"])
    if calculate_function != '4':
        new_config = f'''
    [job-run "MMS Data{program_no}"]
    schedule = {schedule_data}
    container = mms_data{program_no}
    command = python /app/main_data.py

    [job-run "MMS Status{program_no}"]
    schedule = {schedule_status}
    container = mms_status{program_no}
    command = python /app/main_status.py

    [job-run "MMS Alarm{program_no}"]
    schedule = {schedule_alarm}
    container = mms_alarm{program_no}
    command = python /app/main_alarm.py

    [job-run "autodrop{program_no}"]
    schedule = @monthly
    container = auto_drop{program_no}
    command = python /app/autodrop.py

    [job-run "Iot monitor{program_no}"]
    schedule = @every 5m
    container = iot_monitor{program_no}
    command = python /app/monitor.py
    '''
    else:
        new_config = f'''
    [job-run "MMS Data{program_no}"]
    schedule = {schedule_data}
    container = mms_data{program_no}
    command = python /app/main_data.py

    [job-run "MMS Status{program_no}"]
    schedule = {schedule_status}
    container = mms_status{program_no}
    command = python /app/main_status.py

    [job-run "MMS Alarm{program_no}"]
    schedule = {schedule_alarm}
    container = mms_alarm{program_no}
    command = python /app/main_alarm.py

    [job-run "autodrop{program_no}"]
    schedule = @monthly
    container = auto_drop{program_no}
    command = python /app/autodrop.py

    [job-run "Iot monitor{program_no}"]
    schedule = @every 5m
    container = iot_monitor{program_no}
    command = python /app/monitor.py

    [job-run "add_external_data{program_no}"]
    schedule = @every 5m
    container = add_external_data{program_no}
    command = python /app/add_data.py
    '''
    save_schedule_config(new_config)

def load_schedule_config(path,line_no):
    schedule_dict = {
        "@every 1m":"every 1 minute",
        "@every 5m":"every 5 minute",
        "@every 10m":"every 10 minute",
        "@every 30m":"every 30 minute",
        "@hourly":"every hourly"
    }

    if os.path.exists(path):
        with open(path, 'r') as file:
            lines = file.readlines()
            for line in lines:
                if 'schedule' in line:
                    current_schedule = lines[line_no].split("=")[1].strip()
                    current_schedule = schedule_dict.get(current_schedule)
            return current_schedule
    return ''

def calculation_method():
    st.caption("CALCULATION METHOD")
    calculate_select = st.selectbox('Select calculate method',('every period time','every period time with accumulate data','sidelap','combine with external data'),key='calculate_select')
    calculate_dict = {
        "every period time":"1",
        "every period time with accumulate data":"2",
        "sidelap":"3",
        "combine with external data":"4"
            }
    calculate_select_value = calculate_dict.get(calculate_select)

    if calculate_select_value == "2" or calculate_select_value == "4":
        production_column_names = os.environ["PRODUCTION_COLUMN_NAMES"].split(',')
        keyword_separate_group_data = st.multiselect('Select keyword fot separate group data (max 10)',(production_column_names),key='keyword_separate_group_data',max_selections=10)
        column_names_string = ','.join(keyword_separate_group_data)
    else:
        column_names_string=""

    if calculate_select_value == "4":
        column_names_ext = st.text_input("Enter external column like ex1,ex2,ex...  ,1st position is for link between data", key="column_names_ext")
    else:
        column_names_ext = ''

    cal_button = st.button("SUBMIT",key='cal_button')

    if cal_button:
        if calculate_select_value =="4":
            production_col = set(os.environ["PRODUCTION_COLUMN_NAMES"].split(','))
            external_col = set(column_names_ext.split(','))
            production_col_2 = production_col - external_col
            production_col_final = ','.join(production_col_2)
        
            os.environ['PRODUCTION_COLUMN_NAMES_2'] = str(production_col_final)
            dotenv.set_key(dotenv_file,"PRODUCTION_COLUMN_NAMES_2",os.environ["PRODUCTION_COLUMN_NAMES_2"])


        os.environ['CALCULATE_FUNCTION'] = str(calculate_select_value)
        dotenv.set_key(dotenv_file,"CALCULATE_FUNCTION",os.environ["CALCULATE_FUNCTION"])
        os.environ['CALCULATE_FACTOR'] = str(column_names_string)
        dotenv.set_key(dotenv_file,"CALCULATE_FACTOR",os.environ["CALCULATE_FACTOR"])
        os.environ['EXT_TABLE_COLUMNS'] = str(column_names_ext)
        dotenv.set_key(dotenv_file,"EXT_TABLE_COLUMNS",os.environ["EXT_TABLE_COLUMNS"])
        st.success('CONFIEMED', icon="✅") 
        time.sleep(0.5)
        st.rerun()
    st.markdown("---")

def main_layout():
    st.set_page_config(
            page_title="MES System 2.0.11",
            page_icon="💻",
            layout="wide",
            initial_sidebar_state="expanded",
        )
    st.markdown("""<h1 style='text-align: center;'>MACHINE MONITORING SYSTEM</h1>""", unsafe_allow_html=True)
    col1,col2,col3 = st.columns(3)
    with col2:
        text_input_container = st.empty()
        password = text_input_container.text_input("Input password", type="password")

    if password == str(os.environ["ST_PASSWORD_1"]):
        text_input_container.empty()
        tab1,tab2,tab3,tab4,tab5,tab6 = st.tabs(["⚙️ PROJECT CONFIG", "🔑 DB CONNECTION","🕞SCHEDULE", "🔍 DATAFLOW PREVIEW","📝LOG", "📂 DB CREATE"])

        with tab1:
            project_config()
            init_project = str(os.environ["INIT_PROJECT"])
            project_type_1 = os.environ["PROJECT_TYPE_1"]
            init_db = str(os.environ["INIT_DB"])

            if init_project=="True":
                config_mqtt_add()
                config_mqtt_delete()
                if project_type_1 == 'PRODUCTION' and init_db == 'False':
                    config_sensor_registry_add()
            else:
                st.error('NOT INITIAL A PROJECT YET', icon="❌")
        with tab2:
            config_db_connect("SQLSERVER")
            config_db_connect("INFLUXDB")
        with tab3:
            st.header("SCHEDULE")
            a = load_schedule_config(ofelia_path,2)
            b = load_schedule_config(ofelia_path,7)
            c = load_schedule_config(ofelia_path,12)

            col1,col2 = st.columns(2)
            with col1:
                schedule_data = st.selectbox('Select Data Schedule',('every 1 minute','every 5 minute','every 10 minute','every 30 minute', 'every hourly'),key='schedule_data')
                schedule_status = st.selectbox('Select Status Schedule',('every 1 minute','every 5 minute','every 10 minute','every 30 minute', 'every hourly'),key='schedule_status')
                schedule_alarm = st.selectbox('Select Alarm Schedule',('every 1 minute','every 5 minute','every 10 minute','every 30 minute', 'every hourly'),key='schedule_alarm')
            with col2:
                st.text("\n")
                st.text("\n")  
                st.text(f"Current Schedule:{a}")
                st.text("\n")  
                st.text("\n")  
                st.text("\n")  
                st.text(f"Current Schedule:{b}")
                st.text("\n")  
                st.text("\n")  
                st.text("\n")  
                st.text(f"Current Schedule:{c}")

            schedule_dict1 = {
                "every 1 minute":"@every 1m",
                "every 5 minute":"@every 5m",
                "every 10 minute":"@every 10m",
                "every 30 minute":"@every 30m",
                "every hourly":"@hourly"
            }

            schedule_button = st.button("SUBMIT",key='schedule_data_button')

            if schedule_button:
                schedule_data_convert = schedule_dict1.get(schedule_data)
                schedule_status_convert = schedule_dict1.get(schedule_status)
                schedule_alarm_convert = schedule_dict1.get(schedule_alarm)
                schedule_config(schedule_data_convert,schedule_status_convert,schedule_alarm_convert)

                st.success('SCHEDULE CONFIEMED', icon="✅")
                time.sleep(0.5)
                program_no = str(os.environ["NO"])
                restart_container(f"ofelia{program_no}")
                st.rerun()
            calculation_method()
        with tab4:
            st.header("DATAFLOW PREVIEW")
            dataflow_production_influx()
            dataflow_production_sql()
        with tab5:
            st.header("LOG")
            if os.environ["INIT_DB"] == "True":
                log_sqlserver(st,os.environ["SERVER"],os.environ["USER_LOGIN"],os.environ["PASSWORD"],os.environ["DATABASE"],os.environ["TABLE_LOG_1"])
            else:
                st.error('DB NOT INITIAL', icon="❌")    
        with tab6:
            config_initdb()


    elif password == str(os.environ["ST_PASSWORD_2"]):
        text_input_container.empty()
        add_column()

    else:
        st.toast('PASSWORD NOT CORRECT!', icon='❌')       

if __name__ == "__main__":
    dotenv_file = dotenv.find_dotenv()
    dotenv.load_dotenv(dotenv_file,override=True)
    main_layout()