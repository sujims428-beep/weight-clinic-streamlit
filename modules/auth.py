import hashlib, hmac
import streamlit as st

def verify(username, password):
    try:
        sec = st.secrets["auth"]["app_secret"]
        users = st.secrets["auth"]["users"]
        user = users.get(username)
        if not user: return None
        digest = hmac.new(sec.encode(), password.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(digest, user.get("password_hash","")):
            return {"username": username, "role": user.get("role","doctor"), "display_name": user.get("display_name", username)}
    except Exception:
        return None
    return None

def require_login():
    if st.session_state.get("user"): return True
    st.markdown("## 减重门诊管理系统（逢安堂）")
    st.caption("Streamlit Cloud 在线版 v1")
    with st.form("login"):
        u = st.text_input("用户名")
        p = st.text_input("密码", type="password")
        ok = st.form_submit_button("登录", use_container_width=True)
    if ok:
        user = verify(u.strip(), p)
        if user:
            st.session_state["user"] = user
            st.rerun()
        else:
            st.error("用户名或密码错误，或 Secrets 未配置。")
    return False

def logout():
    user = st.session_state.get("user") or {}
    st.sidebar.caption(f"当前用户：{user.get('display_name','')}")
    if st.sidebar.button("退出登录", use_container_width=True):
        st.session_state.pop("user", None)
        st.rerun()
