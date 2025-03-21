
# GitHub Top Stars 

一个获取、分析和可视化 GitHub 仓库的工具。

You can get English version README over [here](./README_en.md).

## 核心功能

- 自动获取GitHub上星标数大于一定值（默认为100）的仓库
    - 按周分批获取数据，避免API限制
    - 存储repository基本信息到MySQL
- 获取仓库的详细信息，包括贡献者、star历史和README内容
    - 使用向量数据库Qdrant存储详细的非关系型信息
- 基于本地保存的数据进行数据分析，并提供一个Web界面展示数据分析结果
- 基于Qdrant和Qwen api构建RAG


## 安装与使用

### 环境需求

- Python 3.9或更高版本
- MySQL
- Qdrant

### 安装依赖

```bash
pip install -r requirements.txt
```

### 使用方法
1. 获取GitHub热门仓库数据
```python
from tools.get_data import get_top_starred_repos, DEFAULT_SETTINGS

# 设置起止日期
start_date = "2023-01-01"
end_date = "2023-12-31"

result = get_top_starred_repos(None, start_date, end_date, DEFAULT_SETTINGS)
```
2. 获取特定仓库的详细信息:
```python
from tools.get_data import get_repo_details, DEFAULT_SETTINGS

# 根据仓库名获取仓库详情
repo_details,_ = get_repo_details("owner/repo", "https://github.com/owner/repo", DEFAULT_SETTINGS)
 ```

 3. 运行Web应用（确保你的数据库中有点数据）:
```python
stramlit run ./app/home.py
 ```

# 其他说明：
- 本项目使用了GitHub API，需要注册并获取api-key。
- 由于作者的电脑显存不够，为了效果，本项目使用了Qwen的text-embedding模型，需要注册并获取api-key
    - 当然你也可以去huggingface上下载embedding模型
- 数据获取时间较长，尤其是get_repo_details函数，按照我目前的设置一个小时大概只能获取将近250条repo的详细数据，如果有每日更新本地数据需要，建议使用多线程获取数据
    - 由于star历史只能一条一条获取然后按天求和，如果你不需要star的历史数据，你可以在get_repo_details函数中注释掉get_repo_star_history函数的调用，这样可以减少获取时间
- 本来只是写了get_top_starred_repos函数，每周跑一遍然后用sql查一下上礼拜哪个项目涨星最多，看看有什么有意思的项目，并没有计划做可视化和RAG。
    现在虽然做了但也没有特地用Vue写个前端，只能算个雏形，肯定有很多不完善的地方（比如可视化的地方可以用物化视图加快下加载速度，也没考虑不同宽度的屏幕适配等问题），后面有时间可能会再搞好点儿。