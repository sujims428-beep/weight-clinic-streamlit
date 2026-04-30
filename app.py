from __future__ import annotations
from datetime import date, timedelta
import json
import pandas as pd
import plotly.express as px
import streamlit as st
from modules.auth import require_login, logout
from modules.calc import LAB_TEMPLATES, abnormal, bmi, fmt, ideal_weight, loss, whr
from modules.db import *
from modules.report import a5_html
from modules.ui import css, hero, boundary, tags_html
try:
    from modules.ui import brand, section, patient_header
except ImportError:
    def brand():
        st.sidebar.markdown("### ⚖️ 逢安堂")
    def section(title):
        st.subheader(title)
    def patient_header(patient):
        st.markdown(
            f"### {patient.get('name','')}\n"
            f"{patient.get('patient_code','')}｜{patient.get('sex','')}｜{patient.get('age','')}岁"
        )

st.set_page_config(page_title="减重门诊管理系统（逢安堂）", page_icon="⚖️", layout="wide")
css()

TAGS=["减重门诊","糖尿病","高脂血症","脂肪肝","高尿酸血症","中药调理","重点复诊","依从性差","血糖异常","血脂异常","代谢综合征"]
DIET=["良好","一般","较差","未记录","基本执行"]; EX=["规律运动","偶尔运动","未运动","未记录"]; SL=["良好","一般","较差","失眠","未记录"]; ST=["正常","便秘","腹泻","不规律","未记录"]
COLMAP={"patient_code":"患者编号","name":"姓名","sex":"性别","age":"年龄","phone":"手机号","height_cm":"身高","first_visit_date":"初诊日期","initial_weight_kg":"初诊体重","target_weight_kg":"目标体重","main_diagnosis":"主要诊断","tags":"标签","notes":"备注","visit_date":"复诊日期","weight_kg":"体重","bmi":"体重指数","waist_cm":"腰围","hip_cm":"臀围","waist_hip_ratio":"腰臀比","systolic_bp":"收缩压","diastolic_bp":"舒张压","heart_rate":"心率","diet_adherence":"饮食执行","exercise_status":"运动情况","sleep_status":"睡眠情况","stool_status":"大便情况","discomfort_symptoms":"不适症状","clinical_assessment":"本次评估","clinical_advice":"本次建议","next_visit_date":"下次复诊","medication_date":"用药日期","medicine_name":"药物/方案","dose":"剂量","frequency":"频次","current_status":"状态","adjustment_type":"调整类型","adjustment_reason":"调整原因","adverse_reaction":"不良反应","lab_date":"检查日期","lab_category":"类别","item_name":"项目","result_value":"结果数值","result_text":"文字结果","unit":"单位","reference_low":"参考下限","reference_high":"参考上限","abnormal_flag":"异常提示","hospital_name":"医院","image_date":"舌象日期","tongue_body_color":"舌质","tongue_coating":"舌苔","tongue_shape":"舌形","tooth_marks":"齿痕","cracks":"裂纹","moisture":"津液","pulse_date":"脉象日期","overall_pulse":"整体脉象","left_cun":"左寸","left_guan":"左关","left_chi":"左尺","right_cun":"右寸","right_guan":"右关","right_chi":"右尺","upload_date":"上传日期","document_date":"资料日期","file_type":"资料类型","file_name":"文件名","file_url":"文件链接"}

