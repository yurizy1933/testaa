"""
启动脚本

使用方式：
    python run.py
    或
    python run.py config.yaml
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from config.settings import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    app = create_app()
    settings = get_settings()

    host = settings.server.get("host", "0.0.0.0")
    port = settings.server.get("port", 5004)
    debug = settings.server.get("debug", False)

    logger.info("=" * 60)
    logger.info("API Testing 服务启动")
    logger.info("=" * 60)
    logger.info(f"监听地址：http://{host}:{port}")
    logger.info(f"调试模式：{debug}")
    logger.info("=" * 60)
    logger.info("可用接口:")
    logger.info("  POST /rpc/ - apitest.getflow (stream=true)")
    logger.info("  POST /rpc/ - llm.chat (stream=true/false)")
    logger.info("  GET  /rpc/health - 健康检查")
    logger.info("  GET  /rpc/status - 服务状态")
    logger.info("=" * 60)

    app.run(host=host, port=port, debug=debug, threaded=True)
