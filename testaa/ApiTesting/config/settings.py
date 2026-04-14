"""
配置管理模块
"""
import os
from typing import Any, Dict, Optional

import yaml


class Settings:
    """配置类"""

    def __init__(self):
        self.server: Dict[str, Any] = {}
        self.llm: Dict[str, Any] = {}
        self.knowledge_service: Dict[str, Any] = {}
        self.database: Dict[str, Any] = {"enabled": False}

    @classmethod
    def from_yaml(cls, path: str) -> "Settings":
        """从 YAML 文件加载配置"""
        if not os.path.exists(path):
            raise FileNotFoundError(f"配置文件不存在：{path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Settings":
        """从字典创建配置"""
        settings = cls()

        settings.server = data.get("server", {
            "host": "0.0.0.0",
            "port": 5001,
            "debug": False
        })

        settings.llm = data.get("llm", {})
        settings.knowledge_service = data.get("knowledge_service", {})
        settings.database = data.get("database", {"enabled": False})

        return settings


# 全局配置实例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取全局配置实例"""
    global _settings
    if _settings is None:
        # 默认配置路径
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "config.yaml"
        )
        _settings = Settings.from_yaml(config_path)
    return _settings
