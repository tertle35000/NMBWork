"""
Streamlit UI สำหรับแก้ไข/ดู config ของ ESP32 แต่ละ department/process
ต้องรัน Api.py (FastAPI) แยกไว้ก่อน ที่ http://localhost:8000

รันด้วย: streamlit run ui_streamlit.py
"""
import json

import pandas as pd
import requests
import streamlit as st

API_BASE_URL = "http://localhost:8000"

# ต้องตรงกับ MAX_ROWS/MAX_ADDRESS/MAX_PAYLOAD_BYTES/MAX_MQTT_DATA_PAYLOAD_BYTES ใน Api.py
# (แสดงผลฝั่ง UI ให้ user เห็นก่อนกด submit เพื่อ feedback ไว แต่ตัวที่ "เชื่อได้จริง" คือ backend validate
# อีกรอบเสมอ เผื่อ UI เพี้ยน/bypass — ดูคอมเมนต์อธิบายความหมายของแต่ละตัวใน Api.py)
MAX_ROWS = 250
MAX_ADDRESS = 256
MAX_PAYLOAD_BYTES = 4096
MAX_MQTT_DATA_PAYLOAD_BYTES = 1024  # ตรงกับ mqttClient.setBufferSize(1024) จริงใน MicMMS.cpp (ไม่ได้แตะฝั่ง ESP32)


def estimate_mqtt_data_payload_bytes(rows: list) -> int:
    """สำเนาของ estimate_mqtt_data_payload_bytes ใน Api.py — เอาไว้ feedback ฝั่ง UI ก่อนกด submit
    ต้องแก้พร้อมกันทั้งสองที่ถ้า logic ฝั่ง ESP32 (func1_Task) เปลี่ยน"""
    FIXED_OVERHEAD = 20
    RSSI_VALUE_WIDTH = 8
    TYPE3_VALUE_WIDTH = 5
    TYPE4_VALUE_WIDTH = 11
    FIELD_SYNTAX_OVERHEAD = 4

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
            i += 2
        elif row_type == "5":
            lot_chars += 2
            i += 1
        else:
            i += 1
    total += lot_chars
    return total

st.set_page_config(page_title="ESP32 Config Manager", layout="wide")
st.title("ESP32 Config Manager")

tab_edit, tab_view = st.tabs(["แก้ไข Config", "ดู Config"])


def fetch_config(department: str, process: str):
    try:
        r = requests.get(f"{API_BASE_URL}/api/config/{department}/{process}", timeout=5)
    except requests.exceptions.RequestException as e:
        return None, f"เชื่อมต่อ backend ไม่ได้: {e}"
    if r.status_code == 404:
        return None, None  # ยังไม่มี config สำหรับ department/process นี้ (ปกติ ไม่ใช่ error)
    if r.status_code != 200:
        return None, f"Backend ตอบ {r.status_code}: {r.text}"
    return r.json(), None


