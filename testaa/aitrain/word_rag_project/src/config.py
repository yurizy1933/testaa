"""
Word文档RAG系统 - 配置管理模块
"""

import yaml
import os

class ConfigManager:
    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        
        return config
    
    def get(self, key, default=None):
        """获取配置值"""
        return self.config.get(key, default)
    
    def get_database_config(self):
        """获取数据库配置"""
        return {
            'host': self.get('MYSQL_HOST'),
            'port': self.get('MYSQL_PORT'),
            'user': self.get('MYSQL_USER'),
            'password': self.get('MYSQL_PASSWORD'),
            'database': self.get('MYSQL_DATABASE')
        }
    
    def get_zhipuai_config(self):
        """获取智谱AI配置"""
        return {
            'api_key': self.get('ZHIPUAI_API_KEY'),
            'embedding_model': self.get('ZHIPUAI_EMBEDDING_MODEL'),
            'chat_model': self.get('ZHIPUAI_CHAT_MODEL'),
            'base_url': self.get('ZHIPUAI_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4')
        } 