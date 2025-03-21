import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pyecharts.charts import ThemeRiver
import pyecharts.options as opts
from pyecharts.charts import Bar, Pie, Line, Calendar, Graph, WordCloud
from pyecharts.globals import ThemeType
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from pyecharts.charts import Page
from pyecharts.options import PageLayoutOpts
from pyecharts.commons.utils import JsCode

import mysql.connector
from qdrant_client import QdrantClient

import matplotlib.font_manager as fm

# 加载字体文件
plt.rcParams['font.sans-serif'] = ['SimHei']  # 指定默认字体为 SimHei（黑体）
 # 指定默认字体为 SimHei（黑体）
plt.rcParams['axes.unicode_minus'] = False

SETTINGS = {
    'mysql_host': 'localhost',
    'mysql_user': 'root',
    'mysql_password': 'root',
    'mysql_port': 3306,
    'qwen_api_key': 'sk-5f9692fe0afc4640a9bc543ada65941d'
}

def conn_init():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='root',
        port=3306,
        database='github_trend',
    )

    return conn

def qdrant_client_init():
    qdrant_client = QdrantClient(
        url="http://localhost:6333"
    )
    return qdrant_client

# 获取每年star数和分支数超过一定量的仓库数
def get_repo_num_by_year(min_stars=100, min_forks = 0):
    conn = conn_init()
    query= f"""
        SELECT 
            YEAR(created_at) AS year,  
            COUNT(*) AS num            
        FROM repositories
        WHERE stars >= {min_stars} and forks>={min_forks}
        GROUP BY year
        ORDER BY year                        
        """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# 绘制不同年份GitHub仓库数量的增长趋势
def visualize_repo_growth_by_year(min_stars=100, min_forks=0):
    """
    可视化不同年份GitHub仓库数量的增长趋势
    
    参数:
    min_stars: 最小star数量筛选条件
    min_forks: 最小fork数量筛选条件
    """
    # 获取数据
    df = get_repo_num_by_year(min_stars, min_forks)
    
    line = Line(
        init_opts=opts.InitOpts(
            width="900px", 
            height="500px", 
            theme=ThemeType.LIGHT,
        )
    )
    
    # 添加x轴数据（年份）
    line.add_xaxis(df['year'].astype(str).tolist())
    
    # 添加y轴数据（仓库数量）
    line.add_yaxis(
        series_name=f"Star≥{min_stars}的仓库数量",
        y_axis=df['num'].tolist(),
        symbol_size=8,
        is_smooth=True,
        label_opts=opts.LabelOpts(is_show=False),
        linestyle_opts=opts.LineStyleOpts(width=3)
    )
    
    # 设置全局选项
    line.set_global_opts(
        title_opts=opts.TitleOpts(
            title="GitHub高质量仓库数量年度变化趋势",
            pos_left="2%",
            padding=[10, 10]
        ),
        tooltip_opts=opts.TooltipOpts(
            trigger="axis",
            formatter="{a} <br/>{b}: {c}"
        ),
        xaxis_opts=opts.AxisOpts(
            type_="category",
            name="年份",
            name_location="end",
            axislabel_opts=opts.LabelOpts(rotate=0)
        ),
        yaxis_opts=opts.AxisOpts(
            type_="value",
            name="仓库数量",
            name_location="end",
            axistick_opts=opts.AxisTickOpts(is_show=True),
            splitline_opts=opts.SplitLineOpts(is_show=True)
        ),
        legend_opts=opts.LegendOpts(pos_top="9%"),
        datazoom_opts=[
            opts.DataZoomOpts(range_start=0, range_end=100),
            opts.DataZoomOpts(type_="inside", range_start=0, range_end=100)
        ],
    )
    
    return line

