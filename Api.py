import json
import uvicorn
from typing import Optional
from fastapi import FastAPI, HTTPException, Query

from db import get_latest_config, init_db


app = FastAPI(title="ESP32 Configuration API")

# สร้างตาราง config_versions ถ้ายังไม่มี (idempotent) — deploy ไปเครื่องใหม่แล้ว schema พร้อมใช้ทันที
# (ข้อมูลจริงอยู่ใน config.db เท่านั้น ไม่มีไฟล์ .json เป็น source แล้ว ต้องเอาไฟล์ config.db ไปเองตอน deploy)
init_db()


@app.get("/api/config/{department}/{process}")
def get_config(department: str, process: str, mac: Optional[str] = Query(None)):
	row = get_latest_config(department, process)
	if row is None:
		raise HTTPException(status_code=404, detail=f"No config found for department/process: {department}/{process}")

	return {"api_version": row["version"], "data": json.loads(row["data"])}

# เพิ่มส่วนนี้ไว้ล่างสุดของไฟล์
if __name__ == "__main__":
    uvicorn.run("Api:app", host="0.0.0.0", port=8000, reload=True)
