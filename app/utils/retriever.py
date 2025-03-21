import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from qdrant_client import QdrantClient
from openai import OpenAI
import mysql.connector
import datetime

class GithubRepoRetriever:
    def __init__(self, settings):
        """
        初始化GitHub仓库检索器
        
        参数:
            settings: 配置字典，包含API认证信息等
        """
        self.settings = settings
        self.qdrant_client = QdrantClient(
            url=settings.get('qdrant_url', 'http://localhost:6333')
        )
        self.collection_name = "github_repos"
        
        # 初始化OpenAI客户端，用于创建嵌入向量
        self.openai_client = OpenAI(
            api_key=settings.get('qwen_api_key'),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
    
    """使用Qwen模型创建文本嵌入"""
    def create_embedding(self, text):
        # 截取文本以适应API限制
        text = text[:8000] if text else ""
        
        try:
            completion = self.openai_client.embeddings.create(
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
    
    """根据查询文本检索相关仓库"""
    def search(self, query, limit=5):
        """        
        参数:
            query: 查询文本
            limit: 返回结果数量上限
            
        返回:
            检索到的仓库列表
        """
        # 创建查询文本的嵌入向量
        query_vector = self.create_embedding(query)
        
        # 在Qdrant中进行向量搜索
        search_result = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit
        )
        
        # 处理搜索结果
        results = []
        for hit in search_result:
            payload = hit.payload
            results.append({
                "repo_name": payload.get("repo_name"),
                "readme_content": payload.get("readme_content"),
                "star_history": payload.get("star_history", {}),
                "score": hit.score,
                "id": hit.id,
                "last_updated": payload.get("last_updated")
            })
        
        return results
    
    """从MySQL获取仓库详细信息"""
    def get_repo_details_from_db(self, repo_name):
        conn = mysql.connector.connect(
            host=self.settings.get('mysql_host', 'localhost'),
            port=self.settings.get('mysql_port', 3306),
            user=self.settings.get('mysql_user', 'root'),
            password=self.settings.get('mysql_password', 'root'),
            database="github_trend"
        )
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT * FROM repositories WHERE name = %s"
        cursor.execute(query, (repo_name,))
        repo_info = cursor.fetchone()
        
        # 获取贡献者信息
        contributors_query = """
        SELECT c.login, c.avatar_url, rc.contributions
        FROM repo_contributors rc
        JOIN contributors c ON rc.contributor_url = c.url
        WHERE rc.repo_url = (SELECT url FROM repositories WHERE name = %s)
        ORDER BY rc.contributions DESC
        LIMIT 10
        """
        cursor.execute(contributors_query, (repo_name,))
        contributors = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if repo_info:
            repo_info['top_contributors'] = contributors
        
        return repo_info