"""
Flask 应用入口
"""
import os
from flask import Flask, jsonify
from flask_cors import CORS

from config.settings import get_settings
from api.routes import rpc_blueprint
from utils.logger import get_logger

logger = get_logger(__name__)


def create_app() -> Flask:
    """创建 Flask 应用"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.urandom(24).hex()

    # 加载配置
    settings = get_settings()

    # 启用 CORS
    CORS(app, resources={r"/rpc/*": {"origins": "*"}})

    # 注册蓝图
    app.register_blueprint(rpc_blueprint)

    # 注册错误处理器
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": "Not Found"},
            "id": None
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": "Internal Server Error"},
            "id": None
        }), 500

    logger.info("Flask 应用创建完成")

    return app


if __name__ == "__main__":
    app = create_app()
    settings = get_settings()

    host = settings.server.get("host", "0.0.0.0")
    port = settings.server.get("port", 5001)
    debug = settings.server.get("debug", False)

    logger.info(f"启动服务：http://{host}:{port}")
    app.run(host=host, port=port, debug=debug, threaded=True)
