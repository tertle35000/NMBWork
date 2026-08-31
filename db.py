"""
เลเยอร์ DB กลางสำหรับ config (SQLite) — ใช้โดย Api.py (ui_streamlit.py คุยผ่าน HTTP ไปที่ Api.py อีกที ไม่ได้ import ไฟล์นี้ตรงๆ)
เก็บทุก api_version เป็นประวัติ ไม่มีการ UPDATE ทับของเก่า มีแต่ INSERT แถวใหม่เพิ่มขึ้นเรื่อย ๆ
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


def _column_names(conn: sqlite3.Connection, table: str) -> set:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def init_db() -> None:
    """สร้างตารางถ้ายังไม่มี — เรียกได้ซ้ำ ๆ ปลอดภัย (idempotent)
    เรียกตอน Api.py เริ่มทำงาน เพื่อให้ deploy ไปเครื่องใหม่แล้ว schema พร้อมใช้ทันที
    (ไม่มีไฟล์ .json เป็น source แล้ว — ถ้า config.db ที่ deploy ไปเป็นไฟล์เปล่า ต้อง copy ไฟล์
    config.db ที่มีข้อมูลอยู่แล้วไปแทนที่)
    """
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS config_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                div TEXT NOT NULL,
                process TEXT NOT NULL,
                api_version INTEGER NOT NULL,
                data TEXT NOT NULL,
                update_time TEXT NOT NULL,
                UNIQUE(div, process, api_version)
            )
            """
        )

        # เผื่อ config.db เก่าที่ยังมีคอลัมน์ชื่อ "version" (ก่อนเปลี่ยนชื่อ) -> rename ให้อัตโนมัติ
        # กันไม่ให้ข้อมูลเก่าหายตอน deploy โค้ดใหม่ทับ DB เดิม
        if "version" in _column_names(conn, "config_versions") and "api_version" not in _column_names(conn, "config_versions"):
            conn.execute("ALTER TABLE config_versions RENAME COLUMN version TO api_version")

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_config_versions_lookup ON config_versions(div, process, api_version)"
        )
        conn.commit()
    finally:
        conn.close()


def get_latest_config(div: str, process: str):
    """คืน sqlite3.Row (api_version, data) ของ api_version ล่าสุดของ div/process นั้น หรือ None ถ้าไม่เจอ"""
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT api_version, data FROM config_versions
            WHERE div = ? AND process = ?
            ORDER BY api_version DESC
            LIMIT 1
            """,
            (div, process),
        ).fetchone()
    finally:
        conn.close()


def insert_next_version(div: str, process: str, data_json: str, update_time: Optional[str] = None) -> int:
    """เพิ่ม config เป็น api_version ถัดไปโดยอัตโนมัติ (current max + 1, เริ่มที่ 1 ถ้ายังไม่มีของ div/process นี้เลย)
    ทำใน transaction เดียว (อ่าน MAX แล้ว INSERT ในการเชื่อมต่อเดียวกัน) กัน race condition ถ้ามีคนกดบันทึกพร้อมกันสองที่
    คืนค่า api_version ที่เพิ่งสร้าง
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT MAX(api_version) AS max_version FROM config_versions WHERE div = ? AND process = ?",
            (div, process),
        ).fetchone()
        next_version = (row["max_version"] or 0) + 1
        conn.execute(
            """
            INSERT INTO config_versions (div, process, api_version, data, update_time)
            VALUES (?, ?, ?, ?, ?)
            """,
            (div, process, next_version, data_json, update_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        return next_version
    finally:
        conn.close()


def list_departments_processes():
    """คืน list ของ (div, process) ที่มีอยู่ใน DB ทั้งหมด (distinct) เรียงตามชื่อ — ใช้โชว์ dropdown ใน UI"""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT DISTINCT div, process FROM config_versions ORDER BY div, process").fetchall()
        return [(r["div"], r["process"]) for r in rows]
    finally:
        conn.close()
