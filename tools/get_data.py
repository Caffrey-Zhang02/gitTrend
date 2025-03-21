import requests
import time
import random
import datetime
import base64
import mysql.connector
import datetime

import mysql.connector
import pandas as pd
from tqdm import tqdm
from qdrant_client import QdrantClient
from qdrant_client.http import models
from openai import OpenAI

# 导入配置项
from tools.config import DEFAULT_SETTINGS

def conn_init(SETTINGS=DEFAULT_SETTINGS):
    """初始化数据库连接"""
    conn = mysql.connector.connect(
        host=SETTINGS['mysql_host'],
        port=SETTINGS['mysql_port'],
        user=SETTINGS['mysql_user'],
        password=SETTINGS['mysql_password'],
        auth_plugin='mysql_native_password',
        database=SETTINGS['database']
    )
    return conn

def create_tables():
    """创建必要的数据库表"""
    # 连接到MySQL服务器
    conn = conn_init()
    cursor = conn.cursor()
    
    # 创建数据库
    cursor.execute("CREATE DATABASE IF NOT EXISTS github_trend")
    cursor.execute("USE github_trend")
    
    # 创建repositories表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS repositories (
        name VARCHAR(255),
        url VARCHAR(255) PRIMARY KEY,
        description TEXT,
        stars INT,
        forks INT,
        language VARCHAR(100),
        created_at DATETIME,
        updated_at DATETIME,
        topics TEXT,
        size INT,
        homepage VARCHAR(255),
        owner_type VARCHAR(50),
        pushed_at DATETIME,
        stars_last_update INT
    )
    """)
    
    # 创建log表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS log (
        table_name VARCHAR(255) PRIMARY KEY,
        last_update DATETIME,
        records_total INT,
        records_new INT,
        records_updated INT
    )
    """)
    
    # 创建repo_qdrant_mapping表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS repo_qdrant_mapping (
        id INT AUTO_INCREMENT PRIMARY KEY,
        repo_name VARCHAR(255) NOT NULL,
        qdrant_id VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY unique_repo_name (repo_name)
    )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()

def get_repo_count(SETTINGS=DEFAULT_SETTINGS, min_stars=100, create_date=None, query=None):
    """获取符合条件的仓库数量"""
    if not query:
        query = f"stars:>={min_stars}"
        if create_date:
            query += f" created:>={create_date}"
        
    GITHUB_API_URL = "https://api.github.com/search/repositories"

    params = {
        "q": query,
        "per_page": 1  # 每页只返回1条结果，减少数据量
    }
    response = requests.get(GITHUB_API_URL, headers=SETTINGS['headers'], params=params)
    if response.status_code == 200:
        data = response.json()
        return data["total_count"]  # 返回符合条件的仓库总数
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

def format_datetime(dt_str):
    """将日期时间字符串转换为 MySQL 兼容格式"""
    if not dt_str:
        return None
    try:
        # 检查是否为 ISO 8601 格式 (包含 'T' 和 'Z')
        if 'T' in dt_str and (dt_str.endswith('Z') or '+' in dt_str):
            # 尝试解析 ISO 8601 格式的日期时间
            if dt_str.endswith('Z'):
                dt = datetime.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")
            else:
                # 处理带时区偏移的格式
                dt = datetime.datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            # 转换为 MySQL 兼容格式
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            # 如果不是 ISO 格式，检查是否已经是 MySQL 兼容格式
            try:
                datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                return dt_str  # 已经是兼容格式，直接返回
            except ValueError:
                # 尝试其他常见格式
                for fmt in ["%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"]:
                    try:
                        dt = datetime.datetime.strptime(dt_str, fmt)
                        return dt.strftime("%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        continue
                # 如果所有尝试都失败，返回当前时间
                return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"日期转换错误: {dt_str}, 错误: {str(e)}")
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def search_github_repos(query, page=1, SETTINGS=DEFAULT_SETTINGS):
    """
    搜索GitHub仓库
    """
    GITHUB_API_URL = "https://api.github.com/search/repositories"
    
    params = {
        "q": query,
        "sort": SETTINGS['sort'],
        "order": SETTINGS['order'],
        "per_page": SETTINGS['perpage'],
        "page": page
    }
    
    try:
        response = requests.get(GITHUB_API_URL, headers=SETTINGS['headers'], params=params)
        
        # 检查是否达到API速率限制
        if response.status_code == 403 and 'X-RateLimit-Remaining' in response.headers and int(response.headers['X-RateLimit-Remaining']) == 0:
            reset_time = int(response.headers['X-RateLimit-Reset'])
            sleep_time = reset_time - time.time() + 10  # 加10秒作为缓冲
            if sleep_time > 0:
                print(f"达到API速率限制，等待 {sleep_time:.0f} 秒后继续...")
                time.sleep(sleep_time)
                return search_github_repos(query, page, SETTINGS)
        
        # 处理其他HTTP错误
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            return None
        
        return response.json()
    
    except Exception as e:
        print(f"请求异常: {e}")
        return None


