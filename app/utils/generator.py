import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from openai import OpenAI
import json
from datetime import datetime

class RAGGenerator:
    def __init__(self, settings, retriever):
        """
        初始化RAG生成器
        
        参数:
            settings: 配置字典，包含API认证信息等
            retriever: 检索器实例
        """
        self.retriever = retriever
        self.openai_client = OpenAI(
            api_key=settings.get('qwen_api_key', os.getenv("OPENAI_API_KEY")),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
    
    def _format_star_history(self, star_history, max_points=10):
        """格式化star历史数据，用于生成回答"""
        if not star_history:
            return "无star历史数据"
        
        # 将star历史转换为按日期排序的列表
        sorted_history = sorted(star_history.items())
        
        # 如果数据点太多，进行采样
        if len(sorted_history) > max_points:
            step = len(sorted_history) // max_points
            sampled_history = sorted_history[::step]
            if sorted_history[-1] not in sampled_history:
                sampled_history.append(sorted_history[-1])
        else:
            sampled_history = sorted_history
        
        # 格式化为文本
        formatted_history = "Star历史:\n"
        for date, count in sampled_history:
            formatted_history += f"- {date}: {count}颗star\n"
        
        return formatted_history
    
    def generate_response(self, query, additional_context=None):
        """
        生成对用户查询的回答
        
        参数:
            query: 用户查询
            additional_context: 额外上下文信息
            
        返回:
            生成的回答
        """
        # 检索相关仓库
        search_results = self.retriever.search(query, limit=3)
        
        if not search_results:
            return "未找到与您的问题相关的GitHub仓库信息。请尝试使用不同的关键词。"
        
        # 构建上下文
        context = "以下是与您的问题相关的GitHub仓库信息：\n\n"
        
        for i, result in enumerate(search_results):
            repo_name = result["repo_name"]
            repo_info = self.retriever.get_repo_details_from_db(repo_name)
            
            if repo_info:
                context += f"{i+1}. 仓库: {repo_name}\n"
                context += f"   描述: {repo_info.get('description', '无描述')}\n"
                context += f"   星标数: {repo_info.get('stars', 0)}\n"
                context += f"   主要语言: {repo_info.get('language', '未知')}\n"
                
                # 添加贡献者信息
                if repo_info.get('top_contributors'):
                    context += f"   主要贡献者: "
                    contributors = [f"{c['login']}({c['contributions']}次提交)" 
                                   for c in repo_info['top_contributors'][:3]]
                    context += ", ".join(contributors) + "\n"
                
                # 添加star历史摘要
                star_history = result.get("star_history", {})
                if star_history:
                    context += f"   {self._format_star_history(star_history, max_points=5)}\n"
                
                # 添加README摘要
                readme_content = result.get("readme_content", "")
                if readme_content:
                    # 截取README的前500个字符作为摘要
                    readme_summary = readme_content[:500] + "..." if len(readme_content) > 500 else readme_content
                    context += f"   README摘要: {readme_summary}\n\n"
        
        if additional_context:
            context += f"\n额外信息: {additional_context}\n"
        
        # 构建提示
        prompt = f"""基于以下GitHub仓库信息，回答用户的问题。
        
上下文信息:
{context}

用户问题: {query}

请提供详细、准确的回答，引用相关仓库的具体信息。如果信息不足，请说明。回答应该对GitHub项目进行分析，并提供有用的见解。
"""
        
        # 调用大语言模型生成回答
        try:
            response = self.openai_client.chat.completions.create(
                model="qwen-max",
                messages=[
                    {"role": "system", "content": "你是一个GitHub项目专家助手，擅长分析和推荐开源项目。你的回答应该基于提供的仓库信息，并且专业、准确。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"生成回答时出错: {str(e)}"