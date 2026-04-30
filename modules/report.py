from datetime import date
from html import escape
from modules.calc import bmi, loss, fmt

def latest(rows, key):
    return sorted(rows or [], key=lambda x: str(x.get(key) or ""), reverse=True)[0] if rows else {}

def a5_html(patient, rel, doctor="苏医生"):
    lv=latest(rel.get("visits",[]),"visit_date")
    labs=sorted(rel.get("labs",[]), key=lambda x: str(x.get("lab_date") or ""), reverse=True)[:6]
    meds=[m for m in rel.get("meds",[]) if m.get("current_status") in ("使用中",None,"")][-5:]
    tongue=latest(rel.get("tongues",[]),"image_date")
    pulse=latest(rel.get("pulses",[]),"pulse_date")
    weight=lv.get("weight_kg") or patient.get("initial_weight_kg")
    b=bmi(weight,patient.get("height_cm"))
    lp=loss(patient.get("initial_weight_kg"), weight)
    lab_rows="".join([f"<tr><td>{escape(str(x.get('item_name') or ''))}</td><td>{escape(str(x.get('result_value') or x.get('result_text') or ''))} {escape(str(x.get('unit') or ''))}</td><td>{escape(str(x.get('abnormal_flag') or ''))}</td></tr>" for x in labs]) or "<tr><td colspan='3'>暂无辅助检查</td></tr>"
    med_rows="".join([f"<li>{escape(str(m.get('medicine_name') or ''))} {escape(str(m.get('dose') or ''))} {escape(str(m.get('frequency') or ''))}</li>" for m in meds]) or "<li>暂无当前用药记录</li>"
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>A5报告</title>
<style>@page{{size:A5 portrait;margin:7mm}}body{{font-family:'Microsoft YaHei',Arial,sans-serif;color:#1f2937}}.head{{display:flex;justify-content:space-between;border-bottom:2px solid #dbeafe;padding-bottom:6px;margin-bottom:8px}}.title{{font-size:18px;font-weight:900}}.section{{border:1px solid #e5edf6;border-radius:10px;padding:8px;margin:8px 0;break-inside:avoid}}.st{{font-weight:900;margin-bottom:6px}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}}.info{{background:#f8fbff;border:1px solid #eef4fb;border-radius:8px;padding:6px}}.info b{{display:block;font-size:9px;color:#64748b}}.info span{{font-size:11px;font-weight:800}}.kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}}.kpi{{border:1px solid #e6edf5;border-radius:10px;padding:7px}}.kpi b{{font-size:10px;color:#64748b;display:block}}.kpi span{{font-size:17px;font-weight:900;color:#0f766e}}table{{width:100%;border-collapse:collapse;font-size:10px}}td,th{{border-bottom:1px solid #edf2f7;padding:5px;text-align:center}}ul,ol{{margin:0;padding-left:18px;font-size:11px;line-height:1.7}}.foot{{font-size:9px;color:#64748b;line-height:1.45;border-top:1px solid #e5edf6;padding-top:8px}}</style></head><body>
<div class='head'><div><div class='title'>减重门诊随访报告（逢安堂）</div><div style='font-size:10px;color:#64748b'>门诊随访展示与健康管理参考</div></div><div style='font-size:10px;color:#1d4ed8'>报告日期：{date.today()}</div></div>
<div class='section'><div class='st'>患者基本信息</div><div class='grid'>
<div class='info'><b>编号</b><span>{escape(str(patient.get('patient_code') or ''))}</span></div><div class='info'><b>姓名</b><span>{escape(str(patient.get('name') or ''))}</span></div><div class='info'><b>性别</b><span>{escape(str(patient.get('sex') or ''))}</span></div><div class='info'><b>年龄</b><span>{escape(str(patient.get('age') or ''))}岁</span></div><div class='info'><b>身高</b><span>{escape(str(patient.get('height_cm') or ''))} cm</span></div><div class='info'><b>初诊日期</b><span>{escape(str(patient.get('first_visit_date') or ''))}</span></div><div class='info'><b>本次复诊</b><span>{escape(str(lv.get('visit_date') or ''))}</span></div><div class='info'><b>主要问题</b><span>{escape(str(patient.get('main_diagnosis') or ''))}</span></div></div></div>
<div class='section'><div class='st'>核心摘要</div><div class='kpis'><div class='kpi'><b>当前体重</b><span>{fmt(weight)} kg</span></div><div class='kpi'><b>当前BMI</b><span>{fmt(b)}</span></div><div class='kpi'><b>累计减重</b><span>{fmt(lp)}%</span></div><div class='kpi'><b>当前腰围</b><span>{fmt(lv.get('waist_cm'))} cm</span></div><div class='kpi'><b>目标体重</b><span>{fmt(patient.get('target_weight_kg'))} kg</span></div><div class='kpi'><b>下次复诊</b><span style='font-size:12px'>{escape(str(lv.get('next_visit_date') or ''))}</span></div></div></div>
<div class='section'><div class='st'>辅助检查摘要</div><table><thead><tr><th>项目</th><th>结果</th><th>提示</th></tr></thead><tbody>{lab_rows}</tbody></table></div>
<div class='section'><div class='st'>当前用药/调理方案</div><ul>{med_rows}</ul></div>
<div class='section'><div class='st'>舌脉观察</div><ul><li>舌象：舌质 {escape(str(tongue.get('tongue_body_color') or '未记录'))}，舌苔 {escape(str(tongue.get('tongue_coating') or '未记录'))}</li><li>脉象：{escape(str(pulse.get('overall_pulse') or '未记录'))}</li></ul></div>
<div class='section' style='background:#fff8eb;border-color:#fed7aa'><div class='st'>本次建议</div><ol><li>{escape(str(lv.get('clinical_advice') or '继续当前方案，按期复诊。'))}</li><li>若出现明显不适，请及时联系门诊。</li></ol></div>
<div class='foot'>说明：体成分相关指标为公式估算值，仅用于同一方法下趋势参考。本报告用于门诊健康管理参考，不作为自动诊断或自动开药依据。<br>接诊医生：{escape(doctor)}</div>
</body></html>"""
