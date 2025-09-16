# XMind转Excel/JSON工具

这是一个基于Python的XMind文件转换工具，可以将XMind文件转换为Excel或JSON格式。

## 功能特性

- ✅ 支持XMind转Excel
- ✅ 支持XMind转JSON  
- ✅ 支持单个文件转换
- ✅ 支持批量文件夹转换
- ✅ 支持忽略指定层级
- ✅ 自动跳过不完整的测试用例（缺少预期结果或用例等级）

## 安装依赖

```bash
pip install xmindparser pandas openpyxl xlsxwriter click
```

## 使用方法

### 基本语法

```bash
python xmindtojson.py -x <xmind文件路径> [-e <excel文件路径>] [-j <json文件路径>] [-i <忽略层级数>]
```

### 参数说明

- `-x, --xmindpath`: XMind文件或文件夹路径（必需）
- `-e, --excelpath`: Excel输出文件或文件夹路径（可选）
- `-j, --jsonpath`: JSON输出文件或文件夹路径（可选）
- `-i, --ignorelayer`: 忽略的层级数，默认为0（可选）

### 使用示例

#### 1. 转换为Excel

```bash
# 单个文件转Excel
python xmindtojson.py -x "D:\program\ai_file\授权全流程测试A.xmind" -e "测试用例.xlsx"

# 批量文件夹转Excel
python xmindtojson.py -x "D:\program\ai_file" -e "output" -i 2
```

#### 2. 转换为JSON

```bash
# 单个文件转JSON
python xmindtojson.py -x "D:\program\ai_file\授权全流程测试A.xmind" -j "测试用例.json"

# 批量文件夹转JSON
python xmindtojson.py -x "D:\program\ai_file" -j "output" -i 2
```

#### 3. 同时转换为Excel和JSON

```bash
# 单个文件同时转Excel和JSON
python xmindtojson.py -x "D:\program\ai_file\授权全流程测试A.xmind" -e "测试用例.xlsx" -j "测试用例.json"

# 批量文件夹同时转Excel和JSON
python xmindtojson.py -x "D:\program\ai_file" -e "output" -j "output" -i 2
```

## 输出格式

### Excel格式

包含以下列：
- 特性层级
- 用例标题
- 用例描述
- 前置条件
- 测试步骤
- 预期结果
- 国家标签
- jira编号
- 用例等级
- 适用阶段
- 用例类型
- 用例负责人
- 用例关键字
- 备注
- 标签

### JSON格式

每个测试用例包含完整的字段信息，格式如下：

```json
[
  {
    "特性层级": "授权全流程 - 业务逻辑（功能） - 流程处理",
    "用例标题": "授权全流程 - 业务逻辑（功能） - 流程处理 - 公共逻辑（0100交易全经过） - 幂等校验 - 幂等校验通过",
    "用例描述": "",
    "前置条件": "前置条件：\n1.阈值验证通过\n2.MTI+DE7+DE11+DE32+DE33+DE37在授权交易流水表中存在匹配记录",
    "测试步骤": "测试步骤：\n1、 组装接口报文，其中MTI+DE7+DE11+DE32+DE33+DE37在授权交易流水表中存在匹配记录\n2、发起授权请求\n3，查看接口返回\n4.查看授权流水表authorization_log_mc\n",
    "预期结果": "预期结果：\n交易匹配成功（匹配到R006:ecom-境内和R008定期支付-境内），根据交易识别规则表rm_rule_info排序取第一条交易规则R006",
    "国家标签": "",
    "jira编号": "",
    "用例等级": "用例等级：\nP1",
    "适用阶段": "",
    "用例类型": "",
    "用例负责人": "",
    "用例关键字": "",
    "备注": "",
    "标签": ""
  }
]
```

## 数据质量保证

- 🔍 **字段完整性检查**: 自动检查"预期结果"和"用例等级"字段
- ⚠️ **跳过不完整数据**: 缺少必需字段的测试用例会被自动跳过
- 📊 **只输出完整数据**: 确保输出的Excel和JSON数据都是完整的
- 📝 **详细处理日志**: 显示处理过程中的详细信息

## 注意事项

1. **必需字段**: "预期结果"和"用例等级"是必需字段，缺少任何一个的测试用例都会被跳过
2. **层级忽略**: 使用`-i`参数可以忽略指定数量的顶层节点
3. **批量处理**: 当输入是文件夹时，会遍历所有.xmind文件进行转换
4. **输出格式**: 可以同时输出Excel和JSON，也可以只输出其中一种

## 错误处理

- 如果XMind文件不存在，会显示错误信息
- 如果输出目录不存在，会自动创建
- 如果测试用例缺少必需字段，会跳过并显示警告信息
- 如果转换过程中出现错误，会显示详细的错误信息

## 技术实现

- 使用`xmindparser`库解析XMind文件
- 使用`pandas`和`openpyxl`处理Excel文件
- 使用`click`库提供命令行接口
- 支持UTF-8编码，确保中文内容正确显示 