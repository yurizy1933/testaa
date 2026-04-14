import os

# 数据库配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '43.139.212.116'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'aitest1234ZY'),
    'database': os.getenv('DB_NAME', 'vectors'),
    'charset': 'utf8mb4'
}

# 智谱AI配置
ZHIPUAI_API_KEY = os.getenv('ZHIPUAI_API_KEY', '')
# 智谱AI配置
ZHIPUAI_API_KEY= "4198d249d529406f8b9571bc10aa2142.Qvg8SQRV9GiKweid"
ZHIPUAI_EMBEDDING_MODEL= "embedding-2"
ZHIPUAI_CHAT_MODEL= "glm-4"
ZHIPUAI_BASE_URL= "https://open.bigmodel.cn/api/paas/v4"
# 向量维度 - 智谱AI embedding-2模型的维度是1024
VECTOR_DIMENSION = 1024

# 分页大小
PAGE_SIZE = 1000 