def get_top_starred_repos(query=None, start_date='2010-01-01', end_date='2025-01-01', SETTINGS=DEFAULT_SETTINGS, start_page=1, max_pages=10):
    """
    获取 GitHub 上 star 数超过指定数量的仓库，并动态保存到MySQL数据库
    如果记录已存在，则只更新变动的值
    
    参数:
        start_date: 开始日期，格式为 "YYYY-MM-DD"
        end_date: 结束日期，格式为 "YYYY-MM-DD"
        SETTINGS: 配置字典，包含各种参数
        max_pages: 最大获取页数，默认为 10
    
    返回:
        包含写入和更新记录数以及错误数据的字典
    """
    # 导入math模块用于向上取整
    import math
    import calendar
    
    # 连接MySQL
    conn = conn_init()
    cursor = conn.cursor()
    
    # GitHub API 搜索端点
    url = "https://api.github.com/search/repositories"
    
    # 记录写入和更新的数量
    total_records = 0
    new_records = 0
    updated_records = 0
    
    # 创建错误数据的列表
    error_data = []

    start_date_obj = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date_obj = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    
    # 计算开始和结束的年月
    start_year, start_month = start_date_obj.year, start_date_obj.month
    end_year, end_month = end_date_obj.year, end_date_obj.month
    
    # 定义月内的时间段
    periods = [
        (1, 7),    # 1-7日
        (8, 14),   # 8-14日
        (15, 21),  # 15-21日
        (22, 31)   # 22日-月末（这里用31作为占位符，后面会根据实际月份调整）
    ]
    
    # 第一层循环：按月遍历
    current_year, current_month = start_year, start_month
    
    while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
        # 获取当月的最后一天
        _, last_day_of_month = calendar.monthrange(current_year, current_month)
        
        # 第二层循环：按月内时间段遍历
        for period_start, period_end in periods:
            # 调整时间段的结束日期，不能超过月末
            actual_period_end = min(period_end, last_day_of_month)
            
            # 如果时间段的开始日期已经超过月末，跳过此时间段
            if period_start > last_day_of_month:
                continue
                
            # 创建当前时间段的开始和结束日期
            try:
                period_start_date = datetime.date(current_year, current_month, period_start)
                period_end_date = datetime.date(current_year, current_month, actual_period_end)
            except ValueError as e:
                print(f"日期创建错误: {e}, 年:{current_year}, 月:{current_month}, 日:{period_start}-{actual_period_end}")
                continue
            
            # 如果是开始月份且时间段开始日期早于指定的开始日期，调整时间段开始日期
            if current_year == start_year and current_month == start_month and period_start_date < start_date_obj:
                if start_date_obj > period_end_date:
                    # 如果整个时间段都在开始日期之前，跳过此时间段
                    continue
                period_start_date = start_date_obj
            
            # 如果是结束月份且时间段结束日期晚于指定的结束日期，调整时间段结束日期
            if current_year == end_year and current_month == end_month and period_end_date > end_date_obj:
                if end_date_obj < period_start_date:
                    # 如果整个时间段都在结束日期之后，跳过此时间段
                    continue
                period_end_date = end_date_obj
            
            # 格式化日期为GitHub API查询格式
            period_start_str = period_start_date.strftime("%Y-%m-%d")
            period_end_str = period_end_date.strftime("%Y-%m-%d")
            
            # 构建查询条件：stars数量大于等于min_stars，且创建时间在指定时间段
            query = f"stars:>={SETTINGS['min_stars']} created:{period_start_str}..{period_end_str}"
            
            print(f"\n开始获取 {current_year}-{current_month:02d} 的 {period_start_date.day}-{period_end_date.day} 日创建的仓库数据...")
            print(f"日期范围: {period_start_str} 到 {period_end_str}")
            
            # 获取符合条件的仓库总数
            params = {
                "q": query,
                "per_page": 1
            }
            response = requests.get(url, headers=SETTINGS['headers'], params=params)
            
            if response.status_code == 200:
                data = response.json()
                repo_count = data.get("total_count", 0)
                print(f"{current_year}-{current_month:02d} 的 {period_start_date.day}-{period_end_date.day} 日符合条件的仓库总数: {repo_count}")
            else:
                print(f"获取仓库数量失败，状态码: {response.status_code}")
                print(f"错误信息: {response.text}")
                # 如果是因为 API 速率限制而失败，等待一段时间后重试
                if response.status_code == 403:
                    reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                    wait_time = max(reset_time - time.time(), 0) + 1
                    print(f"API 速率限制已达到，等待 {wait_time:.0f} 秒后重试...")
                    time.sleep(wait_time)
                    # 重试当前时间段
                    continue
                else:
                    # 跳过当前时间段
                    continue
            
            # 如果没有符合条件的仓库，跳过当前时间段
            if repo_count == 0:
                print(f"{current_year}-{current_month:02d} 的 {period_start_date.day}-{period_end_date.day} 日没有符合条件的仓库，跳过")
                continue
                
            # 计算最大页数 (每页100条，向上取整)
            calculated_max_pages = math.ceil(repo_count / SETTINGS['perpage'])
            # 使用计算出的页数和用户指定的max_pages中较小的一个
            actual_max_pages = min(calculated_max_pages, max_pages)
            
            # 计算结束页码
            end_page = start_page + actual_max_pages - 1
            
            print(f"{current_year}-{current_month:02d} 的 {period_start_date.day}-{period_end_date.day} 日将获取 {start_page} 到 {end_page} 页的数据 (共 {actual_max_pages} 页)")
            
            # 第三层循环：分页获取数据
            for page in tqdm(range(start_page, end_page + 1), desc=f"获取 {current_year}-{current_month:02d} 的 {period_start_date.day}-{period_end_date.day} 日的仓库数据"):
                params = {
                    "q": query,
                    "sort": SETTINGS['sort'],
                    "order": SETTINGS['order'],
                    "per_page": SETTINGS['perpage'],  # 每页最多 100 条结果
                    "page": page
                }
            
                # 发送请求
                response = requests.get(url, headers=SETTINGS['headers'], params=params)
                
                # 检查请求是否成功
                if response.status_code == 200:
                    data = response.json()
                    repos = data.get("items", [])
                    
                    # 如果没有更多仓库，退出循环
                    if not repos:
                        break
                        
                    # 逐条处理数据，使用INSERT ... ON DUPLICATE KEY UPDATE
                    for repo in repos:
                        try:
                            # 处理可能的NULL值
                            description = repo.get("description", "")
                            if description is None:
                                description = ""
                            
                            language = repo.get("language", "")
                            if language is None:
                                language = ""
                                
                            # 处理topics（列表转为逗号分隔的字符串）
                            topics = ",".join(repo.get("topics", []))
                            
                            # 处理homepage
                            homepage = repo.get("homepage", "")
                            if homepage is None:
                                homepage = ""
                            
                            # 获取owner_type
                            owner_type = repo.get("owner", {}).get("type", "")
                            
                            # 使用INSERT ... ON DUPLICATE KEY UPDATE
                            insert_query = """
                            INSERT INTO repositories 
                            (name, url, description, stars, stars_last_update, forks, language, created_at, updated_at, 
                            topics, size, homepage, owner_type, pushed_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                name = VALUES(name),
                                description = VALUES(description),
                                stars_last_update = stars,
                                stars = VALUES(stars),
                                forks = VALUES(forks),
                                language = VALUES(language),
                                updated_at = VALUES(updated_at),
                                topics = VALUES(topics),
                                size = VALUES(size),
                                homepage = VALUES(homepage),
                                owner_type = VALUES(owner_type),
                                pushed_at = VALUES(pushed_at)
                            """
                            
                            # 获取当前star数
                            current_stars = repo.get("stargazers_count", 0)
                            
                            values = (
                                repo.get("full_name", ""),
                                repo.get("html_url", ""),
                                description,
                                current_stars,
                                0,  # 对于新记录，stars_last_update 设为 0
                                repo.get("forks_count", 0),
                                language,
                                format_datetime(repo.get("created_at", "")),
                                format_datetime(repo.get("updated_at", "")),
                                topics,
                                repo.get("size", 0),
                                homepage,
                                owner_type,
                                format_datetime(repo.get("pushed_at", ""))
                            )
                            
                            cursor.execute(insert_query, values)
                            
                            # 检查是插入新记录还是更新已有记录
                            if cursor.rowcount == 1:
                                new_records += 1
                            elif cursor.rowcount == 2:  # MySQL对于ON DUPLICATE KEY UPDATE，如果更新了记录，rowcount为2
                                updated_records += 1
                            
                            total_records += 1
                            
                        except Exception as e:
                            # 记录错误数据
                            error_info = {
                                "repo": repo.get("full_name", ""),
                                "url": repo.get("html_url", ""),
                                "error": str(e),
                                "page": page
                            }
                            error_data.append(error_info)
                            print(f"处理数据出错: {error_info['repo']}, 错误: {str(e)}")
                    
                    # 提交事务
                    conn.commit()
                    
                    print(f"第 {page} 页: 处理了 {len(repos)} 条记录，新增: {new_records}，更新: {updated_records}，错误: {len(error_data)}")
                    
                    # GitHub API 有速率限制，添加延时避免触发限制
                    time.sleep(random.uniform(1,2))
                else:
                    print(f"请求失败，状态码: {response.status_code}")
                    print(f"错误信息: {response.text}")
                    # 如果是因为 API 速率限制而失败，等待一段时间后重试
                    if response.status_code == 403:
                        reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                        wait_time = max(reset_time - time.time(), 0) + 1
                        print(f"API 速率限制已达到，等待 {wait_time:.0f} 秒后重试...")
                        time.sleep(wait_time)
                        # 重试当前页
                        page -= 1
                    else:
                        break
        
        # 移动到下一个月
        if current_month == 12 and current_year != end_year:
            current_year += 1
            current_month = 1
        else:
            current_month += 1
    try:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_query = """
        INSERT INTO log (table_name, last_update, records_total, records_new, records_updated)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            last_update = VALUES(last_update),
            records_total = records_total + %s, 
            records_new = records_new + %s, 
            records_updated = records_updated + %s
        """
        cursor.execute(log_query, ("repositories", current_time, total_records, new_records, updated_records,
                                  total_records, new_records, updated_records))
        conn.commit()
        print(f"日志表更新成功，记录时间: {current_time}")
    except Exception as e:
        print(f"更新日志表出错: {str(e)}")

    # 关闭数据库连接
    cursor.close()
    conn.close()
    
    # 创建错误数据的DataFrame
    error_df = pd.DataFrame(error_data) if error_data else pd.DataFrame()
    
    return {
        "total": total_records, 
        "new": new_records, 
        "updated": updated_records, 
        "error_df": error_df
    }