def show_table(rows, height=None):
    df=pd.DataFrame(rows)
    if df.empty:
        st.info("暂无数据"); return
    hidden=[c for c in df.columns if c.endswith("_id") or c in ["created_at","updated_at","is_deleted","image_path","file_path","source_file_path"]]
    df=df.drop(columns=[c for c in hidden if c in df.columns], errors="ignore")
    df=df.rename(columns={k:v for k,v in COLMAP.items() if k in df.columns})
    st.dataframe(df, use_container_width=True, hide_index=True, height=height)

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
        with st.form("new_patient"):
            a,b,c,d=st.columns(4)
            code=a.text_input("患者编号", f"P{date.today().year}0001"); name=b.text_input("姓名"); sex=c.selectbox("性别",["男","女"]); age=d.number_input("年龄",0,120,40)
            e,f,g,h=st.columns(4)
            phone=e.text_input("手机号"); height=f.number_input("身高（厘米）",80.0,230.0,170.0); first=g.date_input("初诊日期",date.today()); weight=h.number_input("初诊体重（千克）",0.0,value=80.0)
            lo,hi,mid=ideal_weight(height); st.info(f"当前体重指数：{fmt(bmi(weight,height))}；目标体重参考：{fmt(lo)}–{fmt(hi)} 千克")
            target=st.number_input("目标体重（千克）",0.0,value=float(mid or 65)); diag=st.text_input("主要诊断/主要问题","肥胖/体重管理")
            tags=st.multiselect("标签",TAGS,["减重门诊"], placeholder="请选择标签"); notes=st.text_area("备注")
            section("初诊基线")
            x1,x2,x3,x4,x5=st.columns(5)
            waist=x1.number_input("腰围（厘米）",0.0,value=0.0); hip=x2.number_input("臀围（厘米）",0.0,value=0.0); sbp=x3.number_input("收缩压",0,value=0); dbp=x4.number_input("舒张压",0,value=0); hr=x5.number_input("心率",0,value=0)
            y1,y2,y3,y4=st.columns(4)
            diet=y1.selectbox("饮食",DIET); ex=y2.selectbox("运动",EX); sleep=y3.selectbox("睡眠",SL); stool=y4.selectbox("大便",ST)
            discomfort=st.text_input("不适症状","未诉明显不适"); ass=st.text_area("初诊评估","初诊建档，建立减重管理基线。"); adv=st.text_area("初诊建议","进行饮食、运动及生活方式管理，按期复诊。")
            nextd=st.date_input("下次复诊日期", date.today()+timedelta(days=7))
            submitted=st.form_submit_button("保存患者并生成初诊基线", use_container_width=True)
        if submitted:
            if not name: st.error("姓名不能为空"); return
            p=create_patient({"patient_code":code,"name":name,"sex":sex,"age":int(age),"phone":phone,"height_cm":height,"first_visit_date":str(first),"initial_weight_kg":weight,"target_weight_kg":target,"main_diagnosis":diag,"tags":tags,"notes":notes})
            create_visit(p,{"visit_date":str(first),"weight_kg":weight,"waist_cm":waist or None,"hip_cm":hip or None,"systolic_bp":sbp or None,"diastolic_bp":dbp or None,"heart_rate":hr or None,"diet_adherence":diet,"exercise_status":ex,"sleep_status":sleep,"stool_status":stool,"discomfort_symptoms":discomfort,"clinical_assessment":ass,"clinical_advice":adv,"next_visit_date":str(nextd)})
            st.session_state["patient_id"]=p["patient_id"]; st.success("患者保存成功"); st.rerun()

