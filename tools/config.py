"""
本文件包含GitHub数据获取工具所需的所有配置项
This file contains all configuration items needed for GitHub data retrieval tools
"""

# GitHub API配置
# GitHub API Configuration
GITHUB_SETTINGS = {
    'min_stars': 100,
    'sort': 'stars',
    'order': 'desc',
    'perpage': 100,
    'headers': {
        'Authorization': 'your_github_token',
        'Accept': 'application/vnd.github.v3+json'
    }
}

# 数据库配置
# Database Configuration
DB_SETTINGS = {
    'mysql_host': 'localhost',
    'mysql_user': 'root',
    'mysql_password': 'root',
    'mysql_port': 3306,
    'database': 'github_trend'
}

# API密钥配置
# API Key Configuration
API_KEYS = {
    'qwen_api_key': 'your_api_key'
}

# 合并所有配置到一个字典
# Merge all configurations into one dictionary
DEFAULT_SETTINGS = {
    **GITHUB_SETTINGS,
    **DB_SETTINGS,
    **API_KEYS
}