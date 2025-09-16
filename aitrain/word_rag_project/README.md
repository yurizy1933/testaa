# Word文档RAG系统 - 优化版本

一个基于RAG（Retrieval-Augmented Generation）技术的Word文档处理系统，集成MySQL数据库存储和高效文档解析，支持智能分页处理和向量化存储。

## 功能特点

- **智能文档解析**：支持大型Word文档的智能分页处理，多线程优化
- **智谱AI文件解析**：集成智谱AI的文件解析功能，支持多种格式
- **逐页处理**：真正的逐页解析和存储，避免内存溢出
- **断点续传**：支持从上次保存的页面继续处理
- **双重存储**：FAISS向量数据库 + MySQL关系数据库，数据持久化
- **RAG技术**：基于检索增强生成，提供智能问答功能
- **数据库集成**：完整的文档和向量数据管理
- **高效处理**：多线程文档解析，批量向量化处理
- **中文优化**：专门针对中文文档进行优化
- **重复检测**：自动检测已处理文档，避免重复处理
- **内存优化**：生成器模式处理，及时释放内存
- **句子向量**：支持文档总结提炼，为每个关键句子生成向量
- **智能总结**：使用AI对文档内容进行总结提炼
- **句子检索**：支持基于句子的相似性检索

## 项目结构

```
word_rag_project/
├── config.yaml              # 配置文件
├── requirements.txt          # 依赖包
├── main.py                  # 主程序入口
├── example_usage_optimized.py # 优化版本示例
├── src/                     # 源代码目录
│   ├── __init__.py
│   ├── config.py            # 配置管理
│   ├── database_manager.py  # MySQL数据库管理
│   ├── word_parser.py       # Word文档解析（优化版）
│   ├── zhipu_file_parser.py # 智谱AI文件解析
│   ├── file_truncator.py    # 文件截断模块
│   ├── vector_manager.py    # 向量数据库管理
│   ├── ai_client.py         # AI客户端
│   ├── sentence_summarizer.py # 句子总结提炼模块
│   └── rag_processor.py     # RAG处理器（集成数据库）
└── documents/               # 文档目录
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 数据库配置

首先创建MySQL数据库表：

```sql
-- 向量数据表
CREATE TABLE vectors (
    id INT PRIMARY KEY AUTO_INCREMENT,
    vector_id INT NOT NULL,
    text TEXT NOT NULL,
    doc_path VARCHAR(255),
    doc_name VARCHAR(255),
    page INT,
    word_count INT,
    processed_time TIMESTAMP
);

-- 文档信息表
CREATE TABLE documents (
    id INT PRIMARY KEY AUTO_INCREMENT,
    doc_path VARCHAR(255) UNIQUE,
    doc_name VARCHAR(255),
    total_pages INT,
    total_words INT,
    file_size BIGINT,
    processed_time TIMESTAMP
);

-- 处理统计表
CREATE TABLE processing_status (
    id INT PRIMARY KEY AUTO_INCREMENT,
    doc_path VARCHAR(255),
    total_chunks INT,
    success_chunks INT,
    processing_time FLOAT,
    created_at TIMESTAMP
);
```

## 配置说明

编辑 `config.yaml` 文件：

```yaml
# 数据库配置
MYSQL_HOST: "your_mysql_host"
MYSQL_PORT: 3306
MYSQL_USER: "your_username"
MYSQL_PASSWORD: "your_password"
MYSQL_DATABASE: "vectors"

# 智谱AI配置
ZHIPUAI_API_KEY: "your_api_key_here"
ZHIPUAI_EMBEDDING_MODEL: "embedding-2"
ZHIPUAI_CHAT_MODEL: "glm-4"
ZHIPUAI_BASE_URL: "https://open.bigmodel.cn/api/paas/v4"

# 文件解析配置
USE_ZHIPU_FILE_PARSER: true  # 是否使用智谱AI文件解析
FILE_PARSER_CHUNK_SIZE: 1000 # 文件解析块大小
FILE_PARSER_CHUNK_OVERLAP: 200 # 文件解析块重叠

# 文档处理配置
CHUNK_SIZE: 500              # 文本块大小
CHUNK_OVERLAP: 50            # 文本块重叠
MAX_WORKERS: 4               # 文档解析线程数

# 向量数据库配置
FAISS_DB_PATH: "word_vectors.faiss"
VECTOR_DIMENSION: 1024
```

## 使用方法

### 1. 处理文档

```bash
python main.py --mode process --doc documents/your_document.docx
```

### 2. 逐页处理文档

```bash
# 从第1页开始处理
python main.py --mode pages --doc documents/your_document.docx