def page_patients():
    hero("患者管理","新增、搜索、筛选并进入患者详情")
    boundary(); new_patient_panel()
    ps=list_patients()
    if not ps: return
    q=st.text_input("搜索患者", placeholder="姓名 / 手机号 / 患者编号"); tf=st.multiselect("标签筛选",TAGS, placeholder="请选择标签")
    rows=[]
    for p in ps:
        tags=safe_tags(p)
        if q and q not in str(p.get("name","")) and q not in str(p.get("phone","")) and q not in str(p.get("patient_code","")): continue
        if tf and not all(t in tags for t in tf): continue
        rel=related(p["patient_id"]); visits=rel.get("visits",[])
        lv=sorted(visits,key=lambda x:str(x.get("visit_date") or ""), reverse=True)[0] if visits else {}
        rows.append({"patient_id":p["patient_id"],"编号":p.get("patient_code"),"姓名":p.get("name"),"性别":p.get("sex"),"年龄":p.get("age"),"手机号":p.get("phone"),"初诊日期":p.get("first_visit_date"),"最近复诊":lv.get("visit_date"),"最近体重":lv.get("weight_kg"),"最近体重指数":bmi(lv.get("weight_kg"),p.get("height_cm")) if lv else None,"主要诊断":p.get("main_diagnosis"),"标签":"、".join(tags)})
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
        section("最近复诊摘要"); visits=rel.get("visits",[]); lv=sorted(visits,key=lambda x:str(x.get("visit_date") or ""),reverse=True)[0] if visits else {}
        st.write(lv.get("clinical_assessment") or "暂无评估"); st.write("建议：", lv.get("clinical_advice") or "暂无建议")
    with tabs[1]:
        section("新增复诊记录"); visit_form(p)
        section("历次复诊记录")
        for v in sorted(rel.get("visits",[]),key=lambda x:str(x.get("visit_date") or ""),reverse=True):
            with st.expander(f"{v.get('visit_date')}｜体重 {fmt(v.get('weight_kg'))} 千克"):
                visit_form(p,v)
                if st.button("删除该复诊记录", key=f"delv{v['visit_id']}"): delete_visit(v["visit_id"]); st.rerun()
    with tabs[2]:
        with st.form("med"):
            a,b,c,d=st.columns(4); md=a.date_input("日期",date.today()); name=b.text_input("药物/方案"); dose=c.text_input("剂量"); freq=d.text_input("频次")
            status=st.selectbox("状态",["使用中","已停用","暂停","未知"]); adj=st.selectbox("调整类型",["新增","维持","加量","减量","停用","调整方案"]); reason=st.text_input("原因"); notes=st.text_area("备注")
            if st.form_submit_button("保存用药调整") and name: insert("medication_records",{"patient_id":p["patient_id"],"medication_date":str(md),"medicine_name":name,"dose":dose,"frequency":freq,"current_status":status,"adjustment_type":adj,"adjustment_reason":reason,"notes":notes}); st.rerun()
        show_table(rel.get("meds",[]))
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
        df=pd.DataFrame(LAB_TEMPLATES,columns=["类别","项目","单位","参考下限","参考上限"]); edit=st.data_editor(df.assign(结果数值=None,文字结果="",医院=""),use_container_width=True,num_rows="dynamic")
        if st.button("保存批量检查"):
            n=0
            for _,r in edit.iterrows():
                if pd.notna(r.get("结果数值")) or str(r.get("文字结果") or "").strip():
                    insert("lab_results",{"patient_id":p["patient_id"],"lab_date":str(date.today()),"lab_category":r.get("类别"),"item_name":r.get("项目"),"result_value":None if pd.isna(r.get("结果数值")) else float(r.get("结果数值")),"result_text":r.get("文字结果"),"unit":r.get("单位"),"reference_low":None if pd.isna(r.get("参考下限")) else float(r.get("参考下限")),"reference_high":None if pd.isna(r.get("参考上限")) else float(r.get("参考上限")),"abnormal_flag":abnormal(r.get("结果数值"),r.get("文字结果"),r.get("参考下限"),r.get("参考上限")),"hospital_name":r.get("医院")}); n+=1
            st.success(f"保存 {n} 条"); st.rerun()
        show_table(rel.get("labs",[]))
    with tabs[5]:
        ftype=st.selectbox("资料类型",["门诊病历","检验报告","影像报告","体检报告","用药清单","饮食记录","运动记录","知情同意书","其他"]); dd=st.date_input("资料日期",date.today()); file=st.file_uploader("上传文件",type=["jpg","jpeg","png","pdf","doc","docx","xls","xlsx","csv","txt"])
        if st.button("保存资料") and file:
            path,url=upload(file,f"uploaded_files/{ftype}",p["patient_code"],str(dd)); insert("uploaded_files",{"patient_id":p["patient_id"],"upload_date":str(date.today()),"document_date":str(dd),"file_type":ftype,"file_name":file.name,"file_path":path,"file_url":url,"file_extension":file.name.split(".")[-1].lower()}); st.rerun()
        show_table(rel.get("files",[]))
    with tabs[6]:
        html=a5_html(p,rel,(st.session_state.get("user") or {}).get("display_name","苏医生")); st.components.v1.html(html,height=900,scrolling=True); st.download_button("下载打印报告网页文件",html.encode("utf-8"),f"打印报告_{p.get('name')}_{date.today()}.html","text/html",use_container_width=True)
    with tabs[7]:
        with st.form("editp"):
            name=st.text_input("姓名",p.get("name") or ""); phone=st.text_input("手机号",p.get("phone") or ""); tags=st.multiselect("标签",TAGS,safe_tags(p), placeholder="请选择标签"); diag=st.text_input("主要诊断",p.get("main_diagnosis") or "")
            if st.form_submit_button("保存基础信息"): update_patient(p["patient_id"],{"name":name,"phone":phone,"tags":tags,"main_diagnosis":diag}); st.rerun()

def page_trends():
    hero("趋势分析","体重、腰围、体重指数、体成分估算与检验指标趋势")
    p=choose_patient(); 
    if not p: return
    rel=related(p["patient_id"]); cards(p,rel)
    visits=pd.DataFrame(rel.get("visits",[])); est=pd.DataFrame(rel.get("estimates",[])); labs=pd.DataFrame(rel.get("labs",[]))
    def make_line(df,x,y,title,ytitle):
        fig=px.line(df,x=x,y=y,markers=True,title=title,labels={x:"日期",y:ytitle})
        fig.update_traces(line=dict(width=3,color="#14a39a"),marker=dict(size=8,color="#14a39a"))
        fig.update_layout(title=dict(font=dict(size=22,color="#10233d")),plot_bgcolor="white",paper_bgcolor="white",font=dict(family="Microsoft YaHei",color="#42526b"),margin=dict(l=30,r=20,t=60,b=30),hovermode="x unified")
        fig.update_xaxes(title_text="日期",gridcolor="#eef2f7",tickformat="%Y-%m-%d")
        fig.update_yaxes(title_text=ytitle,gridcolor="#eef2f7")
        st.plotly_chart(fig,use_container_width=True)
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
    brand(); page=st.sidebar.radio("功能导航",["患者管理","趋势分析","导出与备份","系统设置"],label_visibility="collapsed"); logout()
    if page=="患者管理": page_patients()
    elif page=="趋势分析": page_trends()
    elif page=="导出与备份": page_export()
    else: page_settings()

if __name__=="__main__": main()
