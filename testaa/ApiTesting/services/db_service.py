"""
数据库服务模块
"""
import json
from typing import Any, Dict, List, Optional

import pymysql


class DBService:
    """数据库服务"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", False)
        self._connection: Optional[pymysql.Connection] = None

    def _get_connection(self) -> pymysql.Connection:
        """获取数据库连接"""
        if self._connection is None or not self._connection.open:
            self._connection = pymysql.connect(
                host=self.config.get("host", "localhost"),
                port=self.config.get("port", 3306),
                user=self.config.get("user"),
                password=self.config.get("password"),
                database=self.config.get("name"),
                charset="utf8mb4",
                autocommit=True
            )
        return self._connection

    def close(self):
        """关闭连接"""
        if self._connection and self._connection.open:
            self._connection.close()
            self._connection = None

    def save_test_cases(self, test_cases: List[Dict[str, Any]], document_id: Optional[int], knowledge_id: Optional[str]) -> int:
        """
        保存测试用例到数据库

        Args:
            test_cases: 测试用例列表
            document_id: 文档 ID（可选）
            knowledge_id: 知识库 ID（可选）

        Returns:
            保存的测试用例数量
        """
        if not self.enabled:
            return 0

        conn = self._get_connection()
        cursor = conn.cursor()

        count = 0
        for case in test_cases:
            try:
                sql = """
                    INSERT INTO api_test_case
                    (case_id, api_name, precondition, testpoint, expectation, document_id, knowledge_id, last_run_status, priority, last_run_result, create_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """
                cursor.execute(sql, (
                    case.get("id", str(count + 1)),
                    case.get("apiname", ""),
                    case.get("precondition", ""),
                    case.get("testpoint", ""),
                    case.get("expectation", ""),
                    document_id,
                    knowledge_id,
                    "pending",  # 设置默认状态
                    "中",  # 设置默认优先级
                    ""  # 设置默认执行结果为空
                ))
                count += 1
            except Exception as e:
                print(f"保存测试用例失败：{case}, 错误：{e}")
                continue

        cursor.close()
        return count

    def get_document_by_knowledge_id(self, knowledge_id: str) -> Optional[Dict[str, Any]]:
        """
        根据 knowledge_id 获取文档

        Args:
            knowledge_id: 知识库 ID

        Returns:
            文档信息，如果不存在则返回 None
        """
        if not self.enabled:
            return None

        conn = self._get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        sql = "SELECT * FROM api_document WHERE knowledge_id = %s ORDER BY id DESC LIMIT 1"
        cursor.execute(sql, (knowledge_id,))
        result = cursor.fetchone()
        cursor.close()

        return result


def get_db_service(config: Dict[str, Any] = None) -> DBService:
    """获取数据库服务实例"""
    return DBService(config or {"enabled": False})
