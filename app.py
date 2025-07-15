# app.py
import streamlit as st
from oracle_core import OracleBrain, Outcome

# Initialize
st.set_page_config(page_title="Oracle v5", layout="centered")
if 'oracle' not in st.session_state:
    st.session_state.oracle = OracleBrain()

# UI Example
st.title("🔮 ORACLE v5")
if st.button("🔵 P"):
    st.session_state.oracle.add_result("P")
if st.button("🔴 B"):
    st.session_state.oracle.add_result("B")
if st.button("⚪ T"):
    st.session_state.oracle.add_result("T")

result = st.session_state.oracle.predict_next()
st.write("คำทำนาย:", result)
