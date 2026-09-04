"""
Streamlit UI สำหรับแก้ไข/ดู config ของ ESP32 แต่ละ department/process
ต้องรัน Api.py (FastAPI) แยกไว้ก่อน — จะรันเครื่องเดียวกันหรือคนละเครื่องกับ UI นี้ก็ได้
(ปรับ URL ได้จากช่อง sidebar ตอนรัน หรือ set env var CONFIG_API_URL ไว้ล่วงหน้าก็ได้)

รันด้วย: streamlit run ui_streamlit.py
"""
import json
import os

import bcrypt
import pandas as pd
import requests
import streamlit as st

DEFAULT_API_BASE_URL = os.environ.get("CONFIG_API_URL", "http://localhost:8000")

# ต้องตรงกับ MAX_ROWS/MIN_ADDRESS/MAX_ADDRESS/MAX_PAYLOAD_BYTES ใน Api.py (แสดงผลฝั่ง UI ให้ user เห็นก่อนกด
# submit เพื่อ feedback ไว แต่ตัวที่ "เชื่อได้จริง" คือ backend validate อีกรอบเสมอ เผื่อ UI เพี้ยน/bypass)
# MIN/MAX_ADDRESS: ต้องตรงกับ num_got_data ใน config.h (ไม่ใช่ 256) เพราะทุก row ถูกเอา Address ไปทำ index
# อ่าน got_data[] ตรง ๆ ใน modbus_Task — Address นอกช่วงนี้ทำให้อ่านนอกขอบ array ได้ค่าเลอะ (ดูรายละเอียดใน Api.py)
MAX_ROWS = 250
MIN_ADDRESS = 1
MAX_ADDRESS = 255  # ต้องตรงกับ num_got_data ใน config.h เสมอ
MAX_PAYLOAD_BYTES = 30000  # ESP32 เปลี่ยนไปใช้ DynamicJsonDocument (heap) แล้ว ไม่ติดเพดาน 4096 เดิม

# เช็คขนาดข้อความ MQTT topic "data" ที่ func1_Task จะ publish จริง — แยกเพดานจาก MAX_PAYLOAD_BYTES ด้านบน
# (คนละ path กันเลย ไม่ผ่าน HTTPClient/loadDefTbFromJson) ต้องตรงกับ mqttClient.setBufferSize(4096) และ
# StaticJsonDocument<4096> json_1 ใน func1_Task (MicMMS.cpp:141,258) — เช็คแค่ฝั่ง UI ก่อน ยังไม่เพิ่มใน Api.py
MAX_MQTT_DATA_PAYLOAD_BYTES = 4096


