"""
智谱AI文件解析模块
使用智谱AI的文件解析功能来提取文档内容
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zhipuai import ZhipuAI
import json
from .file_truncator import FileTruncator

class ZhipuFileParser:
    def __init__(self, api_key: str, base_url: str = "https://open.bigmodel.cn/api/paas/v4"):
        """
        初始化智谱AI文件解析器
        :param api_key: 智谱AI API密钥
        :param base_url: API基础URL
        """
        self.client = ZhipuAI(
            api_key=api_key,
            base_url=base_url
        )
        self.supported_formats = ['.pdf', '.docx', '.doc', '.xls', '.xlsx', '.ppt', '.pptx']
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        
        # 初始化文件截断器
        self.file_truncator = FileTruncator(max_size_mb=45)  # 45MB，留5MB缓冲
    
    def parse_document(self, file_path: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        解析文档文件（支持大文件截断）
        :param file_path: 文件路径
        :return: (成功标志, 错误信息, 解析结果)
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return False, f"文件不存在: {file_path}", None
            
            # 检查文件格式
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext not in self.supported_formats:
                return False, f"不支持的文件格式: {file_ext}", None
            
            # 获取文件信息
            file_info = self.file_truncator.get_file_info(file_path)
            file_size = file_info['file_size']
            
            print(f"处理文件: {file_info['file_name']}, 大小: {file_info['file_size_mb']:.2f} MB")
            
            # 检查是否需要截断
            if file_info['needs_truncation']:
                print(f"文件过大，需要截断为 {file_info['estimated_parts']} 个部分")
                return self._parse_large_document(file_path)
            else:
                print("文件大小在限制范围内，直接处理")
                return self._parse_single_document(file_path)
            
        except Exception as e:
            error_msg = f"文件解析失败: {str(e)}"
            print(error_msg)
            return False, error_msg, None
    
    def _parse_single_document(self, file_path: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        解析单个文档文件
        :param file_path: 文件路径
        :return: (成功标志, 错误信息, 解析结果)
        """
        try:
            file_size = os.path.getsize(file_path)
            print(f"开始上传文件: {file_path}")
            
            # 上传文件
            file_object = self.client.files.create(
                file=Path(file_path), 
                purpose="file-extract"
            )
            
            print(f"文件上传成功，ID: {file_object.id}")
            
            # 等待文件处理完成
            max_wait_time = 300  # 最多等待5分钟
            wait_time = 0
            while wait_time < max_wait_time:
                try:
                    # 获取文件内容
                    file_content = self.client.files.content(file_id=file_object.id)
                    content = file_content.content.decode('utf-8')
                    
                    print(f"文件解析成功，内容长度: {len(content)} 字符")
                    
                    # 构建解析结果
                    result = {
                        'file_path': file_path,
                        'file_name': os.path.basename(file_path),
                        'file_size': file_size,
                        'file_id': file_object.id,
                        'content': content,
                        'content_length': len(content),
                        'parse_time': time.time(),
                        'is_truncated': False
                    }
                    
                    return True, None, result
                    
                except Exception as e:
                    if "not ready" in str(e).lower() or "processing" in str(e).lower():
                        print(f"文件正在处理中，等待... ({wait_time}s)")
                        time.sleep(10)
                        wait_time += 10
                    else:
                        raise e
            
            return False, "文件处理超时", None
            
        except Exception as e:
            error_msg = f"文件解析失败: {str(e)}"
            print(error_msg)
            return False, error_msg, None
    
    def _parse_large_document(self, file_path: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        解析大文档文件（需要截断）
        :param file_path: 文件路径
        :return: (成功标志, 错误信息, 解析结果)
        """
        try:
            # 截断文件
            success, error, truncated_files = self.file_truncator.truncate_large_file(file_path)
            if not success:
                return False, error, None
            
            print(f"文件截断完成，共 {len(truncated_files)} 个部分")
            
            # 解析所有部分
            all_content = []
            total_content_length = 0
            file_ids = []
            
            for i, part_file in enumerate(truncated_files):
                print(f"\n处理第 {i+1}/{len(truncated_files)} 部分: {os.path.basename(part_file)}")
                
                # 解析当前部分
                success, error, result = self._parse_single_document(part_file)
                if not success:
                    print(f"第 {i+1} 部分解析失败: {error}")
                    continue
                
                all_content.append(result['content'])
                total_content_length += result['content_length']
                file_ids.append(result['file_id'])
                
                print(f"第 {i+1} 部分解析成功，内容长度: {result['content_length']} 字符")
            
            # 清理临时文件
            self.file_truncator.cleanup_truncated_files(truncated_files)
            
            if not all_content:
                return False, "所有部分解析失败", None
            
            # 合并所有内容
            combined_content = "\n\n".join(all_content)
            
            # 构建最终结果
            final_result = {
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'file_size': os.path.getsize(file_path),
                'file_ids': file_ids,
                'content': combined_content,
                'content_length': len(combined_content),
                'parse_time': time.time(),
                'is_truncated': True,
                'parts_count': len(truncated_files),
                'successful_parts': len(all_content)
            }
            
            print(f"大文件解析完成，总内容长度: {len(combined_content)} 字符")
            return True, None, final_result
            
        except Exception as e:
            error_msg = f"大文件解析失败: {str(e)}"
            print(error_msg)
            return False, error_msg, None
    
    def parse_document_with_chunks(self, file_path: str, chunk_size: int = 1000, 
                                 chunk_overlap: int = 200) -> Tuple[bool, Optional[str], Optional[List[Dict]]]:
        """
        解析文档并分块
        :param file_path: 文件路径
        :param chunk_size: 块大小
        :param chunk_overlap: 块重叠
        :return: (成功标志, 错误信息, 分块结果)
        """
        success, error, result = self.parse_document(file_path)
        if not success:
            return False, error, None
        
        # 分块处理
        content = result['content']
        chunks = self._split_content_into_chunks(content, chunk_size, chunk_overlap)
        
        # 构建分块结果
        chunk_results = []
        for i, chunk in enumerate(chunks):
            chunk_result = {
                'text': chunk,
                'chunk_index': i,
                'start_pos': i * (chunk_size - chunk_overlap),
                'end_pos': i * (chunk_size - chunk_overlap) + len(chunk),
                'word_count': len(chunk),
                'file_path': file_path,
                'file_name': result['file_name'],
                'file_id': result['file_id']
            }
            chunk_results.append(chunk_result)
        
        print(f"文档分块完成，共 {len(chunk_results)} 个块")
        return True, None, chunk_results
    
    def _split_content_into_chunks(self, content: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """
        将内容分割成块
        :param content: 内容
        :param chunk_size: 块大小
        :param chunk_overlap: 块重叠
        :return: 分块列表
        """
        chunks = []
        start = 0
        
        # 确保重叠小于块大小
        if chunk_overlap >= chunk_size:
            chunk_overlap = chunk_size - 1
            print(f"警告: 重叠大小({chunk_overlap})大于等于块大小({chunk_size})，已调整为 {chunk_overlap}")
        
        # 记录已处理的块，避免重复
        processed_chunks = set()
        
        iteration_count = 0
        max_iterations = len(content) * 2  # 防止无限循环
        
        while start < len(content) and iteration_count < max_iterations:
            iteration_count += 1
            end = min(start + chunk_size, len(content))
            chunk = content[start:end]
            
            print(f"  迭代 {iteration_count}: start={start}, end={end}, 长度={len(chunk)}")
            
            if chunk.strip():
                # 检查块长度是否足够（至少10个字符）
                if len(chunk.strip()) >= 10:
                    # 检查是否已经处理过相同的块
                    chunk_hash = hash(chunk)
                    if chunk_hash not in processed_chunks:
                        chunks.append(chunk)
                        processed_chunks.add(chunk_hash)
                        print(f"    添加块: start={start}, end={end}, 长度={len(chunk)}")
                    else:
                        print(f"    跳过重复块: start={start}, end={end}, 长度={len(chunk)}")
                else:
                    print(f"    跳过短块: start={start}, end={end}, 长度={len(chunk)} (少于10字符)")
            
            # 计算下一个块的开始位置
            next_start = end - chunk_overlap
            
            # 检查是否已经处理完所有内容
            if end >= len(content):
                print(f"    已处理完所有内容，结束循环")
                break
            
            # 确保前进
            if next_start <= start:
                # 如果没有前进，检查是否还有剩余内容
                remaining_content = len(content) - start
                if remaining_content <= chunk_overlap:
                    print(f"    剩余内容不足，结束循环 (剩余: {remaining_content}, 重叠: {chunk_overlap})")
                    break
                else:
                    # 强制前进一个字符
                    next_start = start + 1
                    print(f"    强制前进: start={start} -> next_start={next_start}")
            
            start = next_start
            
            # 如果已经到达末尾，结束
            if start >= len(content):
                print(f"    到达末尾，结束循环")
                break
            
            # 防止无限循环
            if iteration_count >= max_iterations:
                print(f"    警告: 达到最大迭代次数，强制结束")
                break
        
        if iteration_count >= max_iterations:
            print(f"⚠️  警告: 分块过程中达到最大迭代次数，可能存在循环")
        
        print(f"去重后块数: {len(chunks)}")
        return chunks
    
    def get_file_info(self, file_path: str) -> Dict:
        """
        获取文件信息
        :param file_path: 文件路径
        :return: 文件信息
        """
        if not os.path.exists(file_path):
            return {}
        
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_path)[1].lower()
        
        return {
            'file_path': file_path,
            'file_name': file_name,
            'file_size': file_size,
            'file_extension': file_ext,
            'is_supported': file_ext in self.supported_formats,
            'is_within_size_limit': file_size <= self.max_file_size
        }
    
    def test_connection(self) -> bool:
        """
        测试API连接
        :return: 连接是否成功
        """
        try:
            # 尝试获取文件列表来测试连接
            files = self.client.files.list()
            print("智谱AI API连接成功")
            return True
        except Exception as e:
            print(f"智谱AI API连接失败: {e}")
            return False 