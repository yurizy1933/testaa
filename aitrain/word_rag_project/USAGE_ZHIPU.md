# 智谱AI文件解析使用说明

## 概述

本项目集成了智谱AI的文件解析功能，可以更准确地提取各种格式文档的内容，包括PDF、DOCX、DOC、XLS、XLSX、PPT、PPTX等格式。

## 功能特点

- **多格式支持**：支持PDF、DOCX、DOC、XLS、XLSX、PPT、PPTX等格式
- **自动文件截断**：超过限制的文件会自动截断处理
- **自动内容提取**：智能提取文档中的文本内容
- **自定义分块**：支持自定义块大小和重叠
- **API集成**：直接使用智谱AI的文件解析API
- **大文件处理**：支持处理任意大小的文件（通过自动截断）

## 配置说明

在 `config.yaml` 中配置：

```yaml
# 智谱AI配置
ZHIPUAI_API_KEY: "your_api_key_here"
ZHIPUAI_BASE_URL: "https://open.bigmodel.cn/api/paas/v4"

# 文件解析配置
USE_ZHIPU_FILE_PARSER: true  # 启用智谱AI文件解析
FILE_PARSER_CHUNK_SIZE: 1000 # 文件解析块大小
FILE_PARSER_CHUNK_OVERLAP: 200 # 文件解析块重叠
FILE_TRUNCATE_MAX_SIZE_MB: 45 # 文件截断最大大小（MB）
```

## 使用方法

### 1. 基本使用

```python
from src.zhipu_file_parser import ZhipuFileParser

# 初始化解析器
parser = ZhipuFileParser(
    api_key="your_api_key",
    base_url="https://open.bigmodel.cn/api/paas/v4"
)

# 解析文档
success, error, result = parser.parse_document("documents/your_file.docx")

if success:
    print(f"内容长度: {result['content_length']}")
    print(f"内容预览: {result['content'][:500]}")
else:
    print(f"解析失败: {error}")
```

### 2. 分块处理

```python
# 解析并分块
success, error, chunks = parser.parse_document_with_chunks(
    "documents/your_file.docx",
    chunk_size=1000,
    chunk_overlap=200
)

if success:
    print(f"共 {len(chunks)} 个文本块")
    for i, chunk in enumerate(chunks):
        print(f"块 {i+1}: {chunk['text'][:100]}...")
```

### 3. 在RAG系统中使用

```python
from src.rag_processor import RAGProcessor

# 初始化RAG处理器（会自动使用智谱AI解析器）
processor = RAGProcessor("config.yaml")

# 处理文档
result = processor.process_document("documents/your_file.docx")

print(f"处理结果: {result['status']}")
print(f"解析器类型: {result.get('parser_type', '本地解析')}")
```

## 文件格式支持

| 格式 | 扩展名 | 支持状态 |
|------|--------|----------|
| PDF | .pdf | ✅ |
| Word | .docx, .doc | ✅ |
| Excel | .xls, .xlsx | ✅ |
| PowerPoint | .ppt, .pptx | ✅ |

## 限制说明

1. **文件大小**：单个文件最大50MB（超过此大小会自动截断）
2. **文件数量**：最多100个文件
3. **图片大小**：图片文件最大5MB
4. **API限制**：受智谱AI API调用限制
5. **截断大小**：默认45MB（可配置），超过此大小会自动截断

## 错误处理

常见错误及解决方案：

### 1. 文件不存在
```
错误: 文件不存在: documents/your_file.docx
解决: 检查文件路径是否正确
```

### 2. 文件格式不支持
```
错误: 不支持的文件格式: .txt
解决: 使用支持的格式（PDF、DOCX、DOC、XLS、XLSX、PPT、PPTX）
```

### 3. 文件过大
```
错误: 文件过大: 60000000 bytes (最大 52428800 bytes)
解决: 系统会自动截断大文件，无需手动处理
```

### 4. API连接失败
```
错误: 智谱AI API连接失败
解决: 检查API密钥和网络连接
```

## 性能优化

1. **合理设置块大小**：
   - 小块（500-1000字符）：适合详细分析
   - 大块（1000-2000字符）：适合快速处理

2. **调整重叠大小**：
   - 小重叠（100-200字符）：减少重复
   - 大重叠（200-400字符）：保持上下文

3. **批量处理**：
   - 避免同时处理多个大文件
   - 使用队列管理文件处理

## 文件截断功能

### 自动截断机制

当文件大小超过配置的限制（默认45MB）时，系统会自动：

1. **检测文件大小**：检查文件是否超过限制
2. **计算分割份数**：根据文件大小计算需要分割的份数
3. **创建临时文件**：将大文件分割为多个小文件
4. **逐个解析**：分别上传和解析每个小文件
5. **合并内容**：将所有部分的解析结果合并
6. **清理临时文件**：自动删除临时文件

### 配置截断大小

在 `config.yaml` 中设置：

```yaml
FILE_TRUNCATE_MAX_SIZE_MB: 45  # 文件截断最大大小（MB）
```

### 处理大文件的优势

- **无大小限制**：可以处理任意大小的文件
- **自动处理**：无需手动分割文件
- **内容完整**：所有内容都会被解析
- **临时文件管理**：自动清理临时文件

## 示例脚本

### 测试文件截断功能
```bash
python test_file_truncation.py
```

### 测试智谱AI文件解析
```bash
python test_zhipu_file_parser.py
```

### 演示智谱AI文件解析
```bash
python example_zhipu_file_parser.py
```

### 完整RAG系统测试
```bash
python example_usage_optimized.py
```

## 注意事项

1. **API密钥安全**：不要在代码中硬编码API密钥
2. **网络连接**：确保网络连接稳定
3. **文件备份**：处理重要文件前先备份
4. **错误重试**：对于网络错误，可以适当重试
5. **资源监控**：监控内存和CPU使用情况

## 故障排除

### 1. 解析速度慢
- 检查网络连接
- 减小文件大小
- 调整块大小

### 2. 内存使用过高
- 使用生成器模式处理
- 及时清理不需要的数据
- 分批处理大文件

### 3. API调用失败
- 检查API密钥是否正确
- 确认API配额是否充足
- 检查网络连接

## 技术支持

如有问题，请检查：
1. 配置文件是否正确
2. API密钥是否有效
3. 网络连接是否正常
4. 文件格式是否支持
5. 文件大小是否在限制范围内 