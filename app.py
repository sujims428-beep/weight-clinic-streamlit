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
from modules.report import a5_html, doctor_a5_html
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
    for m in sorted(active_rows(meds), key=lambda x: sort_key_date_id(x, "medication_date", "medication_id")):
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


def render_medication_quick_panel(patient, meds_all, prefix="medquick"):
    """当前用药快捷交互：新增、调整、停用、删除误录。"""
    current_meds = current_medications(meds_all)
    section("当前用药快捷处理")
    c_add, c_hint = st.columns([1, 3])
    with c_add:
        if st.button("＋ 新增用药/调理", key=f"{prefix}_show_add", use_container_width=True):
            st.session_state[f"{prefix}_adding"] = not st.session_state.get(f"{prefix}_adding", False)
    with c_hint:
        st.caption("可在这里直接处理当前用药：新增、调整剂量/频次、停用，或删除误录记录。停用会写入时间轴，删除误录会直接删除该条记录。")

    if st.session_state.get(f"{prefix}_adding", False):
        with st.form(f"{prefix}_add_form"):
            a,b,c,d=st.columns(4)
            md=a.date_input("日期",date.today(),key=f"{prefix}_add_date")
            name=b.text_input("药物/方案",key=f"{prefix}_add_name")
            dose=c.text_input("剂量",key=f"{prefix}_add_dose")
            freq=d.text_input("频次",key=f"{prefix}_add_freq")
            reason=st.text_input("原因",value="新增用药/调理方案",key=f"{prefix}_add_reason")
            notes=st.text_area("备注",key=f"{prefix}_add_notes")
            ok_add=st.form_submit_button("保存新增用药/调理",use_container_width=True)
        if ok_add and name.strip():
            insert("medication_records",{
                "patient_id":patient["patient_id"],
                "medication_date":str(md),
                "medicine_name":name.strip(),
                "dose":dose,
                "frequency":freq,
                "current_status":"使用中",
                "adjustment_type":"新增",
                "adjustment_reason":reason,
                "notes":notes
            })
            st.session_state[f"{prefix}_adding"]=False
            st.success("新增用药/调理方案已保存。")
            st.rerun()

    if not current_meds:
        st.info("暂无当前用药。")
        return

    for m in current_meds:
        med_id = m.get("medication_id")
        st.markdown(
            f"""
            <div class="section-card">
              <b>{m.get('medicine_name','未命名')}</b><br>
              剂量：{m.get('dose') or '未记录'} ｜ 频次：{m.get('frequency') or '未记录'} ｜ 最近调整：{m.get('medication_date') or '未记录'}
            </div>
            """,
            unsafe_allow_html=True
        )
        c1,c2,c3,c4 = st.columns(4)
        if c1.button("调整剂量/频次", key=f"{prefix}_adjust_{med_id}", use_container_width=True):
            st.session_state[f"{prefix}_editing_med"] = med_id
        if c2.button("停用", key=f"{prefix}_stop_{med_id}", use_container_width=True):
            insert("medication_records",{
                "patient_id":patient["patient_id"],
                "medication_date":str(date.today()),
                "medicine_name":m.get("medicine_name"),
                "dose":m.get("dose"),
                "frequency":m.get("frequency"),
                "current_status":"已停用",
                "adjustment_type":"停用",
                "adjustment_reason":"医生手动停用",
                "notes":"由当前用药快捷处理生成"
            })
            st.success("已记录停用，并同步到用药时间轴。")
            st.rerun()
        if c3.button("暂停", key=f"{prefix}_pause_{med_id}", use_container_width=True):
            insert("medication_records",{
                "patient_id":patient["patient_id"],
                "medication_date":str(date.today()),
                "medicine_name":m.get("medicine_name"),
                "dose":m.get("dose"),
                "frequency":m.get("frequency"),
                "current_status":"暂停",
                "adjustment_type":"暂停",
                "adjustment_reason":"医生手动暂停",
                "notes":"由当前用药快捷处理生成"
            })
            st.success("已记录暂停，并同步到用药时间轴。")
            st.rerun()
        if c4.button("删除误录", key=f"{prefix}_delete_{med_id}", use_container_width=True):
            mark_record_void("medication_records","medication_id",m,"当前用药快捷处理标记误录")
            st.success("已标记为误录，可在恢复区恢复。")
            st.rerun()

        if st.session_state.get(f"{prefix}_editing_med") == med_id:
            with st.form(f"{prefix}_edit_form_{med_id}"):
                a,b,c,d=st.columns(4)
                adj_date=a.date_input("调整日期", value=date.today(), key=f"{prefix}_edit_date_{med_id}")
                adj_type=b.selectbox("调整类型", ["维持","加量","减量","调整方案"], key=f"{prefix}_edit_type_{med_id}")
                new_dose=c.text_input("调整后剂量", value=m.get("dose") or "", key=f"{prefix}_edit_dose_{med_id}")
                new_freq=d.text_input("调整后频次", value=m.get("frequency") or "", key=f"{prefix}_edit_freq_{med_id}")
                reason=st.text_input("调整原因", value="", key=f"{prefix}_edit_reason_{med_id}")
                notes=st.text_area("备注", value="", key=f"{prefix}_edit_notes_{med_id}")
                save_edit=st.form_submit_button("保存本次调整", use_container_width=True)
            if save_edit:
                insert("medication_records",{
                    "patient_id":patient["patient_id"],
                    "medication_date":str(adj_date),
                    "medicine_name":m.get("medicine_name"),
                    "dose":new_dose,
                    "frequency":new_freq,
                    "current_status":"使用中",
                    "adjustment_type":adj_type,
                    "adjustment_reason":reason,
                    "notes":notes
                })
                st.session_state[f"{prefix}_editing_med"] = None
                st.success("用药调整已保存，并同步到当前用药与时间轴。")
                st.rerun()

