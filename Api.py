import json
import uvicorn
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from db import get_config_version, get_latest_config, init_db, insert_next_version, list_config_versions


app = FastAPI(title="ESP32 Configuration API")

# สร้างตาราง config_versions ถ้ายังไม่มี (idempotent) — deploy ไปเครื่องใหม่แล้ว schema พร้อมใช้ทันที
# (ข้อมูลจริงอยู่ใน config.db เท่านั้น ไม่มีไฟล์ .json เป็น source แล้ว ต้องเอาไฟล์ config.db ไปเองตอน deploy)
init_db()

# ต้องตรงกับข้อจำกัดจริงฝั่ง ESP32 (master_code/config.h, MicMMS.cpp) ไม่งั้น UI จะยอมให้เซฟ config ที่
# ESP32 parse ไม่ผ่านได้ — MAX_ROWS ตรงกับ MAX_DEF_TB_ROWS (ตัว def_tb array เอง เป็นเพดานจริงที่แก้ไม่ได้
# ง่าย ๆ เพราะเป็น fixed-size array)
#
# MIN_ADDRESS/MAX_ADDRESS: *** ไม่ใช่แค่ "address < 256" ตาม flow เดิมอีกต่อไป *** เช็คโค้ดจริงแล้วพบว่า
# ทุก row (ไม่ว่า Type ไหน) ถูกเอา Address ไปทำ index อ่านค่าจาก got_data[] ตรง ๆ
# (def_tb[i][3] = got_data[Address-1] ใน modbus_Task ของ MicMMS.cpp) ซึ่งเป็น array ขนาดแค่ num_got_data
# ช่อง (config.h) — Address=0 หรือ Address>num_got_data ทำให้อ่านนอกขอบ array (undefined behavior) ได้ค่าเลอะ
# ที่ดูเหมือนข้อมูลจริงแต่ไม่ใช่เลย (เจอเคสนี้จริงตอนเทส 250 rows) ฝั่ง ESP32 เพิ่ง fix เพิ่ม bounds check กันไว้แล้ว
# แต่ก็ยังต้องเช็คตั้งแต่ต้นทางตรงนี้ด้วย เพื่อไม่ให้ user กรอก Address ที่ไม่มีความหมายอะไรเลยได้ตั้งแต่แรก
MIN_ADDRESS = 1
MAX_ADDRESS = 255  # ต้องตรงกับ num_got_data ใน config.h เสมอ (255 = เพดานสูงสุดของ uint8_t พอดี)
#
# MAX_PAYLOAD_BYTES: ฝั่ง ESP32 (loadDefTbFromJson()) เปลี่ยนจาก StaticJsonDocument (คงที่บน stack) เป็น
# DynamicJsonDocument (heap, จองตามขนาด jsonPayload จริง สูงสุด 65536 byte) แล้ว ไม่ติดเพดานตายตัวแคบ ๆ
# อีกต่อไป — ตั้งเลขนี้ไว้กว้าง ๆ พอเผื่อ 250 rows (MAX_ROWS) แบบ worst-case (ชื่อยาวหน่อย) ได้สบาย โดยยังเหลือ
# margin ให้ ESP32 มากพอที่จะ parse ผ่านจริง (สูตรฝั่ง ESP32 คือ capacity = raw_len*2 + 1024 เพดาน 65536
# ดังนั้น raw_len ต้อง <= 32256 ถึงจะยังไม่ชนเพดานนั้น — ตั้งไว้ต่ำกว่านั้นอีกหน่อยเผื่อ margin)
#
# เกิน buffer ของ ESP32 (mqttClient.setBufferSize / StaticJsonDocument ของ json_1) จะ publish ไม่ขึ้นเงียบ ๆ
# — ถ้าเกิดเคสนี้ตอนใช้งานจริง ให้ไปขยับ buffer ฝั่ง ESP32 เอาหน้างานตามที่คุยกันไว้
MAX_ROWS = 250
MAX_PAYLOAD_BYTES = 30000


class ConfigRow(BaseModel):
	Name: str
	Address: str
	Type: str


