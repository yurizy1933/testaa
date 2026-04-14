"""
文件截断模块
用于处理超过智谱AI限制的大文件
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Tuple
import tempfile

class FileTruncator:
    def __init__(self, max_size_mb: int = 45):
        """
        初始化文件截断器
        :param max_size_mb: 最大文件大小（MB），默认45MB，留5MB缓冲
        """
        self.max_size_bytes = max_size_mb * 1024 * 1024
    
    def truncate_large_file(self, file_path: str) -> Tuple[bool, str, List[str]]:
        """
        截断大文件
        :param file_path: 原文件路径
        :return: (成功标志, 错误信息, 截断后的文件路径列表)
        """
        try:
            if not os.path.exists(file_path):
                return False, f"文件不存在: {file_path}", []
            
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_path)[1]
            
            print(f"原文件: {file_name}, 大小: {file_size / (1024*1024):.2f} MB")
            
            # 如果文件小于限制，直接返回原文件
            if file_size <= self.max_size_bytes:
                print("文件大小在限制范围内，无需截断")
                return True, None, [file_path]
            
            # 计算需要分割的份数
            num_parts = (file_size + self.max_size_bytes - 1) // self.max_size_bytes
            print(f"文件过大，需要分割为 {num_parts} 个部分")
            
            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix="zhipu_truncate_")
            truncated_files = []
            
            # 分割文件
            with open(file_path, 'rb') as original_file:
                for part_num in range(num_parts):
                    # 生成新文件名
                    base_name = os.path.splitext(file_name)[0]
                    new_file_name = f"{base_name}_part{part_num + 1:03d}{file_ext}"
                    new_file_path = os.path.join(temp_dir, new_file_name)
                    
                    # 读取当前部分的数据
                    chunk_data = original_file.read(self.max_size_bytes)
                    if not chunk_data:
                        break
                    
                    # 写入新文件
                    with open(new_file_path, 'wb') as new_file:
                        new_file.write(chunk_data)
                    
                    truncated_files.append(new_file_path)
                    print(f"创建部分 {part_num + 1}: {new_file_name}, 大小: {len(chunk_data) / (1024*1024):.2f} MB")
            
            print(f"文件截断完成，共 {len(truncated_files)} 个部分")
            return True, None, truncated_files
            
        except Exception as e:
            error_msg = f"文件截断失败: {str(e)}"
            print(error_msg)
            return False, error_msg, []
    
    def cleanup_truncated_files(self, file_paths: List[str]):
        """
        清理截断后的临时文件
        :param file_paths: 文件路径列表
        """
        try:
            for file_path in file_paths:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"已删除临时文件: {file_path}")
            
            # 删除临时目录
            if file_paths:
                temp_dir = os.path.dirname(file_paths[0])
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    print(f"已删除临时目录: {temp_dir}")
                    
        except Exception as e:
            print(f"清理临时文件失败: {e}")
    
    def get_file_info(self, file_path: str) -> Dict:
        """
        获取文件信息
        :param file_path: 文件路径
        :return: 文件信息字典
        """
        if not os.path.exists(file_path):
            return {}
        
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_path)[1]
        
        return {
            'file_path': file_path,
            'file_name': file_name,
            'file_size': file_size,
            'file_size_mb': file_size / (1024 * 1024),
            'file_extension': file_ext,
            'needs_truncation': file_size > self.max_size_bytes,
            'estimated_parts': (file_size + self.max_size_bytes - 1) // self.max_size_bytes
        }
    
    def estimate_processing_time(self, file_size: int) -> Dict:
        """
        估算处理时间
        :param file_size: 文件大小（字节）
        :return: 估算信息
        """
        if file_size <= self.max_size_bytes:
            return {
                'needs_truncation': False,
                'estimated_time': '1-2分钟',
                'parts': 1
            }
        
        num_parts = (file_size + self.max_size_bytes - 1) // self.max_size_bytes
        estimated_time = f"{num_parts * 2}-{num_parts * 5}分钟"
        
        return {
            'needs_truncation': True,
            'estimated_time': estimated_time,
            'parts': num_parts
        } 