def add_ideal_line(fig, ideal_value, label="参考目标线"):
    """给趋势图添加红色虚线参考目标线。"""
    try:
        if ideal_value is None:
            return fig
        val = float(ideal_value)
        fig.add_hline(
            y=val,
            line_dash="dash",
            line_color="#ef4444",
            line_width=2,
            annotation_text=label,
            annotation_position="top left",
            annotation_font_color="#ef4444"
        )
    except Exception:
        pass
    return fig


VOID_PREFIX = "【误录】"

def is_void(row):
    """用备注前缀判断是否为误录记录，不新增数据库字段。"""
    return str((row or {}).get("notes") or "").strip().startswith(VOID_PREFIX)

def active_rows(rows):
    return [r for r in (rows or []) if not is_void(r)]

def void_rows(rows):
    return [r for r in (rows or []) if is_void(r)]

def mark_record_void(table, pk, row, reason="医生标记为误录"):
    """软删除：不真正删除，只在备注前加误录标记，便于恢复。"""
    old_notes = str((row or {}).get("notes") or "")
    if old_notes.startswith(VOID_PREFIX):
        return
    update(table, pk, row.get(pk), {"notes": f"{VOID_PREFIX}{reason}；{old_notes}"})

def restore_record(table, pk, row):
    old_notes = str((row or {}).get("notes") or "")
    new_notes = old_notes
    if old_notes.startswith(VOID_PREFIX):
        new_notes = old_notes.replace(VOID_PREFIX, "", 1)
        if "；" in new_notes:
            new_notes = new_notes.split("；", 1)[1]
    update(table, pk, row.get(pk), {"notes": new_notes})

def render_restore_box(title, table, pk, rows, label_fields):
    bad = void_rows(rows)
    if not bad:
        return
    with st.expander(f"恢复{title}误录记录", expanded=False):
        labels = {}
        for r in bad:
            text = "｜".join([str(r.get(f) or "") for f in label_fields])
            labels[f"{text}｜编号{r.get(pk)}"] = r
        selected = st.selectbox("选择要恢复的记录", list(labels.keys()), key=f"restore_{table}_{pk}")
        if st.button(f"恢复所选{title}记录", key=f"restore_btn_{table}_{pk}"):
            restore_record(table, pk, labels[selected])
            st.success("已恢复所选记录。")
            st.rerun()

