from __future__ import annotations
from datetime import date, timedelta
import json
import re
import pandas as pd
import plotly.express as px
import streamlit as st
from modules.auth import require_login, logout
from modules.calc import LAB_TEMPLATES, abnormal, bmi, fmt, ideal_weight, loss, whr
from modules.db import *
from modules.report import a5_html
from modules.ui import css, hero, boundary, tags_html
try:
    from modules.ui import brand, section, patient_header, stat_grid, overview_cards, chart_open, chart_close
except ImportError:
    # 防止线上只替换 app.py、未同步 modules/ui.py 时直接崩溃
    def brand():
        st.sidebar.markdown("### ⚖️ 逢安堂")
    def section(title):
        st.markdown(f"### {title}")
    def patient_header(patient):
        st.markdown(
            f"### {patient.get('name','')}\n"
            f"{patient.get('patient_code','')}｜{patient.get('sex','')}｜{patient.get('age','')}岁"
        )
    def stat_grid(items):
        cols = st.columns(len(items) if items else 1)
        for col, item in zip(cols, items):
            title, value, note = item
            col.metric(title, value, note)
    def overview_cards(meds, tongue_text, pulse_text, lab_text):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("#### 当前用药 / 调理方案")
            if meds:
                for m in meds:
                    st.write(f"- {m.get('medicine_name','')} {m.get('dose','')} {m.get('frequency','')}")
            else:
                st.caption("暂无当前用药")
        with c2:
            st.markdown("#### 舌象与脉象记录")
            st.write(f"舌象：{tongue_text or '未记录'}")
            st.write(f"脉象：{pulse_text or '未记录'}")
        with c3:
            st.markdown("#### 最近辅助检查")
            st.write(lab_text or "暂无辅助检查")
    def chart_open():
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    def chart_close():
        st.markdown("</div>", unsafe_allow_html=True)

st.set_page_config(page_title="减重门诊管理系统（逢安堂）", page_icon="⚖️", layout="wide")
css()

TAGS=["减重门诊","糖尿病","高脂血症","脂肪肝","高尿酸血症","中药调理","重点复诊","依从性差","血糖异常","血脂异常","代谢综合征"]
DIET=["良好","一般","较差","未记录","基本执行"]; EX=["规律运动","偶尔运动","未运动","未记录"]; SL=["良好","一般","较差","失眠","未记录"]; ST=["正常","便秘","腹泻","不规律","未记录"]

def next_patient_code():
    """根据现有患者编号自动生成下一个编号，避免重复编号导致数据库报错。"""
    year = str(date.today().year)
    max_no = 0
    for p in list_patients():
        code = str(p.get("patient_code") or "")
        m = re.match(rf"^P{year}(\d+)$", code)
        if m:
            try:
                max_no = max(max_no, int(m.group(1)))
            except Exception:
                pass
    return f"P{year}{max_no + 1:04d}"

def optional_float_text(value):
    """把可空输入转成小数；空白代表无。"""
    if value is None:
        return None
    s = str(value).strip()
    if s in ("", "无", "未测", "未记录"):
        return None
    try:
        return float(s)
    except Exception:
        raise ValueError(f"数值格式不正确：{s}")

def optional_int_text(value):
    v = optional_float_text(value)
    return None if v is None else int(round(v))

COLMAP={"patient_code":"患者编号","name":"姓名","sex":"性别","age":"年龄","phone":"手机号","height_cm":"身高","first_visit_date":"初诊日期","initial_weight_kg":"初诊体重","target_weight_kg":"目标体重","main_diagnosis":"主要诊断","tags":"标签","notes":"备注","visit_date":"复诊日期","weight_kg":"体重","bmi":"体重指数","waist_cm":"腰围","hip_cm":"臀围","waist_hip_ratio":"腰臀比","systolic_bp":"收缩压","diastolic_bp":"舒张压","heart_rate":"心率","diet_adherence":"饮食执行","exercise_status":"运动情况","sleep_status":"睡眠情况","stool_status":"大便情况","discomfort_symptoms":"不适症状","clinical_assessment":"本次评估","clinical_advice":"本次建议","next_visit_date":"下次复诊","medication_date":"用药日期","medicine_name":"药物/方案","dose":"剂量","frequency":"频次","current_status":"状态","adjustment_type":"调整类型","adjustment_reason":"调整原因","adverse_reaction":"不良反应","lab_date":"检查日期","lab_category":"类别","item_name":"项目","result_value":"结果数值","result_text":"文字结果","unit":"单位","reference_low":"参考下限","reference_high":"参考上限","abnormal_flag":"异常提示","hospital_name":"医院","image_date":"舌象日期","tongue_body_color":"舌质","tongue_coating":"舌苔","tongue_shape":"舌形","tooth_marks":"齿痕","cracks":"裂纹","moisture":"津液","pulse_date":"脉象日期","overall_pulse":"整体脉象","left_cun":"左寸","left_guan":"左关","left_chi":"左尺","right_cun":"右寸","right_guan":"右关","right_chi":"右尺","upload_date":"上传日期","document_date":"资料日期","file_type":"资料类型","file_name":"文件名","file_url":"文件链接"}

