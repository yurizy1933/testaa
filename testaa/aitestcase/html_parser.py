"""
HTML解析模块
负责从HTML文档中提取API接口信息
"""

from bs4 import BeautifulSoup


def parse_html_doc_content(content):
    """
    解析HTML文档内容，提取接口信息
    支持常见的HTML格式接口文档解析

    Args:
        content: HTML文档内容

    Returns:
        list: 接口信息列表
    """
    interfaces = []

    try:
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(content, 'html.parser')

        # 尝试不同的HTML结构来提取接口信息
        # 方法1: 查找表格（table）结构
        tables = soup.find_all('table')
        if tables:
            for table in tables:
                # 获取表头
                headers = []
                thead = table.find('thead')
                if thead:
                    header_rows = thead.find_all('tr')
                    if header_rows:
                        headers = [th.get_text(strip=True) for th in header_rows[0].find_all(['th', 'td'])]

                # 获取表格内容
                tbody = table.find('tbody')
                if not tbody:
                    tbody = table

                rows = tbody.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        # 尝试从表格中提取接口信息
                        interface = extract_interface_from_table_row(cells, headers)
                        # extract_interface_from_table_row已经检查了api_path，这里只需要检查interface不为None
                        if interface:
                            interfaces.append(interface)

        # 方法2: 查找列表（ul/ol）结构
        if not interfaces:
            lists = soup.find_all(['ul', 'ol'])
            for lst in lists:
                items = lst.find_all('li')
                current_interface = None
                for item in items:
                    text = item.get_text(strip=True)
                    if is_interface_start(text):
                        if current_interface:
                            # 只有有api_path的接口才添加到列表
                            if current_interface.get('api_path'):
                                interfaces.append(current_interface)
                        current_interface = create_interface_from_text(text)
                    elif current_interface:
                        update_interface_from_text(current_interface, text)

                # 添加最后一个接口，只有有api_path的接口才添加到列表
                if current_interface and current_interface.get('api_path'):
                    interfaces.append(current_interface)

        # 方法3: 查找div结构
        if not interfaces:
            divs = soup.find_all('div')
            current_interface = None
            for div in divs:
                text = div.get_text(strip=True)
                if is_interface_start(text):
                    if current_interface:
                        # 只有有api_path的接口才添加到列表
                        if current_interface.get('api_path'):
                            interfaces.append(current_interface)
                    current_interface = create_interface_from_text(text)
                elif current_interface and len(text) < 500:  # 避免太长的文本块
                    update_interface_from_text(current_interface, text)

            # 添加最后一个接口，只有有api_path的接口才添加到列表
            if current_interface and current_interface.get('api_path'):
                interfaces.append(current_interface)

    except Exception as e:
        # 如果HTML解析失败，尝试按行解析
        interfaces = parse_text_content(content)

    return interfaces


def extract_interface_from_table_row(cells, headers):
    """
    从表格行中提取接口信息

    Args:
        cells: 表格单元格列表
        headers: 表头列表

    Returns:
        dict: 接口信息字典，如果无法提取则返回None
    """
    # 如果有表头，根据表头映射
    if headers:
        interface = {
            'api_name': '',
            'api_path': '',
            'method': 'GET',
            'request_params': '',
            'response_params': '',
            'remark': ''
        }

        # 建立表头到字段的映射
        for i, header in enumerate(headers):
            if i < len(cells):
                cell_text = cells[i].get_text(strip=True)
                if '接口名' in header or '接口名称' in header:
                    interface['api_name'] = cell_text
                elif '方法' in header or 'Method' in header.lower():
                    method = cell_text.upper()
                    if method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                        interface['method'] = method
                elif '路径' in header or 'URL' in header or 'url' in header.lower():
                    interface['api_path'] = cell_text
                elif '入参' in header or '请求参数' in header or '参数' in header:
                    interface['request_params'] = cell_text
                elif '出参' in header or '响应参数' in header or '返回参数' in header:
                    interface['response_params'] = cell_text
                elif '备注' in header or '说明' in header or '描述' in header:
                    interface['remark'] = cell_text

        # 如果没有明确的表头，尝试根据内容推断
        if not interface['api_name'] and len(cells) >= 1:
            interface['api_name'] = cells[0].get_text(strip=True)

        # 必须有api_path才认为是有效接口
        return interface if interface['api_name'] and interface['api_path'] else None

    # 如果没有表头，假设第一列是接口名
    if len(cells) >= 1:
        interface = {
            'api_name': cells[0].get_text(strip=True),
            'api_path': cells[1].get_text(strip=True) if len(cells) > 1 else '',
            'method': 'GET',
            'request_params': '',
            'response_params': '',
            'remark': ''
        }
        # 必须有api_path才认为是有效接口
        return interface if interface['api_name'] and interface['api_path'] else None

    return None


