import streamlit as st
import os


# 设置页面配置

RAG_page = st.Page("./Pages/01_RAG.py", title="RAG", icon="🔍")
Visualization_page = st.Page("./Pages/02_Visualization.py", title="Visualization", icon="📊")
homepage = st.Page("./Pages/home.py", title="Home", icon="🏠")
pg = st.navigation([homepage, RAG_page, Visualization_page])

pg.run()