def show_table(rows, height=None):
    df=pd.DataFrame(rows)
    if df.empty:
        st.info("暂无数据"); return
    hidden=[c for c in df.columns if c.endswith("_id") or c in ["created_at","updated_at","is_deleted","image_path","file_path","source_file_path"]]
    df=df.drop(columns=[c for c in hidden if c in df.columns], errors="ignore")
    df=df.rename(columns={k:v for k,v in COLMAP.items() if k in df.columns})
    # Streamlit 新版本不接受 height=None，所以只有明确传入高度时才写入 height 参数。
    if height is None:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True, height=height)


def as_date(value, default=None):
    if default is None:
        default = date.today()
    if not value:
        return default
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return default

def sort_key_date_id(row, date_key, id_key):
    return (str(row.get(date_key) or ""), int(row.get(id_key) or 0))

def current_medications(meds):
    """按药物名称读取最新一条记录，最新状态为“使用中”时才认为是当前用药。"""
    latest = {}
    for m in sorted(meds or [], key=lambda x: sort_key_date_id(x, "medication_date", "medication_id")):
        name = (m.get("medicine_name") or "").strip()
        if not name:
            continue
        latest[name] = m
    current = []
    for m in latest.values():
        if (m.get("current_status") or "使用中") == "使用中":
            current.append(m)
    return sorted(current, key=lambda x: sort_key_date_id(x, "medication_date", "medication_id"), reverse=True)

def safe_float_for_edit(x, default=0.0):
    try:
        if x is None or x == "":
            return float(default)
        return float(x)
    except Exception:
        return float(default)

def current_med_names(meds):
    return [f"{m.get('medicine_name','')} {m.get('dose','')} {m.get('frequency','')}" for m in current_medications(meds)]



def stop_if_unconfigured():
    if not ok():
        hero("减重门诊管理系统（逢安堂）", "在线版")
        st.error("尚未配置云数据库。请在部署平台的密钥设置中填写云数据库地址与服务密钥。")
        st.stop()

def safe_tags(p):
    x=p.get("tags") or []
    if isinstance(x,str):
        try: return json.loads(x)
        except Exception: return []
    return x

def choose_patient(label="选择患者"):
    ps=list_patients()
    if not ps:
        st.info("暂无患者。请先新增患者。")
        return None
    opts={f"{p['patient_code']}｜{p['name']}｜{p['sex']}｜{p.get('age','')}岁":p["patient_id"] for p in ps}
    sel=st.selectbox(label, list(opts))
    st.session_state["patient_id"]=opts[sel]
    return get_patient(opts[sel])

def cards(p, rel=None):
    rel=rel or related(p["patient_id"])
    visits=rel.get("visits",[])
    lv=sorted(visits,key=lambda x:str(x.get("visit_date") or ""), reverse=True)[0] if visits else {}
    wt=lv.get("weight_kg") or p.get("initial_weight_kg")
    c1,c2,c3,c4=st.columns(4)
    c1.metric("当前体重", f"{fmt(wt)} 千克", f"累计减重 {fmt(loss(p.get('initial_weight_kg'), wt))}%")
    c2.metric("当前体重指数", fmt(bmi(wt,p.get("height_cm"))))
    c3.metric("最近腰围", f"{fmt(lv.get('waist_cm'))} 厘米")
    c4.metric("目标体重", f"{fmt(p.get('target_weight_kg'))} 千克")
    st.markdown(tags_html(safe_tags(p)), unsafe_allow_html=True)

