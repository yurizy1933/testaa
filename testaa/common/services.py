"""
文档解析服务 - 调用AITools进行HTML解析
"""
from typing import Dict
from AITools.parsers.html_parser import HTMLParser
from common.models import CommonDoc, ApiInterface
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


class DocumentParserService:
    """文档解析服务类"""

    def parse_html_sync(self, doc_id: str, ai_provider: str = 'zhipu') -> Dict:
        """同步解析HTML文档"""
        try:
            # 1. 提取HTML内容
            doc = get_object_or_404(CommonDoc, id=doc_id)
            html_content = self._extract_html_content(doc)
            logger.info(f"提取HTML内容 - 文档ID: {doc_id}, 内容长度: {len(html_content)}字符, 前200字: {html_content[:200]!r}")

            # 2. 调用AITools解析器
            parser = HTMLParser(ai_provider=ai_provider)
            parse_result = parser.parse_html_content(html_content)

            # 3. 存储到数据库
            saved_count = self._save_interfaces_to_db(doc, parse_result['interfaces'])

            logger.info(f"HTML解析完成 - 文档ID: {doc_id}, 发现接口: {parse_result['statistics']['total_found']}, 有效接口: {parse_result['statistics']['valid_count']}, 保存接口: {saved_count}")

            return {
                'saved_count': saved_count,
                'statistics': parse_result['statistics']
            }
        except Exception as e:
            logger.error(f"HTML解析失败 - 文档ID: {doc_id}, 错误: {str(e)}")
            raise

    def parse_html_async(self, doc_id: str, ai_provider: str = 'zhipu') -> str:
        """异步解析HTML文档"""
        # TODO: 创建异步任务并返回任务ID
        pass

    def _extract_html_content(self, doc: CommonDoc) -> str:
        """提取HTML文档内容（针对API文档定向提取 api-reference-detail-container）"""
        if doc.file_type not in ('html', 'htm'):
            return doc.doc_content

        from bs4 import BeautifulSoup

        with open(doc.file_path.path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')

        containers = soup.select('div.api-reference-detail-container')
        if containers:
            parts = []
            for container in containers:
                text = container.get_text(separator='\n', strip=True)
                parts.append(text)
            return '\n---\n'.join(parts)

        # 兜底：未找到目标容器时回退到全文提取
        logger.warning(f"未找到 api-reference-detail-container，回退到全文提取 - 文档ID: {doc.id}")
        return doc.doc_content

    def _save_interfaces_to_db(self, doc: CommonDoc, interfaces: list) -> int:
        """保存接口到数据库"""
        with transaction.atomic():
            # 清空该文档下已有的接口
            ApiInterface.objects.filter(api_doc=doc).delete()

            # 批量创建接口记录
            created_count = 0
            for interface_data in interfaces:
                try:
                    ApiInterface.objects.create(
                        api_doc=doc,
                        api_name=interface_data.get('api_name', ''),
                        api_path=interface_data.get('api_path', ''),
                        method=interface_data.get('method', 'GET'),
                        request_params=interface_data.get('request_params', ''),
                        response_params=interface_data.get('response_params', ''),
                        remark=interface_data.get('remark', '')
                    )
                    created_count += 1
                except Exception as e:
                    # 记录错误但继续处理其他接口
                    logger.error(f"保存接口失败: {e}, 接口数据: {interface_data}")
                    continue

            return created_count