#  根据提供的数据，绘制主题河流图
def draw_river(result:pd.DataFrame, is_percentage=False):
    data_list = []
    for year in result.index:
        for language in result.columns:
            # 确保百分比值为浮点数而非整数
            percentage = float(result.loc[year, language])
            # 如果是百分比格式，将小数转换为百分比值
            if is_percentage:
                percentage = percentage * 100
            # ThemeRiver需要日期格式为字符串，确保年份为字符串
            data_list.append([f"{int(year)}", percentage, language])
    
    series = result.columns.tolist()
    
    if is_percentage:
        # 格式化提示框内容
        tooltip_formatter=JsCode("""
                function(params){
                console.log(params);
                var result ='<b>' + params[0].value[0] + '</b><br/>';
                params.forEach(function (item) {
            
                var year = item.value[0];  
                var percentage = item.value[1];  
                var language = item.value[2];  

                var formattedPercentage = percentage.toFixed(2);  
                result += language + ' : ' + formattedPercentage + '%<br/>';
                });

                return result
                }
            """)
    else:
        # 格式化提示框内容
        tooltip_formatter=JsCode("""
                function(params){
                console.log(params);
                var result ='<b>' + params[0].value[0] + '</b><br/>';
                params.forEach(function (item) {
            
                var year = item.value[0];  
                var percentage = item.value[1];  
                var language = item.value[2];  

                result += language + ' : ' + percentage + '<br/>';
                });

                return result
                }
        """)
    if is_percentage:
        title = "主流语言变化趋势（百分比）"
    else:
        title = "主流语言变化趋势（数量）"

    
    # 绘制，设置类型为时间
    theme_river = ThemeRiver(
            init_opts=opts.InitOpts(
                theme=ThemeType.LIGHT,
                width="100%",
                height="500px",
            )
        ).add(
            series_name=series, 
            data=data_list,  # 使用正确的数据列表
            singleaxis_opts=opts.SingleAxisOpts(
                type_='time',
                pos_left="2%",         # 设置左侧边距
                pos_right="0%",
                pos_top="15%",  
            ),
            label_opts=opts.LabelOpts(is_show=False)
        ).set_global_opts(
            title_opts=opts.TitleOpts(
                pos_left="2%",
                title=title,
                pos_top="0%",   # 放在顶部
                title_textstyle_opts=opts.TextStyleOpts(
                    font_size=20,
                    font_weight="bold",
                    color="#333"
                ),
                subtitle_textstyle_opts=opts.TextStyleOpts(
                    font_size=14,
                    color="#666"
                )
            ),
            tooltip_opts=opts.TooltipOpts(
                trigger = "axis",
                background_color="rgba(255,255,255,0.8)",
                border_color="#ccc",
                border_width=1,
                formatter=tooltip_formatter,  # 使用条件格式化
                textstyle_opts=opts.TextStyleOpts(color="#333")
            ),
            # 修改图例位置到右上角
            legend_opts=opts.LegendOpts(
                pos_right="2%",  # 放置在右侧
                pos_left="5%",
                pos_top="7%",    # 放在顶部
                orient="horizontal",  # 水平排列
                item_gap=5,
                item_width=20,
                item_height=12,
                textstyle_opts=opts.TextStyleOpts(
                    color="#333",
                    font_size=10
                    )
            ),
        )

    return theme_river

# 绘制主流语言变化的主题河流图
def draw_language_river(percentaged=True, top = 20):
    conn = conn_init()
    query = f"""
            WITH top_languages AS (
            SELECT `language`
            FROM repositories
            GROUP BY `language`
            ORDER BY COUNT(*) DESC
            LIMIT {top}
            )
            SELECT 
                CASE 
                    WHEN `language` IN ('') THEN '非程序性项目'
                    WHEN `language` IN ('JavaScript', 'TypeScript') THEN 'JavaScript/TypeScript'
                    WHEN `language` IN ('C', 'C++', 'C#') THEN 'C/C++/C#'
                    WHEN `language` IN (SELECT `language` FROM top_languages) THEN `language`  -- 保留前 20 的语言
                    ELSE 'others'  -- 其他语言汇总为 'others'
                END AS language_group,  -- 重命名分组后的语言
                YEAR(created_at) AS year,  -- 提取年份
                COUNT(*) AS num  -- 计算每年的记录数
            FROM 
                repositories
            GROUP BY 
                language_group, year  -- 按分组后的语言和年份分组
            ORDER BY 
                year;  -- 按年份排序
        """
    result = pd.read_sql(query, conn)
    result=result.pivot(index='year', columns='language_group', values='num').fillna(0)
    if percentaged:
        result=result.div(result.sum(axis=1), axis=0)

    return draw_river(result, percentaged)