def new_patient_panel():
    with st.expander("＋ 新增患者 / 初诊建档", expanded=False):
        default_code = next_patient_code()
        with st.form("new_patient"):
            a,b,c,d=st.columns(4)
            code=a.text_input("患者编号", default_code)
            name=b.text_input("姓名")
            sex=c.selectbox("性别",["男","女"])
            age=d.number_input("年龄",0,120,40)

            e,f,g,h=st.columns(4)
            phone=e.text_input("手机号")
            height=f.number_input("身高（厘米）",80.0,230.0,170.0)
            first=g.date_input("初诊日期",date.today())
            weight=h.number_input("初诊体重（千克）",0.0,value=80.0)

            lo,hi,mid=ideal_weight(height)
            st.info(f"当前体重指数：{fmt(bmi(weight,height))}；目标体重参考：{fmt(lo)}–{fmt(hi)} 千克")

            target=st.number_input("目标体重（千克）",0.0,value=float(mid or 65))
            diag=st.text_input("主要诊断/主要问题","肥胖/体重管理")
            tags=st.multiselect("标签",TAGS,["减重门诊"], placeholder="请选择标签")
            notes=st.text_area("备注")

            section("初诊基线")
            st.caption("没有检测或没有记录的项目请留空，系统会按“无”处理，不再默认写入 0。")
            x1,x2,x3,x4,x5=st.columns(5)
            waist_text=x1.text_input("腰围（厘米）", value="", placeholder="无")
            hip_text=x2.text_input("臀围（厘米）", value="", placeholder="无")
            sbp_text=x3.text_input("收缩压", value="", placeholder="无")
            dbp_text=x4.text_input("舒张压", value="", placeholder="无")
            hr_text=x5.text_input("心率", value="", placeholder="无")

            y1,y2,y3,y4=st.columns(4)
            diet=y1.selectbox("饮食",DIET)
            ex=y2.selectbox("运动",EX)
            sleep=y3.selectbox("睡眠",SL)
            stool=y4.selectbox("大便",ST)

            discomfort=st.text_input("不适症状","未诉明显不适")
            ass=st.text_area("初诊评估","初诊建档，建立减重管理基线。")
            adv=st.text_area("初诊建议","进行饮食、运动及生活方式管理，按期复诊。")
            nextd=st.date_input("下次复诊日期", date.today()+timedelta(days=7))
            submitted=st.form_submit_button("保存患者并生成初诊基线", use_container_width=True)

        if submitted:
            if not name:
                st.error("姓名不能为空")
                return
            try:
                waist = optional_float_text(waist_text)
                hip = optional_float_text(hip_text)
                sbp = optional_int_text(sbp_text)
                dbp = optional_int_text(dbp_text)
                hr = optional_int_text(hr_text)

                p=create_patient({
                    "patient_code":code.strip(),
                    "name":name.strip(),
                    "sex":sex,
                    "age":int(age),
                    "phone":phone,
                    "height_cm":height,
                    "first_visit_date":str(first),
                    "initial_weight_kg":weight,
                    "target_weight_kg":target,
                    "main_diagnosis":diag,
                    "tags":tags,
                    "notes":notes
                })

                create_visit(p,{
                    "visit_date":str(first),
                    "weight_kg":weight,
                    "waist_cm":waist,
                    "hip_cm":hip,
                    "systolic_bp":sbp,
                    "diastolic_bp":dbp,
                    "heart_rate":hr,
                    "diet_adherence":diet,
                    "exercise_status":ex,
                    "sleep_status":sleep,
                    "stool_status":stool,
                    "discomfort_symptoms":discomfort,
                    "clinical_assessment":ass,
                    "clinical_advice":adv,
                    "next_visit_date":str(nextd)
                })
                st.session_state["patient_id"]=p["patient_id"]
                st.success("患者保存成功")
                st.rerun()
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                msg = str(e)
                if "duplicate" in msg.lower() or "unique" in msg.lower() or "patients_patient_code" in msg.lower():
                    st.error("保存失败：患者编号已存在。系统已自动生成新编号，请刷新页面后再试，或手动修改患者编号。")
                else:
                    st.error("保存失败：数据库写入异常。请检查患者编号是否重复、建表文件是否完整执行。")


def page_patients():
    hero("患者管理","新增、搜索、筛选并进入患者详情")
    boundary(); new_patient_panel()
    ps=list_patients()
    if not ps:
        st.info("暂无患者，请先新增患者。")
        return
    diabetes=sum("糖尿病" in safe_tags(p) or "血糖异常" in safe_tags(p) for p in ps)
    lipid=sum("高脂血症" in safe_tags(p) or "血脂异常" in safe_tags(p) for p in ps)
    key_follow=sum("重点复诊" in safe_tags(p) for p in ps)
    stat_grid([("患者总数",len(ps),"当前已建档患者"),("血糖相关",diabetes,"糖尿病或血糖异常"),("血脂相关",lipid,"高脂血症或血脂异常"),("重点复诊",key_follow,"需要重点随访")])
    section("患者检索与筛选")
    q=st.text_input("搜索患者", placeholder="姓名 / 手机号 / 患者编号"); tf=st.multiselect("标签筛选",TAGS, placeholder="请选择标签")
    rows=[]
    for p in ps:
        tags=safe_tags(p)
        if q and q not in str(p.get("name","")) and q not in str(p.get("phone","")) and q not in str(p.get("patient_code","")): continue
        if tf and not all(t in tags for t in tf): continue
        rel=related(p["patient_id"]); visits=rel.get("visits",[])
        lv=sorted(visits,key=lambda x:str(x.get("visit_date") or ""), reverse=True)[0] if visits else {}
        rows.append({"patient_id":p["patient_id"],"编号":p.get("patient_code"),"姓名":p.get("name"),"性别":p.get("sex"),"年龄":p.get("age"),"手机号":p.get("phone"),"初诊日期":p.get("first_visit_date"),"最近复诊":lv.get("visit_date"),"最近体重":lv.get("weight_kg"),"最近体重指数":bmi(lv.get("weight_kg"),p.get("height_cm")) if lv else None,"主要诊断":p.get("main_diagnosis"),"标签":"、".join(tags)})
    section("患者列表")
    df=pd.DataFrame(rows); st.dataframe(df.drop(columns=["patient_id"]) if not df.empty else df, use_container_width=True, hide_index=True)
    if rows:
        labels=[f"{r['编号']}｜{r['姓名']}｜{r['性别']}｜{r['年龄']}岁" for r in rows]; label=st.selectbox("选择患者",labels)
        pid=rows[labels.index(label)]["patient_id"]
        c1,c2=st.columns(2)
        if c1.button("查看详情", use_container_width=True): st.session_state["patient_id"]=pid; st.session_state["show_detail"]=True; st.rerun()
        if c2.button("删除该患者（软删除）", use_container_width=True): soft_delete_patient(pid); st.rerun()
    if st.session_state.get("show_detail") and st.session_state.get("patient_id"): st.divider(); patient_detail(st.session_state["patient_id"])