def get_coordinates(query,SETTINGS=DEFAULT_SETTINGS):
    conn = conn_init(SETTINGS=SETTINGS)
    cursor = conn.cursor()

    cursor.execute(query)
    results = cursor.fetchall()
    result = [result[0] for result in results]
    cursor.close()
    conn.close()

    return result

def clean_markdown(markdown_text):
    """
    清理Markdown文本，去除链接、换行符、HTML标签和HTML实体
    
    参数:
        markdown_text: 原始Markdown文本
        
    返回:
        清理后的纯文本
    """
    import re
    
    if not markdown_text:
        return ""
    
    # 去除Markdown链接，保留链接文本
    # 例如：[链接文本](https://example.com) -> 链接文本
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', markdown_text)
    
    # 去除图片标记
    # 例如：![图片描述](image.jpg) -> 图片描述
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)
    
    # 去除HTML标签
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # 去除HTML实体
    text = re.sub(r'&[a-zA-Z0-9#]+;', ' ', text)
    
    # 去除代码块
    text = re.sub(r'```[\s\S]*?```', ' ', text)
    text = re.sub(r'`[^`]*`', ' ', text)
    
    # 去除多余的空白字符（包括换行符、制表符等）
    text = re.sub(r'\s+', ' ', text)
    
    # 去除Markdown标题标记 (# 标题)
    text = re.sub(r'#+\s+', '', text)
    
    # 去除Markdown强调标记 (*斜体* 或 **粗体**)
    text = re.sub(r'\*+([^*]+)\*+', r'\1', text)
    
    # 去除Markdown分隔线
    text = re.sub(r'---+', ' ', text)
    text = re.sub(r'===+', ' ', text)
    
    # 去除Markdown列表标记
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # 再次清理多余空白
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text

