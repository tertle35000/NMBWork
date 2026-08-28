"""
เลเยอร์ DB กลางสำหรับ config (SQLite) — ใช้ร่วมกันระหว่าง Api.py และสคริปต์ migrate/เขียนข้อมูล
เก็บทุก version เป็นประวัติ ไม่มีการ UPDATE ทับของเก่า มีแต่ INSERT แถวใหม่เพิ่มขึ้นเรื่อย ๆ
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "config.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """สร้างตารางถ้ายังไม่มี — เรียกได้ซ้ำ ๆ ปลอดภัย (idempotent)
    เรียกตอน Api.py เริ่มทำงาน เพื่อให้ deploy ไปเครื่องใหม่แล้ว schema พร้อมใช้ทันที
    (ไม่มีไฟล์ .json เป็น source แล้ว — ถ้า config.db ที่ deploy ไปเป็นไฟล์เปล่า ต้องเอาข้อมูลเข้าเอง
    ผ่าน insert_new_version() หรือ copy ไฟล์ config.db ที่มีข้อมูลอยู่แล้วไปแทนที่)
    """
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS config_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                div TEXT NOT NULL,
                process TEXT NOT NULL,
                version INTEGER NOT NULL,
                data TEXT NOT NULL,
                update_time TEXT NOT NULL,
                UNIQUE(div, process, version)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_config_versions_lookup ON config_versions(div, process, version)"
        )
        conn.commit()
    finally:
        conn.close()


def get_latest_config(div: str, process: str):
    """คืน sqlite3.Row (version, data) ของ version ล่าสุดของ div/process นั้น หรือ None ถ้าไม่เจอ"""
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT version, data FROM config_versions
            WHERE div = ? AND process = ?
            ORDER BY version DESC
            LIMIT 1
            """,
            (div, process),
        ).fetchone()
    finally:
        conn.close()


def insert_new_version(div: str, process: str, version: int, data_json: str, update_time: Optional[str] = None) -> None:
    """เพิ่ม version ใหม่ (ไม่ทับของเก่า) — ถ้า (div, process, version) ซ้ำจะ error เพราะมี UNIQUE constraint กันไว้"""
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO config_versions (div, process, version, data, update_time)
            VALUES (?, ?, ?, ?, ?)
            """,
            (div, process, version, data_json, update_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
    finally:
        conn.close()
