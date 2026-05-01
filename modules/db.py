from __future__ import annotations
from datetime import datetime, date
from io import BytesIO
import json, uuid, mimetypes, zipfile
import pandas as pd
import streamlit as st
from supabase import create_client
from modules.calc import bmi, whr, estimate

TABLES = ["patients","visits","body_composition_estimates","medication_records","lab_results","tongue_images","pulse_records","uploaded_files","system_logs"]


def _secret_text(value) -> str:
    """把 Streamlit secrets 中的配置值转成干净字符串。"""
    if value is None:
        return ""
    text = str(value).strip()

    # 处理用户误把引号、隐藏字符、不可见空格复制进去的情况
    text = text.strip('"').strip("'").strip()
    for ch in ("\ufeff", "\u200b", "\u200c", "\u200d", "\u2060", "\xa0"):
        text = text.replace(ch, "")

    return text.strip()


def _has_space(text: str) -> bool:
    """检查密钥中是否混入空格、换行、制表符等字符。"""
    return any(ch.isspace() for ch in text)


def _is_ascii(text: str) -> bool:
    """HTTP 请求头只能安全使用 ASCII 字符；Supabase key 必须是纯英文/数字/符号。"""
    try:
        text.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def _show_supabase_config_error(message: str):
    """显示一次 Supabase 配置错误，避免页面刷屏。"""
    st.session_state["_supabase_config_error"] = message
    st.error(message)


def _validate_supabase_config(url: str, key: str):
    """在真正创建 Supabase 客户端前做配置校验，避免 UnicodeEncodeError 白屏。"""
    if not url or not key:
        raise ValueError(
            "Supabase 配置不完整：请检查 Streamlit Secrets 中 [supabase] 的 url 和 service_role_key。"
        )

    if "YOUR_" in url or "YOUR_" in key:
        raise ValueError(
            "Supabase 仍是示例占位配置：请把 Secrets 中的 YOUR_PROJECT_ID 和 YOUR_SUPABASE_SERVICE_ROLE_KEY 替换为真实值。"
        )

    if not _is_ascii(url):
        raise ValueError(
            "Supabase url 中含有中文、中文标点或隐藏字符。请在 Streamlit Secrets 中删除后重新粘贴，只保留 https://xxxxx.supabase.co。"
        )

    if not _is_ascii(key):
        raise ValueError(
            "Supabase service_role_key 中含有中文、中文标点或隐藏字符。请在 Streamlit Secrets 中删除备注说明，只保留纯密钥字符串。"
        )

    if _has_space(url):
        raise ValueError(
            "Supabase url 中含有空格或换行。请在 Streamlit Secrets 中重新粘贴为单行。"
        )

    if _has_space(key):
        raise ValueError(
            "Supabase service_role_key 中含有空格或换行。请在 Streamlit Secrets 中重新粘贴为单行，不要分行。"
        )

    if not url.startswith("https://"):
        raise ValueError(
            "Supabase url 格式不正确：应以 https:// 开头，例如 https://xxxxx.supabase.co。"
        )


@st.cache_resource(show_spinner=False)
def client():
    """创建 Supabase 客户端。

    修复点：
    1. 原版本如果 service_role_key 混入中文/隐藏字符，会在 httpx 组装请求头时触发 UnicodeEncodeError；
    2. 新版本在创建客户端前主动校验配置，并在页面上给出中文提示；
    3. 主动初始化 postgrest，提前捕获 header 编码错误，避免进入患者管理页后直接白屏。
    """
    try:
        supabase_config = st.secrets.get("supabase", {})
        url = _secret_text(supabase_config.get("url", ""))
        key = _secret_text(supabase_config.get("service_role_key", ""))

        _validate_supabase_config(url, key)

        sb = create_client(url, key)

        # supabase-py 会延迟创建 postgrest 客户端；这里主动触发一次，提前捕获 header 编码错误
        _ = sb.postgrest

        return sb

    except Exception as e:
        message = (
            "数据库连接配置异常，系统已阻止继续访问 Supabase。\n\n"
            "最常见原因：Streamlit Secrets 里的 supabase.service_role_key 混入了中文说明、中文标点、空格、换行或隐藏字符。\n\n"
            "请到 Streamlit Cloud → Manage app → Settings → Secrets，检查并确保配置类似下面这样，且密钥为单行纯英文字符：\n\n"
            "[supabase]\n"
            "url = \"https://你的项目ID.supabase.co\"\n"
            "service_role_key = \"你的真实Supabase密钥\"\n"
            "bucket = \"weight-clinic-files\"\n\n"
            "修正后点击 Save，并重启应用。"
        )
        _show_supabase_config_error(message)
        return None


def bucket():
    try:
        return _secret_text(st.secrets["supabase"].get("bucket", "weight-clinic-files")) or "weight-clinic-files"
    except Exception:
        return "weight-clinic-files"


def ok():
    return client() is not None


def data(resp):
    return resp.data or []


def now():
    return datetime.utcnow().isoformat()


def _require_client():
    sb = client()
    if not sb:
        st.stop()
    return sb