# ---------------------------------------------------------------- แก้ไข Config ----
with tab_edit:
    col1, col2 = st.columns(2)
    department = col1.text_input("Department", value="mic", key="edit_department")
    process = col2.text_input("Process", value="demo1", key="edit_process")

    if st.button("โหลด config ปัจจุบัน", key="load_edit"):
        payload, err = fetch_config(department, process)
        # ทุกครั้งที่กด "โหลด" ต้องเปลี่ยน key ของ data_editor ด้านล่างด้วย (เพิ่ม counter) ไม่งั้น
        # Streamlit จะจำ state เก่าของ editor ค้างไว้ (ผูกกับ key เดิม) ไม่ยอมแสดง/แก้ข้อมูลที่เพิ่งโหลดใหม่
        # ทั้งที่ st.session_state["edit_df"] เปลี่ยนไปแล้วจริง ๆ — เป็นสาเหตุที่กด "บันทึก" แล้วดูเหมือน
        # config.db ไม่อัปเดตตามที่โหลดมา (จริง ๆ คือมันบันทึกทับด้วยข้อมูลค้างของรอบก่อนหน้าแทน)
        st.session_state["edit_load_counter"] = st.session_state.get("edit_load_counter", 0) + 1
        if err:
            st.error(err)
        elif payload is None:
            st.info(f"ยังไม่มี config สำหรับ {department}/{process} — สร้างใหม่ได้เลย (เริ่มจากตารางว่างด้านล่าง)")
            st.session_state["edit_df"] = pd.DataFrame(columns=["Name", "Address", "Type"])
            st.session_state["edit_current_version"] = None
        else:
            st.success(f"โหลดสำเร็จ — api_version ปัจจุบัน: {payload['api_version']} ({len(payload['data'])} rows)")
            st.session_state["edit_df"] = pd.DataFrame(payload["data"])
            st.session_state["edit_current_version"] = payload["api_version"]

    if "edit_df" not in st.session_state:
        st.session_state["edit_df"] = pd.DataFrame(columns=["Name", "Address", "Type"])

    st.caption(
        f"ข้อจำกัด: สูงสุด {MAX_ROWS} rows / Address ต้องเป็นตัวเลข 0-{MAX_ADDRESS - 1} / "
        f"ขนาด config รวมต้องไม่เกิน {MAX_PAYLOAD_BYTES} byte / "
        f"ข้อความ MQTT topic 'data' ที่จะเกิดขึ้นต้องไม่เกิน {MAX_MQTT_DATA_PAYLOAD_BYTES} byte"
    )
    edited_df = st.data_editor(
        st.session_state["edit_df"],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Name": st.column_config.TextColumn("Name", required=True),
            "Address": st.column_config.TextColumn("Address", required=True, help="ตัวเลข 0-255"),
            "Type": st.column_config.TextColumn("Type", required=True),
        },
        key=f"config_editor_{st.session_state.get('edit_load_counter', 0)}",
    )

    if st.button("บันทึก (สร้าง version ใหม่)", type="primary", key="save_edit"):
        rows = edited_df.fillna("").astype(str).to_dict(orient="records")

        # เช็คฝั่ง UI ก่อนคร่าว ๆ เพื่อ feedback ไว (backend จะเช็คซ้ำอีกทีอยู่ดี เป็นตัวที่เชื่อถือได้จริง)
        problems = []
        if len(rows) == 0:
            problems.append("ต้องมีอย่างน้อย 1 row")
        if len(rows) > MAX_ROWS:
            problems.append(f"จำนวน row ({len(rows)}) เกิน {MAX_ROWS}")
        for row in rows:
            try:
                addr = int(row.get("Address", ""))
                if not (0 <= addr < MAX_ADDRESS):
                    problems.append(f"Address {addr} ของ '{row.get('Name')}' ต้องอยู่ในช่วง 0-{MAX_ADDRESS - 1}")
            except ValueError:
                problems.append(f"Address '{row.get('Address')}' ของ '{row.get('Name')}' ไม่ใช่ตัวเลข")
        payload_size = len(json.dumps({"api_version": 0, "data": rows}, ensure_ascii=False).encode("utf-8"))
        if payload_size >= MAX_PAYLOAD_BYTES:
            problems.append(f"ขนาด config ({payload_size} byte) เกิน {MAX_PAYLOAD_BYTES} byte")
        mqtt_estimate = estimate_mqtt_data_payload_bytes(rows)
        if mqtt_estimate >= MAX_MQTT_DATA_PAYLOAD_BYTES:
            problems.append(
                f"ข้อความ MQTT topic 'data' ที่จะเกิดขึ้นประมาณ {mqtt_estimate} byte เกิน "
                f"{MAX_MQTT_DATA_PAYLOAD_BYTES} byte — ESP32 จะไม่ publish ข้อมูลขึ้นเลยถ้าบันทึกแบบนี้"
            )

        if problems:
            for p in problems:
                st.error(p)
        else:
            try:
                r = requests.post(
                    f"{API_BASE_URL}/api/config/{department}/{process}",
                    json={"data": rows},
                    timeout=5,
                )
            except requests.exceptions.RequestException as e:
                st.error(f"เชื่อมต่อ backend ไม่ได้: {e}")
            else:
                if r.status_code == 200:
                    result = r.json()
                    st.success(f"บันทึกสำเร็จ! api_version ใหม่: {result['api_version']}")
                    st.session_state["edit_current_version"] = result["api_version"]
                else:
                    st.error(f"บันทึกไม่สำเร็จ ({r.status_code}): {r.json().get('detail', r.text)}")

# ---------------------------------------------------------------- ดู Config ----
with tab_view:
    col1, col2 = st.columns(2)
    v_department = col1.text_input("Department", value="mic", key="view_department")
    v_process = col2.text_input("Process", value="demo1", key="view_process")

    if st.button("ดู config", key="load_view"):
        payload, err = fetch_config(v_department, v_process)
        if err:
            st.error(err)
        elif payload is None:
            st.warning(f"ยังไม่มี config สำหรับ {v_department}/{v_process}")
        else:
            st.metric("api_version", payload["api_version"])
            st.metric("จำนวน rows", len(payload["data"]))
            st.dataframe(pd.DataFrame(payload["data"]), use_container_width=True)