class ConfigUpdateRequest(BaseModel):
	data: List[ConfigRow]


@app.get("/api/config/{department}/{process}")
def get_config(department: str, process: str, mac: Optional[str] = Query(None)):
	row = get_latest_config(department, process)
	if row is None:
		raise HTTPException(status_code=404, detail=f"No config found for department/process: {department}/{process}")

	return {"api_version": row["api_version"], "data": json.loads(row["data"])}


@app.get("/api/config/{department}/{process}/history")
def get_config_history(department: str, process: str):
	"""คืนทุก api_version ของ department/process นี้ (ใหม่สุดก่อน) แบบไม่รวม data เต็ม ๆ — ใช้โชว์ list ใน
	history tab ของ UI ก่อน แล้วค่อยเรียก /history/{version} ต่อเฉพาะ version ที่ user คลิกดู
	"""
	versions = list_config_versions(department, process)
	if not versions:
		raise HTTPException(status_code=404, detail=f"No config found for department/process: {department}/{process}")
	return {"versions": versions}


@app.get("/api/config/{department}/{process}/history/{version}")
def get_config_history_version(department: str, process: str, version: int):
	"""คืนเนื้อหาเต็ม ๆ ของ api_version ที่ระบุเจาะจง — ใช้เปิดดู/เทียบ diff/rollback ไป version เก่าใน UI
	(rollback ทำโดย UI ดึงข้อมูลจาก endpoint นี้ แล้วยิงไป POST /api/config/{department}/{process} ตามปกติ
	เพื่อสร้างเป็น version ใหม่ต่อท้าย — ไม่มี endpoint แยกสำหรับ rollback โดยเฉพาะ เพราะใช้ endpoint POST เดิมได้เลย)
	"""
	row = get_config_version(department, process, version)
	if row is None:
		raise HTTPException(status_code=404, detail=f"No api_version {version} found for department/process: {department}/{process}")
	return {"api_version": row["api_version"], "data": json.loads(row["data"]), "update_time": row["update_time"]}


@app.post("/api/config/{department}/{process}")
def update_config(department: str, process: str, payload: ConfigUpdateRequest):
	if len(payload.data) == 0:
		raise HTTPException(status_code=400, detail="ต้องมีอย่างน้อย 1 row")
	if len(payload.data) > MAX_ROWS:
		raise HTTPException(status_code=400, detail=f"จำนวน row ({len(payload.data)}) เกินที่ ESP32 รองรับ (MAX_DEF_TB_ROWS={MAX_ROWS})")

	for row in payload.data:
		try:
			addr = int(row.Address)
		except ValueError:
			raise HTTPException(status_code=400, detail=f"Address '{row.Address}' ของ '{row.Name}' ไม่ใช่ตัวเลข")
		if not (MIN_ADDRESS <= addr <= MAX_ADDRESS):
			raise HTTPException(status_code=400, detail=f"Address {addr} ของ '{row.Name}' ต้องอยู่ในช่วง {MIN_ADDRESS}-{MAX_ADDRESS}")

	data_list = [row.model_dump() for row in payload.data]
	data_json = json.dumps(data_list, ensure_ascii=False)

	# เช็คขนาด response เต็ม ๆ ที่ ESP32 จะได้รับจริง ({"api_version": N, "data": [...]}) ไม่ใช่แค่ data เฉย ๆ
	full_payload_size = len(json.dumps({"api_version": 0, "data": data_list}, ensure_ascii=False).encode("utf-8"))
	if full_payload_size >= MAX_PAYLOAD_BYTES:
		raise HTTPException(status_code=400, detail=f"ขนาด config ({full_payload_size} byte) เกิน {MAX_PAYLOAD_BYTES} byte")

	new_version = insert_next_version(department, process, data_json)
	return {"api_version": new_version, "data": data_list}

# เพิ่มส่วนนี้ไว้ล่างสุดของไฟล์
if __name__ == "__main__":
    uvicorn.run("Api:app", host="0.0.0.0", port=8000, reload=True)