def get_fastest_growing_repo_2025():
    """
    查询repositories表中stars和stars_last_update差值最大的且created_at在2025年内的仓库
    
    返回:
    str: 增长最快的仓库名称
    """
    conn = conn_init()
    query = """
        SELECT 
            name,
            stars,
            stars_last_update,
            (stars - stars_last_update) AS star_growth
        FROM 
            repositories
        WHERE 
            created_at >= '2025-01-01' AND 
            created_at <= '2025-12-31' AND
            stars_last_update IS NOT NULL
        ORDER BY 
            star_growth DESC
        LIMIT 1
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    if df.empty:
        print("未找到符合条件的仓库")
        return None
    
    repo_name = str(df['name'].iloc[0])
    return repo_name

# 获得仓库的star历史
def get_repo_star_history(repo_name, qdrant_client):
    # 构建查询
    query_filter  = Filter(
        must=[  # 必须满足的条件
            FieldCondition(
                key="repo_name",  # payload 中的字段
                match=MatchValue(value=repo_name),  # 匹配值
            )
        ]
    )
    
    # 从Qdrant获取数据
    search_result = qdrant_client.scroll(
        collection_name="github_repos",
        scroll_filter=query_filter,
        limit=10  # 根据需要调整
    )
    
    if not search_result:
        print(f"未找到仓库 {repo_name} 的数据")
        return None
    
    repo= search_result[0][0]
    star_history = repo.payload.get('star_history', {})

    if not star_history:
        print(f"仓库 {repo_name} 没有Star历史记录")
        return None
    
    star_history_df = pd.DataFrame(list(star_history.items()), columns=['date', 'stars'])
    star_history_df['date'] = pd.to_datetime(star_history_df['date'])
    star_history_df.sort_values(by='date', inplace=True)
    star_history_df['cumulative_stars'] = star_history_df['stars'].cumsum()
    return star_history_df

# 绘制star增长趋势图
def visualize_stars_over_time(star_df, repo_name):
    """
    可视化仓库随时间获得的star数量
    """
    if star_df.empty:
        print("没有star历史数据，无法创建时间趋势图")
        return None

    average_growth = star_df['stars'].mean()
    show_labels = (star_df['stars'] > average_growth).tolist()
    
    # 创建折线图
    line = (Line(
        init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="100%", height='400px',)
        ).add_xaxis(
            star_df['date'].dt.strftime('%Y-%m-%d').tolist()
        ).add_yaxis(
            "累计Star数", 
            star_df['cumulative_stars'].tolist(), 
            is_smooth=True,
            is_hover_animation=True,
            label_opts=opts.LabelOpts(
                is_show=False,  # 默认显示标签
                position="top",  # 标签位置
            ),
        ).set_global_opts(
            title_opts=opts.TitleOpts(title=f"Star增长趋势"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            xaxis_opts=opts.AxisOpts(
                name_location="end",
                name_gap=1,
                type_="category", 
                name="日期",
                 ),
            yaxis_opts=opts.AxisOpts(
                type_="value",
                name="Star数量",

                axislabel_opts=opts.LabelOpts(
                    rotate=0,
                    font_size=12,
                    margin=1,
                )
            ),
            datazoom_opts=[
                opts.DataZoomOpts(range_start=0, range_end=100),
                opts.DataZoomOpts(type_="inside", range_start=0, range_end=100),
            ],
            legend_opts=opts.LegendOpts(
                pos_right="2%",  # 放置在右侧
                pos_left="70%",
                pos_top="3%",    # 放在顶部
            ),
            
        )
    )
    
    return line

# 绘制star日历图
def visualize_star_calendar(star_df, repo_name):
    """
    创建Star活动的日历热图
    """
    if star_df.empty:
        print("没有star历史数据，无法创建日历热图")
        return None
    
    # 准备日历图数据
    calendar_data = [
        [str(star_df.loc[i, 'date'].strftime("%Y-%m-%d")), int(star_df.loc[i, 'stars'])]
        for i in range(len(star_df))
    ]
    
    # 获取日期范围
    from datetime import datetime, timedelta
    
    def get_week_range(date):
        """
        获取给定日期所在星期的第一天和最后一天
        """
        start_of_week = date - timedelta(days=date.weekday()+1)  # 星期一是第一天
        end_of_week = start_of_week + timedelta(days=6)        # 星期日是最后一天
        return start_of_week, end_of_week

    # 获取star_df中第一行日期的星期范围
    min_date = star_df.iloc[0,0].date()
    max_date = star_df.iloc[-1,0].date()

    # 调整为星期范围
    min_date, _ = get_week_range(min_date)
    _, max_date = get_week_range(max_date)

    # 创建日历热图
    calendar = (Calendar(
        init_opts=opts.InitOpts(theme=ThemeType.LIGHT,width="90%",height='300px',)
        ).add(
            series_name="Star数量",
            yaxis_data=calendar_data,
            singleaxis_opts=opts.SingleAxisOpts(
                type_='time',
                pos_left="0%",         # 设置左侧边距
                pos_right="1%" 
                ),
            calendar_opts=opts.CalendarOpts(
                range_=[min_date, max_date],
                pos_right="10",

                daylabel_opts=opts.CalendarDayLabelOpts(name_map="en"),
                monthlabel_opts=opts.CalendarMonthLabelOpts(name_map="en"),
            ),
        ).set_global_opts(
            title_opts=opts.TitleOpts(title=f"Star增长日历"),
            visualmap_opts=opts.VisualMapOpts(
                max_=int(star_df['stars'].max()),
                min_=int(star_df['stars'].min()),
                orient="horizontal",
                is_piecewise=False,
                pos_top="0%",  # 距离顶部5%
                pos_right="1%"  # 距离右侧5%
            ),
            legend_opts=opts.LegendOpts(is_show=False),
            xaxis_opts=opts.AxisOpts(
                offset=-15
            ),
        )
    )
    
    return calendar

# 获得仓库的topic数据
def get_topics_num_dict(begin_year=None,end_year=None, year=None):
    conn = conn_init()
    query = """
        select name, topics 
        from repositories
    """
    if year:
        query += f" where created_at >= '{year}-01-01' and created_at <= '{year}-12-31'"
    elif begin_year and end_year:
        query += f" where created_at >= '{begin_year}-01-01' and created_at <= '{end_year}-12-31'"
    result =pd.read_sql(query, conn)
    result.head()
    length = result.shape[0]
    topics_num_dict = {}
    for i in range(length):
        elements = result['topics'][i].split(',')
        if elements == ['']:
            continue
        for element in elements:
            if element in topics_num_dict:
                topics_num_dict[element] += 1
            else:
                topics_num_dict[element] = 1
    topics_num_dict = {k: v for k, v in sorted(topics_num_dict.items(), key=lambda item: item[1], reverse=True)}

    return topics_num_dict

# 根据topic词表绘制词云图
def draw_topic_wordcloud(data=None,mask_img_path=None):
    if not data:
        data = get_topics_num_dict()
    data =[(k,v) for k,v in data.items()][:min(100,len(data))]

    wordcloud = (
        WordCloud(
            init_opts=opts.InitOpts(theme=ThemeType.LIGHT,width="100%",height='300px',)
        )
        .add(
            series_name="Topic",  # 系列名称
            data_pair=data,  # 数据
            word_size_range=[10, 80],  # 词语字体大小范围
            width = "100%", 
            pos_right="0%",

        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="主题词云"),  # 标题
            tooltip_opts=opts.TooltipOpts(is_show=True),  # 提示框
        )
    )
    return wordcloud

"""绘制主题网络图"""
# 获得图数据
def get_topics_graph_data(min_node_value=1000, min_edge_value=100, max_nodes=200):
    """
    获取主题网络图数据
    
    参数:
    min_node_value: 节点最小出现次数
    min_edge_value: 边的最小权重
    max_nodes: 最大节点数量
    """
    conn = conn_init()
    query = """
        select name, topics 
        from repositories
    """
    result = pd.read_sql(query, conn)
    conn.close()
    
    # 存储节点信息
    nodes_dict = {}  # 记录每个topic元素出现的次数
    # 存储边信息（无向图）
    edges_dict = {}  # 记录任意两个topic元素共同出现的次数
    
    length = result.shape[0]
    for i in range(length):
        elements = result['topics'][i].split(',')
        if elements == ['']:
            continue
            
        # 去重，确保同一仓库中重复的topic只计算一次
        elements = list(set(elements))
        
        # 更新节点出现次数
        for element in elements:
            if element in nodes_dict:
                nodes_dict[element] += 1
            else:
                nodes_dict[element] = 1
        
        # 更新边的权重（任意两个元素的共现次数）
        for i in range(len(elements)):
            for j in range(i+1, len(elements)):  # 只处理不重复的组合
                # 确保边的两个节点按字母顺序排序，保证无向图的唯一性
                edge = tuple(sorted([elements[i], elements[j]]))
                if edge in edges_dict:
                    edges_dict[edge] += 1
                else:
                    edges_dict[edge] = 1
    
    # 筛选出现次数较多的节点
    filtered_nodes = {k: v for k, v in nodes_dict.items() if v >= min_node_value}
    # 按出现次数排序并限制节点数量
    sorted_nodes = dict(sorted(filtered_nodes.items(), key=lambda item: item[1], reverse=True)[:max_nodes])
    
    # 筛选权重较高的边，且边的两个节点都在筛选后的节点集合中
    filtered_edges = {e: count for e, count in edges_dict.items() 
                     if count >= min_edge_value and e[0] in sorted_nodes and e[1] in sorted_nodes}
    
    # 返回节点和边的原始数据
    return {"nodes": sorted_nodes, "edges": filtered_edges}

def colorsys_hsv_to_rgb(h, s, v):
    """HSV转RGB"""
    if s == 0.0:
        return (v, v, v)
    i = int(h * 6.0)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i = i % 6
    if i == 0:
        return (v, t, p)
    if i == 1:
        return (q, v, p)
    if i == 2:
        return (p, v, t)
    if i == 3:
        return (p, q, v)
    if i == 4:
        return (t, p, v)
    if i == 5:
        return (v, p, q)

def detect_communities(graph_data, algorithm='louvain'):
    """
    使用igraph进行社区发现
    
    参数:
    graph_data: 图数据，包含节点和边
    algorithm: 社区发现算法，可选 'louvain', 'label_propagation', 'fast_greedy'
    
    返回:
    带有社区标签的节点和边数据
    """
    try:
        import igraph as ig
    except ImportError:
        print("请安装igraph库: pip install python-igraph")
        # 如果没有igraph，回退到NetworkX
        return detect_communities_nx(graph_data, algorithm)
    
    # 创建igraph图
    G = ig.Graph()
    
    # 添加节点
    node_names = list(graph_data["nodes"].keys())
    node_weights = list(graph_data["nodes"].values())
    G.add_vertices(len(node_names))
    
    # 设置节点名称属性
    G.vs["name"] = node_names
    G.vs["weight"] = node_weights
    
    # 创建节点名称到索引的映射
    name_to_idx = {name: i for i, name in enumerate(node_names)}
    
    # 添加边
    edges = []
    weights = []
    for edge, weight in graph_data["edges"].items():
        edges.append((name_to_idx[edge[0]], name_to_idx[edge[1]]))
        weights.append(weight)
    
    G.add_edges(edges)
    G.es["weight"] = weights
    
    # 社区发现
    if algorithm == 'louvain':
        # Louvain方法
        partition = G.community_multilevel(weights="weight")
    elif algorithm == 'label_propagation':
        # 标签传播
        partition = G.community_label_propagation(weights="weight")
    elif algorithm == 'fast_greedy':
        # 快速贪婪算法
        partition = G.community_fastgreedy(weights="weight").as_clustering()
    else:
        # 默认使用Louvain
        partition = G.community_multilevel(weights="weight")
    
    # 获取社区数量
    num_communities = len(partition)
    
    # 生成社区颜色
    colors = generate_colors(num_communities)
    
    # 构建节点列表，包含社区信息
    nodes = []
    for i, node in enumerate(node_names):
        # 找到节点所属的社区
        community_id = None
        for j, community in enumerate(partition):
            if i in community:
                community_id = j
                break
        
        weight = graph_data["nodes"][node]
        nodes.append({
            "name": node, 
            "symbolSize": min(weight/100 + 10, 50), 
            "value": weight,
            "category": community_id,
            "itemStyle": {"color": colors[community_id]}
        })
    
    # 构建边列表
    links = []
    for edge, weight in graph_data["edges"].items():
        links.append({
            "source": edge[0], 
            "target": edge[1], 
            "value": weight
        })
    
    # 构建类别列表
    categories = [{"name": f"社区 {i}"} for i in range(num_communities)]
    
    return {"nodes": nodes, "links": links, "categories": categories}

def generate_colors(n):
    """生成n种不同的颜色"""
    colors = []
    for i in range(n):
        # 使用HSV色彩空间生成均匀分布的颜色
        hue = i / n
        # 转换为RGB十六进制
        r, g, b = [int(x * 255) for x in colorsys_hsv_to_rgb(hue, 0.7, 0.9)]
        colors.append(f"#{r:02x}{g:02x}{b:02x}")
    return colors


def visualize_topics_network(community_data):
    """创建主题网络图，包含社区信息"""
    c = (
        Graph(init_opts=opts.InitOpts(theme=ThemeType.LIGHT,width="100%", height="800px",))
        .add(
            "",
            community_data["nodes"],
            community_data["links"],
            categories=community_data["categories"],
            repulsion=10000,
            edge_length=150,
            gravity=0.2,
            layout="force",
            edge_label=opts.LabelOpts(is_show=False),
            label_opts=opts.LabelOpts(
                is_show=True,
                position="right",
                formatter="{b}"
            ),
            linestyle_opts=opts.LineStyleOpts(
                width=1,
                curve=0.3,
                opacity=0.7,
            ),
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="主题网络"),
            legend_opts=opts.LegendOpts(
                is_show=True,
                orient="vertical",
                pos_left="2%",
                pos_top="middle"
            ),
            tooltip_opts=opts.TooltipOpts(
                formatter="""
                <div>
                    <div>主题: {b}</div>
                    <div>出现次数: {c}</div>
                    <div>社区: {d}</div>
                </div>
                """
            ),
        )
    )
    return c


def get_top_contributors(limit=20):
    """
    从top_contributors视图中获取前N名贡献者数据
    
    参数:
    limit: 获取的贡献者数量，默认为20
    
    返回:
    包含贡献者名称和贡献数量的DataFrame
    """
    conn = conn_init()
    query = f"""
        SELECT curl, total_allocated_star
        FROM top_contributors
        LIMIT {limit}
    """
    df = pd.read_sql(query, conn)
    df['contributor_name'] = df['curl'].str.replace('https://github.com/', '')
    conn.close()
    return df

# 可视化贡献者数据为条形图
def visualize_top_contributors(contributors_df=None, limit=20):
    """
    将贡献者数据可视化为水平条形图
    
    参数:
    contributors_df: 包含贡献者数据的DataFrame，如果为None则自动获取
    limit: 如果contributors_df为None，获取的贡献者数量
    
    返回:
    pyecharts Bar图表对象
    """
    if contributors_df is None:
        contributors_df = get_top_contributors(limit)
    
    if contributors_df.empty:
        print("没有贡献者数据，无法创建可视化")
        return None
    
    # 反转数据顺序，使最高贡献者显示在顶部    
    contributors_df = contributors_df.sort_values(by='total_allocated_star')
    
    tooltip_formatter=JsCode("""
            function(params){
            var result = params.value;  
            result = result.toFixed(0);  

            return result
            }
        """)
    x_label_formatter = JsCode("""
            function(params){
            params = params/1000 + 'k';

            return params
            }
        """)

    bar = (
        Bar(
            init_opts=opts.InitOpts(
                height="650px", 
                theme=ThemeType.LIGHT,
            )
        )
        .add_xaxis(contributors_df['contributor_name'].tolist())
        .add_yaxis(
            "贡献数量",
            contributors_df['total_allocated_star'].tolist(),
            label_opts=opts.LabelOpts(
                position="right",
                formatter=tooltip_formatter
            ),
        )
        .reversal_axis()  # 反转坐标轴，使贡献者名称在y轴
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title="Top贡献者",
                subtitle="贡献值根据对repository的contribution以相应的star数量加权计算",
                title_textstyle_opts=opts.TextStyleOpts(
                    font_size=20,
                    font_weight="bold",
                    color="#333"
                ),
                subtitle_textstyle_opts=opts.TextStyleOpts(
                    font_size=10,
                    color="#666"
                ),
                pos_left="2%",
                padding=[2, 10],
                item_gap = 5
            
            ),
            xaxis_opts=opts.AxisOpts(
                name="贡献量",
                name_location="end",
                name_gap=1,
                axistick_opts=opts.AxisTickOpts(is_show=True),
                splitline_opts=opts.SplitLineOpts(is_show=True),
                axislabel_opts=opts.LabelOpts(
                    rotate=45,
                    formatter=x_label_formatter,
                ),
                
            ),
            yaxis_opts=opts.AxisOpts(
                name="贡献者",
                name_location="end",
                name_gap=1,
                axislabel_opts=opts.LabelOpts(
                    rotate=0,
                    font_size=10,
                    margin=1,
                ),

            ),
            legend_opts=opts.LegendOpts(is_show=False)
        )
    )
    
    return bar
