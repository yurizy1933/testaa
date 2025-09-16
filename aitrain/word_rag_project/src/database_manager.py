"""
数据库管理模块 - MySQL数据库操作
"""

import mysql.connector
from mysql.connector import Error
from typing import List, Dict, Optional, Tuple
import time
from datetime import datetime

class DatabaseManager:
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
        self._connect()
    
    def _connect(self):
        """建立数据库连接"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                autocommit=True
            )
            print(f"数据库连接成功: {self.host}:{self.port}/{self.database}")
        except Error as e:
            print(f"数据库连接失败: {e}")
            raise
    
    def _ensure_connection(self):
        """确保数据库连接有效"""
        if self.connection is None or not self.connection.is_connected():
            self._connect()
    
    def save_document_info(self, doc_path: str, doc_name: str, total_pages: int, 
                          total_words: int, file_size: int) -> int:
        """保存文档信息"""
        self._ensure_connection()
        
        query = """
        INSERT INTO documents (doc_path, doc_name, total_pages, total_words, file_size, processed_time)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        doc_name = VALUES(doc_name),
        total_pages = VALUES(total_pages),
        total_words = VALUES(total_words),
        file_size = VALUES(file_size),
        processed_time = VALUES(processed_time)
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, (doc_path, doc_name, total_pages, total_words, file_size, datetime.now()))
            doc_id = cursor.lastrowid
            cursor.close()
            return doc_id
        except Error as e:
            print(f"保存文档信息失败: {e}")
            raise
    
    def save_vector_data(self, vector_id: int, text: str, doc_path: str, doc_name: str,
                        page: int, word_count: int) -> int:
        """保存向量数据"""
        self._ensure_connection()
        
        query = """
        INSERT INTO vectors (vector_id, text, doc_path, doc_name, page, word_count, processed_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, (vector_id, text, doc_path, doc_name, page, word_count, datetime.now()))
            record_id = cursor.lastrowid
            cursor.close()
            return record_id
        except Error as e:
            print(f"保存向量数据失败: {e}")
            raise
    
    def save_processing_status(self, doc_path: str, total_chunks: int, success_chunks: int,
                             processing_time: float) -> int:
        """保存处理状态"""
        self._ensure_connection()
        
        query = """
        INSERT INTO processing_status (doc_path, total_chunks, success_chunks, processing_time, created_at)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, (doc_path, total_chunks, success_chunks, processing_time, datetime.now()))
            status_id = cursor.lastrowid
            cursor.close()
            return status_id
        except Error as e:
            print(f"保存处理状态失败: {e}")
            raise
    
    def get_document_by_path(self, doc_path: str) -> Optional[Dict]:
        """根据路径获取文档信息"""
        self._ensure_connection()
        
        query = "SELECT * FROM documents WHERE doc_path = %s"
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, (doc_path,))
            result = cursor.fetchone()
            cursor.close()
            return result
        except Error as e:
            print(f"获取文档信息失败: {e}")
            return None
    
    def get_vectors_by_doc_path(self, doc_path: str) -> List[Dict]:
        """根据文档路径获取所有向量数据"""
        self._ensure_connection()
        
        query = "SELECT * FROM vectors WHERE doc_path = %s ORDER BY page, vector_id"
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, (doc_path,))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Error as e:
            print(f"获取向量数据失败: {e}")
            return []
    
    def get_vector_by_id(self, vector_id: int) -> Optional[Dict]:
        """根据向量ID获取向量数据"""
        self._ensure_connection()
        
        query = "SELECT * FROM vectors WHERE vector_id = %s"
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, (vector_id,))
            result = cursor.fetchone()
            cursor.close()
            return result
        except Error as e:
            print(f"获取向量数据失败: {e}")
            return None
    
    def get_all_documents(self) -> List[Dict]:
        """获取所有文档信息"""
        self._ensure_connection()
        
        query = "SELECT * FROM documents ORDER BY processed_time DESC"
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            return results
        except Error as e:
            print(f"获取文档列表失败: {e}")
            return []
    
    def get_processing_stats(self) -> Dict:
        """获取处理统计信息"""
        self._ensure_connection()
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # 获取文档总数
            cursor.execute("SELECT COUNT(*) as total_docs FROM documents")
            total_docs = cursor.fetchone()['total_docs']
            
            # 获取向量总数
            cursor.execute("SELECT COUNT(*) as total_vectors FROM vectors")
            total_vectors = cursor.fetchone()['total_vectors']
            
            # 获取最近处理状态
            cursor.execute("""
                SELECT * FROM processing_status 
                ORDER BY created_at DESC 
                LIMIT 10
            """)
            recent_status = cursor.fetchall()
            
            cursor.close()
            
            return {
                'total_documents': total_docs,
                'total_vectors': total_vectors,
                'recent_processing': recent_status
            }
        except Error as e:
            print(f"获取统计信息失败: {e}")
            return {}
    
    def get_processed_pages(self, doc_path: str) -> List[int]:
        """获取已处理的页面列表"""
        self._ensure_connection()
        
        query = "SELECT DISTINCT page FROM vectors WHERE doc_path = %s ORDER BY page"
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, (doc_path,))
            pages = [row[0] for row in cursor.fetchall()]
            cursor.close()
            return pages
        except Error as e:
            print(f"获取已处理页面失败: {e}")
            return []
    
    def get_document_progress(self, doc_path: str) -> Dict:
        """获取文档处理进度"""
        self._ensure_connection()
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # 获取文档信息
            cursor.execute("SELECT * FROM documents WHERE doc_path = %s", (doc_path,))
            doc_info = cursor.fetchone()
            
            # 获取已处理的页面
            processed_pages = self.get_processed_pages(doc_path)
            
            # 获取向量统计
            cursor.execute("SELECT COUNT(*) as vector_count FROM vectors WHERE doc_path = %s", (doc_path,))
            vector_count = cursor.fetchone()['vector_count']
            
            cursor.close()
            
            return {
                'doc_info': doc_info,
                'processed_pages': processed_pages,
                'total_vectors': vector_count,
                'last_processed_page': max(processed_pages) if processed_pages else 0
            }
        except Error as e:
            print(f"获取文档进度失败: {e}")
            return {}
    
    def save_processing_progress(self, doc_path: str, current_page: int, total_pages: int):
        """保存处理进度"""
        self._ensure_connection()
        
        query = """
        INSERT INTO processing_status (doc_path, total_chunks, success_chunks, processing_time, created_at)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, (doc_path, total_pages, current_page, 0.0, datetime.now()))
            cursor.close()
        except Error as e:
            print(f"保存处理进度失败: {e}")
    
    def update_document_status(self, doc_path: str, status: str, current_page: int = 0):
        """更新文档处理状态"""
        self._ensure_connection()
        
        # 这里可以添加一个文档状态表来跟踪处理状态
        # 暂时使用processing_status表
        query = """
        INSERT INTO processing_status (doc_path, total_chunks, success_chunks, processing_time, created_at)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, (doc_path, 0, current_page, 0.0, datetime.now()))
            cursor.close()
        except Error as e:
            print(f"更新文档状态失败: {e}")
    
    def delete_document_data(self, doc_path: str) -> bool:
        """删除文档相关数据"""
        self._ensure_connection()
        
        try:
            cursor = self.connection.cursor()
            
            # 删除向量数据
            cursor.execute("DELETE FROM vectors WHERE doc_path = %s", (doc_path,))
            vectors_deleted = cursor.rowcount
            
            # 删除文档信息
            cursor.execute("DELETE FROM documents WHERE doc_path = %s", (doc_path,))
            docs_deleted = cursor.rowcount
            
            # 删除处理状态
            cursor.execute("DELETE FROM processing_status WHERE doc_path = %s", (doc_path,))
            
            cursor.close()
            
            print(f"删除文档数据: {vectors_deleted} 个向量, {docs_deleted} 个文档记录")
            return True
        except Error as e:
            print(f"删除文档数据失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("数据库连接已关闭")
    
    def save_page_info(self, page_info: Dict) -> bool:
        """
        保存页面信息
        :param page_info: 页面信息字典
        :return: 是否保存成功
        """
        try:
            cursor = self.connection.cursor()
            
            insert_query = """
            INSERT INTO pages (doc_path, page_num, text_content, image_count, table_count, paragraph_count, processed_time)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(insert_query, (
                page_info['doc_path'],
                page_info['page_num'],
                page_info['text_content'],
                page_info['image_count'],
                page_info['table_count'],
                page_info['paragraph_count']
            ))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            print(f"保存页面信息失败: {e}")
            return False
    
    def save_point_info(self, point_info: Dict) -> bool:
        """
        保存信息点
        :param point_info: 信息点字典
        :return: 是否保存成功
        """
        try:
            cursor = self.connection.cursor()
            
            insert_query = """
            INSERT INTO document_points (doc_path, point_index, point_type, content, page_num, hash_value, vector_success, vector_id, processed_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(insert_query, (
                point_info['doc_path'],
                point_info['point_index'],
                point_info['point_type'],
                point_info['content'],
                point_info['page_num'],
                point_info['hash'],
                point_info['vector_success'],
                point_info.get('vector_id')
            ))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            print(f"保存信息点失败: {e}")
            return False
    
    def save_analysis_info(self, analysis_info: Dict) -> bool:
        """
        保存分析结果信息
        :param analysis_info: 分析结果字典
        :return: 是否保存成功
        """
        try:
            cursor = self.connection.cursor()
            
            insert_query = """
            INSERT INTO document_analysis (doc_path, doc_name, total_points, success_vectors, fail_vectors, processed_time)
            VALUES (%s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(insert_query, (
                analysis_info['doc_path'],
                analysis_info['doc_name'],
                analysis_info['total_points'],
                analysis_info['success_vectors'],
                analysis_info['fail_vectors']
            ))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            print(f"保存分析结果失败: {e}")
            return False 