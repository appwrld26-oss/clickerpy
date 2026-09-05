import streamlit as st

st.set_page_config(page_title="Test Dashboard", layout="wide")

st.title("⚡ لوحة الاختبار التشخيصية")
st.write("إذا ظهرت هذه الصفحة، فهذا يعني أن Streamlit يعمل بشكل سليم وأن المشكلة إما في مكتبة psycopg2 أو اتصال قاعدة البيانات.")

try:
    import psycopg2
    st.success("✅ مكتبة psycopg2 مثبتة بنجاح.")
except Exception as e:
    st.error(f"❌ خطأ في مكتبة psycopg2: {e}")

try:
    import pandas as pd
    st.success("✅ مكتبة pandas مثبتة بنجاح.")
except Exception as e:
    st.error(f"❌ خطأ في مكتبة pandas: {e}")