def log(action, obj="", oid="", detail=None):
    sb = client()
    if not sb:
        return
    try:
        user = st.session_state.get("user") or {}
        sb.table("system_logs").insert({
            "username": user.get("username", ""),
            "action": action,
            "object_type": obj,
            "object_id": str(oid or ""),
            "detail": detail or {}
        }).execute()
    except Exception:
        pass


def list_patients():
    sb = client()
    if not sb:
        return []
    return data(sb.table("patients").select("*").eq("is_deleted", False).order("created_at", desc=True).execute())


def get_patient(pid):
    sb = client()
    if not sb:
        return None
    r = data(sb.table("patients").select("*").eq("patient_id", pid).limit(1).execute())
    return r[0] if r else None


def insert(table, row):
    sb = _require_client()
    out = data(sb.table(table).insert(row).execute())
    log("insert_" + table, table, out[0] if out else "")
    return out[0] if out else {}


def update(table, pk, val, row):
    sb = _require_client()
    row = row.copy()
    row["updated_at"] = now()
    out = data(sb.table(table).update(row).eq(pk, val).execute())
    log("update_" + table, table, val)
    return out[0] if out else {}


def delete(table, pk, val):
    sb = _require_client()
    sb.table(table).delete().eq(pk, val).execute()
    log("delete_" + table, table, val)


def create_patient(row):
    return insert("patients", row)


def update_patient(pid, row):
    return update("patients", "patient_id", pid, row)


def soft_delete_patient(pid):
    return update("patients", "patient_id", pid, {"is_deleted": True})


def related(pid):
    sb = client()
    if not sb:
        return {}
    return {
        "visits": data(sb.table("visits").select("*").eq("patient_id", pid).order("visit_date").execute()),
        "meds": data(sb.table("medication_records").select("*").eq("patient_id", pid).order("medication_date").execute()),
        "labs": data(sb.table("lab_results").select("*").eq("patient_id", pid).order("lab_date").execute()),
        "tongues": data(sb.table("tongue_images").select("*").eq("patient_id", pid).order("image_date").execute()),
        "pulses": data(sb.table("pulse_records").select("*").eq("patient_id", pid).order("pulse_date").execute()),
        "files": data(sb.table("uploaded_files").select("*").eq("patient_id", pid).order("document_date").execute()),
        "estimates": data(sb.table("body_composition_estimates").select("*").eq("patient_id", pid).order("estimate_date").execute()),
    }


def create_visit(patient, row):
    row = row.copy()
    row["patient_id"] = patient["patient_id"]
    row["bmi"] = bmi(row.get("weight_kg"), patient.get("height_cm"))
    row["waist_hip_ratio"] = whr(row.get("waist_cm"), row.get("hip_cm"))
    visit = insert("visits", row)
    sync_estimate(patient, visit)
    return visit


def update_visit(patient, vid, row):
    row = row.copy()
    row["bmi"] = bmi(row.get("weight_kg"), patient.get("height_cm"))
    row["waist_hip_ratio"] = whr(row.get("waist_cm"), row.get("hip_cm"))
    visit = update("visits", "visit_id", vid, row)
    sync_estimate(patient, visit or (row | {"visit_id": vid}))
    return visit


def delete_visit(vid):
    sb = _require_client()
    for table in ["medication_records", "lab_results", "tongue_images", "pulse_records", "uploaded_files"]:
        try:
            sb.table(table).update({"visit_id": None}).eq("visit_id", vid).execute()
        except Exception:
            pass
    sb.table("body_composition_estimates").delete().eq("visit_id", vid).execute()
    sb.table("visits").delete().eq("visit_id", vid).execute()
    log("delete_visit", "visit", vid)


def sync_estimate(patient, visit):
    sb = client()
    if not sb or not visit:
        return
    est = estimate(patient, visit)
    old = data(sb.table("body_composition_estimates").select("estimate_id").eq("visit_id", visit.get("visit_id")).limit(1).execute())
    if old:
        sb.table("body_composition_estimates").update(est).eq("estimate_id", old[0]["estimate_id"]).execute()
    else:
        sb.table("body_composition_estimates").insert(est).execute()


def upload(file, folder, patient_code, doc_date=None):
    sb = _require_client()
    ext = file.name.split(".")[-1].lower() if "." in file.name else "bin"
    path = f"{folder}/{patient_code}/{doc_date or date.today()}_{uuid.uuid4().hex[:10]}.{ext}"
    mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
    sb.storage.from_(bucket()).upload(path, file.getvalue(), {"content-type": mime, "upsert": "true"})
    try:
        url = sb.storage.from_(bucket()).get_public_url(path)
    except Exception:
        url = ""
    return path, url


def export_zip():
    sb = _require_client()
    bio = BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
        for t in TABLES:
            try:
                rows = data(sb.table(t).select("*").execute())
                z.writestr(f"{t}.csv", pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig"))
                z.writestr(f"{t}.json", json.dumps(rows, ensure_ascii=False, indent=2, default=str))
            except Exception as e:
                z.writestr(f"{t}_ERROR.txt", str(e))
    return bio.getvalue()
