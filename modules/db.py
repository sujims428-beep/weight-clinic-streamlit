from __future__ import annotations
from datetime import datetime, date
from io import BytesIO
import json, uuid, mimetypes, zipfile
import pandas as pd
import streamlit as st
from supabase import create_client
from modules.calc import bmi, whr, estimate

TABLES = ["patients","visits","body_composition_estimates","medication_records","lab_results","tongue_images","pulse_records","uploaded_files","system_logs"]

@st.cache_resource(show_spinner=False)
def client():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["service_role_key"]
        if "YOUR_" in url or "YOUR_" in key: return None
        return create_client(url, key)
    except Exception:
        return None

def bucket():
    try: return st.secrets["supabase"].get("bucket","weight-clinic-files")
    except Exception: return "weight-clinic-files"

def ok(): return client() is not None
def data(resp): return resp.data or []
def now(): return datetime.utcnow().isoformat()

def log(action, obj="", oid="", detail=None):
    sb = client()
    if not sb: return
    try:
        user = st.session_state.get("user") or {}
        sb.table("system_logs").insert({"username":user.get("username",""),"action":action,"object_type":obj,"object_id":str(oid or ""),"detail":detail or {}}).execute()
    except Exception: pass

def list_patients():
    sb=client()
    return [] if not sb else data(sb.table("patients").select("*").eq("is_deleted", False).order("created_at", desc=True).execute())

def get_patient(pid):
    sb=client()
    r=data(sb.table("patients").select("*").eq("patient_id", pid).limit(1).execute())
    return r[0] if r else None

def insert(table, row):
    sb=client()
    out=data(sb.table(table).insert(row).execute())
    log("insert_"+table, table, out[0] if out else "")
    return out[0] if out else {}

def update(table, pk, val, row):
    sb=client()
    row=row.copy(); row["updated_at"]=now()
    out=data(sb.table(table).update(row).eq(pk, val).execute())
    log("update_"+table, table, val)
    return out[0] if out else {}

def delete(table, pk, val):
    sb=client(); sb.table(table).delete().eq(pk,val).execute(); log("delete_"+table, table, val)

def create_patient(row):
    return insert("patients", row)

def update_patient(pid,row): return update("patients","patient_id",pid,row)
def soft_delete_patient(pid): return update("patients","patient_id",pid,{"is_deleted":True})

def related(pid):
    sb=client()
    if not sb: return {}
    return {
      "visits": data(sb.table("visits").select("*").eq("patient_id",pid).order("visit_date").execute()),
      "meds": data(sb.table("medication_records").select("*").eq("patient_id",pid).order("medication_date").execute()),
      "labs": data(sb.table("lab_results").select("*").eq("patient_id",pid).order("lab_date").execute()),
      "tongues": data(sb.table("tongue_images").select("*").eq("patient_id",pid).order("image_date").execute()),
      "pulses": data(sb.table("pulse_records").select("*").eq("patient_id",pid).order("pulse_date").execute()),
      "files": data(sb.table("uploaded_files").select("*").eq("patient_id",pid).order("document_date").execute()),
      "estimates": data(sb.table("body_composition_estimates").select("*").eq("patient_id",pid).order("estimate_date").execute()),
    }

def create_visit(patient,row):
    row=row.copy()
    row["patient_id"]=patient["patient_id"]
    row["bmi"]=bmi(row.get("weight_kg"), patient.get("height_cm"))
    row["waist_hip_ratio"]=whr(row.get("waist_cm"), row.get("hip_cm"))
    visit=insert("visits", row)
    sync_estimate(patient, visit)
    return visit

def update_visit(patient, vid,row):
    row=row.copy()
    row["bmi"]=bmi(row.get("weight_kg"), patient.get("height_cm"))
    row["waist_hip_ratio"]=whr(row.get("waist_cm"), row.get("hip_cm"))
    visit=update("visits","visit_id",vid,row)
    sync_estimate(patient, visit or (row|{"visit_id":vid}))
    return visit

def delete_visit(vid):
    sb=client()
    for table in ["medication_records","lab_results","tongue_images","pulse_records","uploaded_files"]:
        try: sb.table(table).update({"visit_id":None}).eq("visit_id",vid).execute()
        except Exception: pass
    sb.table("body_composition_estimates").delete().eq("visit_id",vid).execute()
    sb.table("visits").delete().eq("visit_id",vid).execute()
    log("delete_visit","visit",vid)

def sync_estimate(patient, visit):
    sb=client()
    est=estimate(patient, visit)
    old=data(sb.table("body_composition_estimates").select("estimate_id").eq("visit_id",visit.get("visit_id")).limit(1).execute())
    if old: sb.table("body_composition_estimates").update(est).eq("estimate_id", old[0]["estimate_id"]).execute()
    else: sb.table("body_composition_estimates").insert(est).execute()

def upload(file, folder, patient_code, doc_date=None):
    sb=client()
    ext=file.name.split(".")[-1].lower() if "." in file.name else "bin"
    path=f"{folder}/{patient_code}/{doc_date or date.today()}_{uuid.uuid4().hex[:10]}.{ext}"
    mime=mimetypes.guess_type(file.name)[0] or "application/octet-stream"
    sb.storage.from_(bucket()).upload(path, file.getvalue(), {"content-type":mime, "upsert":"true"})
    try: url=sb.storage.from_(bucket()).get_public_url(path)
    except Exception: url=""
    return path,url

def export_zip():
    sb=client(); bio=BytesIO()
    with zipfile.ZipFile(bio,"w",zipfile.ZIP_DEFLATED) as z:
        for t in TABLES:
            try:
                rows=data(sb.table(t).select("*").execute())
                z.writestr(f"{t}.csv", pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig"))
                z.writestr(f"{t}.json", json.dumps(rows, ensure_ascii=False, indent=2, default=str))
            except Exception as e:
                z.writestr(f"{t}_ERROR.txt", str(e))
    return bio.getvalue()
