"""
DeepSeek提供商实现
"""

from typing import Dict, List, Optional
from ..core.base import AIProvider, AIResponse
from ..core.config import get_config


class DeepSeekProvider(AIProvider):
    """DeepSeek提供商类"""

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com", **kwargs):
        super().__init__(api_key, **kwargs)
        self.base_url = base_url

        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )
        except ImportError:
            raise ImportError("openai package is required for DeepSeek provider")

    @property
    def name(self) -> str:
        return "deepseek"

    @property
    def default_model(self) -> str:
        return "deepseek-chat"

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

            if json_mode:
                json_instruction = {"role": "system", "content": "请确保只返回JSON格式的数据，不要包含其他说明文字。"}
                if messages[0]['role'] == 'system':
                    messages[0]['content'] = json_instruction['content'] + "\n\n" + messages[0]['content']
                else:
                    messages.insert(0, json_instruction)

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
            raise Exception(f"DeepSeek API call failed: {str(e)}")

    def supports_json_mode(self, model: str) -> bool:
        return False

    def get_cost_per_1k_tokens(self, model: str) -> float:
        config = get_config()
        cost = config.get_cost(model)
        if cost > 0:
            return cost

        return 0.14

    def validate_messages(self, messages: List[Dict[str, str]]) -> bool:
        if not super().validate_messages(messages):
            return False

        for msg in messages:
            if msg['role'] not in ['system', 'user', 'assistant']:
                return False

        return True
