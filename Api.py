import json
import uvicorn
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from db import get_latest_config, init_db, insert_next_version


app = FastAPI(title="ESP32 Configuration API")

# สร้างตาราง config_versions ถ้ายังไม่มี (idempotent) — deploy ไปเครื่องใหม่แล้ว schema พร้อมใช้ทันที
# (ข้อมูลจริงอยู่ใน config.db เท่านั้น ไม่มีไฟล์ .json เป็น source แล้ว ต้องเอาไฟล์ config.db ไปเองตอน deploy)
init_db()

# ต้องตรงกับข้อจำกัดจริงฝั่ง ESP32 (master_code/config.h, MicMMS.cpp) ไม่งั้น UI จะยอมให้เซฟ config ที่
# ESP32 parse ไม่ผ่านได้ — MAX_ROWS ตรงกับ MAX_DEF_TB_ROWS (ตัว def_tb array เอง เป็นเพดานจริงที่แก้ไม่ได้
# ง่าย ๆ เพราะเป็น fixed-size array) และ MAX_ADDRESS ตรงกับ "address < 256" ใน flow
#
# MAX_PAYLOAD_BYTES: ฝั่ง ESP32 (loadDefTbFromJson()) เปลี่ยนจาก StaticJsonDocument (คงที่บน stack) เป็น
# DynamicJsonDocument (heap, จองตามขนาด jsonPayload จริง สูงสุด 65536 byte) แล้ว ไม่ติดเพดานตายตัวแคบ ๆ
# อีกต่อไป — ตั้งเลขนี้ไว้กว้าง ๆ พอเผื่อ 250 rows (MAX_ROWS) แบบ worst-case (ชื่อยาวหน่อย) ได้สบาย โดยยังเหลือ
# margin ให้ ESP32 มากพอที่จะ parse ผ่านจริง (สูตรฝั่ง ESP32 คือ capacity = raw_len*2 + 1024 เพดาน 65536
# ดังนั้น raw_len ต้อง <= 32256 ถึงจะยังไม่ชนเพดานนั้น — ตั้งไว้ต่ำกว่านั้นอีกหน่อยเผื่อ margin)
#
# หมายเหตุ: ตั้งใจไม่เช็คขนาดข้อความ MQTT topic "data" ที่จะเกิดขึ้นจริงแล้ว (ดู commit ก่อนหน้า) — ช่วงนี้ยังไม่ได้
# ต่อ GOT/PLC จริง กำลังแค่ทดสอบว่า ESP32 ช้าลงมั้ยตอน config มีเยอะ ถ้า config ที่บันทึกได้ทำให้ข้อความ MQTT
# เกิน buffer ของ ESP32 (mqttClient.setBufferSize / StaticJsonDocument ของ json_1) จะ publish ไม่ขึ้นเงียบ ๆ
# — ถ้าเกิดเคสนี้ตอนใช้งานจริง ให้ไปขยับ buffer ฝั่ง ESP32 เอาหน้างานตามที่คุยกันไว้
MAX_ROWS = 250
MAX_ADDRESS = 256
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
		if not (0 <= addr < MAX_ADDRESS):
			raise HTTPException(status_code=400, detail=f"Address {addr} ของ '{row.Name}' ต้องอยู่ในช่วง 0-{MAX_ADDRESS - 1}")

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