def visit_form(p, v=None):
    v=v or {}
    with st.form(f"visit_{v.get('visit_id','new')}"):
        a,b,c,d=st.columns(4)
        vd=a.date_input("复诊日期", pd.to_datetime(v.get("visit_date") or date.today()).date()); wt=b.number_input("体重（千克）",0.0,value=float(v.get("weight_kg") or p.get("initial_weight_kg") or 0)); waist=c.number_input("腰围（厘米）",0.0,value=float(v.get("waist_cm") or 0)); hip=d.number_input("臀围（厘米）",0.0,value=float(v.get("hip_cm") or 0))
        st.info(f"体重指数：{fmt(bmi(wt,p.get('height_cm')))}；腰臀比：{fmt(whr(waist,hip))}；累计减重：{fmt(loss(p.get('initial_weight_kg'),wt))}%")
        e,f,g=st.columns(3); sbp=e.number_input("收缩压",0,value=int(v.get("systolic_bp") or 0)); dbp=f.number_input("舒张压",0,value=int(v.get("diastolic_bp") or 0)); hr=g.number_input("心率",0,value=int(v.get("heart_rate") or 0))
        h,i,j,k=st.columns(4)
        diet=h.selectbox("饮食",DIET,index=DIET.index(v.get("diet_adherence")) if v.get("diet_adherence") in DIET else 0); ex=i.selectbox("运动",EX,index=EX.index(v.get("exercise_status")) if v.get("exercise_status") in EX else 0); sleep=j.selectbox("睡眠",SL,index=SL.index(v.get("sleep_status")) if v.get("sleep_status") in SL else 0); stool=k.selectbox("大便",ST,index=ST.index(v.get("stool_status")) if v.get("stool_status") in ST else 0)
        dis=st.text_input("不适症状",v.get("discomfort_symptoms") or "未诉明显不适"); ass=st.text_area("评估",v.get("clinical_assessment") or ""); adv=st.text_area("建议",v.get("clinical_advice") or ""); nextd=st.date_input("下次复诊",pd.to_datetime(v.get("next_visit_date") or (date.today()+timedelta(days=7))).date()); notes=st.text_area("备注",v.get("notes") or "")
        ok=st.form_submit_button("保存复诊记录", use_container_width=True)
    if ok:
        row={"visit_date":str(vd),"weight_kg":wt,"waist_cm":waist or None,"hip_cm":hip or None,"systolic_bp":sbp or None,"diastolic_bp":dbp or None,"heart_rate":hr or None,"diet_adherence":diet,"exercise_status":ex,"sleep_status":sleep,"stool_status":stool,"discomfort_symptoms":dis,"clinical_assessment":ass,"clinical_advice":adv,"next_visit_date":str(nextd),"notes":notes}
        if v.get("visit_id"): update_visit(p,v["visit_id"],row)
        else: create_visit(p,row)
        st.success("已保存"); st.rerun()