def get_readme(repo_name, headers):
    """获取仓库的README内容"""
    
    base_url = "https://api.github.com"
    readme_url = f"{base_url}/repos/{repo_name}/readme"
    response = requests.get(readme_url, headers=headers)
    
    readme_content = ""
    if response.status_code == 200:
        readme_data = response.json()
        if readme_data.get("encoding") == "base64":
            try:
                readme_content = base64.b64decode(readme_data.get("content", "")).decode('utf-8')
                readme_content = clean_markdown(readme_content)
            except Exception as e:
                print(f"解码README内容出错: {str(e)}")
    else:
        print(f"获取README失败，状态码: {response.status_code}")
    
    return readme_content

def get_contributors(repo_name, headers):
    """获取仓库的贡献者信息"""
    import requests
    import time
    
    base_url = "https://api.github.com"
    contributors_url = f"{base_url}/repos/{repo_name}/contributors"
    contributors = []
    page = 1
    per_page = 100
    
    while True:
        params = {
            "page": page,
            "per_page": per_page
        }
        response = requests.get(contributors_url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"获取贡献者信息失败，状态码: {response.status_code}")
            break
        
        page_contributors = response.json()
        if not page_contributors:
            break
            
        for contributor in page_contributors:
            contributors.append({
                "login": contributor.get("login"),
                "contributions": contributor.get("contributions"),
                "url": contributor.get("html_url"),
                "avatar_url": contributor.get("avatar_url")  # 添加头像URL
            })
        
        page += 1
        time.sleep(0.5)
        
        if len(page_contributors) < per_page:
            break
    
    return contributors

