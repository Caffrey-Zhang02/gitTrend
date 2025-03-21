import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
from utils.visualization import *
from streamlit_echarts import st_pyecharts

# 设置页面配置
st.set_page_config(page_title="GitHub 数据看板", page_icon="📊",layout="wide")


# 自定义 CSS：设置页面高度为 1600px，并划分上下部分比例
st.markdown("""
    <style>
        .main-header {
            font-size: 2.5rem;
            color: #0366d6;
            text-align: center;
            margin-bottom: 1rem;
        }
        body {
            height: 1600px; /* 固定页面高度 */
            overflow: hidden; /* 禁止滚动条 */
        }
        .block-container {
                            padding-top: 1rem;
                            padding-bottom: 0rem;
                            padding-left: 1rem;
                            padding-right: 1rem;
                        }
        .stMainBlockContainer{padding:40px 60px 10px 60px}
        .footer {
        text-align: center;
        margin-top: 3rem;
        color: #586069;
        font-size: 0.9rem;
        } 

        /* 减少列元素之间的间距 */
        .st-emotion-cache-1r6slb0 {
            gap: 0.5rem !important;
        }
        
        /* 减少行元素之间的间距 */
        .st-emotion-cache-16txtl3 {
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
        }
        
        /* 减少容器内部的padding */
        .st-emotion-cache-1wmy9hl {
            padding: 0.5rem !important;
        }
        
        /* 减少卡片元素的margin */
        .st-emotion-cache-1erivf3 {
            margin: 0.2rem !important;
        }
        [data-testid="stVerticalBlock"] > div:has([data-testid="stVerticalBlock"][data-key="lower_container"]) {
            overflow: hidden !important;
            }
        .st-emotion-cache-1eh06om{
            overflow: hidden !important;

        }
    </style>
    
    """, unsafe_allow_html=True)

# st.markdown("""<style> .stAppHeader{} footer {visibility: hidden;} body { background-color : #ffffff;}} </style>""", unsafe_allow_html=True)

# 上半部分（40%）
with st.container(height=360, border=False):
    col1, col2, col3 = st.columns([35, 30, 35])  # 三列，比例 30:30:40

    with col1:
        with st.spinner("正在生成折线图..."):

            # 使用真实数据替换模拟数据
            repo_growth_data = get_repo_num_by_year(min_stars=100)
            # 使用 Streamlit 显示月度趋势图
            monthly_trend_chart = visualize_repo_growth_by_year()
            st_pyecharts(monthly_trend_chart, height="350px",width = "100%")
        
    with col2:
        with st.spinner("正在生成词云图..."):

            # 使用真实的主题词云数据
            topic_data = get_topics_num_dict()
            wordcloud_chart = draw_topic_wordcloud(topic_data)
            st_pyecharts(wordcloud_chart, height="350px", width = "100%")

    with col3:
        with st.spinner("正在生成主题河流图..."):
            # 使用语言河流图
            language_river_chart = draw_language_river(percentaged=False, top=15)
            st_pyecharts(language_river_chart, height="350px",width = "100%")
        

# 下半部分（60%）
with st.container(height=680, border=False, key="lower_container"):
    # 添加自定义CSS专门针对这个容器

    col3, col4, col5 = st.columns([30, 45, 20])  # 左右两列，比例 30:70
    with col3:
        with st.spinner("正在生成条形图..."):
            bar_chart = visualize_top_contributors()
            st_pyecharts(bar_chart, height="600px",width = "100%")
       

    with col4:
        with st.container(height=80, border=False):
            # 使用真实的主题网络图数据
            col4_1, col4_2, col4_3 = st.columns([10, 10, 10])  # 左右两列，比例 30:70
            with col4_1:
                # 使用真实的主题网络图数据
                min_node_value = st.slider("最小节点值", 500, 1500, 1000)
            with col4_2:
                # 使用真实的主题网络图数据
                min_edge_value = st.slider("最小边权重", 100, 200, 100)
            with col4_3:
                # 使用真实的主题网络图数据
                max_nodes = st.slider("最大节点数", 100, 300, 200)
                # 添加滑块以控制最小节点值和最小边权重
        
        # 获取网络图数据并可视化
        with st.spinner("正在生成网络图..."):
            graph_data = get_topics_graph_data(min_node_value, min_edge_value, max_nodes)
            # 社区发现
            community_data = detect_communities(graph_data)

            # 显示数据统计
            # 创建并显示网络图
            chart = visualize_topics_network(community_data)
            st_pyecharts(chart, height="450px",width = "100%")

    with col5:

         # 使用真实的语言分布数据
        # language_data = get_language_distribution()
        # language_pie_chart = visualize_language_pie(language_data)
        # st_pyecharts(language_pie_chart, height="220px")
        
        # 添加仓库星标历史查询功能
        repo_name = get_fastest_growing_repo_2025()
        st.markdown(f"##### 上周涨星最多的仓库:{repo_name}")
        with st.spinner("正在获取数据..."):
            qdrant_client = qdrant_client_init()
            star_df = get_repo_star_history(repo_name, qdrant_client)
            if star_df is not None:
                line_chart = visualize_stars_over_time(star_df, repo_name)
                calendar = visualize_star_calendar(star_df, repo_name)
                st_pyecharts(line_chart, height="300px",width = "100%")
                st_pyecharts(calendar, height="300px",width = "100%")
            else:
                st.error("未找到该仓库数据或数据获取失败")
            
# 添加额外的数据分析部分
with st.expander("View More"):
    with st.container(height=600, border=False):
        st.header("更多数据分析")
        tab1, tab2, tab3 = st.tabs(["Star-Fork 关系", "contributor网络", "自定义分析"])

st.markdown('<div class="footer">GitHub项目智能助手 © 2025</div>', unsafe_allow_html=True)