def patient_detail(pid=None):
    p=get_patient(pid or st.session_state.get("patient_id"))
    if not p: st.info("请选择患者"); return
    rel=related(p["patient_id"]); hero("患者详情","患者随访、用药、舌脉、辅助检查与报告管理"); patient_header(p); cards(p,rel)
    tabs=st.tabs(["概览","复诊记录","用药调整","舌象/脉象","辅助检查","资料归档","打印报告","编辑基础信息"])
    with tabs[0]:
        visits=rel.get("visits",[]); lv=sorted(visits,key=lambda x:str(x.get("visit_date") or ""),reverse=True)[0] if visits else {}
        meds=current_med_names(rel.get("meds",[]))
        tongue=sorted(rel.get("tongues",[]),key=lambda x:str(x.get("image_date") or ""),reverse=True)[0] if rel.get("tongues") else {}
        pulse=sorted(rel.get("pulses",[]),key=lambda x:str(x.get("pulse_date") or ""),reverse=True)[0] if rel.get("pulses") else {}
        labs=sorted(rel.get("labs",[]),key=lambda x:str(x.get("lab_date") or ""),reverse=True)[:4]
        lab_text=[f"{x.get('item_name','')}：{x.get('result_value') or x.get('result_text') or '暂无'} {x.get('unit') or ''}（{x.get('abnormal_flag') or '未判断'}）" for x in labs]
        overview_cards(meds[-4:], f"舌质 {tongue.get('tongue_body_color','未记录')}，舌苔 {tongue.get('tongue_coating','未记录')}，舌形 {tongue.get('tongue_shape','未记录')}", pulse.get('overall_pulse','未记录'), lab_text)
        section("最近复诊摘要")
        st.markdown(f"<div class='section-card'><p><b>本次评估：</b>{lv.get('clinical_assessment') or '暂无评估'}</p><p><b>本次建议：</b>{lv.get('clinical_advice') or '暂无建议'}</p></div>", unsafe_allow_html=True)
    with tabs[1]:
        section("新增复诊记录"); visit_form(p)
        section("历次复诊记录")
        for v in sorted(rel.get("visits",[]),key=lambda x:str(x.get("visit_date") or ""),reverse=True):
            with st.expander(f"{v.get('visit_date')}｜体重 {fmt(v.get('weight_kg'))} 千克"):
                visit_form(p,v)
                if st.button("删除该复诊记录", key=f"delv{v['visit_id']}"): delete_visit(v["visit_id"]); st.rerun()
    with tabs[2]:
        section("当前用药")
        st.caption("当前用药按“同一药物/方案的最新记录”判断；如果最新记录为“停用”或“暂停”，则不再显示为当前用药。")
        meds_all = sorted(rel.get("meds", []), key=lambda x: sort_key_date_id(x, "medication_date", "medication_id"), reverse=True)
        current_meds = current_medications(meds_all)

        if not current_meds:
            st.info("暂无当前用药。可在下方新增用药或调理方案。")
        else:
            for m in current_meds:
                title = f"{m.get('medicine_name','未命名')}｜{m.get('dose') or '未填剂量'}｜{m.get('frequency') or '未填频次'}"
                with st.expander(title, expanded=False):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("药物/方案", m.get("medicine_name") or "未记录")
                    c2.metric("当前剂量", m.get("dose") or "未记录")
                    c3.metric("当前频次", m.get("frequency") or "未记录")
                    c4.metric("最近调整", m.get("medication_date") or "未记录")
                    with st.form(f"adjust_current_med_{m.get('medication_id')}"):
                        a,b,c,d = st.columns(4)
                        adj_date = a.date_input("调整日期", value=date.today(), key=f"adj_date_{m.get('medication_id')}")
                        adj_type = b.selectbox("调整类型", ["维持", "加量", "减量", "调整方案", "停用", "暂停"], key=f"adj_type_{m.get('medication_id')}")
                        new_dose = c.text_input("调整后剂量", value=m.get("dose") or "", key=f"adj_dose_{m.get('medication_id')}")
                        new_freq = d.text_input("调整后频次", value=m.get("frequency") or "", key=f"adj_freq_{m.get('medication_id')}")
                        reason = st.text_input("调整原因", value="", key=f"adj_reason_{m.get('medication_id')}")
                        notes = st.text_area("备注", value="", key=f"adj_notes_{m.get('medication_id')}")
                        ok_adj = st.form_submit_button("保存本次用药调整", use_container_width=True)
                    if ok_adj:
                        new_status = "使用中"
                        if adj_type == "停用":
                            new_status = "已停用"
                        elif adj_type == "暂停":
                            new_status = "暂停"
                        insert("medication_records", {
                            "patient_id": p["patient_id"],
                            "medication_date": str(adj_date),
                            "medicine_name": m.get("medicine_name"),
                            "dose": new_dose,
                            "frequency": new_freq,
                            "current_status": new_status,
                            "adjustment_type": adj_type,
                            "adjustment_reason": reason,
                            "notes": notes
                        })
                        st.success("用药调整已记录，并已同步到当前用药与时间轴。")
                        st.rerun()

        section("新增用药 / 调理方案")
        with st.form("med"):
            a,b,c,d=st.columns(4)
            md=a.date_input("日期",date.today())
            name=b.text_input("药物/方案")
            dose=c.text_input("剂量")
            freq=d.text_input("频次")
            status=st.selectbox("状态",["使用中","已停用","暂停","未知"])
            adj=st.selectbox("调整类型",["新增","维持","加量","减量","停用","调整方案"])
            reason=st.text_input("原因")
            notes=st.text_area("备注")
            if st.form_submit_button("保存用药调整") and name:
                insert("medication_records",{
                    "patient_id":p["patient_id"],
                    "medication_date":str(md),
                    "medicine_name":name,
                    "dose":dose,
                    "frequency":freq,
                    "current_status":status,
                    "adjustment_type":adj,
                    "adjustment_reason":reason,
                    "notes":notes
                })
                st.success("用药调整已保存。")
                st.rerun()

        section("用药调整时间轴")
        show_table(meds_all)

        if meds_all:
            st.markdown("#### 删除误录的用药记录")
            labels = {
                f"{m.get('medication_date')}｜{m.get('medicine_name')}｜{m.get('dose') or ''}｜{m.get('adjustment_type') or ''}｜编号{m.get('medication_id')}": m.get("medication_id")
                for m in meds_all
            }
            selected_label = st.selectbox("选择要删除的误录记录", list(labels.keys()), key="delete_med_select")
            if st.button("删除所选用药记录", key="delete_med_button"):
                delete("medication_records", "medication_id", labels[selected_label])
                st.success("已删除所选用药记录。")
                st.rerun()
    with tabs[3]:
        with st.form("tongue"):
            a,b,c=st.columns(3); td=a.date_input("舌象日期",date.today()); body=b.selectbox("舌质",["未记录","淡红","淡白","红","绛","紫暗","暗红","胖嫩","其他"]); coating=c.selectbox("舌苔",["未记录","薄白","白腻","黄腻","薄黄","少苔","厚苔","其他"])
            shape=st.selectbox("舌形",["未记录","正常","胖大","瘦薄","齿痕明显","裂纹明显","其他"]); img=st.file_uploader("舌象图片",type=["jpg","jpeg","png"]); tn=st.text_area("备注")
            if st.form_submit_button("保存舌象"):
                path,url=("", "")
                if img: path,url=upload(img,"tongue_images",p["patient_code"],str(td))
                insert("tongue_images",{"patient_id":p["patient_id"],"image_date":str(td),"image_path":path,"image_url":url,"tongue_body_color":body,"tongue_coating":coating,"tongue_shape":shape,"notes":tn}); st.rerun()
        with st.form("pulse"):
            pd1=st.date_input("脉象日期",date.today()); overall=st.text_input("整体脉象"); pn=st.text_area("脉象备注")
            if st.form_submit_button("保存脉象"): insert("pulse_records",{"patient_id":p["patient_id"],"pulse_date":str(pd1),"overall_pulse":overall,"notes":pn}); st.rerun()
        show_table(rel.get("tongues",[])); show_table(rel.get("pulses",[]))
    with tabs[4]:
        section("批量录入辅助检查")
        df=pd.DataFrame(LAB_TEMPLATES,columns=["类别","项目","单位","参考下限","参考上限"])
        check_date = st.date_input("本次检查日期", value=date.today(), key="batch_lab_date")
        edit=st.data_editor(df.assign(结果数值=None,文字结果="",医院=""),use_container_width=True,num_rows="dynamic")
        if st.button("保存批量检查"):
            n=0
            for _,r in edit.iterrows():
                if pd.notna(r.get("结果数值")) or str(r.get("文字结果") or "").strip():
                    insert("lab_results",{
                        "patient_id":p["patient_id"],
                        "lab_date":str(check_date),
                        "lab_category":r.get("类别"),
                        "item_name":r.get("项目"),
                        "result_value":None if pd.isna(r.get("结果数值")) else float(r.get("结果数值")),
                        "result_text":r.get("文字结果"),
                        "unit":r.get("单位"),
                        "reference_low":None if pd.isna(r.get("参考下限")) else float(r.get("参考下限")),
                        "reference_high":None if pd.isna(r.get("参考上限")) else float(r.get("参考上限")),
                        "abnormal_flag":abnormal(r.get("结果数值"),r.get("文字结果"),r.get("参考下限"),r.get("参考上限")),
                        "hospital_name":r.get("医院")
                    })
                    n+=1
            st.success(f"保存 {n} 条")
            st.rerun()

        section("历史辅助检查")
        labs_all = sorted(rel.get("labs", []), key=lambda x: sort_key_date_id(x, "lab_date", "lab_id"), reverse=True)
        show_table(labs_all)

        if labs_all:
            section("编辑辅助检查记录")
            labels = {
                f"{x.get('lab_date')}｜{x.get('item_name')}｜{x.get('result_value') or x.get('result_text') or '未填结果'}｜编号{x.get('lab_id')}": x
                for x in labs_all
            }
            selected_lab_label = st.selectbox("选择要编辑的检查记录", list(labels.keys()), key="edit_lab_select")
            lab = labels[selected_lab_label]
            with st.form(f"edit_lab_form_{lab.get('lab_id')}"):
                a,b,c,d = st.columns(4)
                lab_date = a.date_input("检查日期", value=as_date(lab.get("lab_date")), key=f"lab_date_{lab.get('lab_id')}")
                category = b.text_input("类别", value=lab.get("lab_category") or "", key=f"lab_category_{lab.get('lab_id')}")
                item = c.text_input("项目", value=lab.get("item_name") or "", key=f"lab_item_{lab.get('lab_id')}")
                unit = d.text_input("单位", value=lab.get("unit") or "", key=f"lab_unit_{lab.get('lab_id')}")
                e,f,g,h = st.columns(4)
                result_value_text = e.text_input("结果数值", value="" if lab.get("result_value") is None else str(lab.get("result_value")), key=f"lab_value_{lab.get('lab_id')}")
                result_text = f.text_input("文字结果", value=lab.get("result_text") or "", key=f"lab_text_{lab.get('lab_id')}")
                low_text = g.text_input("参考下限", value="" if lab.get("reference_low") is None else str(lab.get("reference_low")), key=f"lab_low_{lab.get('lab_id')}")
                high_text = h.text_input("参考上限", value="" if lab.get("reference_high") is None else str(lab.get("reference_high")), key=f"lab_high_{lab.get('lab_id')}")
                hospital = st.text_input("医院", value=lab.get("hospital_name") or "", key=f"lab_hospital_{lab.get('lab_id')}")
                notes = st.text_area("备注", value=lab.get("notes") or "", key=f"lab_notes_{lab.get('lab_id')}")
                ok_lab = st.form_submit_button("保存检查记录修改", use_container_width=True)
            if ok_lab:
                try:
                    rv = optional_float_text(result_value_text)
                    low = optional_float_text(low_text)
                    high = optional_float_text(high_text)
                    flag = abnormal(rv, result_text, low, high)
                    update("lab_results", "lab_id", lab.get("lab_id"), {
                        "lab_date": str(lab_date),
                        "lab_category": category,
                        "item_name": item,
                        "result_value": rv,
                        "result_text": result_text,
                        "unit": unit,
                        "reference_low": low,
                        "reference_high": high,
                        "abnormal_flag": flag,
                        "hospital_name": hospital,
                        "notes": notes
                    })
                    st.success("辅助检查记录已更新。")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
            if st.button("删除所选检查记录", key=f"delete_lab_{lab.get('lab_id')}"):
                delete("lab_results", "lab_id", lab.get("lab_id"))
                st.success("已删除所选检查记录。")
                st.rerun()
    with tabs[5]:
        ftype=st.selectbox("资料类型",["门诊病历","检验报告","影像报告","体检报告","用药清单","饮食记录","运动记录","知情同意书","其他"]); dd=st.date_input("资料日期",date.today()); file=st.file_uploader("上传文件",type=["jpg","jpeg","png","pdf","doc","docx","xls","xlsx","csv","txt"])
        if st.button("保存资料") and file:
            path,url=upload(file,f"uploaded_files/{ftype}",p["patient_code"],str(dd)); insert("uploaded_files",{"patient_id":p["patient_id"],"upload_date":str(date.today()),"document_date":str(dd),"file_type":ftype,"file_name":file.name,"file_path":path,"file_url":url,"file_extension":file.name.split(".")[-1].lower()}); st.rerun()
        show_table(rel.get("files",[]))
    with tabs[6]:
        html=a5_html(p,rel,(st.session_state.get("user") or {}).get("display_name","苏医生")); st.components.v1.html(html,height=900,scrolling=True); st.download_button("下载打印报告网页文件",html.encode("utf-8"),f"打印报告_{p.get('name')}_{date.today()}.html","text/html",use_container_width=True)
    with tabs[7]:
        section("编辑患者原始信息")
        visits_sorted = sorted(rel.get("visits", []), key=lambda x: sort_key_date_id(x, "visit_date", "visit_id"))
        initial_visit = visits_sorted[0] if visits_sorted else {}

        with st.form("editp"):
            a,b,c,d=st.columns(4)
            code = a.text_input("患者编号", p.get("patient_code") or "")
            name = b.text_input("姓名",p.get("name") or "")
            sex = c.selectbox("性别", ["男","女"], index=0 if p.get("sex")=="男" else 1)
            age = d.number_input("年龄",0,120,int(p.get("age") or 0))

            e,f,g,h=st.columns(4)
            phone = e.text_input("手机号",p.get("phone") or "")
            height = f.number_input("身高（厘米）",80.0,230.0,value=safe_float_for_edit(p.get("height_cm"),170.0))
            first_date = g.date_input("初诊日期", value=as_date(p.get("first_visit_date")))
            initial_weight = h.number_input("初诊体重（千克）",0.0,value=safe_float_for_edit(p.get("initial_weight_kg"),0.0))

            i,j=st.columns(2)
            target_weight = i.number_input("目标体重（千克）",0.0,value=safe_float_for_edit(p.get("target_weight_kg"),0.0))
            diag = j.text_input("主要诊断",p.get("main_diagnosis") or "")

            tags=st.multiselect("标签",TAGS,safe_tags(p), placeholder="请选择标签")
            notes=st.text_area("患者备注",p.get("notes") or "")

            section("编辑初诊基线")
            st.caption("这里用于修正初诊时的原始体格信息。没有记录的项目留空即可。")
            x1,x2,x3,x4,x5=st.columns(5)
            waist_text=x1.text_input("初诊腰围（厘米）", value="" if initial_visit.get("waist_cm") is None else str(initial_visit.get("waist_cm")))
            hip_text=x2.text_input("初诊臀围（厘米）", value="" if initial_visit.get("hip_cm") is None else str(initial_visit.get("hip_cm")))
            sbp_text=x3.text_input("初诊收缩压", value="" if initial_visit.get("systolic_bp") is None else str(initial_visit.get("systolic_bp")))
            dbp_text=x4.text_input("初诊舒张压", value="" if initial_visit.get("diastolic_bp") is None else str(initial_visit.get("diastolic_bp")))
            hr_text=x5.text_input("初诊心率", value="" if initial_visit.get("heart_rate") is None else str(initial_visit.get("heart_rate")))

            y1,y2,y3,y4=st.columns(4)
            diet0=y1.selectbox("初诊饮食", DIET, index=DIET.index(initial_visit.get("diet_adherence")) if initial_visit.get("diet_adherence") in DIET else 0)
            ex0=y2.selectbox("初诊运动", EX, index=EX.index(initial_visit.get("exercise_status")) if initial_visit.get("exercise_status") in EX else 0)
            sleep0=y3.selectbox("初诊睡眠", SL, index=SL.index(initial_visit.get("sleep_status")) if initial_visit.get("sleep_status") in SL else 0)
            stool0=y4.selectbox("初诊大便", ST, index=ST.index(initial_visit.get("stool_status")) if initial_visit.get("stool_status") in ST else 0)

            discomfort0=st.text_input("初诊不适症状", value=initial_visit.get("discomfort_symptoms") or "未诉明显不适")
            ass0=st.text_area("初诊评估", value=initial_visit.get("clinical_assessment") or "初诊建档，建立减重管理基线。")
            adv0=st.text_area("初诊建议", value=initial_visit.get("clinical_advice") or "进行饮食、运动及生活方式管理，按期复诊。")
            next0=st.date_input("初诊时设置的下次复诊日期", value=as_date(initial_visit.get("next_visit_date"), date.today()+timedelta(days=7)))

            ok_base = st.form_submit_button("保存患者原始信息与初诊基线", use_container_width=True)

        if ok_base:
            try:
                waist0=optional_float_text(waist_text)
                hip0=optional_float_text(hip_text)
                sbp0=optional_int_text(sbp_text)
                dbp0=optional_int_text(dbp_text)
                hr0=optional_int_text(hr_text)

                update_patient(p["patient_id"],{
                    "patient_code": code.strip(),
                    "name": name.strip(),
                    "sex": sex,
                    "age": int(age),
                    "phone": phone,
                    "height_cm": height,
                    "first_visit_date": str(first_date),
                    "initial_weight_kg": initial_weight,
                    "target_weight_kg": target_weight,
                    "main_diagnosis": diag,
                    "tags": tags,
                    "notes": notes
                })

                refreshed_patient = p.copy()
                refreshed_patient.update({
                    "patient_code": code.strip(),
                    "name": name.strip(),
                    "sex": sex,
                    "age": int(age),
                    "phone": phone,
                    "height_cm": height,
                    "first_visit_date": str(first_date),
                    "initial_weight_kg": initial_weight,
                    "target_weight_kg": target_weight,
                    "main_diagnosis": diag,
                    "tags": tags,
                    "notes": notes
                })

                initial_visit_data = {
                    "visit_date": str(first_date),
                    "weight_kg": initial_weight,
                    "waist_cm": waist0,
                    "hip_cm": hip0,
                    "systolic_bp": sbp0,
                    "diastolic_bp": dbp0,
                    "heart_rate": hr0,
                    "diet_adherence": diet0,
                    "exercise_status": ex0,
                    "sleep_status": sleep0,
                    "stool_status": stool0,
                    "discomfort_symptoms": discomfort0,
                    "clinical_assessment": ass0,
                    "clinical_advice": adv0,
                    "next_visit_date": str(next0),
                    "notes": "初诊基线已修正"
                }

                if initial_visit.get("visit_id"):
                    update_visit(refreshed_patient, initial_visit.get("visit_id"), initial_visit_data)
                else:
                    create_visit(refreshed_patient, initial_visit_data)

                st.success("患者原始信息与初诊基线已保存。")
                st.rerun()
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error("保存失败：请检查患者编号是否与其他患者重复，或稍后重试。")

