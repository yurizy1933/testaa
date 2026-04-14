"""
智谱AI提供商实现
"""

from typing import Dict, List, Any, Optional
from ..core.base import AIProvider, AIResponse
from ..core.config import get_config


class ZhipuProvider(AIProvider):
    """智谱AI提供商类"""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        try:
            from zhipuai import ZhipuAI
            self._client = ZhipuAI(api_key=api_key)
        except ImportError:
            raise ImportError("zhipuai package is required for ZhipuAI provider")

    @property
    def name(self) -> str:
        return "zhipu"

    @property
    def default_model(self) -> str:
        return "glm-4"

    def call_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        json_mode: bool = False,
        **kwargs
    ) -> AIResponse:
        """
        调用智谱AI聊天完成接口

        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            json_mode: 是否强制JSON模式
            **kwargs: 其他参数

        Returns:
            AIResponse: AI响应对象
        """
        if model is None:
            model = self.default_model

        try:
            # 构建请求参数
            request_params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            # 如果启用JSON模式
            if json_mode and self.supports_json_mode(model):
                request_params["response_format"] = {"type": "json_object"}

            # 添加其他参数
            request_params.update(kwargs)

            # 调用API
            response = self._client.chat.completions.create(**request_params)

            # 解析响应
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else None

            return AIResponse(
                content=content,
                model=model,
                tokens_used=tokens_used,
                cost=None,  # 稍后计算
                provider=self.name,
                raw_response=response
            )

        except Exception as e:
            raise Exception(f"ZhipuAI API call failed: {str(e)}")

    def supports_json_mode(self, model: str) -> bool:
        """
        检查模型是否支持JSON模式

        Args:
            model: 模型名称

        Returns:
            bool: 是否支持JSON模式
        """
        # 智谱AI的glm-4系列支持JSON模式
        return model.startswith('glm-4')

    def get_cost_per_1k_tokens(self, model: str) -> float:
        """
        获取每千token的成本

        Args:
            model: 模型名称

        Returns:
            float: 每千token的成本（美元）
        """
        config = get_config()
        cost = config.get_cost(model)
        if cost > 0:
            return cost

        # 默认成本（智谱AI官方价格）
        # glm-4: 0.12美元/千token
        if model.startswith('glm-4'):
            return 0.12
        elif model.startswith('glm-3'):
            return 0.005
        else:
            return 0.12  # 默认使用glm-4的价格

    def validate_messages(self, messages: List[Dict[str, str]]) -> bool:
        """验证消息格式"""
        # 先调用基类的验证
        if not super().validate_messages(messages):
            return False

        # 智谱AI特定的验证
        for msg in messages:
            if msg['role'] not in ['system', 'user', 'assistant']:
                return False

        return True
