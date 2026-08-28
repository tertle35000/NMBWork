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
# ESP32 parse ไม่ผ่านได้ — MAX_ROWS ตรงกับ MAX_DEF_TB_ROWS, MAX_ADDRESS ตรงกับ "address < 256" ใน flow
#
# หมายเหตุ: มี "4096" อยู่ 2 ที่ที่ไม่เกี่ยวกันเลย อย่าสับสน —
#   1) MAX_PAYLOAD_BYTES ด้านล่าง = ขนาดไฟล์ config ดิบที่ ESP32 ต้อง parse ตอนโหลดจาก API (HTTPClient +
#      loadDefTbFromJson) — ตอนนี้แก้ฝั่ง ESP32 แล้ว (StaticJsonDocument<4096> ใน loadDefTbFromJson())
#      *** ข้อควรระวัง: 4096 คือพื้นที่ผลลัพธ์หลัง parse (มี overhead ต่อ field + string ถูกก็อปปี้ซ้ำ)
#      ไม่ใช่ขนาด jsonPayload ดิบ 1:1 ดังนั้น config ที่ raw byte ใกล้ 4096 พอดีมีโอกาส parse ไม่ผ่านจริง
#      ถ้าเกิดขึ้น ESP32 จะ fallback ไปใช้ cache เก่าแบบไม่ crash (ดูคอมเมนต์ที่ loadDefTbFromJson())
#      ต้องดู Serial log "callAPI stack remaining" บนบอร์ดจริงหลัง flash ด้วยว่าเหลือขอบพอมั้ย ***
#   2) MAX_MQTT_DATA_PAYLOAD_BYTES = ขนาดข้อความ MQTT topic "data" ที่ func1_Task จะ publish ขึ้นจริง
#      (คนละ path กับข้อ 1 เลย — ไม่ผ่าน HTTPClient เลยด้วยซ้ำ) ตั้งใจ**ไม่แตะฝั่ง ESP32**
#      (mqttClient.setBufferSize(1024) + StaticJsonDocument<300> ของ json_1 ใน MicMMS.cpp ปล่อยไว้ตามเดิม) —
#      ค่านี้จึงต้องตรงกับ 1024 ที่ ESP32 มีจริงตอนนี้ ไม่ใช่เพดานที่เราอยากได้ ถ้าหน้างานต้องการส่งข้อมูล
#      เยอะกว่านี้จริง ๆ ให้ทีมช่างไปแก้ทั้งสองจุดใน MicMMS.cpp เอง แล้วค่อยขยับเลขนี้ให้ตรงกันทีหลัง
MAX_ROWS = 250
MAX_ADDRESS = 256
MAX_PAYLOAD_BYTES = 4096
MAX_MQTT_DATA_PAYLOAD_BYTES = 1024


def estimate_mqtt_data_payload_bytes(rows: List[dict]) -> int:
	"""ประมาณขนาด (byte) ของข้อความ MQTT topic "data" ที่ func1_Task ใน MicMMS.cpp จะ publish จริงจาก config นี้
	เป็นค่าประมาณแบบเผื่อเหลือ (โอนไปทางประเมินสูงไว้ก่อน) ไม่ใช่การจำลองไบต์ต่อไบต์ เพราะค่า register จริง
	ขึ้นกับข้อมูล Modbus ณ ขณะนั้น ไม่รู้ล่วงหน้า — อ้างอิงจากลอจิกใน func1_Task:
	  Type "3" -> 1 field ต่อ 1 row (uint16 register, สูงสุด 5 หลัก)
	  Type "4" -> 1 field ต่อ 2 row (จับคู่ต่อเนื่องเหมือน def_tb[j]/def_tb[j+1], รวมเป็น int32 สูงสุด 11 หลัก)
	  Type "5" -> ไม่แยก field แต่สะสมเข้าคีย์ "lot" คีย์เดียว (2 ตัวอักษรต่อ 1 row)
	"""
	FIXED_OVERHEAD = 20  # {"rssi":...,"lot":"..."} braces/คีย์ตายตัว
	RSSI_VALUE_WIDTH = 8  # เช่น "-100.00"
	TYPE3_VALUE_WIDTH = 5  # uint16 register เดี่ยว: "65535"
	TYPE4_VALUE_WIDTH = 11  # int32 รวม 2 register: "-2147483648"
	FIELD_SYNTAX_OVERHEAD = 4  # "":,  ต่อ 1 field (quote 2 ตัว + colon + comma)

	total = FIXED_OVERHEAD + RSSI_VALUE_WIDTH
	lot_chars = 0
	i = 0
	while i < len(rows):
		row_type = rows[i].get("Type")
		name = rows[i].get("Name", "")
		if row_type == "3":
			total += len(name) + TYPE3_VALUE_WIDTH + FIELD_SYNTAX_OVERHEAD
			i += 1
		elif row_type == "4":
			total += len(name) + TYPE4_VALUE_WIDTH + FIELD_SYNTAX_OVERHEAD
			i += 2  # จับคู่ 2 row เหมือน ESP32 (def_tb[j] กับ def_tb[j+1])
		elif row_type == "5":
			lot_chars += 2
			i += 1
		else:
			i += 1  # type "1"/"2" (status/alarm) ไม่ทำให้ topic "data" โต ไม่ต้องนับ
	total += lot_chars
	return total


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

	# เช็คแยกอีกชั้น: ต่อให้ config parse ผ่าน แต่ตอน publish ขึ้น MQTT topic "data" จริง ข้อความอาจใหญ่เกิน
	# buffer ของ ESP32 แล้วเงียบ ๆ ไม่ถูกส่งขึ้นเลย (publish() คืน false เฉย ๆ ไม่มี error ให้เห็น) — เช็คดักไว้ตรงนี้
	mqtt_payload_estimate = estimate_mqtt_data_payload_bytes(data_list)
	if mqtt_payload_estimate >= MAX_MQTT_DATA_PAYLOAD_BYTES:
		raise HTTPException(
			status_code=400,
			detail=(
				f"ข้อความ MQTT topic 'data' ที่จะเกิดจาก config นี้ประมาณ {mqtt_payload_estimate} byte "
				f"เกิน {MAX_MQTT_DATA_PAYLOAD_BYTES} byte ที่ ESP32 รองรับ — config จะบันทึกได้แต่ ESP32 จะไม่ publish "
				f"ข้อมูลขึ้น MQTT เลย ต้องลดจำนวน row type 3/4/5 ลง หรือให้ทีมช่างไปขยับ buffer ใน MicMMS.cpp เอง"
			),
		)

	new_version = insert_next_version(department, process, data_json)
	return {"api_version": new_version, "data": data_list}

# เพิ่มส่วนนี้ไว้ล่างสุดของไฟล์
if __name__ == "__main__":
    uvicorn.run("Api:app", host="0.0.0.0", port=8000, reload=True)
