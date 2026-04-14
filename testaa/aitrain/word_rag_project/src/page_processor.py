"""
逐页处理器 - 实现真正的逐页处理和存储
"""

import os
import time
import gc
from typing import List, Dict, Optional, Tuple, Generator
import numpy as np

from .word_parser import WordDocumentParser
from .ai_client import AIClient
from .vector_manager import VectorManager
from .database_manager import DatabaseManager

class PageProcessor:
    def __init__(self, word_parser: WordDocumentParser, ai_client: AIClient, 
                 vector_manager: VectorManager, db_manager: DatabaseManager):
        self.word_parser = word_parser
        self.ai_client = ai_client
        self.vector_manager = vector_manager
        self.db_manager = db_manager
        self.max_chunks_per_page = 20  # 每页最大块数
        self.max_batch_size = 10  # 每批处理的最大页面数
    
    def process_document_by_pages(self, doc_path: str, start_page: int = 1, 
                                 end_page: Optional[int] = None) -> Generator[Dict, None, None]:
        """
        逐页处理文档，生成器模式，避免内存溢出
        :param doc_path: 文档路径
        :param start_page: 开始页面
        :param end_page: 结束页面（None表示处理到文档末尾）
        :yield: 每页的处理结果
        """
        if not os.path.exists(doc_path):
            raise FileNotFoundError(f"文档不存在: {doc_path}")
        
        # 获取文档信息
        doc_info = self.word_parser.get_document_info(doc_path)
        total_pages = doc_info['estimated_pages']
        
        if end_page is None:
            end_page = total_pages
        
        print(f"开始逐页处理文档: {doc_path}")
        print(f"处理页面范围: {start_page}-{end_page}，共 {total_pages} 页")
        
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
        
        # 逐页处理
        for page_num in range(start_page, end_page + 1):
            try:
                page_result = self._process_single_page(doc_path, page_num, doc_info)
                yield page_result
                
                # 强制垃圾回收，释放内存
                gc.collect()
                
            except Exception as e:
                print(f"处理第 {page_num} 页失败: {e}")
                yield {
                    'page': page_num,
                    'success': False,
                    'error': str(e),
                    'vector_count': 0,
                    'chunk_count': 0
                }
    
    def _process_single_page(self, doc_path: str, page_num: int, doc_info: Dict) -> Dict:
        """
        处理单个页面
        :param doc_path: 文档路径
        :param page_num: 页面编号
        :param doc_info: 文档信息
        :return: 页面处理结果
        """
        print(f"处理第 {page_num} 页...")
        start_time = time.time()
        
        try:
            # 解析当前页面
            chunks = self._parse_page_chunks(doc_path, page_num)
            
            print(f"解析第 {page_num} 页，得到 {len(chunks)} 个文本块")
            
            if not chunks:
                print(f"第 {page_num} 页无内容")
                return {
                    'page': page_num,
                    'success': True,
                    'message': '页面无内容',
                    'vector_count': 0,
                    'chunk_count': 0,
                    'processing_time': time.time() - start_time
                }
            
            # 限制每页的块数，避免内存溢出
            if len(chunks) > self.max_chunks_per_page:
                print(f"页面块数过多({len(chunks)})，截取前{self.max_chunks_per_page}个块")
                chunks = chunks[:self.max_chunks_per_page]
            
            # 提取文本内容
            texts = [chunk['text'] for chunk in chunks]
            
            # 调试：显示前几个文本块的内容
            if texts:
                print(f"第 {page_num} 页文本示例:")
                for i, text in enumerate(texts[:3]):
                    print(f"  块{i+1}: {text[:100]}...")
            else:
                print(f"第 {page_num} 页无有效文本")
            
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
                        'text': chunks[i]['text'],
                        'page': page_num,
                        'start_pos': chunks[i]['start_pos'],
                        'end_pos': chunks[i]['end_pos'],
                        'word_count': chunks[i]['word_count'],
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
            
            processing_time = time.time() - start_time
            
            return {
                'page': page_num,
                'success': True,
                'vector_count': len(vector_ids),
                'chunk_count': len(chunks),
                'success_chunks': success_count,
                'processing_time': processing_time
            }
            
        except Exception as e:
            return {
                'page': page_num,
                'success': False,
                'error': str(e),
                'vector_count': 0,
                'chunk_count': 0,
                'processing_time': time.time() - start_time
            }
    
    def _parse_page_chunks(self, doc_path: str, page_num: int) -> List[Dict]:
        """
        解析指定页面的文本块
        :param doc_path: 文档路径
        :param page_num: 页面编号
        :return: 文本块列表
        """
        from docx import Document
        
        doc = Document(doc_path)
        page_chunks = []
        current_text = ""
        current_page = 1
        
        # 如果请求第1页，直接处理所有内容直到遇到第一个标题
        if page_num == 1:
            for para in doc.paragraphs:
                if not para.text.strip():
                    continue
                
                # 如果遇到标题，说明第1页结束
                if self.word_parser._is_heading(para) and current_text.strip():
                    page_chunks = self.word_parser._split_text_into_chunks(
                        current_text, page_num
                    )
                    break
                else:
                    current_text += para.text + "\n"
            
            # 如果没有遇到标题，处理所有内容作为第1页
            if not page_chunks and current_text.strip():
                page_chunks = self.word_parser._split_text_into_chunks(
                    current_text, page_num
                )
        else:
            # 处理其他页面
            for para in doc.paragraphs:
                if not para.text.strip():
                    continue
                
                # 检查是否是标题（用于分页）
                if self.word_parser._is_heading(para):
                    # 如果到达目标页面，处理当前页内容
                    if current_page == page_num and current_text.strip():
                        page_chunks = self.word_parser._split_text_into_chunks(
                            current_text, page_num
                        )
                        break
                    
                    # 开始新页
                    current_page += 1
                    current_text = para.text + "\n"
                else:
                    current_text += para.text + "\n"
            
            # 处理最后一页（如果目标页面是最后一页）
            if current_page == page_num and current_text.strip() and not page_chunks:
                page_chunks = self.word_parser._split_text_into_chunks(
                    current_text, page_num
                )
        
        return page_chunks
    
    def process_document_with_progress(self, doc_path: str, start_page: int = 1) -> Dict:
        """
        带进度跟踪的文档处理
        :param doc_path: 文档路径
        :param start_page: 开始页面
        :return: 处理结果
        """
        print(f"开始带进度跟踪的文档处理: {doc_path}")
        start_time = time.time()
        
        # 获取文档信息
        doc_info = self.word_parser.get_document_info(doc_path)
        total_pages = doc_info['estimated_pages']
        
        # 获取已处理页面
        progress = self.db_manager.get_document_progress(doc_path)
        processed_pages = progress.get('processed_pages', [])
        
        if processed_pages:
            print(f"发现已处理页面: {processed_pages}")
            start_page = max(processed_pages) + 1
        
        if start_page > total_pages:
            return {
                'doc_path': doc_path,
                'status': 'completed',
                'message': '文档已处理完成',
                'total_pages': total_pages,
                'processed_pages': len(processed_pages)
            }
        
        # 逐页处理
        total_vectors = 0
        success_pages = 0
        
        for page_result in self.process_document_by_pages(doc_path, start_page):
            if page_result['success']:
                total_vectors += page_result['vector_count']
                success_pages += 1
                print(f"第 {page_result['page']} 页处理完成: {page_result['vector_count']} 个向量")
            else:
                print(f"第 {page_result['page']} 页处理失败: {page_result.get('error', '未知错误')}")
        
        processing_time = time.time() - start_time
        
        # 保存处理状态
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
            'start_page': start_page
        }
    
    def get_processing_status(self, doc_path: str) -> Dict:
        """获取处理状态"""
        try:
            progress = self.db_manager.get_document_progress(doc_path)
            doc_info = progress.get('doc_info', {})
            processed_pages = progress.get('processed_pages', [])
            total_vectors = progress.get('total_vectors', 0)
            
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
                'status': 'in_progress' if len(processed_pages) < total_pages else 'completed',
                'total_pages': total_pages,
                'processed_pages': len(processed_pages),
                'last_processed_page': max(processed_pages) if processed_pages else 0,
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