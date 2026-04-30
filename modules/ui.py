import streamlit as st

def css():
    st.markdown("""<style>.main .block-container{padding-top:1.5rem;max-width:1500px}.hero{padding:20px 24px;border-radius:22px;background:linear-gradient(135deg,#effaf8,#f4f8ff);border:1px solid #dbeafe;margin-bottom:18px}.tag{display:inline-block;padding:5px 10px;border-radius:999px;background:#ecfdf5;color:#047857;margin:2px;font-size:12px;font-weight:700}.warn{padding:14px 16px;border-radius:14px;background:#fff8eb;border:1px solid #fed7aa;color:#8a4b10;margin:10px 0}</style>""", unsafe_allow_html=True)

def hero(t,s=""):
    st.markdown(f"<div class='hero'><h1 style='margin:0;color:#12233d'>{t}</h1><div style='color:#667085;margin-top:6px'>{s}</div></div>", unsafe_allow_html=True)

def tags_html(tags):
    return " ".join([f"<span class='tag'>{x}</span>" for x in (tags or [])])

def boundary():
    st.markdown("<div class='warn'>本系统用于减重门诊随访记录、趋势展示与报告生成；不用于自动诊断，不用于自动开药。体成分相关指标为公式估算值，仅用于同一方法下趋势参考。</div>", unsafe_allow_html=True)
