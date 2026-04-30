
import streamlit as st


def css():
    st.markdown("""
<style>
:root{
  --bg0:#f6f9fc;--bg1:#eef6f8;--panel:#ffffff;--line:#e3edf5;--text:#14243b;--muted:#66758a;
  --teal:#12a89d;--teal2:#e8fbf8;--blue:#2f6df6;--blue2:#edf4ff;--orange:#f59e0b;--orange2:#fff7e8;--red:#ef4444;
  --shadow:0 16px 42px rgba(31,50,74,.08);--shadow2:0 8px 22px rgba(31,50,74,.05);--radius:24px;
}
html,body,[data-testid="stAppViewContainer"]{
  background:radial-gradient(circle at 20% 0%,#f4fffc 0%,rgba(244,255,252,0) 32%),linear-gradient(180deg,#fbfdff 0%,#f2f7fb 100%)!important;
  color:var(--text);font-family:"Microsoft YaHei","PingFang SC","Noto Sans CJK SC",Arial,sans-serif;
}
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer, header, [data-testid="stStatusWidget"]{display:none!important;visibility:hidden!important;height:0!important;}
.main .block-container{padding-top:1.6rem;padding-bottom:3rem;max-width:1380px;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#ffffff 0%,#f7fbfc 100%)!important;border-right:1px solid #e7eef5;box-shadow:10px 0 30px rgba(31,50,74,.04);}
[data-testid="stSidebar"] .stRadio > label{font-weight:900;color:#26364f;}
[data-testid="stSidebar"] [role="radiogroup"] label{padding:8px 10px;border-radius:12px;margin:3px 0;}
[data-testid="stSidebar"] [role="radiogroup"] label:hover{background:#f0fbf9;}
.wc-brand{padding:18px 16px;border-radius:22px;background:linear-gradient(135deg,#e4fbf7 0%,#eef5ff 100%);border:1px solid #d4edf2;margin:4px 0 20px;box-shadow:var(--shadow2)}
.wc-brand-title{font-size:24px;font-weight:900;color:#10233d;margin:0;letter-spacing:.5px}.wc-brand-sub{font-size:13px;color:#68798f;margin-top:5px;font-weight:700}
.hero{padding:30px 34px;border-radius:30px;background:linear-gradient(135deg,#e9fbf8 0%,#f3f8ff 52%,#ffffff 100%);border:1px solid #d7eaf2;box-shadow:var(--shadow);margin-bottom:22px;position:relative;overflow:hidden;}
.hero:before{content:"";position:absolute;left:-80px;bottom:-80px;width:180px;height:180px;border-radius:50%;background:radial-gradient(circle,rgba(47,109,246,.10),rgba(47,109,246,0) 68%)}
.hero:after{content:"";position:absolute;right:-70px;top:-70px;width:220px;height:220px;border-radius:50%;background:radial-gradient(circle,rgba(18,168,157,.14),rgba(18,168,157,0) 72%)}
.hero h1{margin:0;color:#10233d;font-size:40px;font-weight:950;letter-spacing:.5px;position:relative;z-index:1}.hero .sub{color:#667085;margin-top:10px;font-size:15px;line-height:1.8;font-weight:700;position:relative;z-index:1}
.boundary{padding:14px 18px;border-radius:18px;background:linear-gradient(135deg,#fff9ef,#fffdf8);border:1px solid #f9d39a;color:#8a4b10;margin:12px 0 18px;font-size:14px;line-height:1.8;box-shadow:0 8px 20px rgba(245,158,11,.07)}
.tag{display:inline-block;padding:6px 12px;border-radius:999px;background:#eefbf6;border:1px solid #bcebd7;color:#047857;margin:3px 5px 3px 0;font-size:12px;font-weight:900;}
.stat-row{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:18px 0 20px}.stat-card{background:linear-gradient(180deg,#fff,#fbfdff);border:1px solid var(--line);border-radius:24px;padding:18px 20px;box-shadow:var(--shadow);position:relative;overflow:hidden}.stat-card:after{content:"";position:absolute;right:-35px;top:-35px;width:90px;height:90px;border-radius:50%;background:rgba(18,168,157,.08)}.stat-card b{display:block;color:#708198;font-size:13px;margin-bottom:9px}.stat-card strong{font-size:30px;color:#10233d;line-height:1.1}.stat-card small{display:block;color:#0f9d90;font-size:12px;font-weight:900;margin-top:8px}
.section-title{font-size:22px;font-weight:950;color:#10233d;margin:18px 0 12px;display:flex;align-items:center;gap:8px}.section-title:before{content:"";width:8px;height:22px;border-radius:999px;background:linear-gradient(180deg,#12a89d,#2f6df6)}
.patient-strip{padding:20px 22px;border-radius:26px;background:linear-gradient(135deg,#ffffff,#f5fbff);border:1px solid #e0edf7;box-shadow:var(--shadow);margin:14px 0 18px;display:flex;justify-content:space-between;gap:16px;align-items:flex-start;}
.patient-name{font-size:30px;font-weight:950;color:#10233d;margin-bottom:6px}.patient-meta{color:#667085;line-height:1.8;font-size:14px;font-weight:700}.patient-avatar{width:70px;height:70px;border-radius:22px;display:grid;place-items:center;font-size:30px;font-weight:950;box-shadow:inset 0 -8px 18px rgba(255,255,255,.5)}.patient-avatar.male{background:linear-gradient(135deg,#e2f3ff,#dbe8ff);color:#2f6df6}.patient-avatar.female{background:linear-gradient(135deg,#ffe4ef,#ffd9eb);color:#db2777}
.section-card{background:#fff;border:1px solid var(--line);border-radius:24px;padding:18px 20px;box-shadow:var(--shadow);margin:16px 0;line-height:1.9;color:#52657e}.overview-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin:18px 0}.overview-card{background:#fff;border:1px solid var(--line);border-radius:24px;padding:18px 20px;box-shadow:var(--shadow);min-height:168px}.overview-card h3{font-size:20px;margin:0 0 14px;color:#10233d}.overview-card p,.overview-card li{font-size:14px;line-height:1.85;color:#5e6f86}.overview-card ul{margin:0;padding-left:18px}.overview-pill{display:inline-block;padding:4px 10px;border-radius:999px;background:#ecfdf5;color:#047857;font-size:12px;font-weight:900;margin-left:8px}
.chart-card{background:#fff;border:1px solid var(--line);border-radius:26px;padding:18px 20px;margin:18px 0;box-shadow:var(--shadow)}
div[data-testid="stMetric"]{background:linear-gradient(180deg,#fff,#fbfdff);border:1px solid var(--line);border-radius:24px;padding:17px 20px;box-shadow:var(--shadow);}
div[data-testid="stMetricLabel"]{color:#708198!important;font-weight:900}div[data-testid="stMetricValue"]{color:#10233d!important;font-weight:950!important}div[data-testid="stMetricDelta"]{font-weight:900!important}
.stButton>button,.stDownloadButton>button,.stFormSubmitButton>button{border-radius:15px!important;border:1px solid #d9e4ef!important;background:#fff!important;color:#22344d!important;font-weight:900!important;min-height:44px;box-shadow:0 6px 14px rgba(31,50,74,.05);}
.stButton>button:hover,.stDownloadButton>button:hover,.stFormSubmitButton>button:hover{border-color:#12a89d!important;color:#0f766e!important;background:#f3fffd!important;transform:translateY(-1px)}
div[data-testid="stForm"]{border:1px solid #e4edf5;border-radius:26px;padding:22px 24px;background:#fff;box-shadow:var(--shadow);}
div[data-testid="stExpander"]{border:1px solid #e4edf5!important;border-radius:20px!important;background:#fff!important;box-shadow:var(--shadow2);}
div[data-testid="stDataFrame"]{border:1px solid #e4edf5;border-radius:20px;overflow:hidden;box-shadow:var(--shadow);}
div[data-baseweb="tab-list"]{gap:8px;border-bottom:1px solid #e5edf6;}button[data-baseweb="tab"]{border-radius:14px 14px 0 0;font-weight:900;color:#52657e;}button[data-baseweb="tab"][aria-selected="true"]{color:#12a89d;border-bottom:3px solid #12a89d;background:#f3fffd;}
.stTextInput input,.stNumberInput input,.stDateInput input,textarea,.stSelectbox div[data-baseweb="select"],.stMultiSelect div[data-baseweb="select"]{border-radius:14px!important;border-color:#dfe8f1!important;background:#f8fbfe!important;}
[data-testid="stAlert"]{border-radius:18px!important}.wc-note{color:#667085;font-size:13px;line-height:1.8}
@media(max-width:1100px){.stat-row,.overview-grid{grid-template-columns:repeat(2,1fr)}.hero h1{font-size:32px}.patient-strip{display:block}.patient-avatar{margin-top:12px}}
@media(max-width:760px){.stat-row,.overview-grid{grid-template-columns:1fr}.main .block-container{padding-left:1rem;padding-right:1rem}}

/* v3.2 sidebar user card fix */
.wc-user-card{
  display:flex;
  align-items:center;
  gap:10px;
  padding:12px 12px;
  margin:16px 0 10px 0;
  border-radius:18px;
  background:linear-gradient(135deg,#ffffff,#f2fbfa);
  border:1px solid #dbeef0;
  box-shadow:0 8px 20px rgba(31,50,74,.06);
}
.wc-user-avatar{
  width:36px;
  height:36px;
  border-radius:14px;
  display:grid;
  place-items:center;
  background:#e9f8ff;
  color:#2563eb;
  font-weight:900;
}
.wc-user-name{
  font-size:14px;
  color:#10233d;
  font-weight:900;
  line-height:1.2;
}
.wc-user-role{
  font-size:12px;
  color:#72839a;
  margin-top:2px;
}
[data-testid="stSidebar"] .stButton>button{
  margin-top:4px;
}

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
    sex = patient.get('sex','')
    avatar_class = 'female' if sex == '女' else 'male'
    avatar = '♀' if sex == '女' else '♂'
    st.markdown(
        f"""
        <div class='patient-strip'>
          <div>
            <div class='patient-name'>{patient.get('name','')}</div>
            <div class='patient-meta'>
            {patient.get('patient_code','')}｜{patient.get('sex','')}｜{patient.get('age','')}岁｜身高 {patient.get('height_cm','')} 厘米｜初诊 {patient.get('first_visit_date','')}
            </div>
          </div>
          <div class='patient-avatar {avatar_class}'>{avatar}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat_grid(items):
    html = "<div class='stat-row'>"
    for title, value, note in items:
        html += f"<div class='stat-card'><b>{title}</b><strong>{value}</strong><small>{note}</small></div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def overview_cards(meds, tongue_text, pulse_text, labs):
    def med_to_text(m):
        if isinstance(m, dict):
            name = m.get("medicine_name") or "未命名方案"
            dose = m.get("dose") or ""
            freq = m.get("frequency") or ""
            status = m.get("current_status") or ""
            text = " ".join([str(x) for x in [name, dose, freq] if x])
            return f"{text}（{status}）" if status else text
        return str(m)

    def lab_to_text(x):
        if isinstance(x, dict):
            item = x.get("item_name") or "未命名项目"
            value = x.get("result_value") if x.get("result_value") is not None else x.get("result_text")
            unit = x.get("unit") or ""
            flag = x.get("abnormal_flag") or ""
            result = f"{value} {unit}".strip() if value not in (None, "") else "未填结果"
            return f"{item}：{result}（{flag}）" if flag else f"{item}：{result}"
        return str(x)

    med_items = "".join([f"<li>{med_to_text(m)}</li>" for m in (meds or [])]) or "<li>暂无当前用药记录</li>"
    lab_items = "".join([f"<li>{lab_to_text(x)}</li>" for x in (labs or [])]) or "<li>暂无近期辅助检查</li>"
    st.markdown(
        f"""
        <div class='overview-grid'>
          <div class='overview-card'><h3>当前用药 / 调理方案</h3><ul>{med_items}</ul></div>
          <div class='overview-card'><h3>舌象与脉象记录</h3><p><b>舌象：</b>{tongue_text}</p><p><b>脉象：</b>{pulse_text}</p></div>
          <div class='overview-card'><h3>最近辅助检查</h3><ul>{lab_items}</ul></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def chart_open():
    st.markdown("<div class='chart-card'>", unsafe_allow_html=True)


def chart_close():
    st.markdown("</div>", unsafe_allow_html=True)
