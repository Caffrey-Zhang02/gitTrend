import streamlit as st
import os


# 设置页面配置

st.set_page_config(
    page_title="GitHub项目智能助手",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)
# 自定义CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #0366d6;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #586069;
        text-align: center;
        margin-bottom: 2rem;
    }
    .feature-header {
        font-size: 1.2rem;
        color: #24292e;
        margin-top: 1rem;
    }
    .feature-box {
        background-color: #f6f8fa;
        border-radius: 6px;
        padding: 0.5rem;
        margin-bottom: 1rem;
        border-left: 4px solid #0366d6;
    }
    .tech-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        margin: 0.25rem;
        border-radius: 2rem;
        background-color: #e1e4e8;
        color: #24292e;
        font-size: 0.85rem;
    }
    .footer {
        text-align: center;
        margin-top: 3rem;
        color: #586069;
        font-size: 0.9rem;
    }
    /* 减少容器内部的padding */
    .st-emotion-cache-1wmy9hl {
        padding: 0.5rem !important;
    }
    .stMainBlockContainer{padding:40px 60px 10px 60px}

</style>
""", unsafe_allow_html=True)

# 加载项目logo（如果有的话）
logo_path = os.path.join(os.path.dirname(__file__), "static", "github_logo.png")
if os.path.exists(logo_path):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(logo_path, width=200)

# 主标题和副标题
st.markdown('<h1 class="main-header">GitHub项目智能助手</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">探索、分析和了解GitHub上的热门开源项目</p>', unsafe_allow_html=True)

# 项目简介
st.markdown("""
## 项目概述

GitHub项目智能助手是一个综合性工具，旨在帮助开发者、研究人员和技术爱好者更好地了解GitHub上的开源生态系统。

通过数据分析和可视化，我们提供了对GitHub热门项目的深入洞察，帮助您发现有价值的开源资源。
""")

# 功能介绍
st.markdown("## 主要功能")

col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="feature-box"><h3 class="feature-header">🔍 智能搜索</h3></div>', unsafe_allow_html=True)
    st.markdown("""
    - 基于RAG技术的智能搜索引擎
    - 自然语言查询GitHub项目
    - 获取项目详细信息和推荐
    - ...
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    

with col2:
    st.markdown('<div class="feature-box"><h3 class="feature-header">📊 数据可视化</h3></div>', unsafe_allow_html=True)
    st.markdown("""
    - 交互式数据看板
    - 项目语言分布变化
    - 主题关联网络图
    - ...
    """)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("""
选择左侧边栏中的功能模块开始探索：

1. **搜索助手** - 使用自然语言查询GitHub项目
2. **数据可视化** - 探索GitHub数据看板和趋势分析
""")
# 技术栈
st.markdown("## 技术栈")
st.markdown("""
<div style="text-align: center">
    <span class="tech-badge">Python</span>
    <span class="tech-badge">Streamlit</span>
    <span class="tech-badge">MySQL</span>
    <span class="tech-badge">Qdrant</span>
    <span class="tech-badge">Plotly</span>
    <span class="tech-badge">ECharts</span>
    <span class="tech-badge">通义千问</span>
    <span class="tech-badge">RAG</span>
</div>
""", unsafe_allow_html=True)



# 页脚
st.markdown('<div class="footer">GitHub项目智能助手 © 2025 | 基于RAG技术构建</div>', unsafe_allow_html=True)