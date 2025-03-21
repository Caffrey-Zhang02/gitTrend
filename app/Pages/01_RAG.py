import streamlit as st
st.set_page_config(page_title="GitHub项目智能助手", page_icon="🔍", layout="wide")

import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import json
from datetime import datetime
import mysql.connector

# 将项目根目录添加到Python模块搜索路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.retriever import GithubRepoRetriever
from utils.generator import RAGGenerator

# 配置信息
SETTINGS = {
    'mysql_host': 'localhost',
    'mysql_user': 'root',
    'mysql_password': 'root',
    'mysql_port': 3306,
    'qdrant_url': 'http://localhost:6333',
    'qwen_api_key': 'your_api_key'
}

# 初始化检索器和生成器
@st.cache_resource
def init_rag_system():
    retriever = GithubRepoRetriever(SETTINGS)
    generator = RAGGenerator(SETTINGS, retriever)
    return retriever, generator

retriever, generator = init_rag_system()


# 页面内容
# 页面设置

st.title("GitHub项目智能助手")
st.markdown("输入您的问题，获取关于GitHub项目的智能回答:")
st.markdown("""<style>
    .stMainBlockContainer{padding:40px 60px 10px 60px}
    .footer {
    text-align: center;
    margin-top: 3rem;
    color: #586069;
    font-size: 0.9rem;
    } 
 </style>""", unsafe_allow_html=True)


with st.container(border=False, height=670, key="main"):

    # 用户输入
    query = st.text_area('您的问题：',height=100, placeholder="例如：推荐几个最流行的机器学习框架", label_visibility ='collapsed')
    col1, col2 = st.columns([1, 3])
    with col1:
        search_only = st.checkbox("仅显示检索结果（不生成回答）")
    with col2:
        result_count = st.slider("检索结果数量", min_value=1, max_value=10, value=3)
    submit_button = st.button("提交")

    # 处理查询
    if submit_button and query:
        with st.spinner("正在处理您的问题..."):
            if search_only:
                # 仅显示检索结果
                search_results = retriever.search(query, limit=result_count)
                st.subheader("检索到的相关仓库")
                
                for i, result in enumerate(search_results):
                    repo_name = result["repo_name"]
                    repo_info = retriever.get_repo_details_from_db(repo_name)
                    
                    with st.expander(f"{i+1}. {repo_name} (相关度: {result['score']:.2f})"):
                        if repo_info:
                            col1, col2 = st.columns([3, 2])
                            with col1:
                                st.markdown(f"**描述**: {repo_info.get('description', '无描述')}")
                                st.markdown(f"**星标数**: {repo_info.get('stars', 0):,}")
                                st.markdown(f"**语言**: {repo_info.get('language', '未知')}")
                                st.markdown(f"**创建时间**: {repo_info.get('created_at', '未知')}")
                                st.markdown(f"**最后更新**: {repo_info.get('updated_at', '未知')}")
                                
                                # 显示README摘要
                                readme_content = result.get("readme_content", "")
                                if readme_content:
                                    st.markdown(readme_content[:1000] + "..." if len(readme_content) > 1000 else readme_content)
                            
                            with col2:
                                github_url = f"https://github.com/{repo_name}"
                                st.markdown(f"[在GitHub上查看]({github_url})")
                                # 显示贡献者信息
                                if repo_info.get('top_contributors'):
                                    st.subheader("主要贡献者")
                                    for c in repo_info['top_contributors'][:5]:
                                        st.markdown(f"- {c['login']} ({c['contributions']}次提交)")
                                
                                # 显示星标历史
                                star_history = result.get("star_history", {})
                                if star_history and len(star_history) > 1:
                                    st.subheader("星标增长趋势")
                                    history_data = sorted([(k, v) for k, v in star_history.items()])
                                    dates = [item[0] for item in history_data]
                                    stars = [item[1] for item in history_data]
                                    
                                    fig = px.line(x=dates, y=stars, labels={'x': '日期', 'y': '星标数'})
                                    st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.write("无法获取该仓库的详细信息")
            else:
                # 生成完整回答
                temperature = st.session_state.get('temperature', 0.7)
                max_tokens = st.session_state.get('max_tokens', 1500)
                
                # 获取检索结果
                search_results = retriever.search(query, limit=result_count)
                
                # 生成回答
                response = generator.generate_response(query)
                
                # 显示回答
                st.subheader("AI助手回答")
                st.markdown(response)
                
                # 显示检索到的相关仓库
                st.subheader("检索到的相关仓库")
                for i, result in enumerate(search_results):
                    repo_name = result["repo_name"]
                    with st.expander(f"{i+1}. {repo_name} (相关度: {result['score']:.2f})"):
                        repo_info = retriever.get_repo_details_from_db(repo_name)
                        if repo_info:
                            st.markdown(f"**描述**: {repo_info.get('description', '无描述')}")
                            st.markdown(f"**星标数**: {repo_info.get('stars', 0):,}")
                            st.markdown(f"**主要语言**: {repo_info.get('language', '未知')}")
                            
                            # 显示README摘要
                            readme_content = result.get("readme_content", "")
                            if readme_content:
                                st.markdown(readme_content[:2000] + "..." if len(readme_content) > 2000 else readme_content)


# 添加页脚
st.markdown('<div class="footer">GitHub项目智能助手 © 2025 | 基于RAG技术构建</div>', unsafe_allow_html=True)


st.sidebar.title("高级选项")
with st.sidebar.expander("查询设置"):
    st.write("自定义您的查询参数")
    temperature = st.slider("温度 (创造性)", min_value=0.0, max_value=1.0, value=0.7, step=0.1)
    max_tokens = st.slider("最大生成长度", min_value=500, max_value=3000, value=1500, step=100)
    
    # 保存设置到session_state
    st.session_state['temperature'] = temperature
    st.session_state['max_tokens'] = max_tokens