def get_star_history(repo_name, headers, max_pages=1000, silence=True):
    """获取仓库的star历史"""
    import requests
    import time
    import math
    from datetime import datetime
    
    base_url = "https://api.github.com"
    
    # 先获取仓库的总star数
    search_url = f"{base_url}/search/repositories"
    params = {
        "q": f"repo:{repo_name}",
        "per_page": 1
    }
    
    try:
        response = requests.get(search_url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if "items" in data and len(data["items"]) > 0:
                total_stars = data["items"][0].get("stargazers_count", 0)
                if not silence:
                    print(f"仓库 {repo_name} 的总star数: {total_stars}")
                
                # 计算需要获取的页数 (每页100条，向上取整)
                estimated_pages = math.ceil(total_stars / 100)
                if not silence:
                    print(f"预计需要获取 {estimated_pages} 页")
                
                # 如果预计页数超过最大页数限制，直接返回空结果
                if estimated_pages > max_pages:
                    print(f"预计需要获取 {estimated_pages} 页，超过最大限制 {max_pages} 页，跳过获取star历史")
                    return {}, True
            else:
                print(f"未找到仓库 {repo_name} 的信息")
        else:
            print(f"获取仓库信息失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
    except Exception as e:
        print(f"获取仓库star数出错: {str(e)}")
    
    # 继续原有的获取star历史的逻辑
    stargazers_url = f"{base_url}/repos/{repo_name}/stargazers"
    
    # 需要使用特殊的Accept头部来获取时间戳信息
    headers_with_timestamp = headers.copy()
    headers_with_timestamp['Accept'] = 'application/vnd.github.v3.star+json'
    
    star_history = {}
    page = 1
    per_page = 100
    exceeded_limit = False
    
    if not silence:
        print(f"开始获取 {repo_name} 的star历史...")
    
    while True:
        params = {
            "page": page,
            "per_page": per_page
        }
        response = requests.get(stargazers_url, headers=headers_with_timestamp, params=params)
        
        if response.status_code != 200:
            print(f"获取star历史失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            break
        
        stargazers = response.json()
        if not stargazers:
            break
            
        for star in stargazers:
            starred_at = star.get("starred_at")
            if starred_at:
                date_str = starred_at.split('T')[0]
                if date_str in star_history:
                    star_history[date_str] += 1
                else:
                    star_history[date_str] = 1
                
        page += 1
        if page>=500:
            time.sleep(2)
        else:
            time.sleep(1)
            
        if page%10 ==0 and not silence:
            print(f"已获取 {page*per_pagee} 条star记录")
        
        if len(stargazers) < per_page:
            break
        
        if page > max_pages:
            print(f"达到获取上限({max_pages}页)，停止获取更多star记录")
            exceeded_limit = True
            break
    
    return star_history, exceeded_limit

def create_embedding(text, SETTINGS=DEFAULT_SETTINGS):
    """使用Qwen模型创建文本嵌入"""
    
    client = OpenAI(
        api_key=SETTINGS.get('qwen_api_key'),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    
    # 截取文本以适应API限制
    text = text[:8000] if text else ""
    
    try:
        completion = client.embeddings.create(
            model="text-embedding-v3",
            input=text,
            dimensions=1024,
            encoding_format="float"
        )
        return completion.data[0].embedding
    except Exception as e:
        print(f"创建嵌入向量失败: {str(e)}")
        # 返回一个全零向量作为fallback
        return [0.0] * 1024

def save_contributors_to_db(contributors, repo_name, repo_url, conn, silence=True):
    """将贡献者信息保存到MySQL数据库"""
    cursor = conn.cursor()
    
    try:
        # 保存贡献者基本信息
        for contributor in contributors:
            # 插入或更新贡献者信息
            insert_contributor_query = """
            INSERT INTO contributors (url, login, avatar_url)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                login = VALUES(login),
                avatar_url = VALUES(avatar_url)
            """
            cursor.execute(insert_contributor_query, (
                contributor.get("url", ""),
                contributor.get("login", ""),
                contributor.get("avatar_url", "")
            ))
            
            # 插入或更新贡献者与仓库的关系
            insert_relation_query = """
            INSERT INTO repo_contributors (contributor_url, repo_url, contributions)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE contributions = VALUES(contributions)
            """
            cursor.execute(insert_relation_query, (
                contributor.get("url", ""),
                repo_url,
                contributor.get("contributions", 0)
            ))
        
        conn.commit()
        if not silence:
            print(f"已保存 {len(contributors)} 位贡献者信息到数据库")
    except Exception as e:
        conn.rollback()
        print(f"保存贡献者信息失败: {str(e)}")
    finally:
        cursor.close()

def save_to_qdrant(repo_name, readme_content, star_history, qdrant_client, collection_name, SETTINGS):
    """将数据保存到Qdrant"""
    import uuid
    from datetime import datetime
    
    # 基于仓库名生成确定性UUID (UUID v5)
    # 使用UUID命名空间和仓库名作为名称，确保同一仓库始终生成相同的UUID
    namespace = uuid.NAMESPACE_URL  # 使用URL命名空间
    qdrant_id = str(uuid.uuid5(namespace, f"github.com/{repo_name}"))
    
    # 创建README的嵌入向量
    embedding = create_embedding(readme_content, SETTINGS)
    
    # 存储到Qdrant
    qdrant_client.upsert(
        collection_name=collection_name,
        points=[
            models.PointStruct(
                id=qdrant_id,
                vector=embedding,
                payload={
                    "repo_name": repo_name,
                    "readme_content": readme_content,
                    "star_history": star_history,
                    "last_updated": datetime.now().isoformat()
                }
            )
        ]
    )
    
    return qdrant_id        

def update_mysql_mapping(repo_name, qdrant_id, conn, silence=True):
    """更新MySQL中的仓库-Qdrant ID映射"""
    cursor = conn.cursor()
    
    try:
        upsert_query = """
        INSERT INTO repo_qdrant_mapping (repo_name, qdrant_id, last_updated)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            qdrant_id = VALUES(qdrant_id),
            last_updated = VALUES(last_updated)
        """
        
        cursor.execute(upsert_query, (repo_name, qdrant_id, datetime.datetime.now()))
        conn.commit()
        if not silence:
            print(f"已更新 {repo_name} 的Qdrant ID映射")
    except Exception as e:
        conn.rollback()
        print(f"更新Qdrant ID映射失败: {str(e)}")
    finally:
        cursor.close()

def get_cached_data(repo_name, qdrant_client, collection_name, conn, ):
    """从缓存中获取数据"""
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 检查MySQL中是否已有该仓库的Qdrant ID映射
        query = "SELECT qdrant_id, last_updated FROM repo_qdrant_mapping WHERE repo_name = %s"
        cursor.execute(query, (repo_name,))
        mapping = cursor.fetchone()
        
        if mapping:
            qdrant_id = mapping['qdrant_id']
            last_updated = mapping['last_updated']
            
            # 如果上次更新时间在1天内，使用缓存数据
            if (datetime.datetime.now() - last_updated).days <= 1:
                print(f"{repo_name}使用缓存的数据，上次更新时间: {last_updated}")
                
                # 从Qdrant获取数据
                points = qdrant_client.retrieve(
                    collection_name=collection_name,
                    ids=[qdrant_id]
                )
                
                if points:
                    return {
                        "qdrant_id": qdrant_id,
                        "payload": points[0].payload,
                        "is_fresh": True
                    }
        
        return {"is_fresh": False}
    finally:
        cursor.close()

def get_repo_details(repo_name,repo_url, SETTINGS=DEFAULT_SETTINGS, renew_markdown=True, renew = False):
    """
    获取指定仓库的详细信息，包括贡献者、star增长记录、README文件内容
    将star历史和README内容存储到Qdrant中，并在MySQL中建立映射关系
    
    参数:
        repo_name: 仓库全名，格式为 "owner/repo"
        SETTINGS: 配置字典，包含GitHub API的认证信息等
        renew_markdown: 是否重新获取README内容，默认为True
        
    返回:
        包含仓库详细信息的字典
    """
    # 初始化结果字典
    result = {
        "name": repo_name,
        "contributors": [],
        "star_history": {},
        "readme_content": "",
    }

    
    # 超过API限制的项目列表
    exceeded_limit_repos = []
    
    # 连接MySQL
    conn = conn_init(SETTINGS)
    
    # 连接Qdrant
    qdrant_client = QdrantClient(
        url=SETTINGS.get('qdrant_url', 'http://localhost:6333')
    )
    
    # 确保集合存在
    collection_name = "github_repos"
    try:
        qdrant_client.get_collection(collection_name)
    except Exception:
        # 如果集合不存在，创建它
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=1024,  # 使用Qwen模型的嵌入维度
                distance=models.Distance.COSINE
            )
        )
    
    # 检查缓存
    cached_data = get_cached_data(repo_name, qdrant_client, collection_name, conn)
    
    need_update_stars = True
    need_update_readme = renew_markdown
    qdrant_id = cached_data.get("qdrant_id")
    
    # 如果有缓存且缓存是新鲜的
    if cached_data.get("is_fresh", False) and renew== False:
        payload = cached_data.get("payload", {})
        result["star_history"] = payload.get("star_history", {})
        
        # 如果不需要更新README，则使用缓存的README内容
        if not need_update_readme:
            result["readme_content"] = payload.get("readme_content", "")
            
        need_update_stars = False
    
    # 获取README内容
    if need_update_readme:
        result["readme_content"] = get_readme(repo_name, SETTINGS['headers'])
    
    # 获取贡献者信息
    result["contributors"] = get_contributors(repo_name, SETTINGS['headers'])
    
    # 保存贡献者信息到MySQL
    save_contributors_to_db(result["contributors"], repo_name, repo_url, conn)
    
    # 获取star历史
    if need_update_stars:
        star_history, exceeded_limit = get_star_history(repo_name, SETTINGS['headers'])
        result["star_history"] = star_history
        
        # 如果超过API限制，添加到列表
        if exceeded_limit:
            exceeded_limit_repos.append(repo_name)
    
    # 将数据存储到Qdrant和MySQL
    if need_update_stars or need_update_readme:
        # 保存到Qdrant
        qdrant_id = save_to_qdrant(
            repo_name, 
            result["readme_content"], 
            result["star_history"], 
            qdrant_client, 
            collection_name, 
            SETTINGS
        )
        
        # 更新MySQL中的映射关系
        update_mysql_mapping(repo_name, qdrant_id, conn)
    
    # 关闭数据库连接
    conn.close()
    
    # 返回结果和超过API限制的仓库列表
    return result, exceeded_limit_repos

# 示例使用方法
if __name__ == "__main__":
    """获取21年以来的star数大于一定值的仓库信息"""
    # 创建必要的数据库表
    create_tables()
    
    # 设置日期范围
    start_date = "2021-01-01"
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # 获取热门仓库数据
    result = get_top_starred_repos(None, start_date, end_date, DEFAULT_SETTINGS, start_page=1, max_pages=10)
    
    # 打印结果统计
    print(f"总共处理记录数: {result['total']}")
    print(f"新增记录数: {result['new']}")
    print(f"更新记录数: {result['updated']}")
    
    # 如果有错误数据，可以查看或保存
    if not result['error_df'].empty:
        print(f"错误数据量:{result['error_df'].shape[0]}")
        # 保存错误数据到CSV文件
        result['error_df'].to_csv(f"./error_repos_{end_date}.csv", index=False)


    """获取2025年以来的star数大于一定值的仓库详细信息"""
    conn=conn_init(DEFAULT_SETTINGS)
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT name, url 
        from repositories
        where created_at>='2025-01-01'
    """

    # 执行查询获取仓库列表
    cursor.execute(query)
    repos = cursor.fetchall()

    # 关闭游标和连接
    cursor.close()
    conn.close()

    print(f"共找到 {len(repos)} 个仓库需要处理")

    # 初始化结果
    result = {
        "total": len(repos),
        "processed": 0,
        "success": 0,
        "failed": 0,
        "exceeded_limit_repos": []
    }

    # 使用tqdm创建进度条
    with tqdm(total=len(repos), desc="处理仓库") as pbar:
        # 处理每个仓库
        for repo in repos:
            repo_name = repo.get('name')
            repo_url = repo.get('url')
            if not repo_name:
                pbar.set_postfix({"状态": "跳过 - 无仓库名"})
                result["failed"] += 1
                pbar.update(1)
                continue
            
            pbar.set_description(f"处理: {repo_name}")
            
            try:
                # 调用get_repo_details函数获取仓库详情
                repo_details, exceeded_repos = get_repo_details(repo_name, repo_url, DEFAULT_SETTINGS, renew_markdown=True)
                
                # 更新结果
                result["processed"] += 1
                result["success"] += 1
                
                # 添加超出API限制的仓库
                if exceeded_repos:
                    result["exceeded_limit_repos"].extend(exceeded_repos)
                    pbar.set_postfix({"状态": "成功 - 超出API限制"})
                else:
                    pbar.set_postfix({"状态": "成功"})
                
                # 避免触发GitHub API限制，每个请求后等待一段时间
                time.sleep(1.5)
                
            except Exception as e:
                pbar.set_postfix({"状态": f"失败 - {str(e)[:30]}..."})
                result["processed"] += 1
                result["failed"] += 1
            
            pbar.update(1)

    # 输出最终结果
    print("\n处理完成!")
    print(f"总共: {result['total']} 个仓库")
    print(f"成功: {result['success']} 个仓库")
    print(f"失败: {result['failed']} 个仓库")
    print(f"超出API限制: {len(result['exceeded_limit_repos'])} 个仓库")

    # 如果有超出API限制的仓库，输出它们的名称
    if result["exceeded_limit_repos"]:
        print("\n超出API限制的仓库列表:")
        for repo in result["exceeded_limit_repos"]:
            print(f"- {repo}")