def abnormal_first_labs(labs, limit=4):
    rows = active_rows(labs)
    abnormal_flags = {"升高", "降低", "阳性"}
    abnormal_rows = [x for x in rows if str(x.get("abnormal_flag") or "") in abnormal_flags]
    normal_rows = [x for x in rows if x not in abnormal_rows]
    ordered = sorted(abnormal_rows, key=lambda x: str(x.get("lab_date") or ""), reverse=True)
    if len(ordered) < limit:
        ordered += sorted(normal_rows, key=lambda x: str(x.get("lab_date") or ""), reverse=True)
    return ordered[:limit]

def quick_lab_form(patient, key_prefix="quick_lab"):
    section("快捷录入辅助检查")
    template = pd.DataFrame(LAB_TEMPLATES, columns=["类别","项目","单位","参考下限","参考上限"])
    item_names = template["项目"].tolist()
    with st.form(f"{key_prefix}_form"):
        c1,c2,c3,c4 = st.columns(4)
        lab_date = c1.date_input("检查日期", value=date.today(), key=f"{key_prefix}_date")
        item = c2.selectbox("检查项目", item_names, key=f"{key_prefix}_item")
        selected = template[template["项目"] == item].iloc[0].to_dict()
        result_value_text = c3.text_input("结果数值", value="", placeholder="未测可留空", key=f"{key_prefix}_value")
        result_text = c4.text_input("文字结果", value="", placeholder="如阴性/阳性", key=f"{key_prefix}_text")
        c5,c6,c7 = st.columns(3)
        low_text = c5.text_input("参考下限", value=str(selected.get("参考下限") if selected.get("参考下限") is not None else ""), key=f"{key_prefix}_low")
        high_text = c6.text_input("参考上限", value=str(selected.get("参考上限") if selected.get("参考上限") is not None else ""), key=f"{key_prefix}_high")
        hospital = c7.text_input("医院", value="", key=f"{key_prefix}_hospital")
        ok_lab = st.form_submit_button("保存辅助检查", use_container_width=True)
    if ok_lab:
        try:
            rv = optional_float_text(result_value_text)
            low = optional_float_text(low_text)
            high = optional_float_text(high_text)
            rt = str(result_text or "").strip()
            if rv is None and not rt:
                st.warning("请至少填写结果数值或文字结果。")
                return
            insert("lab_results", {
                "patient_id": patient["patient_id"],
                "lab_date": str(lab_date),
                "lab_category": selected.get("类别"),
                "item_name": item,
                "result_value": rv,
                "result_text": rt,
                "unit": selected.get("单位"),
                "reference_low": low,
                "reference_high": high,
                "abnormal_flag": abnormal(rv, rt, low, high),
                "hospital_name": hospital
            })
            st.success("辅助检查已保存。")
            st.rerun()
        except ValueError as e:
            st.error(str(e))





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