def page_trends():
    hero("趋势分析","体重、腰围、体重指数、体成分估算与检验指标趋势")
    p=choose_patient(); 
    if not p: return
    rel=related(p["patient_id"]); cards(p,rel)
    visits=pd.DataFrame(rel.get("visits",[])); est=pd.DataFrame(rel.get("estimates",[])); labs=pd.DataFrame(rel.get("labs",[]))
    def make_line(df,x,y,title,ytitle):
        fig=px.line(df,x=x,y=y,markers=True,title=title,labels={x:"日期",y:ytitle})
        fig.update_traces(line=dict(width=3,color="#14a39a"),marker=dict(size=8,color="#14a39a"))
        fig.update_layout(title=dict(font=dict(size=22,color="#10233d")),plot_bgcolor="white",paper_bgcolor="white",font=dict(family="Microsoft YaHei",color="#42526b"),height=390,margin=dict(l=30,r=20,t=60,b=30),hovermode="x unified",showlegend=False)
        fig.update_xaxes(title_text="日期",gridcolor="#eef2f7",tickformat="%Y-%m-%d")
        fig.update_yaxes(title_text=ytitle,gridcolor="#eef2f7")
        chart_open(); st.plotly_chart(fig,use_container_width=True, config={"displayModeBar": False}); chart_close()
    if not visits.empty:
        visits["visit_date"]=pd.to_datetime(visits["visit_date"])
        for y,t,yt in [("weight_kg","体重变化","体重（千克）"),("waist_cm","腰围变化","腰围（厘米）"),("bmi","体重指数变化","体重指数")]:
            if y in visits: make_line(visits,"visit_date",y,t,yt)
    if not est.empty:
        est["estimate_date"]=pd.to_datetime(est["estimate_date"])
        for y,t,yt in [("body_fat_percent_est","体脂率估算变化","体脂率（%）"),("fat_mass_kg_est","脂肪量估算变化","脂肪量（千克）")]:
            if y in est: make_line(est,"estimate_date",y,t,yt)
    if not labs.empty:
        item=st.selectbox("检验项目",sorted(labs["item_name"].dropna().unique()))
        sub=labs[labs["item_name"]==item].copy(); sub["lab_date"]=pd.to_datetime(sub["lab_date"])
        make_line(sub,"lab_date","result_value",f"{item}趋势","检查结果")

