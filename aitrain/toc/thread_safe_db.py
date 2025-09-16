#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
线程安全的数据库管理器
"""

import pymysql
import threading
import json
from config import DB_CONFIG

class ThreadSafeDatabaseManager:
    def __init__(self):
        self._local = threading.local()
        self._lock = threading.Lock()
        self._create_initial_tables()
    
    def _get_connection(self):
        """获取当前线程的数据库连接"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            with self._lock:
                try:
                    self._local.connection = pymysql.connect(**DB_CONFIG)
                    print(f"线程 {threading.current_thread().name} 创建数据库连接")
                except Exception as e:
                    print(f"线程 {threading.current_thread().name} 数据库连接失败: {e}")
                    raise
        return self._local.connection
    
    def _create_initial_tables(self):
        """创建初始表（只在主线程中执行一次）"""
        try:
            connection = pymysql.connect(**DB_CONFIG)
            with connection.cursor() as cursor:
                # 创建文档内容表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS adocument_content (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        file_name VARCHAR(255) NOT NULL,
                        page_number INT NOT NULL,
                        paragraph_number INT NOT NULL,
                        content_type ENUM('text', 'image', 'table') NOT NULL,
                        content_text TEXT,
                        original_content TEXT,
                        section_title VARCHAR(500),
                        section_level INT DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_file_page (file_name, page_number),
                        INDEX idx_section (section_title)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                
                # 创建文档要点表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS adocument_point (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        file_name VARCHAR(255) NOT NULL,
                        point_text TEXT NOT NULL,
                        faiss_id INT,
                        vector_data JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_file (file_name),
                        INDEX idx_faiss (faiss_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
            
            connection.commit()
            connection.close()
            print("数据库表创建成功")
        except Exception as e:
            print(f"创建表失败: {e}")
            raise
    
    def insert_content(self, file_name, page_number, paragraph_number, content_type, content_text, original_content=None, section_title=None, section_level=1):
        """插入文档内容（线程安全）"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                connection = self._get_connection()
                with connection.cursor() as cursor:
                    sql = """
                        INSERT INTO adocument_content 
                        (file_name, page_number, paragraph_number, content_type, content_text, original_content, section_title, section_level)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(sql, (file_name, page_number, paragraph_number, content_type, content_text, original_content, section_title, section_level))
                connection.commit()
                print(f"线程 {threading.current_thread().name} 插入内容成功: {file_name} - 章节:{section_title} - 第{paragraph_number}段")
                return True
            except Exception as e:
                print(f"线程 {threading.current_thread().name} 插入内容失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    # 重置连接
                    try:
                        if hasattr(self._local, 'connection'):
                            self._local.connection.close()
                    except:
                        pass
                    self._local.connection = None
                    import time
                    time.sleep(0.1)  # 短暂等待
                else:
                    print(f"线程 {threading.current_thread().name} 插入内容最终失败")
                    return False
    
    def insert_point(self, file_name, point_text, faiss_id, vector_data):
        """插入文档要点（线程安全）"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                connection = self._get_connection()
                with connection.cursor() as cursor:
                    sql = """
                        INSERT INTO adocument_point 
                        (file_name, point_text, faiss_id, vector_data)
                        VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(sql, (file_name, point_text, faiss_id, json.dumps(vector_data)))
                connection.commit()
                print(f"线程 {threading.current_thread().name} 插入要点成功: {file_name} - faiss_id: {faiss_id}")
                return True
            except Exception as e:
                print(f"线程 {threading.current_thread().name} 插入要点失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    # 重置连接
                    try:
                        if hasattr(self._local, 'connection'):
                            self._local.connection.close()
                    except:
                        pass
                    self._local.connection = None
                    import time
                    time.sleep(0.1)  # 短暂等待
                else:
                    print(f"线程 {threading.current_thread().name} 插入要点最终失败")
                    return False
    
    def get_sections_by_file(self, file_name):
        """获取文档的所有章节信息"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                connection = self._get_connection()
                with connection.cursor() as cursor:
                    sql = """
                        SELECT DISTINCT section_title, section_level
                        FROM adocument_content 
                        WHERE file_name = %s AND section_title IS NOT NULL
                        ORDER BY section_level, section_title
                    """
                    cursor.execute(sql, (file_name,))
                    results = cursor.fetchall()
                    
                    sections = []
                    for row in results:
                        sections.append({
                            'section_title': row[0],
                            'section_level': row[1]
                        })
                    
                    print(f"线程 {threading.current_thread().name} 获取章节信息成功: {file_name} - {len(sections)} 个章节")
                    return sections
                    
            except Exception as e:
                print(f"线程 {threading.current_thread().name} 获取章节信息失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    # 重置连接
                    try:
                        if hasattr(self._local, 'connection'):
                            self._local.connection.close()
                    except:
                        pass
                    self._local.connection = None
                    import time
                    time.sleep(0.1)  # 短暂等待
                else:
                    print(f"线程 {threading.current_thread().name} 获取章节信息最终失败")
                    return []
    
    def get_content_by_section(self, file_name, section_title):
        """获取指定章节的所有内容"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                connection = self._get_connection()
                with connection.cursor() as cursor:
                    sql = """
                        SELECT content_type, content_text, original_content, paragraph_number
                        FROM adocument_content 
                        WHERE file_name = %s AND section_title = %s
                        ORDER BY paragraph_number
                    """
                    cursor.execute(sql, (file_name, section_title))
                    results = cursor.fetchall()
                    
                    content_items = []
                    for row in results:
                        content_items.append({
                            'content_type': row[0],
                            'content_text': row[1],
                            'original_content': row[2],
                            'paragraph_number': row[3]
                        })
                    
                    print(f"线程 {threading.current_thread().name} 获取章节内容成功: {file_name} - {section_title} - {len(content_items)} 个内容项")
                    return content_items
                    
            except Exception as e:
                print(f"线程 {threading.current_thread().name} 获取章节内容失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    # 重置连接
                    try:
                        if hasattr(self._local, 'connection'):
                            self._local.connection.close()
                    except:
                        pass
                    self._local.connection = None
                    import time
                    time.sleep(0.1)  # 短暂等待
                else:
                    print(f"线程 {threading.current_thread().name} 获取章节内容最终失败")
                    return []
    
    def close(self):
        """关闭数据库连接（兼容性方法）"""
        self.close_all_connections()
    
    def close_all_connections(self):
        """关闭所有线程的数据库连接"""
        try:
            if hasattr(self._local, 'connection') and self._local.connection:
                self._local.connection.close()
                print(f"线程 {threading.current_thread().name} 数据库连接已关闭")
        except Exception as e:
            print(f"关闭数据库连接失败: {e}")
    
    def __del__(self):
        """析构函数，确保连接被关闭"""
        self.close_all_connections() 

    def execute_query(self, sql, params=None):
        """执行SQL查询（线程安全）"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                connection = self._get_connection()
                with connection.cursor() as cursor:
                    cursor.execute(sql, params or ())
                    # 不在这里commit，因为这是查询操作
                    return cursor
            except Exception as e:
                print(f"线程 {threading.current_thread().name} 执行查询失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    # 重置连接
                    try:
                        if hasattr(self._local, 'connection'):
                            self._local.connection.close()
                    except:
                        pass
                    self._local.connection = None
                    import time
                    time.sleep(0.1)  # 短暂等待
                else:
                    print(f"线程 {threading.current_thread().name} 执行查询最终失败")
                    return None
    
    def fetch_all(self):
        """获取所有查询结果"""
        try:
            connection = self._get_connection()
            with connection.cursor() as cursor:
                # 重新执行查询
                return cursor.fetchall()
        except Exception as e:
            print(f"获取查询结果失败: {e}")
            return []
    
    def query_all(self, sql, params=None):
        """执行查询并返回所有结果（字典格式）"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                connection = self._get_connection()
                with connection.cursor() as cursor:
                    cursor.execute(sql, params or ())
                    results = cursor.fetchall()
                    
                    # 转换为字典列表
                    if results:
                        columns = [desc[0] for desc in cursor.description]
                        return [dict(zip(columns, row)) for row in results]
                    return []
            except Exception as e:
                print(f"线程 {threading.current_thread().name} 查询失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    # 重置连接
                    try:
                        if hasattr(self._local, 'connection'):
                            self._local.connection.close()
                    except:
                        pass
                    self._local.connection = None
                    import time
                    time.sleep(0.1)  # 短暂等待
                else:
                    print(f"线程 {threading.current_thread().name} 查询最终失败")
                    return []
    
    def get_all_points(self):
        """获取所有需求要点数据"""
        try:
            sql = "SELECT faiss_id, point_text FROM adocument_point"
            return self.query_all(sql)
        except Exception as e:
            print(f"获取所有point失败: {e}")
            return []
    
    def get_all_cases(self):
        """获取所有测试用例数据"""
        try:
            sql = "SELECT faiss_id, case_title FROM test_cases"
            return self.query_all(sql)
        except Exception as e:
            print(f"获取所有case失败: {e}")
            return [] 