def visit_form(p, v=None, form_suffix='', show_extended_fields=True):
    v=v or {}
    with st.form(f"visit_{v.get('visit_id','new')}_{form_suffix}"):
        a,b,c,d=st.columns(4)
        vd=a.date_input("复诊日期", pd.to_datetime(v.get("visit_date") or date.today()).date()); wt=b.number_input("体重（千克）",0.0,value=float(v.get("weight_kg") or p.get("initial_weight_kg") or 0)); waist=c.number_input("腰围（厘米）",0.0,value=float(v.get("waist_cm") or 0)); hip=d.number_input("臀围（厘米）",0.0,value=float(v.get("hip_cm") or 0))
        st.info(f"体重指数：{fmt(bmi(wt,p.get('height_cm')))}；腰臀比：{fmt(whr(waist,hip))}；累计减重：{fmt(loss(p.get('initial_weight_kg'),wt))}%")
        e,f,g=st.columns(3); sbp=e.number_input("收缩压",0,value=int(v.get("systolic_bp") or 0)); dbp=f.number_input("舒张压",0,value=int(v.get("diastolic_bp") or 0)); hr=g.number_input("心率",0,value=int(v.get("heart_rate") or 0))
        h,i,j,k=st.columns(4)
        diet=h.selectbox("饮食",DIET,index=DIET.index(v.get("diet_adherence")) if v.get("diet_adherence") in DIET else 0); ex=i.selectbox("运动",EX,index=EX.index(v.get("exercise_status")) if v.get("exercise_status") in EX else 0); sleep=j.selectbox("睡眠",SL,index=SL.index(v.get("sleep_status")) if v.get("sleep_status") in SL else 0); stool=k.selectbox("大便",ST,index=ST.index(v.get("stool_status")) if v.get("stool_status") in ST else 0)
        dis=st.text_input("不适症状",v.get("discomfort_symptoms") or "未诉明显不适")
        if show_extended_fields:
            ass=st.text_area("评估",v.get("clinical_assessment") or "")
            adv=st.text_area("建议",v.get("clinical_advice") or "")
            nextd=st.date_input("下次复诊",pd.to_datetime(v.get("next_visit_date") or (date.today()+timedelta(days=7))).date())
            notes=st.text_area("备注",v.get("notes") or "")
        else:
            ass=v.get("clinical_assessment") or ""
            adv=v.get("clinical_advice") or ""
            nextd=pd.to_datetime(v.get("next_visit_date") or (date.today()+timedelta(days=7))).date()
            notes=v.get("notes") or ""
        ok=st.form_submit_button("保存复诊记录", use_container_width=True)
    if ok:
        row={"visit_date":str(vd),"weight_kg":wt,"waist_cm":waist or None,"hip_cm":hip or None,"systolic_bp":sbp or None,"diastolic_bp":dbp or None,"heart_rate":hr or None,"diet_adherence":diet,"exercise_status":ex,"sleep_status":sleep,"stool_status":stool,"discomfort_symptoms":dis,"clinical_assessment":ass,"clinical_advice":adv,"next_visit_date":str(nextd),"notes":notes}
        if v.get("visit_id"): update_visit(p,v["visit_id"],row)
        else: create_visit(p,row)
        st.success("已保存"); st.rerun()

