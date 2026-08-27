import json
import uvicorn
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Query


app = FastAPI(title="ESP32 Configuration API")


# ที่เก็บไฟล์ config จริง (ทีหลังค่อยย้ายไป DB) แต่ละไฟล์เป็น {"api_version": N, "data": [...]}
CONFIG_DIR = Path(__file__).parent / "mic"

# key = "department/process" (ตรงกับ dp_name "/Department/Process/" ฝั่ง ESP32) -> ชื่อไฟล์ config (ไม่มีนามสกุล)
CONFIG_FILE_MAP = {
	"mic/demo1": "config_A",
	"mic/demo2": "config_B",
	"mic/demo3": "config_C",
}


@app.get("/api/config/{department}/{process}")
def get_config(department: str, process: str, mac: Optional[str] = Query(None)):
	key = f"{department}/{process}"
	filename = CONFIG_FILE_MAP.get(key)
	if filename is None:
		raise HTTPException(status_code=404, detail=f"No config mapping for department/process: {key}")

	file_path = CONFIG_DIR / f"{filename}.json"
	if not file_path.exists():
		raise HTTPException(status_code=404, detail=f"Config file not found: {file_path.name}")

	with open(file_path, "r", encoding="utf-8") as f:
		return json.load(f)

# เพิ่มส่วนนี้ไว้ล่างสุดของไฟล์
if __name__ == "__main__":
    uvicorn.run("Api:app", host="0.0.0.0", port=8000, reload=True)