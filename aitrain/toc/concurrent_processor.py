#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
并发处理器 - 使用多线程提高文档解析和总结效率
"""

import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import logging

class ConcurrentProcessor:
    def __init__(self, max_workers=4):
        """
        初始化并发处理器
        
        Args:
            max_workers: 最大工作线程数
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.lock = threading.Lock()
        self.results_queue = queue.Queue()
        
        # 设置日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        print(f"并发处理器初始化完成，最大工作线程数: {max_workers}")
    
    def process_content_blocks_concurrent(self, content_blocks, process_func, *args, **kwargs):
        """
        并发处理内容块
        
        Args:
            content_blocks: 内容块列表
            process_func: 处理函数
            *args, **kwargs: 传递给处理函数的参数
        
        Returns:
            处理结果列表，保持原始顺序
        """
        if not content_blocks:
            return []
        
        print(f"开始并发处理 {len(content_blocks)} 个内容块")
        
        # 创建任务列表
        futures = []
        for i, block in enumerate(content_blocks):
            future = self.executor.submit(
                self._process_single_block,
                i, block, process_func, *args, **kwargs
            )
            futures.append(future)
        
        # 收集结果
        results = [None] * len(content_blocks)
        completed_count = 0
        
        for future in as_completed(futures):
            try:
                index, result = future.result()
                results[index] = result
                completed_count += 1
                
                if completed_count % 10 == 0:  # 每处理10个块输出一次进度
                    print(f"已处理 {completed_count}/{len(content_blocks)} 个内容块")
                    
            except Exception as e:
                self.logger.error(f"处理内容块时发生错误: {e}")
                import traceback
                self.logger.error(f"详细错误: {traceback.format_exc()}")
        
        print(f"并发处理完成，共处理 {completed_count} 个内容块")
        return results
    
    def _process_single_block(self, index, block, process_func, *args, **kwargs):
        """
        处理单个内容块（线程安全）
        
        Args:
            index: 块索引
            block: 内容块
            process_func: 处理函数
            *args, **kwargs: 传递给处理函数的参数
        
        Returns:
            (index, result) 元组
        """
        try:
            with self.lock:
                print(f"线程 {threading.current_thread().name} 开始处理第 {index + 1} 个内容块")
            
            # 调用处理函数
            result = process_func(block, *args, **kwargs)
            
            with self.lock:
                print(f"线程 {threading.current_thread().name} 完成处理第 {index + 1} 个内容块")
            
            return (index, result)
            
        except Exception as e:
            with self.lock:
                self.logger.error(f"处理第 {index + 1} 个内容块时发生错误: {e}")
            return (index, None)
    
    def process_pages_concurrent(self, pages, process_func, *args, **kwargs):
        """
        并发处理页面
        
        Args:
            pages: 页面列表
            process_func: 处理函数
            *args, **kwargs: 传递给处理函数的参数
        
        Returns:
            处理结果列表
        """
        if not pages:
            return []
        
        print(f"开始并发处理 {len(pages)} 个页面")
        
        futures = []
        for i, page in enumerate(pages):
            future = self.executor.submit(
                self._process_single_page,
                i, page, process_func, *args, **kwargs
            )
            futures.append(future)
        
        results = []
        completed_count = 0
        
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
                completed_count += 1
                
                print(f"已处理 {completed_count}/{len(pages)} 个页面")
                
            except Exception as e:
                self.logger.error(f"处理页面时发生错误: {e}")
                import traceback
                self.logger.error(f"详细错误: {traceback.format_exc()}")
        
        print(f"页面并发处理完成，共处理 {completed_count} 个页面")
        return results
    
    def process_sections_concurrent(self, sections, process_func, *args, **kwargs):
        """
        并发处理章节
        
        Args:
            sections: 章节列表
            process_func: 处理函数
            *args, **kwargs: 传递给处理函数的参数
        
        Returns:
            处理结果列表
        """
        if not sections:
            return []
        
        print(f"开始并发处理 {len(sections)} 个章节")
        
        futures = []
        for i, section in enumerate(sections):
            future = self.executor.submit(
                self._process_single_section,
                i, section, process_func, *args, **kwargs
            )
            futures.append(future)
        
        results = []
        completed_count = 0
        
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
                completed_count += 1
                
                print(f"已处理 {completed_count}/{len(sections)} 个章节")
                
            except Exception as e:
                self.logger.error(f"处理章节时发生错误: {e}")
                import traceback
                self.logger.error(f"详细错误: {traceback.format_exc()}")
        
        print(f"章节并发处理完成，共处理 {completed_count} 个章节")
        return results
    
    def process_images_concurrent(self, image_data_list, process_func, *args, **kwargs):
        """
        并发处理图片识别
        
        Args:
            image_data_list: 图片数据列表 [(rel_id, image_data), ...]
            process_func: 处理函数
            *args, **kwargs: 传递给处理函数的参数
        
        Returns:
            处理结果列表 [(rel_id, image_text), ...]
        """
        if not image_data_list:
            return []
        
        print(f"开始并发处理 {len(image_data_list)} 个图片")
        
        futures = []
        for i, image_data_tuple in enumerate(image_data_list):
            future = self.executor.submit(
                self._process_single_image,
                i, image_data_tuple, process_func, *args, **kwargs
            )
            futures.append(future)
        
        results = []
        completed_count = 0
        
        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    results.append(result)
                completed_count += 1
                
                print(f"已处理 {completed_count}/{len(image_data_list)} 个图片")
                
            except Exception as e:
                self.logger.error(f"处理图片时发生错误: {e}")
                import traceback
                self.logger.error(f"详细错误: {traceback.format_exc()}")
        
        print(f"图片并发处理完成，共处理 {completed_count} 个图片")
        return results
    
    def _process_single_page(self, index, page, process_func, *args, **kwargs):
        """
        处理单个页面（线程安全）
        
        Args:
            index: 页面索引
            page: 页面内容
            process_func: 处理函数
            *args, **kwargs: 传递给处理函数的参数
        
        Returns:
            处理结果
        """
        try:
            with self.lock:
                print(f"线程 {threading.current_thread().name} 开始处理第 {index + 1} 页")
            
            # 调用处理函数
            result = process_func(page, *args, **kwargs)
            
            with self.lock:
                print(f"线程 {threading.current_thread().name} 完成处理第 {index + 1} 页")
            
            return result
            
        except Exception as e:
            with self.lock:
                self.logger.error(f"处理第 {index + 1} 页时发生错误: {e}")
            return None
    
    def _process_single_section(self, index, section, process_func, *args, **kwargs):
        """
        处理单个章节（线程安全）
        
        Args:
            index: 章节索引
            section: 章节内容
            process_func: 处理函数
            *args, **kwargs: 传递给处理函数的参数
        
        Returns:
            处理结果
        """
        try:
            section_title = section.get('section_title', section.get('title', '未知章节'))
            with self.lock:
                print(f"线程 {threading.current_thread().name} 开始处理第 {index + 1} 个章节: {section_title}")
            
            # 调用处理函数
            result = process_func(section, *args, **kwargs)
            
            with self.lock:
                print(f"线程 {threading.current_thread().name} 完成处理第 {index + 1} 个章节: {section_title}")
            
            return result
            
        except Exception as e:
            with self.lock:
                self.logger.error(f"处理第 {index + 1} 个章节时发生错误: {e}")
            return None
    
    def _process_single_image(self, index, image_data_tuple, process_func, *args, **kwargs):
        """
        处理单个图片（线程安全）
        
        Args:
            index: 图片索引
            image_data_tuple: 图片数据元组 (rel_id, image_data)
            process_func: 处理函数
            *args, **kwargs: 传递给处理函数的参数
        
        Returns:
            处理结果 (rel_id, image_text)
        """
        try:
            rel_id, image_data = image_data_tuple
            with self.lock:
                print(f"线程 {threading.current_thread().name} 开始处理第 {index + 1} 个图片: {rel_id}")
            
            # 调用处理函数
            result = process_func(image_data_tuple, *args, **kwargs)
            
            with self.lock:
                print(f"线程 {threading.current_thread().name} 完成处理第 {index + 1} 个图片: {rel_id}")
            
            return result
            
        except Exception as e:
            with self.lock:
                self.logger.error(f"处理第 {index + 1} 个图片时发生错误: {e}")
            return None
    
    def shutdown(self):
        """关闭线程池"""
        self.executor.shutdown(wait=True)
        print("并发处理器已关闭") 