def patient_detail(pid=None):
    p=get_patient(pid or st.session_state.get("patient_id"))
    if not p: st.info("请选择患者"); return
    raw_rel=related(p["patient_id"])
    rel={k: active_rows(v) if isinstance(v, list) else v for k, v in raw_rel.items()}
    hero("患者详情","患者随访、用药、舌脉、辅助检查与报告管理")
    patient_header(p)
    cards(p,rel)

    section("快捷操作")
    q1,q2,q3,q4=st.columns(4)
    if q1.button("今日复诊", use_container_width=True, key=f"quick_visit_{p['patient_id']}"):
        st.session_state["quick_action"] = "visit"
    if q2.button("调整用药", use_container_width=True, key=f"quick_med_{p['patient_id']}"):
        st.session_state["quick_action"] = "med"
    if q3.button("录入检查", use_container_width=True, key=f"quick_lab_{p['patient_id']}"):
        st.session_state["quick_action"] = "lab"
    if q4.button("生成报告", use_container_width=True, key=f"quick_report_{p['patient_id']}"):
        st.session_state["quick_action"] = "report"

    if st.session_state.get("quick_action") == "visit":
        section("今日复诊")
        visit_form(p, form_suffix="quick", show_extended_fields=False)
    elif st.session_state.get("quick_action") == "med":
        render_medication_quick_panel(p, sorted(raw_rel.get("meds", []), key=lambda x: sort_key_date_id(x, "medication_date", "medication_id"), reverse=True), prefix=f"quick_med_panel_{p['patient_id']}")
    elif st.session_state.get("quick_action") == "lab":
        quick_lab_form(p, key_prefix=f"quick_lab_{p['patient_id']}")
    elif st.session_state.get("quick_action") == "report":
        html_patient=a5_html(p,rel,(st.session_state.get("user") or {}).get("display_name","苏医生"))
        html_doctor=doctor_a5_html(p,rel,(st.session_state.get("user") or {}).get("display_name","苏医生"))
        cpa,cpb=st.columns(2)
        cpa.download_button("下载患者版报告",html_patient.encode("utf-8"),f"患者版报告_{p.get('name')}_{date.today()}.html","text/html",use_container_width=True)
        cpb.download_button("下载医生版报告",html_doctor.encode("utf-8"),f"医生版报告_{p.get('name')}_{date.today()}.html","text/html",use_container_width=True)
    tabs=st.tabs(["概览","复诊记录","用药调整","舌象/脉象","辅助检查","资料归档","打印报告","编辑基础信息"])
    with tabs[0]:
        visits=rel.get("visits",[]); lv=sorted(visits,key=lambda x:str(x.get("visit_date") or ""),reverse=True)[0] if visits else {}
        meds=current_med_names(rel.get("meds",[]))
        tongue=sorted(rel.get("tongues",[]),key=lambda x:str(x.get("image_date") or ""),reverse=True)[0] if rel.get("tongues") else {}
        pulse=sorted(rel.get("pulses",[]),key=lambda x:str(x.get("pulse_date") or ""),reverse=True)[0] if rel.get("pulses") else {}
        labs=abnormal_first_labs(rel.get("labs",[]), limit=4)
        lab_text=[f"{x.get('item_name','')}：{x.get('result_value') or x.get('result_text') or '暂无'} {x.get('unit') or ''}（{x.get('abnormal_flag') or '未判断'}）" for x in labs]
        overview_cards(current_med_names(rel.get("meds",[]))[-4:], f"舌质 {tongue.get('tongue_body_color','未记录')}，舌苔 {tongue.get('tongue_coating','未记录')}，舌形 {tongue.get('tongue_shape','未记录')}", pulse.get('overall_pulse','未记录'), lab_text)
        render_medication_quick_panel(p, sorted(rel.get("meds", []), key=lambda x: sort_key_date_id(x, "medication_date", "medication_id"), reverse=True), prefix=f"overview_med_{p['patient_id']}")
        section("最近复诊摘要")
        st.markdown(f"<div class='section-card'><p><b>本次评估：</b>{lv.get('clinical_assessment') or '暂无评估'}</p><p><b>本次建议：</b>{lv.get('clinical_advice') or '暂无建议'}</p></div>", unsafe_allow_html=True)
    with tabs[1]:
        section("新增复诊记录"); visit_form(p)
        section("历次复诊记录")
        render_restore_box("复诊", "visits", "visit_id", raw_rel.get("visits", []), ["visit_date","weight_kg","clinical_assessment"])
        for v in sorted(rel.get("visits",[]),key=lambda x:str(x.get("visit_date") or ""),reverse=True):
            with st.expander(f"{v.get('visit_date')}｜体重 {fmt(v.get('weight_kg'))} 千克"):
                visit_form(p,v)
                if st.button("删除该复诊记录", key=f"delv{v['visit_id']}"): mark_record_void("visits", "visit_id", v, "医生标记为误录"); st.success("已标记为误录，可恢复。"); st.rerun()
    with tabs[2]:
        section("当前用药")
        meds_all = sorted(rel.get("meds", []), key=lambda x: sort_key_date_id(x, "medication_date", "medication_id"), reverse=True)
        render_medication_quick_panel(p, meds_all, prefix=f"tab_med_{p['patient_id']}")

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
        show_table(active_rows(meds_all))
        render_restore_box("用药", "medication_records", "medication_id", meds_all, ["medication_date","medicine_name","dose","adjustment_type"])

        if active_rows(meds_all):
            st.markdown("#### 删除误录的用药记录")
            labels = {
                f"{m.get('medication_date')}｜{m.get('medicine_name')}｜{m.get('dose') or ''}｜{m.get('adjustment_type') or ''}｜编号{m.get('medication_id')}": m.get("medication_id")
                for m in active_rows(meds_all)
            }
            selected_label = st.selectbox("选择要删除的误录记录", list(labels.keys()), key="delete_med_select")
            if st.button("删除所选用药记录", key="delete_med_button"):
                mark_record_void("medication_records", "medication_id", next(x for x in meds_all if x.get("medication_id")==labels[selected_label]), "医生标记为误录")
                st.success("已标记为误录，可在恢复区恢复。")
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
            try:
                for _,r in edit.iterrows():
                    result_value = optional_float_text(r.get("结果数值"))
                    result_text = str(r.get("文字结果") or "").strip()
                    reference_low = optional_float_text(r.get("参考下限"))
                    reference_high = optional_float_text(r.get("参考上限"))
                    if result_value is not None or result_text:
                        insert("lab_results",{
                            "patient_id":p["patient_id"],
                            "lab_date":str(check_date),
                            "lab_category":r.get("类别"),
                            "item_name":r.get("项目"),
                            "result_value":result_value,
                            "result_text":result_text,
                            "unit":r.get("单位"),
                            "reference_low":reference_low,
                            "reference_high":reference_high,
                            "abnormal_flag":abnormal(result_value,result_text,reference_low,reference_high),
                            "hospital_name":r.get("医院")
                        })
                        n+=1
                st.success(f"保存 {n} 条")
                st.rerun()
            except ValueError as e:
                st.error(str(e))

        section("历史辅助检查")
        labs_all = sorted(rel.get("labs", []), key=lambda x: sort_key_date_id(x, "lab_date", "lab_id"), reverse=True)
        show_table(active_rows(labs_all))
        render_restore_box("辅助检查", "lab_results", "lab_id", labs_all, ["lab_date","item_name","result_value","abnormal_flag"])

        if active_rows(labs_all):
            section("编辑辅助检查记录")
            labels = {
                f"{x.get('lab_date')}｜{x.get('item_name')}｜{x.get('result_value') or x.get('result_text') or '未填结果'}｜编号{x.get('lab_id')}": x
                for x in active_rows(labs_all)
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
                mark_record_void("lab_results", "lab_id", lab, "医生标记为误录")
                st.success("已标记为误录，可在恢复区恢复。")
                st.rerun()
    with tabs[5]:
        ftype=st.selectbox("资料类型",["门诊病历","检验报告","影像报告","体检报告","用药清单","饮食记录","运动记录","知情同意书","其他"]); dd=st.date_input("资料日期",date.today()); file=st.file_uploader("上传文件",type=["jpg","jpeg","png","pdf","doc","docx","xls","xlsx","csv","txt"])
        if st.button("保存资料") and file:
            path,url=upload(file,f"uploaded_files/{ftype}",p["patient_code"],str(dd)); insert("uploaded_files",{"patient_id":p["patient_id"],"upload_date":str(date.today()),"document_date":str(dd),"file_type":ftype,"file_name":file.name,"file_path":path,"file_url":url,"file_extension":file.name.split(".")[-1].lower()}); st.rerun()
        show_table(rel.get("files",[]))
    with tabs[6]:
        report_type = st.radio("报告类型", ["患者版", "医生版"], horizontal=True)
        if report_type == "患者版":
            html=a5_html(p,rel,(st.session_state.get("user") or {}).get("display_name","苏医生"))
            file_name=f"患者版报告_{p.get('name')}_{date.today()}.html"
        else:
            html=doctor_a5_html(p,rel,(st.session_state.get("user") or {}).get("display_name","苏医生"))
            file_name=f"医生版报告_{p.get('name')}_{date.today()}.html"
        st.components.v1.html(html,height=900,scrolling=True)
        st.download_button(f"下载{report_type}报告网页文件",html.encode("utf-8"),file_name,"text/html",use_container_width=True)
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
    raw_rel=related(p["patient_id"])
    rel={k: active_rows(v) if isinstance(v, list) else v for k, v in raw_rel.items()}
    cards(p,rel)
    visits=pd.DataFrame(rel.get("visits",[])); est=pd.DataFrame(rel.get("estimates",[])); labs=pd.DataFrame(rel.get("labs",[]))
    def make_line(df,x,y,title,ytitle,ideal_value=None,ideal_label="参考目标线"):
        fig=px.line(df,x=x,y=y,markers=True,title=title,labels={x:"日期",y:ytitle})
        fig.update_traces(line=dict(width=3,color="#14a39a"),marker=dict(size=8,color="#14a39a"))
        add_ideal_line(fig, ideal_value, ideal_label)
        fig.update_layout(title=dict(font=dict(size=22,color="#10233d")),plot_bgcolor="white",paper_bgcolor="white",font=dict(family="Microsoft YaHei",color="#42526b"),height=390,margin=dict(l=30,r=20,t=60,b=30),hovermode="x unified",showlegend=False)
        fig.update_xaxes(title_text="日期",gridcolor="#eef2f7",tickformat="%Y-%m-%d")
        fig.update_yaxes(title_text=ytitle,gridcolor="#eef2f7")
        chart_open(); st.plotly_chart(fig,use_container_width=True, config={"displayModeBar": False}); chart_close()

    ideal_weight_value = p.get("target_weight_kg")
    ideal_waist_value = 85 if p.get("sex")=="男" else 80
    ideal_bmi_value = 23.9
    ideal_body_fat_value = 20 if p.get("sex")=="男" else 28
    ideal_fat_mass_value = None
    try:
        if ideal_weight_value and ideal_body_fat_value:
            ideal_fat_mass_value = float(ideal_weight_value) * float(ideal_body_fat_value) / 100
    except Exception:
        ideal_fat_mass_value = None

    if not visits.empty:
        visits["visit_date"]=pd.to_datetime(visits["visit_date"])
        section("核心趋势")
        chart_cfg = [
            ("weight_kg","体重变化","体重（千克）",ideal_weight_value,"目标体重"),
            ("waist_cm","腰围变化","腰围（厘米）",ideal_waist_value,"腰围参考目标"),
            ("bmi","体重指数变化","体重指数",ideal_bmi_value,"体重指数参考上限"),
        ]
        for y,t,yt,ideal,label in chart_cfg:
            if y in visits: make_line(visits,"visit_date",y,t,yt,ideal,label)
    else:
        st.info("暂无复诊趋势数据。")

    with st.expander("展开查看体成分估算趋势", expanded=False):
        if not est.empty:
            est["estimate_date"]=pd.to_datetime(est["estimate_date"])
            chart_cfg_est = [
                ("body_fat_percent_est","体脂率估算变化","体脂率（%）",ideal_body_fat_value,"体脂率参考目标"),
                ("fat_mass_kg_est","脂肪量估算变化","脂肪量（千克）",ideal_fat_mass_value,"脂肪量参考目标"),
            ]
            for y,t,yt,ideal,label in chart_cfg_est:
                if y in est: make_line(est,"estimate_date",y,t,yt,ideal,label)
        else:
            st.info("暂无体成分估算趋势。")

    with st.expander("展开查看检验指标趋势", expanded=False):
        if not labs.empty:
            item=st.selectbox("检验项目",sorted(labs["item_name"].dropna().unique()))
            sub=labs[labs["item_name"]==item].copy(); sub["lab_date"]=pd.to_datetime(sub["lab_date"])
            ref_high = None
            try:
                vals = sub["reference_high"].dropna().tolist()
                ref_high = vals[-1] if vals else None
            except Exception:
                ref_high = None
            make_line(sub,"lab_date","result_value",f"{item}趋势","检查结果",ref_high,"参考上限")
        else:
            st.info("暂无检验趋势。")

def page_export():
    hero("导出与备份","导出云端数据备份和患者报告")
    if st.button("生成完整数据备份文件",use_container_width=True):
        z=export_zip(); st.download_button("下载完整数据备份文件",z,f"weight_clinic_backup_{date.today()}.zip","application/zip",use_container_width=True)
    p=choose_patient("选择患者生成报告")
    if p:
        rel=related(p["patient_id"])
        html_patient=a5_html(p,rel,(st.session_state.get("user") or {}).get("display_name","苏医生"))
        html_doctor=doctor_a5_html(p,rel,(st.session_state.get("user") or {}).get("display_name","苏医生"))
        c1,c2=st.columns(2)
        c1.download_button("下载患者版报告",html_patient.encode("utf-8"),f"患者版报告_{p.get('name')}_{date.today()}.html","text/html",use_container_width=True)
        c2.download_button("下载医生版报告",html_doctor.encode("utf-8"),f"医生版报告_{p.get('name')}_{date.today()}.html","text/html",use_container_width=True)

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
