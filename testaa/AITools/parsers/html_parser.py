"""
HTML文档解析器
"""
from AITools.core.manager import AIManager
from ..prompts.html_parser import HTMLParserPrompt
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class HTMLParser:
    """HTML文档解析器"""

    def __init__(self, ai_provider: str = 'zhipu'):
        self.ai_manager = AIManager(provider_name=ai_provider)
        self.prompt = HTMLParserPrompt()

    def parse_html_content(self, html_content: str) -> Dict:
        """解析HTML内容，提取完整接口"""

        try:
            # 获取提示词
            system_prompt = self.prompt.get_system_prompt()
            user_prompt = self.prompt.get_user_prompt(content=html_content)

            logger.info(f"AITools调用开始 - HTML内容长度: {len(html_content)}字符")

            # 调用AI
            response = self.ai_manager.call_with_prompt(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_mode=True
            )

            # 解析响应
            logger.debug(f"AI原始响应内容: {response.content[:500]}")
            interfaces = self.prompt.parse_response(response.content)
            logger.info(f"parse_response解析结果: {len(interfaces)}个接口")

            # 过滤完整接口
            valid_interfaces = self._filter_complete_interfaces(interfaces)

            statistics = {
                'total_found': len(interfaces),
                'valid_count': len(valid_interfaces),
                'filtered_count': len(interfaces) - len(valid_interfaces),
                'filter_rate': f"{((len(interfaces) - len(valid_interfaces))/len(interfaces)*100):.1f}%" if interfaces else "0%"
            }

            logger.info(f"AITools解析完成 - 发现接口: {statistics['total_found']}, 有效接口: {statistics['valid_count']}, 过滤接口: {statistics['filtered_count']}")

            return {
                'interfaces': valid_interfaces,
                'statistics': statistics
            }

        except Exception as e:
            logger.error(f"HTML内容解析失败: {str(e)}")
            raise

    def _filter_complete_interfaces(self, interfaces: List[Dict]) -> List[Dict]:
        """过滤完整接口（委托给Prompt类）"""
        return self.prompt._filter_valid_interfaces(interfaces)
