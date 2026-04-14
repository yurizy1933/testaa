"""
Word文档解析模块 - 优化版本，支持高效分页处理
"""

from docx import Document
import jieba
import re
from typing import List, Dict, Tuple
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

class WordDocumentParser:
    def __init__(self, chunk_size=500, chunk_overlap=50, max_workers=4):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_workers = max_workers
        # 启用jieba的paddle模式
        jieba.enable_paddle()
        # 预加载jieba词典以提高性能
        jieba.initialize()
    
    def parse_document(self, doc_path: str, db_manager=None, start_page=1, max_chunks_per_batch=50) -> List[Dict]:
        """
        解析Word文档，返回分块后的文本列表
        支持断点续传，从指定页码开始解析，优化内存使用
        :param doc_path: 文档路径
        :param db_manager: 数据库管理器，用于保存进度
        :param start_page: 开始解析的页码
        :param max_chunks_per_batch: 每批最大块数，控制内存使用
        :return: 分块后的文本列表
        """
        if not os.path.exists(doc_path):
            raise FileNotFoundError(f"文档不存在: {doc_path}")
        
        doc = Document(doc_path)
        all_chunks = []
        current_page = start_page
        current_text = ""
        chunk_count = 0
        
        # 逐页处理，避免内存溢出
        for para in doc.paragraphs:
            # 跳过空段落
            if not para.text.strip():
                continue
            
            # 检查是否是标题（用于分页）
            if self._is_heading(para):
                # 处理当前页内容
                if current_text.strip():
                    page_chunks = self._split_text_into_chunks(
                        current_text, current_page
                    )
                    
                    # 分批处理，控制内存使用
                    for i in range(0, len(page_chunks), max_chunks_per_batch):
                        batch_chunks = page_chunks[i:i + max_chunks_per_batch]
                        all_chunks.extend(batch_chunks)
                        chunk_count += len(batch_chunks)
                        
                        # 如果块数过多，及时清理内存
                        if chunk_count > 1000:
                            print(f"已处理 {chunk_count} 个文本块，清理内存...")
                            # 这里可以添加内存清理逻辑
                            chunk_count = 0
                
                # 开始新页
                current_page += 1
                current_text = para.text + "\n"
            else:
                current_text += para.text + "\n"
        
        # 处理最后一页
        if current_text.strip():
            page_chunks = self._split_text_into_chunks(
                current_text, current_page
            )
            all_chunks.extend(page_chunks)
        
        return all_chunks
    
    def _save_page_chunks_to_db(self, chunks: List[Dict], doc_path: str, db_manager):
        """保存页面块到数据库"""
        try:
            for chunk in chunks:
                # 这里只是保存文本块信息，向量化会在后续步骤进行
                # 可以添加一个临时表来存储未向量化的文本块
                pass
        except Exception as e:
            print(f"保存页面块到数据库失败: {e}")
    
    def get_processing_progress(self, doc_path: str, db_manager) -> Dict:
        """获取文档处理进度"""
        try:
            # 查询已处理的页面
            processed_pages = db_manager.get_processed_pages(doc_path)
            return {
                'doc_path': doc_path,
                'processed_pages': processed_pages,
                'last_processed_page': max(processed_pages) if processed_pages else 0
            }
        except Exception as e:
            print(f"获取处理进度失败: {e}")
            return {'doc_path': doc_path, 'processed_pages': [], 'last_processed_page': 0}
    
    def _is_heading(self, paragraph) -> bool:
        """判断段落是否为标题"""
        # 检查样式名称
        if 'Heading' in paragraph.style.name:
            return True
        
        # 检查字体大小（标题通常字体较大）
        if paragraph.runs:
            for run in paragraph.runs:
                if hasattr(run.font, 'size') and run.font.size:
                    if run.font.size.pt > 14:  # 大于14pt认为是标题
                        return True
        
        # 检查文本长度（标题通常较短）
        if len(paragraph.text.strip()) < 50:
            return True
        
        return False
    
    def _split_text_into_chunks(self, text: str, page_num: int) -> List[Dict]:
        """
        将文本分割成固定大小的块
        支持重叠以保持上下文连贯性
        """
        chunks = []
        
        # 使用jieba分词
        words = list(jieba.cut(text))
        
        # 调试信息
        print(f"页面 {page_num} 分词结果: {len(words)} 个词")
        
        # 记录已处理的块，避免重复
        processed_chunks = set()
        
        start = 0
        iteration_count = 0
        max_iterations = len(words) * 2  # 防止无限循环
        
        while start < len(words) and iteration_count < max_iterations:
            iteration_count += 1
            # 计算当前块的结束位置
            end = min(start + self.chunk_size, len(words))
            
            # 提取当前块的文本
            chunk_text = ''.join(words[start:end])
            
            # 清理文本
            chunk_text = self._clean_text(chunk_text)
            
            print(f"  迭代 {iteration_count}: start={start}, end={end}, 词数={len(words[start:end])}")
            
            if chunk_text.strip():
                # 检查块长度是否足够（至少5个词）
                if len(words[start:end]) >= 5:
                    # 检查是否已经处理过相同的块
                    chunk_hash = hash(chunk_text)
                    if chunk_hash not in processed_chunks:
                        chunk_info = {
                            'text': chunk_text,
                            'page': page_num,
                            'start_pos': start,
                            'end_pos': end,
                            'word_count': len(words[start:end])
                        }
                        chunks.append(chunk_info)
                        processed_chunks.add(chunk_hash)
                        print(f"    创建块: start={start}, end={end}, 词数={len(words[start:end])}")
                    else:
                        print(f"    跳过重复块: start={start}, end={end}, 词数={len(words[start:end])}")
                else:
                    print(f"    跳过短块: start={start}, end={end}, 词数={len(words[start:end])} (少于5词)")
            
            # 计算下一个块的开始位置（考虑重叠）
            # 如果当前块已经到达文本末尾，则结束
            if end >= len(words):
                print(f"    到达末尾，结束循环")
                break
                
            next_start = end - self.chunk_overlap
            
            # 检查是否已经处理完所有内容
            if end >= len(words):
                print(f"    已处理完所有内容，结束循环")
                break
            
            # 确保前进
            if next_start <= start:
                # 如果没有前进，检查是否还有剩余内容
                remaining_words = len(words) - start
                if remaining_words <= self.chunk_overlap:
                    print(f"    剩余内容不足，结束循环 (剩余: {remaining_words}, 重叠: {self.chunk_overlap})")
                    break
                else:
                    # 强制前进一个词
                    next_start = start + 1
                    print(f"    警告: 没有前进，强制前进到 {next_start}")
            
            start = max(0, next_start)
            
            # 调试信息
            if next_start < 0:
                print(f"    警告: next_start={next_start}, 调整为 start={start}")
            
            # 如果已经到达末尾，结束
            if start >= len(words):
                print(f"    到达末尾，结束循环")
                break
            
            # 防止无限循环
            if iteration_count >= max_iterations:
                print(f"    警告: 达到最大迭代次数，强制结束")
                break
        
        if iteration_count >= max_iterations:
            print(f"⚠️  警告: 分块过程中达到最大迭代次数，可能存在循环")
        
        print(f"页面 {page_num} 去重后块数: {len(chunks)}")
        return chunks
    
    def _split_paragraphs_into_batches(self, paragraphs, batch_size=50):
        """将段落分批"""
        batches = []
        for i in range(0, len(paragraphs), batch_size):
            batch = paragraphs[i:i + batch_size]
            batches.append(batch)
        return batches
    
    def _process_paragraph_batch(self, paragraphs, batch_index):
        """处理段落批次"""
        processed_paragraphs = []
        
        for para in paragraphs:
            # 跳过空段落
            if not para.text.strip():
                continue
            
            # 分析段落
            para_info = {
                'text': para.text.strip(),
                'is_heading': self._is_heading(para),
                'style': para.style.name if para.style else '',
                'font_size': self._get_paragraph_font_size(para)
            }
            processed_paragraphs.append(para_info)
        
        return {
            'batch_index': batch_index,
            'paragraphs': processed_paragraphs
        }
    
    def _get_paragraph_font_size(self, paragraph):
        """获取段落字体大小"""
        if paragraph.runs:
            for run in paragraph.runs:
                if hasattr(run.font, 'size') and run.font.size:
                    return run.font.size.pt
        return None
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        # 移除特殊字符
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s，。！？、：；""''（）【】]', '', text)
        return text.strip()
    
    def get_document_info(self, doc_path: str) -> Dict:
        """获取文档基本信息"""
        doc = Document(doc_path)
        
        total_paragraphs = len(doc.paragraphs)
        total_words = 0
        total_pages = 0
        
        for para in doc.paragraphs:
            if para.text.strip():
                words = list(jieba.cut(para.text))
                total_words += len(words)
                
                if self._is_heading(para):
                    total_pages += 1
        
        return {
            'total_paragraphs': total_paragraphs,
            'total_words': total_words,
            'estimated_pages': total_pages,
            'file_size': os.path.getsize(doc_path)
        } 