def page_export():
    hero("导出与备份","导出云端数据备份和患者报告")
    if st.button("生成完整数据备份文件",use_container_width=True):
        z=export_zip(); st.download_button("下载完整数据备份文件",z,f"weight_clinic_backup_{date.today()}.zip","application/zip",use_container_width=True)
    p=choose_patient("选择患者生成报告")
    if p:
        html=a5_html(p,related(p["patient_id"]),(st.session_state.get("user") or {}).get("display_name","苏医生"))
        st.download_button("下载当前患者打印报告网页文件",html.encode("utf-8"),f"打印报告_{p.get('name')}_{date.today()}.html","text/html",use_container_width=True)

def page_settings():
    hero("系统设置","部署状态、医学边界和配置检查"); boundary(); st.write("云数据库连接状态：", "已连接" if ok() else "未连接"); st.markdown("部署步骤：执行建表文件 → 创建云端文件柜 → 上传代码仓库 → 在线平台选择主程序文件 → 填写密钥 → 发布。")

def main():
    if not require_login(): return
    stop_if_unconfigured()
    brand()
    page=st.sidebar.radio("功能导航",["患者管理","趋势分析","导出与备份","系统设置"],label_visibility="collapsed")
    logout()
    if page=="患者管理": page_patients()
    elif page=="趋势分析": page_trends()
    elif page=="导出与备份": page_export()
    else: page_settings()

if __name__=="__main__": main()
