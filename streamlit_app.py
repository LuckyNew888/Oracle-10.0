# streamlit_app.py

import streamlit as st
from oracle_engine import OracleBaccaratAI

st.set_page_config(page_title="🔮 Oracle Baccarat AI", layout="centered")

st.markdown("""
    <div style='text-align:center'>
        <h1>🔮 Oracle Baccarat AI</h1>
        <p>ระบบวิเคราะห์บาคาร่า 7 ขั้นตอนอัจฉริยะ</p>
    </div>
""", unsafe_allow_html=True)

with st.form("oracle_form"):
    user_input = st.text_input("🎲 ป้อนผลย้อนหลัง (เช่น BBPPPTPBPB):")
    submit = st.form_submit_button("🔍 วิเคราะห์")

if submit:
    input_data = list(user_input.strip().upper())
    input_data = [i for i in input_data if i in ['B', 'P', 'T']]

    if len(input_data) < 15:
        st.warning("⚠️ กรุณาใส่อย่างน้อย 15 ตัว")
    else:
        oracle = OracleBaccaratAI()
        result = oracle.predict(input_data)

        st.markdown("### 📊 ผลการวิเคราะห์")
        for k, v in result.items():
            if isinstance(v, list):
                st.markdown(f"**{k}**: {' | '.join([''.join(x) for x in v])}")
            else:
                st.markdown(f"**{k}**: {v}")
