from fastapi import FastAPI, Query


app = FastAPI(title="ESP32 Configuration API")


CONFIG_ROWS = [
	{"Name": "RUN", "Address": "1", "Type": "1"},
	{"Name": "STOP", "Address": "2", "Type": "1"},
	{"Name": "ALARM", "Address": "3", "Type": "1"},
	{"Name": "Alarm1", "Address": "11", "Type": "2"},
	{"Name": "Alarm2", "Address": "12", "Type": "2"},
	{"Name": "Alarm3", "Address": "13", "Type": "2"},
	{"Name": "Alarm4", "Address": "14", "Type": "2"},
	{"Name": "Alarm5", "Address": "15", "Type": "2"},
	{"Name": "data1", "Address": "21", "Type": "3"},
	{"Name": "data2", "Address": "22", "Type": "3"},
	{"Name": "data3", "Address": "23", "Type": "3"},
	{"Name": "data4", "Address": "24", "Type": "3"},
	{"Name": "data5", "Address": "25", "Type": "3"},
	{"Name": "lot", "Address": "31", "Type": "4"},
	{"Name": "lot", "Address": "32", "Type": "4"},
	{"Name": "lot", "Address": "33", "Type": "4"},
	{"Name": "lot", "Address": "34", "Type": "4"},
	{"Name": "mod", "Address": "35", "Type": "5"},
	{"Name": "mod", "Address": "36", "Type": "5"},
	{"Name": "mod", "Address": "37", "Type": "5"},
	{"Name": "data6", "Address": "26", "Type": "3"},
	{"Name": "data7", "Address": "27", "Type": "3"},
	{"Name": "data8", "Address": "28", "Type": "3"},
]


@app.get("/api/config")
def get_config(mac: str = Query(..., min_length=1)):
	return CONFIG_ROWS[:50]
