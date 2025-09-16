
DATABASES = {
    'default': {
        # 'ENGINE': 'django.db.backends.sqlite3',
        # 'NAME': BASE_DIR / 'db.sqlite3',
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'vectors',
        'USER':'root',
        'PORT': 3306,
        'PASSWORD': 'aitest1234ZY',
        'HOST': '43.139.212.116'
    }
}

OPENAI_API_BASE: ""
ZHIPU_APIKEY="4198d249d529406f8b9571bc10aa2142"  # 请填写您自己的APIKey
DEEPSEEK_APIKEY = 'sk-ae89b4e492104945ae83c6a2647410c9'

# 向量模型名称
OPENAI_API_MODEL_EMBEDDING = "embedding-2"

# 自然语言处理模型
OPENAI_API_MODEL_GLM4= "GLM-4-Flash"

# 最大线程数
MAX_THREADING: 10

# 请求间隔，单位：秒
REQUEST_INTERVAL: 10

# 项目名称
PROJECT_NAME: "洋么科技文本转向量框架"

# 项目描述
PROJECT_DESC: "将需求文档拆分转成向量数据，并用Mysql维护数据与向量之间的管理，向量数据存本地"

NEEDS_NAME: [
  '洋么科技需求文档.docx',
]

# 向量数据库路径
FAISS_DB_PATH: "needs_vectors.faiss"

# 相似度阈值
SIMILARITY_THRESHOLD: 0.65

# 总结提炼设定长度值
SUMMARY_LENGTH: 300

# 执行任务 1 代表处理需求文档及处理向量数据  2 代表在向量数据中查找相似需求文档  3 新的处理文档逻辑
EXECUTE_TASK= "2"

# 统计分词的长度。 注意：如何设置的过长，可能导致漏掉某些需求内容
NGRAM = 2
# 统计分词热度的比率，一般设置为0就行，如有实际需要可自己更改值，为整数
TOP_N= 0

# 版权所有 © 张家界市洋么科技有限公司 2024. All rights reserved.
# 版权所有 © 张家界市洋么科技有限公司 2024. All rights reserved.
# 版权所有 © 张家界市洋么科技有限公司 2024. All rights reserved.
# 版权所有 © 张家界市洋么科技有限公司 2024. All rights reserved.
# 版权所有 © 张家界市洋么科技有限公司 2024. All rights reserved.