def estimate_mqtt_data_payload_bytes(rows: list) -> int:
    """ประมาณขนาด (byte) ของข้อความ MQTT topic "data" ที่ func1_Task ใน MicMMS.cpp จะ publish จริงจาก config นี้
    เป็นค่าประมาณแบบเผื่อเหลือ (โอนไปทางประเมินสูงไว้ก่อน) ไม่ใช่การจำลองไบต์ต่อไบต์ เพราะค่า register จริง
    ขึ้นกับข้อมูล Modbus ณ ขณะนั้น ไม่รู้ล่วงหน้า — อ้างอิงจากลอจิกใน func1_Task:
      Type "1"/"2" (status/alarm 0-1) -> ไม่ทำให้ topic "data" โต ไม่ต้องนับ
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

st.set_page_config(page_title="ESP32 Config Manager", layout="wide")


def check_login() -> bool:
    """เช็ก login ก่อนเข้าหน้าหลัก — เก็บสถานะไว้ใน session_state (login ค้างไว้จนกว่าจะปิด/รีเฟรช session)
    credential เทียบกับ .streamlit/secrets.toml (ไฟล์นี้ .gitignore ไว้ ไม่ขึ้น git) — ดูตัวอย่างการตั้งค่า
    ที่ .streamlit/secrets.toml.example ถ้ายังไม่เคยสร้างไฟล์จริง
    """
    if st.session_state.get("authenticated"):
        return True

    # จำกัดความกว้างของฟอร์ม login ด้วย column แบ่ง 3 ส่วน (ซ้าย/กลาง/ขวา) แล้ววางฟอร์มไว้เฉพาะคอลัมน์กลาง
    # เผื่อ layout="wide" ของหน้าหลัก ไม่งั้นฟอร์มจะยืดเต็มความกว้างจอ
    st.write("")
    st.write("")
    _, center_col, _ = st.columns([1, 1.1, 1])
    with center_col:
        st.title("เข้าสู่ระบบ")
        with st.container(border=True):
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("เข้าสู่ระบบ", use_container_width=True)

        if submitted:
            try:
                expected_username = st.secrets["auth"]["username"]
                expected_hash = st.secrets["auth"]["password_hash"].encode("utf-8")
            except (KeyError, FileNotFoundError):
                st.error(
                    "ยังไม่ได้ตั้งค่า .streamlit/secrets.toml — คัดลอกจาก "
                    ".streamlit/secrets.toml.example แล้วใส่ username/password ที่ต้องการ"
                )
                return False

            # ใช้ bcrypt.checkpw เทียบ hash (กัน timing attack ในตัวอยู่แล้ว) — เช็ค username ตรง ๆ
            # เพราะไม่ใช่ secret ที่ต้องกันเดา (ต่างจาก password)
            if username == expected_username and bcrypt.checkpw(password.encode("utf-8"), expected_hash):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("username หรือ password ไม่ถูกต้อง")

    return False


if not check_login():
    st.stop()

st.title("ESP32 Config Manager")

# ให้ปรับ backend URL ได้จากหน้าเว็บเลย เผื่อสลับไปมาระหว่างรัน Api.py เครื่องเดียวกับ UI (localhost)
# กับรันคนละเครื่อง (เช่น backend จริงอยู่ที่ .204 ส่วน UI รันเครื่องนี้)
with st.sidebar:
    st.subheader("Backend connection")
    API_BASE_URL = st.text_input("API base URL", value=DEFAULT_API_BASE_URL).rstrip("/")
    try:
        health = requests.get(f"{API_BASE_URL}/docs", timeout=3)
        st.success(f"เชื่อม backend ได้ ({API_BASE_URL})")
    except requests.exceptions.RequestException:
        st.error(f"เชื่อม backend ที่ {API_BASE_URL} ไม่ได้ — เช็ค Api.py รันอยู่มั้ย/firewall เครื่องปลายทาง")

    st.divider()
    if st.button("ออกจากระบบ"):
        st.session_state["authenticated"] = False
        st.rerun()

tab_edit, tab_view, tab_history = st.tabs(["✏️ แก้ไข Config", "🔍 ดู Config", "📜 ประวัติ (History)"])


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


def fetch_config_history(department: str, process: str):
    """คืน list ของ {api_version, update_time} เรียงใหม่สุดก่อน — ไม่รวมเนื้อหา data (เรียก fetch_config_version ต่อ)"""
    try:
        r = requests.get(f"{API_BASE_URL}/api/config/{department}/{process}/history", timeout=5)
    except requests.exceptions.RequestException as e:
        return None, f"เชื่อมต่อ backend ไม่ได้: {e}"
    if r.status_code == 404:
        return None, None  # ยังไม่มี config สำหรับ department/process นี้ (ปกติ ไม่ใช่ error)
    if r.status_code != 200:
        return None, f"Backend ตอบ {r.status_code}: {r.text}"
    return r.json()["versions"], None


def fetch_config_version(department: str, process: str, version: int):
    """คืนเนื้อหาเต็ม ๆ ({api_version, data, update_time}) ของ api_version ที่ระบุเจาะจง"""
    try:
        r = requests.get(f"{API_BASE_URL}/api/config/{department}/{process}/history/{version}", timeout=5)
    except requests.exceptions.RequestException as e:
        return None, f"เชื่อมต่อ backend ไม่ได้: {e}"
    if r.status_code != 200:
        return None, f"Backend ตอบ {r.status_code}: {r.text}"
    return r.json(), None


def diff_config_rows(old_rows: list, new_rows: list):
    """เทียบ config 2 version กัน คีย์ด้วย Address (ไม่ใช่ Name!) เพราะ Name ไม่ได้การันตีว่าไม่ซ้ำ — Type "4"
    (จับคู่ 2 row ต่อเนื่อง) กับ Type "5" (สะสมเข้าคีย์ "lot" เดียว) ตั้งใจให้หลายแถวใช้ Name ซ้ำกันได้ตามปกติ
    (ดู estimate_mqtt_data_payload_bytes ด้านบน) ส่วน Address คือ slot ทางกายภาพของ modbus register จริง ๆ
    จึงเป็น identity ที่ไม่ซ้ำของแต่ละแถวในทางปฏิบัติ
    คืน (added_df, removed_df, changed_df) — changed_df มีคอลัมน์ Address/Name เก่า/Name ใหม่/Type เก่า/Type ใหม่
    เฉพาะแถวที่ Name หรือ Type ต่างกันจริง (Address เดิมที่ค่าอื่นเหมือนกันทุกอย่างจะไม่ถูกนับว่าเปลี่ยน)
    """
    old_df = pd.DataFrame(old_rows) if old_rows else pd.DataFrame(columns=["Name", "Address", "Type"])
    new_df = pd.DataFrame(new_rows) if new_rows else pd.DataFrame(columns=["Name", "Address", "Type"])

    old_addrs = set(old_df["Address"])
    new_addrs = set(new_df["Address"])

    added_df = new_df[new_df["Address"].isin(new_addrs - old_addrs)].reset_index(drop=True)
    removed_df = old_df[old_df["Address"].isin(old_addrs - new_addrs)].reset_index(drop=True)

    common_addrs = old_addrs & new_addrs
    merged = old_df[old_df["Address"].isin(common_addrs)].merge(
        new_df[new_df["Address"].isin(common_addrs)], on="Address", suffixes=("_เก่า", "_ใหม่")
    )
    changed_df = merged[
        (merged["Name_เก่า"] != merged["Name_ใหม่"]) | (merged["Type_เก่า"] != merged["Type_ใหม่"])
    ].reset_index(drop=True)

    return added_df, removed_df, changed_df


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
            loaded_payload_size = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            loaded_mqtt_estimate = estimate_mqtt_data_payload_bytes(payload["data"])
            st.caption(
                # f"ขนาด config: {loaded_payload_size} byte (เพดาน {MAX_PAYLOAD_BYTES}) / "
                f"ขนาด MQTT topic 'data' โดยประมาณ: {loaded_mqtt_estimate} byte (เพดาน {MAX_MQTT_DATA_PAYLOAD_BYTES})"
            )
            st.session_state["edit_df"] = pd.DataFrame(payload["data"])
            st.session_state["edit_current_version"] = payload["api_version"]

    if "edit_df" not in st.session_state:
        st.session_state["edit_df"] = pd.DataFrame(columns=["Name", "Address", "Type"])

    st.caption(
        f"ข้อจำกัด: สูงสุด {MAX_ROWS} rows / Address ต้องเป็นตัวเลข {MIN_ADDRESS}-{MAX_ADDRESS} / "
        # f"ขนาด config รวมต้องไม่เกิน {MAX_PAYLOAD_BYTES} byte / "
        f"ข้อความ MQTT topic 'data' ที่จะเกิดขึ้นต้องไม่เกิน {MAX_MQTT_DATA_PAYLOAD_BYTES} byte"
    )
    edited_df = st.data_editor(
        st.session_state["edit_df"],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Name": st.column_config.TextColumn("Name", required=True),
            "Address": st.column_config.TextColumn("Address", required=True, help=f"ตัวเลข {MIN_ADDRESS}-{MAX_ADDRESS}"),
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
        for row_num, row in enumerate(rows, start=1):
            name = row.get("Name", "").strip()
            address = row.get("Address", "").strip()
            type_ = row.get("Type", "").strip()

            # เช็คก่อนว่ากรอกครบทั้ง 3 ช่องมั้ย — ถ้าไม่ครบ บอกเลขแถว+ช่องที่ขาด แล้วข้าม ไม่ต้องเช็ค Address
            # เป็นตัวเลขต่อ (เดี๋ยวจะซ้ำซ้อนกับข้อความ "ไม่ใช่ตัวเลข" ของ Address ว่างเปล่า)
            missing = []
            if not name:
                missing.append("Name")
            if not address:
                missing.append("Address")
            if not type_:
                missing.append("Type")
            if missing:
                problems.append(f"แถวที่ {row_num}: กรอกไม่ครบ ({', '.join(missing)})")
                continue

            try:
                addr = int(address)
                if not (MIN_ADDRESS <= addr <= MAX_ADDRESS):
                    problems.append(f"แถวที่ {row_num}: Address {addr} ของ '{name}' ต้องอยู่ในช่วง {MIN_ADDRESS}-{MAX_ADDRESS}")
            except ValueError:
                problems.append(f"แถวที่ {row_num}: Address '{address}' ของ '{name}' ไม่ใช่ตัวเลข")
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
                    st.caption(
                        f"ขนาด config: {payload_size} byte (เพดาน {MAX_PAYLOAD_BYTES}) / "
                        f"ขนาด MQTT topic 'data' โดยประมาณ: {mqtt_estimate} byte (เพดาน {MAX_MQTT_DATA_PAYLOAD_BYTES})"
                    )
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
            view_payload_size = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            view_mqtt_estimate = estimate_mqtt_data_payload_bytes(payload["data"])
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("api_version", payload["api_version"])
            col_m2.metric("จำนวน rows", len(payload["data"]))
            # col_m4.metric("ขนาด config (byte)", view_payload_size, help=f"เพดาน {MAX_PAYLOAD_BYTES} byte")
            col_m3.metric("MQTT 'data' โดยประมาณ (byte)", view_mqtt_estimate, help=f"เพดาน {MAX_MQTT_DATA_PAYLOAD_BYTES} byte")
            st.dataframe(pd.DataFrame(payload["data"]), use_container_width=True)

# ---------------------------------------------------------------- ประวัติ (History) ----
with tab_history:
    col1, col2 = st.columns(2)
    h_department = col1.text_input("Department", value="mic", key="history_department")
    h_process = col2.text_input("Process", value="demo1", key="history_process")

    if st.button("โหลดประวัติ", key="load_history"):
        versions, err = fetch_config_history(h_department, h_process)
        # ล้าง state ของรอบก่อนหน้าทุกครั้งที่โหลดใหม่ (คนละ department/process กันได้ ไม่งั้น dropdown/เนื้อหา
        # ที่เคยดูค้างของ department/process เดิมจะโผล่มาปนกับอันใหม่)
        st.session_state.pop("history_view_payload", None)
        if err:
            st.error(err)
        elif versions is None:
            st.warning(f"ยังไม่มี config สำหรับ {h_department}/{h_process}")
            st.session_state["history_versions"] = None
        else:
            st.session_state["history_versions"] = versions
            st.session_state["history_dept_process"] = (h_department, h_process)

    versions = st.session_state.get("history_versions")
    if versions:
        st.dataframe(pd.DataFrame(versions), use_container_width=True, hide_index=True)
        version_options = [v["api_version"] for v in versions]
        dept, proc = st.session_state["history_dept_process"]

        st.markdown("---")
        st.subheader("ดูเนื้อหา / Rollback")
        selected_version = st.selectbox("เลือก version", version_options, key="history_selected_version")

        if st.button("ดูเนื้อหา version นี้", key="load_history_version"):
            payload, err = fetch_config_version(dept, proc, selected_version)
            if err:
                st.error(err)
            else:
                st.session_state["history_view_payload"] = payload

        view_payload = st.session_state.get("history_view_payload")
        if view_payload and view_payload["api_version"] == selected_version:
            st.caption(f"api_version {view_payload['api_version']} — บันทึกเมื่อ {view_payload['update_time']}")
            st.dataframe(pd.DataFrame(view_payload["data"]), use_container_width=True)

            latest_version = version_options[0]  # versions เรียงใหม่สุดก่อนอยู่แล้ว (จาก list_config_versions)
            if selected_version == latest_version:
                st.info("นี่คือ version ล่าสุดอยู่แล้ว ไม่ต้อง rollback")
            else:
                confirm_rollback = st.checkbox(
                    f"ยืนยันว่าต้องการ rollback ไป api_version {selected_version} "
                    f"(จะสร้างเป็น api_version {latest_version + 1} ใหม่ ไม่ทับของเดิม)",
                    key="confirm_rollback",
                )
                if st.button("Rollback ไป version นี้", type="primary", key="do_rollback", disabled=not confirm_rollback):
                    try:
                        r = requests.post(
                            f"{API_BASE_URL}/api/config/{dept}/{proc}",
                            json={"data": view_payload["data"]},
                            timeout=5,
                        )
                    except requests.exceptions.RequestException as e:
                        st.error(f"เชื่อมต่อ backend ไม่ได้: {e}")
                    else:
                        if r.status_code == 200:
                            result = r.json()
                            st.success(f"Rollback สำเร็จ! สร้าง api_version ใหม่: {result['api_version']} (คัดลอกจาก {selected_version})")
                            st.session_state.pop("history_versions", None)
                            st.session_state.pop("history_view_payload", None)
                            st.rerun()
                        else:
                            st.error(f"Rollback ไม่สำเร็จ ({r.status_code}): {r.json().get('detail', r.text)}")

        st.markdown("---")
        st.subheader("เทียบความต่างระหว่าง 2 version")
        col_a, col_b = st.columns(2)
        # ค่าเริ่มต้น: A = version ก่อนหน้าล่าสุด, B = version ล่าสุด (คู่ที่คนอยากเทียบบ่อยสุด)
        default_a_index = 1 if len(version_options) > 1 else 0
        diff_version_a = col_a.selectbox("Version เก่า (A)", version_options, index=default_a_index, key="diff_version_a")
        diff_version_b = col_b.selectbox("Version ใหม่ (B)", version_options, index=0, key="diff_version_b")

        if st.button("เทียบความต่าง", key="do_diff"):
            if diff_version_a == diff_version_b:
                st.warning("เลือก version A กับ B ให้ต่างกันก่อน")
            else:
                payload_a, err_a = fetch_config_version(dept, proc, diff_version_a)
                payload_b, err_b = fetch_config_version(dept, proc, diff_version_b)
                if err_a or err_b:
                    st.error(err_a or err_b)
                else:
                    added_df, removed_df, changed_df = diff_config_rows(payload_a["data"], payload_b["data"])
                    if added_df.empty and removed_df.empty and changed_df.empty:
                        st.info(f"api_version {diff_version_a} กับ {diff_version_b} เหมือนกันทุกแถว")
                    else:
                        if not added_df.empty:
                            st.write(f"🟢 เพิ่มใหม่ใน version {diff_version_b} ({len(added_df)} แถว)")
                            st.dataframe(added_df, use_container_width=True, hide_index=True)
                        if not removed_df.empty:
                            st.write(f"🔴 มีใน version {diff_version_a} แต่หายไปใน {diff_version_b} ({len(removed_df)} แถว)")
                            st.dataframe(removed_df, use_container_width=True, hide_index=True)
                        if not changed_df.empty:
                            st.write(f"🟡 แก้ไข Address/Type ({len(changed_df)} แถว)")
                            st.dataframe(changed_df, use_container_width=True, hide_index=True)
