"""
智谱AI提供商实现
"""

from typing import Dict, List, Optional
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
        if model is None:
            model = self.default_model

        try:
            request_params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if json_mode and self.supports_json_mode(model):
                request_params["response_format"] = {"type": "json_object"}

            request_params.update(kwargs)

            response = self._client.chat.completions.create(**request_params)

            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else None

            return AIResponse(
                content=content,
                model=model,
                tokens_used=tokens_used,
                cost=None,
                provider=self.name,
                raw_response=response
            )

        except Exception as e:
            raise Exception(f"ZhipuAI API call failed: {str(e)}")

    def supports_json_mode(self, model: str) -> bool:
        return model.startswith('glm-4')

    def get_cost_per_1k_tokens(self, model: str) -> float:
        config = get_config()
        cost = config.get_cost(model)
        if cost > 0:
            return cost

        if model.startswith('glm-4'):
            return 0.12
        elif model.startswith('glm-3'):
            return 0.005
        else:
            return 0.12

    def validate_messages(self, messages: List[Dict[str, str]]) -> bool:
        if not super().validate_messages(messages):
            return False

        for msg in messages:
            if msg['role'] not in ['system', 'user', 'assistant']:
                return False

        return True