def is_interface_start(text):
    """
    判断是否是接口定义的开始

    Args:
        text: 文本内容

    Returns:
        bool: 是否是接口定义的开始
    """
    keywords = ['接口名称', '接口名', 'API', 'api']
    return any(keyword in text for keyword in keywords)


def create_interface_from_text(text):
    """
    从文本创建接口对象

    Args:
        text: 文本内容

    Returns:
        dict: 接口信息字典
    """
    interface = {
        'api_name': '',
        'api_path': '',
        'method': 'GET',
        'request_params': '',
        'response_params': '',
        'remark': ''
    }

    # 尝试提取接口名
    if '：' in text:
        parts = text.split('：')
        if len(parts) >= 2:
            interface['api_name'] = parts[-1].strip()
    elif ':' in text:
        parts = text.split(':')
        if len(parts) >= 2:
            interface['api_name'] = parts[-1].strip()
    else:
        interface['api_name'] = text

    # 检查是否包含请求方法
    methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
    for method in methods:
        if method in text.upper():
            interface['method'] = method
            break

    # 尝试提取路径
    if '/' in text:
        path_part = text.split('/')[-1].strip()
        if path_part:
            interface['api_path'] = '/' + path_part

    return interface


def update_interface_from_text(interface, text):
    """
    根据文本更新接口信息

    Args:
        interface: 接口信息字典
        text: 文本内容
    """
    if '请求方法' in text or 'Method' in text or 'method' in text:
        method = text.split('：')[-1].split(':')[-1].strip().upper()
        methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
        if method in methods:
            interface['method'] = method
    elif '接口路径' in text or '路径' in text or 'URL' in text or 'url' in text:
        path = text.split('：')[-1].split(':')[-1].strip()
        interface['api_path'] = path
    elif '入参' in text or '请求参数' in text or '参数' in text:
        params = text.split('：')[-1].split(':')[-1].strip()
        interface['request_params'] = params
    elif '出参' in text or '响应参数' in text or '返回参数' in text:
        params = text.split('：')[-1].split(':')[-1].strip()
        interface['response_params'] = params
    elif '备注' in text or '说明' in text or '描述' in text:
        remark = text.split('：')[-1].split(':')[-1].strip()
        interface['remark'] = remark


def parse_text_content(content):
    """
    将内容按行解析（作为HTML解析的备选方案）

    Args:
        content: 文本内容

    Returns:
        list: 接口信息列表
    """
    interfaces = []
    lines = content.split('\n')

    current_interface = None

    for line in lines:
        line = line.strip()

        # 跳过空行
        if not line:
            continue

        # 尝试识别接口定义
        if is_interface_start(line):
            if current_interface:
                # 只有有api_path的接口才添加到列表
                if current_interface.get('api_path'):
                    interfaces.append(current_interface)
            current_interface = create_interface_from_text(line)

        elif current_interface:
            update_interface_from_text(current_interface, line)

    # 添加最后一个接口，只有有api_path的接口才添加到列表
    if current_interface and current_interface.get('api_path'):
        interfaces.append(current_interface)

    return interfaces
