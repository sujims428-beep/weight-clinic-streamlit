import streamlit as st


def css():
    st.markdown("""
<style>
:root{
  --bg:#f5f8fb;--panel:#ffffff;--line:#e4edf5;--text:#17233a;--muted:#667085;
  --teal:#14a39a;--blue:#2f6df6;--orange:#f59e0b;--red:#ef4444;
  --shadow:0 14px 34px rgba(31,50,74,.08);--radius:22px;
}
html,body,[data-testid="stAppViewContainer"]{background:linear-gradient(180deg,#f8fbfd 0%,#f3f7fb 100%)!important;color:var(--text);font-family:"Microsoft YaHei","PingFang SC","Noto Sans CJK SC",Arial,sans-serif;}
[data-testid="stToolbar"],[data-testid="stDecoration"],#MainMenu,footer,header{visibility:hidden!important;height:0!important;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#ffffff 0%,#f7fafc 100%)!important;border-right:1px solid #e8eef5;box-shadow:8px 0 28px rgba(31,50,74,.04);}
[data-testid="stSidebar"] .stRadio label{font-weight:800!important;color:#26364f!important;}
.main .block-container{padding-top:1.4rem;padding-bottom:3rem;max-width:1320px;}
.wc-brand{padding:16px 14px 18px;border-radius:20px;background:linear-gradient(135deg,#e8fbf8,#f2f6ff);border:1px solid #d9eef2;margin:6px 0 18px;}
.wc-brand-title{font-size:22px;font-weight:900;letter-spacing:.5px;color:#10233d;margin:0;}.wc-brand-sub{color:#68798f;font-size:13px;margin-top:4px;}
.hero{padding:28px 32px;border-radius:28px;background:linear-gradient(135deg,#ecfbf8 0%,#f2f7ff 58%,#ffffff 100%);border:1px solid #d7eaf2;box-shadow:var(--shadow);margin-bottom:22px;position:relative;overflow:hidden;}
.hero:after{content:"";position:absolute;right:-80px;top:-80px;width:220px;height:220px;border-radius:50%;background:radial-gradient(circle,rgba(20,163,154,.12),rgba(20,163,154,0) 70%);}
.hero h1{margin:0;color:#10233d;font-size:38px;font-weight:900;letter-spacing:.5px;}.hero .sub{color:#667085;margin-top:10px;font-size:15px;line-height:1.8;}
.boundary{padding:15px 18px;border-radius:18px;background:linear-gradient(135deg,#fff8ec,#fffdf6);border:1px solid #fed7aa;color:#8a4b10;margin:12px 0 18px;font-size:14px;line-height:1.8;}
.tag{display:inline-block;padding:6px 12px;border-radius:999px;background:#eefbf6;border:1px solid #bcebd7;color:#047857;margin:3px 5px 3px 0;font-size:12px;font-weight:800;}
.section-title{font-size:22px;font-weight:900;color:#10233d;margin:18px 0 12px;}
.patient-strip{padding:18px 20px;border-radius:22px;background:linear-gradient(135deg,#ffffff,#f6fbff);border:1px solid #e5eef7;box-shadow:var(--shadow);margin:14px 0 18px;}.patient-name{font-size:28px;font-weight:900;color:#10233d;margin-bottom:5px;}.patient-meta{color:#667085;line-height:1.8;font-size:14px;}
div[data-testid="stMetric"]{background:#fff;border:1px solid var(--line);border-radius:22px;padding:16px 18px;box-shadow:var(--shadow);}div[data-testid="stMetricLabel"]{color:#708198!important;font-weight:800;}div[data-testid="stMetricValue"]{color:#10233d!important;font-weight:900!important;}
.stButton>button,.stDownloadButton>button,.stFormSubmitButton>button{border-radius:14px!important;border:1px solid #d9e4ef!important;background:#ffffff!important;color:#23344d!important;font-weight:800!important;min-height:42px;box-shadow:0 6px 14px rgba(31,50,74,.05);}.stButton>button:hover,.stDownloadButton>button:hover,.stFormSubmitButton>button:hover{border-color:#14a39a!important;color:#0f766e!important;background:#f4fffd!important;}
div[data-testid="stForm"]{border:1px solid #e4edf5;border-radius:24px;padding:20px 22px;background:#fff;box-shadow:var(--shadow);}div[data-testid="stExpander"]{border:1px solid #e4edf5!important;border-radius:18px!important;background:#fff!important;box-shadow:0 8px 22px rgba(31,50,74,.05);}div[data-testid="stDataFrame"]{border:1px solid #e4edf5;border-radius:18px;overflow:hidden;box-shadow:var(--shadow);}
div[data-baseweb="tab-list"]{gap:6px;border-bottom:1px solid #e5edf6;}button[data-baseweb="tab"]{border-radius:12px 12px 0 0;font-weight:800;color:#52657e;}button[data-baseweb="tab"][aria-selected="true"]{color:#14a39a;border-bottom:3px solid #14a39a;}
.stTextInput input,.stNumberInput input,.stDateInput input,textarea,.stSelectbox div[data-baseweb="select"],.stMultiSelect div[data-baseweb="select"]{border-radius:14px!important;border-color:#dfe8f1!important;background:#f8fbfe!important;}
.wc-note{color:#667085;font-size:13px;line-height:1.8;}@media(max-width:1000px){.hero h1{font-size:30px}}
</style>
""", unsafe_allow_html=True)


def hero(t, s=""):
    st.markdown(f"<div class='hero'><h1>{t}</h1><div class='sub'>{s}</div></div>", unsafe_allow_html=True)


def tags_html(tags):
    return " ".join([f"<span class='tag'>{x}</span>" for x in (tags or [])])


def boundary():
    st.markdown("<div class='boundary'>本系统用于减重门诊随访记录、趋势展示与报告生成；不用于自动诊断，不用于自动开药。体成分相关指标为公式估算值，仅用于同一方法下趋势参考。</div>", unsafe_allow_html=True)


def brand():
    st.sidebar.markdown("<div class='wc-brand'><div class='wc-brand-title'>⚖️ 逢安堂</div><div class='wc-brand-sub'>减重门诊管理系统</div></div>", unsafe_allow_html=True)


def section(title):
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)


def patient_header(patient):
    st.markdown(f"""
    <div class='patient-strip'>
      <div class='patient-name'>{patient.get('name','')}</div>
      <div class='patient-meta'>{patient.get('patient_code','')}｜{patient.get('sex','')}｜{patient.get('age','')}岁｜身高 {patient.get('height_cm','')} 厘米｜初诊 {patient.get('first_visit_date','')}</div>
    </div>
    """, unsafe_allow_html=True)
