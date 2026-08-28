"""
สคริปต์ migrate ครั้งเดียว: อ่าน config เก่าจากไฟล์ mic/*.json (ตาม CONFIG_FILE_MAP เดิม)
ยัดเข้า config.db (SQLite) เป็น version เริ่มต้นของแต่ละ div/process
รันครั้งเดียวตอนย้ายมาใช้ DB (หรือรันซ้ำได้ปลอดภัย เพราะเช็คก่อนว่ามี version นั้นอยู่แล้วหรือยัง)

ใช้งาน: python migrate_config_files.py
"""
import json
from pathlib import Path

from db import get_latest_config, init_db, insert_new_version

CONFIG_DIR = Path(__file__).parent / "mic"

# ตรงกับ CONFIG_FILE_MAP เดิมใน Api.py ก่อนย้ายมาใช้ DB
FILE_MAP = {
    ("mic", "demo1"): "config_A",
    ("mic", "demo2"): "config_B",
    ("mic", "demo3"): "config_C",
}


def migrate() -> None:
    init_db()

    for (div, process), filename in FILE_MAP.items():
        file_path = CONFIG_DIR / f"{filename}.json"
        if not file_path.exists():
            print(f"[skip] {file_path.name} ไม่พบไฟล์")
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        version = int(payload["api_version"])
        data_json = json.dumps(payload["data"], ensure_ascii=False)

        existing = get_latest_config(div, process)
        if existing is not None and existing["version"] >= version:
            print(f"[skip] {div}/{process} มี version {existing['version']} อยู่แล้วใน DB (>= {version} จากไฟล์)")
            continue

        insert_new_version(div, process, version, data_json)
        print(f"[ok] migrate {div}/{process} <- {file_path.name} (version {version}, {len(payload['data'])} rows)")

    print("Migrate เสร็จแล้ว — ไฟล์ .json เดิมยังอยู่ครบ (ไม่ได้ลบ) แต่ Api.py จะไม่อ่านจากไฟล์อีกต่อไป")


if __name__ == "__main__":
    migrate()
