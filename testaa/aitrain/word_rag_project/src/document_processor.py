"""
文档处理管理器 - 实现逐页处理和断点续传
"""

import os
import time
from typing import List, Dict, Optional, Tuple
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

from .word_parser import WordDocumentParser
from .ai_client import AIClient
from .vector_manager import VectorManager
from .database_manager import DatabaseManager

class DocumentProcessor:
    def __init__(self, word_parser: WordDocumentParser, ai_client: AIClient, 
                 vector_manager: VectorManager, db_manager: DatabaseManager):
        self.word_parser = word_parser
        self.ai_client = ai_client
        self.vector_manager = vector_manager
        self.db_manager = db_manager
        self.batch_size = 5  # 每批处理的页面数量
    
    def process_document_incremental(self, doc_path: str, force_restart: bool = False) -> Dict:
        """
        增量处理文档，支持断点续传
        :param doc_path: 文档路径
        :param force_restart: 是否强制重新开始
        :return: 处理结果
        """
        print(f"开始增量处理文档: {doc_path}")
        start_time = time.time()
        
        # 检查文档是否存在
        if not os.path.exists(doc_path):
            raise FileNotFoundError(f"文档不存在: {doc_path}")
        
        # 获取文档信息
        doc_info = self.word_parser.get_document_info(doc_path)
        total_pages = doc_info['estimated_pages']
        
        # 保存文档信息到数据库
        try:
            self.db_manager.save_document_info(
                doc_path=doc_path,
                doc_name=os.path.basename(doc_path),
                total_pages=total_pages,
                total_words=doc_info['total_words'],
                file_size=doc_info['file_size']
            )
        except Exception as e:
            print(f"保存文档信息失败: {e}")
        
        # 获取处理进度
        progress = self.db_manager.get_document_progress(doc_path)
        processed_pages = progress.get('processed_pages', [])
        last_processed_page = progress.get('last_processed_page', 0)
        
        if force_restart:
            print("强制重新开始处理")
            start_page = 1
            processed_pages = []
        else:
            if processed_pages:
                print(f"发现已处理页面: {processed_pages}")
                start_page = last_processed_page + 1
            else:
                print("开始新文档处理")
                start_page = 1
        
        if start_page > total_pages:
            print("文档已完全处理完成")
            return {
                'doc_path': doc_path,
                'status': 'completed',
                'message': '文档已完全处理完成',
                'processed_pages': processed_pages,
                'total_pages': total_pages
            }
        
        print(f"从第 {start_page} 页开始处理，共 {total_pages} 页")
        
        # 分批处理页面
        total_vectors = 0
        success_pages = 0
        
        for batch_start in range(start_page, total_pages + 1, self.batch_size):
            batch_end = min(batch_start + self.batch_size - 1, total_pages)
            print(f"处理页面批次: {batch_start}-{batch_end}")
            
            try:
                batch_result = self._process_page_batch(
                    doc_path, batch_start, batch_end, doc_info
                )
                
                if batch_result['success']:
                    total_vectors += batch_result['vector_count']
                    success_pages += batch_result['page_count']
                    print(f"批次处理成功: {batch_result['page_count']} 页, {batch_result['vector_count']} 个向量")
                else:
                    print(f"批次处理失败: {batch_result['error']}")
                    break
                    
            except Exception as e:
                print(f"批次处理异常: {e}")
                break
        
        processing_time = time.time() - start_time
        
        # 保存最终处理状态
        try:
            self.db_manager.save_processing_status(
                doc_path=doc_path,
                total_chunks=total_pages,
                success_chunks=success_pages,
                processing_time=processing_time
            )
        except Exception as e:
            print(f"保存处理状态失败: {e}")
        
        return {
            'doc_path': doc_path,
            'status': 'success',
            'total_pages': total_pages,
            'processed_pages': success_pages,
            'total_vectors': total_vectors,
            'processing_time': processing_time,
            'start_page': start_page,
            'last_processed_page': start_page + success_pages - 1
        }
    
    def _process_page_batch(self, doc_path: str, start_page: int, end_page: int, 
                           doc_info: Dict) -> Dict:
        """
        处理页面批次
        :param doc_path: 文档路径
        :param start_page: 开始页面
        :param end_page: 结束页面
        :param doc_info: 文档信息
        :return: 处理结果
        """
        try:
            # 解析指定页面范围的文档
            chunks = self.word_parser.parse_document(
                doc_path, self.db_manager, start_page
            )
            
            if not chunks:
                return {
                    'success': False,
                    'error': '未解析到文本块',
                    'page_count': 0,
                    'vector_count': 0
                }
            
            # 过滤指定页面范围的块
            filtered_chunks = [
                chunk for chunk in chunks 
                if start_page <= chunk['page'] <= end_page
            ]
            
            if not filtered_chunks:
                return {
                    'success': False,
                    'error': '指定页面范围内无文本块',
                    'page_count': 0,
                    'vector_count': 0
                }
            
            # 提取文本内容
            texts = [chunk['text'] for chunk in filtered_chunks]
            
            # 批量获取向量
            print(f"获取 {len(texts)} 个文本块的向量...")
            vector_results = self.ai_client.get_embeddings_batch(texts)
            
            # 处理向量结果
            vectors = []
            metadata = []
            success_count = 0
            
            for i, (success, vector) in enumerate(vector_results):
                if success and vector is not None:
                    vectors.append(vector)
                    # 构建元数据
                    meta = {
                        'text': filtered_chunks[i]['text'],
                        'page': filtered_chunks[i]['page'],
                        'start_pos': filtered_chunks[i]['start_pos'],
                        'end_pos': filtered_chunks[i]['end_pos'],
                        'word_count': filtered_chunks[i]['word_count'],
                        'doc_path': doc_path,
                        'doc_name': os.path.basename(doc_path),
                        'processed_time': time.time()
                    }
                    metadata.append(meta)
                    success_count += 1
                else:
                    print(f"文本块 {i} 向量化失败")
            
            print(f"成功处理 {success_count}/{len(texts)} 个文本块")
            
            # 添加到向量数据库
            vector_ids = []
            if vectors:
                vector_ids = self.vector_manager.add_vectors(vectors, metadata)
                print(f"成功添加到向量数据库，向量ID: {vector_ids}")
            
            return {
                'success': True,
                'page_count': end_page - start_page + 1,
                'vector_count': len(vector_ids),
                'chunk_count': len(filtered_chunks),
                'success_chunks': success_count
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'page_count': 0,
                'vector_count': 0
            }
    
    def get_document_status(self, doc_path: str) -> Dict:
        """获取文档处理状态"""
        try:
            progress = self.db_manager.get_document_progress(doc_path)
            doc_info = progress.get('doc_info', {})
            processed_pages = progress.get('processed_pages', [])
            total_vectors = progress.get('total_vectors', 0)
            last_processed_page = progress.get('last_processed_page', 0)
            
            if not doc_info:
                return {
                    'doc_path': doc_path,
                    'status': 'not_started',
                    'message': '文档未开始处理'
                }
            
            total_pages = doc_info.get('total_pages', 0)
            progress_percentage = (len(processed_pages) / total_pages * 100) if total_pages > 0 else 0
            
            return {
                'doc_path': doc_path,
                'status': 'in_progress' if last_processed_page < total_pages else 'completed',
                'total_pages': total_pages,
                'processed_pages': len(processed_pages),
                'last_processed_page': last_processed_page,
                'total_vectors': total_vectors,
                'progress_percentage': round(progress_percentage, 2),
                'doc_info': doc_info
            }
            
        except Exception as e:
            return {
                'doc_path': doc_path,
                'status': 'error',
                'error': str(e)
            }
    
    def resume_processing(self, doc_path: str) -> Dict:
        """恢复文档处理"""
        status = self.get_document_status(doc_path)
        
        if status['status'] == 'completed':
            return {
                'doc_path': doc_path,
                'status': 'already_completed',
                'message': '文档已处理完成'
            }
        
        return self.process_document_incremental(doc_path, force_restart=False)
    
    def restart_processing(self, doc_path: str) -> Dict:
        """重新开始文档处理"""
        # 删除现有数据
        self.db_manager.delete_document_data(doc_path)
        
        return self.process_document_incremental(doc_path, force_restart=True) 