# 从指定页面开始处理
python main.py --mode pages --doc documents/your_document.docx --start_page 5
```

### 3. 查看文档处理状态

```bash
python main.py --mode status --doc documents/your_document.docx
```

### 4. 搜索相似内容

```bash
python main.py --mode search --query "你的搜索查询"
```

### 5. 智能问答

```bash
python main.py --mode ask --question "你的问题"
```

### 6. 获取文档摘要

```bash
python main.py --mode summary --doc documents/your_document.docx
```

### 7. 查看系统统计

```bash
python main.py --mode stats
```

### 8. 查看文档列表

```bash
python main.py --mode docs
```

### 9. 删除文档

```bash
python main.py --mode delete --doc documents/your_document.docx
```

### 10. 句子向量处理

```bash
# 处理文档为句子向量
python main.py --mode sentences --doc documents/your_document.docx --max_sentences 10
```

### 11. 交互模式

```bash
python main.py --mode interactive
```

在交互模式中，可以使用以下命令：
- `process <文档路径>` - 处理文档
- `pages <文档路径> [起始页]` - 逐页处理文档
- `status <文档路径>` - 查看文档处理状态
- `search <查询文本>` - 搜索相似内容
- `ask <问题>` - 基于文档回答问题
- `sentences <文档路径> [句子数量]` - 处理文档为句子向量
- `stats` - 显示系统统计
- `docs` - 显示文档列表
- `delete <文档路径>` - 删除文档
- `clear` - 清空索引
- `quit` - 退出



## 核心模块说明

### DatabaseManager
- MySQL数据库连接管理
- 文档信息存储和检索
- 向量数据持久化
- 处理状态跟踪

### WordDocumentParser（优化版）
- 智能解析Word文档
- 多线程并行处理
- 支持分页处理
- 自动识别标题和段落
- 文本分块和重叠处理

### ZhipuFileParser（智谱AI文件解析）
- 集成智谱AI文件解析功能
- 支持多种文档格式（PDF、DOCX、DOC、XLS、XLSX、PPT、PPTX）

### SentenceSummarizer（句子总结提炼）
- 智能提取文档关键句子
- 使用AI进行文档内容总结
- 为每个句子生成向量表示
- 支持句子相似性检索
- 自动文件截断（超过限制自动分割）
- 自动内容提取和分块
- 支持自定义块大小和重叠

### FileTruncator（文件截断模块）
- 自动检测大文件并分割
- 支持任意大小的文件处理
- 临时文件自动管理
- 可配置的截断大小

### VectorManager（集成数据库）
- FAISS向量数据库管理
- MySQL数据持久化
- 支持向量添加、搜索、删除
- 元数据管理
- 索引持久化

### AIClient
- 智谱AI API封装
- 支持批量向量化
- 并发处理优化
- 错误处理和重试机制

### PageProcessor
- 逐页处理Word文档
- 生成器模式，避免内存溢出
- 支持断点续传
- 内存优化和垃圾回收
- 实时进度跟踪

### RAGProcessor（集成数据库）
- 整合所有模块功能
- 提供完整的RAG流程
- 支持批量处理
- 智能问答功能
- 重复文档检测
- 支持智谱AI文件解析和本地解析

## 技术特点

1. **逐页处理**：真正的逐页解析和存储，避免内存溢出
2. **断点续传**：支持从上次保存的页面继续处理
3. **双重存储**：FAISS向量数据库 + MySQL关系数据库，数据持久化
4. **高效解析**：多线程文档解析，提高处理效率
5. **智能分页**：通过识别标题和段落结构，实现智能分页
6. **向量化存储**：使用FAISS进行高效的向量相似度搜索
7. **并发优化**：多线程处理提高AI API调用效率
8. **中文优化**：使用jieba分词，专门针对中文文档优化
9. **重复检测**：自动检测已处理文档，避免重复处理
10. **智谱AI集成**：支持智谱AI文件解析，提高解析准确性和效率
11. **大文件处理**：自动文件截断，支持处理任意大小的文件
10. **内存优化**：生成器模式处理，及时释放内存
11. **完整管理**：文档信息、向量数据、处理状态的全方位管理

## 注意事项

1. 请确保配置正确的MySQL数据库连接信息
2. 请确保配置正确的智谱AI API密钥
3. 大型文档处理可能需要较长时间
4. 建议在处理前备份重要文档
5. 确保有足够的磁盘空间存储向量数据库
6. 数据库表结构必须按照提供的SQL语句创建

## 许可证

本项目仅供学习和研究使用。 