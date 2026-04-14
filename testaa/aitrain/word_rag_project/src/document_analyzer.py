"""
文档分析器模块 - 解析文档图片、提炼内容并存储向量
"""

import os
import time
import hashlib
from typing import List, Dict, Tuple, Optional
from docx import Document
from docx.document import Document as DocumentType
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph
import jieba
import numpy as np
from PIL import Image
import io
import base64

from .ai_client import AIClient
from .database_manager import DatabaseManager
from .vector_manager import VectorManager
from .config import ConfigManager

class DocumentAnalyzer:
    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化文档分析器
        :param config_path: 配置文件路径
        """
        # 加载配置
        self.config = ConfigManager(config_path)
        
        # 初始化数据库管理器
        db_config = self.config.get_database_config()
        self.db_manager = DatabaseManager(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )
        
        # 初始化AI客户端
        zhipuai_config = self.config.get_zhipuai_config()
        self.ai_client = AIClient(
            api_key=zhipuai_config['api_key'],
            embedding_model=zhipuai_config['embedding_model'],
            chat_model=zhipuai_config['chat_model'],
            max_threads=self.config.get('MAX_THREADS', 5),
            request_interval=self.config.get('REQUEST_INTERVAL', 0.5)
        )
        
        # 初始化向量管理器
        self.vector_manager = VectorManager(
            vector_dimension=self.config.get('VECTOR_DIMENSION', 1024),
            faiss_path=self.config.get('FAISS_DB_PATH', 'document_vectors.faiss'),
            db_manager=self.db_manager
        )
        
        # 启用jieba
        jieba.enable_paddle()
        jieba.initialize()
    
    def analyze_document(self, doc_path: str) -> Dict:
        """
        分析文档：解析图片、提炼内容、存储向量
        :param doc_path: 文档路径
        :return: 分析结果
        """
        print(f"开始分析文档: {doc_path}")
        
        if not os.path.exists(doc_path):
            return {'error': f'文档不存在: {doc_path}'}
        
        try:
            # 1. 解析文档结构和图片
            doc_structure = self._parse_document_structure(doc_path)
            
            # 2. 按页存储到数据库
            page_results = self._store_pages_to_db(doc_path, doc_structure)
            
            # 3. 提炼和总结文档信息
            summary_points = self._extract_summary_points(doc_structure)
            
            # 4. 生成向量并存储
            vector_results = self._store_vectors_to_faiss(doc_path, summary_points)
            
            # 5. 保存到MySQL
            mysql_results = self._store_to_mysql(doc_path, summary_points, vector_results)
            
            return {
                'doc_path': doc_path,
                'total_pages': len(doc_structure['pages']),
                'total_images': doc_structure['total_images'],
                'summary_points': len(summary_points),
                'vector_count': len(vector_results),
                'mysql_success': mysql_results,
                'page_results': page_results,
                'vector_results': vector_results
            }
            
        except Exception as e:
            print(f"文档分析失败: {e}")
            return {'error': str(e)}
    
    def _parse_document_structure(self, doc_path: str) -> Dict:
        """
        解析文档结构，包括文本、图片、表格等
        :param doc_path: 文档路径
        :return: 文档结构信息
        """
        print(f"解析文档结构: {doc_path}")
        
        doc = Document(doc_path)
        pages = []
        total_images = 0
        current_page = 1
        current_page_content = {
            'page_num': current_page,
            'text_content': '',
            'images': [],
            'tables': [],
            'paragraphs': []
        }
        
        # 遍历所有段落
        for paragraph in doc.paragraphs:
            text = paragraph.text.strip()
            if text:
                current_page_content['text_content'] += text + '\n'
                current_page_content['paragraphs'].append({
                    'text': text,
                    'style': paragraph.style.name if paragraph.style else '',
                    'runs': len(paragraph.runs)
                })
                
                # 检查段落中的图片
                for run in paragraph.runs:
                    if run._element.findall('.//pic:pic', {'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture'}):
                        total_images += 1
                        current_page_content['images'].append({
                            'type': 'inline',
                            'description': f'段落中的图片 {total_images}'
                        })
        
        # 遍历所有表格
        for table in doc.tables:
            table_data = []
            for row in table.rows:
                row_data = []
                for cell in row.cells:
                    row_data.append(cell.text.strip())
                table_data.append(row_data)
            
            current_page_content['tables'].append({
                'rows': len(table_data),
                'cols': len(table_data[0]) if table_data else 0,
                'data': table_data
            })
            
            # 检查表格中的图片
            for row in table.rows:
                for cell in row.cells:
                    if cell._element.findall('.//pic:pic', {'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture'}):
                        total_images += 1
                        current_page_content['images'].append({
                            'type': 'table',
                            'description': f'表格中的图片 {total_images}'
                        })
        
        # 检查是否需要分页
        if self._should_start_new_page(current_page_content):
            # 将当前页内容添加到页面列表
            if current_page_content['text_content'] or current_page_content['images'] or current_page_content['tables']:
                pages.append(current_page_content)
                current_page += 1
                current_page_content = {
                    'page_num': current_page,
                    'text_content': '',
                    'images': [],
                    'tables': [],
                    'paragraphs': []
                }
        
        # 添加最后一页
        if current_page_content['text_content'] or current_page_content['images'] or current_page_content['tables']:
            pages.append(current_page_content)
        
        # 如果没有页面，创建一个默认页面
        if not pages:
            pages.append(current_page_content)
        
        print(f"解析完成: {len(pages)} 页, {total_images} 张图片")
        print(f"总文本长度: {sum(len(page['text_content']) for page in pages)} 字符")
        
        return {
            'pages': pages,
            'total_images': total_images,
            'total_pages': len(pages)
        }
    
    def _should_start_new_page(self, page_content: Dict) -> bool:
        """
        判断是否应该开始新页
        :param page_content: 页面内容
        :return: 是否开始新页
        """
        # 基于内容长度判断
        text_length = len(page_content['text_content'])
        if text_length > 2000:  # 超过2000字符开始新页
            return True
        
        # 基于段落数量判断
        if len(page_content['paragraphs']) > 10:  # 超过10个段落开始新页
            return True
        
        # 基于图片数量判断
        if len(page_content['images']) > 3:  # 超过3张图片开始新页
            return True
        
        return False
    
    def _store_pages_to_db(self, doc_path: str, doc_structure: Dict) -> Dict:
        """
        将页面信息存储到数据库
        :param doc_path: 文档路径
        :param doc_structure: 文档结构
        :return: 存储结果
        """
        print(f"存储页面信息到数据库")
        
        try:
            doc_name = os.path.basename(doc_path)
            total_pages = doc_structure['total_pages']
            total_images = doc_structure['total_images']
            
            # 保存文档基本信息
            doc_name = os.path.basename(doc_path)
            total_pages = doc_structure['total_pages']
            total_images = doc_structure['total_images']
            file_size = os.path.getsize(doc_path)
            
            # 计算总词数
            total_words = 0
            for page in doc_structure['pages']:
                if page['text_content']:
                    words = list(jieba.cut(page['text_content']))
                    total_words += len(words)
            
            self.db_manager.save_document_info(doc_path, doc_name, total_pages, total_words, file_size)
            
            # 保存每页信息
            for page in doc_structure['pages']:
                page_info = {
                    'doc_path': doc_path,
                    'page_num': page['page_num'],
                    'text_content': page['text_content'],
                    'image_count': len(page['images']),
                    'table_count': len(page['tables']),
                    'paragraph_count': len(page['paragraphs']),
                    'processed_time': time.time()
                }
                
                # 保存页面信息到数据库
                self.db_manager.save_page_info(page_info)
            
            return {
                'success': True,
                'total_pages': total_pages,
                'total_images': total_images
            }
            
        except Exception as e:
            print(f"存储页面信息失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _extract_summary_points(self, doc_structure: Dict) -> List[Dict]:
        """
        提炼和总结文档信息，拆分成独立的点
        :param doc_structure: 文档结构
        :return: 总结点列表
        """
        print(f"提炼文档信息点")
        
        summary_points = []
        
        for page in doc_structure['pages']:
            print(f"处理第 {page['page_num']} 页:")
            print(f"  文本长度: {len(page['text_content'])} 字符")
            print(f"  段落数: {len(page['paragraphs'])}")
            print(f"  表格数: {len(page['tables'])}")
            print(f"  图片数: {len(page['images'])}")
            
            # 处理文本内容
            if page['text_content']:
                points = self._extract_text_points(page['text_content'], page['page_num'])
                print(f"  提取文本信息点: {len(points)} 个")
                summary_points.extend(points)
            
            # 处理表格内容
            for table in page['tables']:
                points = self._extract_table_points(table, page['page_num'])
                print(f"  提取表格信息点: {len(points)} 个")
                summary_points.extend(points)
            
            # 处理图片信息
            for image in page['images']:
                points = self._extract_image_points(image, page['page_num'])
                print(f"  提取图片信息点: {len(points)} 个")
                summary_points.extend(points)
        
        # 使用AI进行进一步总结
        if summary_points:
            ai_summary_points = self._ai_summarize_points(summary_points)
            summary_points.extend(ai_summary_points)
        
        print(f"提炼完成: {len(summary_points)} 个信息点")
        return summary_points
    
    def _extract_text_points(self, text: str, page_num: int) -> List[Dict]:
        """
        从文本中提取信息点
        :param text: 文本内容
        :param page_num: 页码
        :return: 信息点列表
        """
        points = []
        
        # 分句
        sentences = text.split('。')
        print(f"    文本分句: {len(sentences)} 个句子")
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # 过滤短句
                # 使用jieba分词
                words = list(jieba.cut(sentence))
                
                # 提取关键信息
                point = {
                    'type': 'text',
                    'content': sentence,
                    'page_num': page_num,
                    'word_count': len(words),
                    'key_words': self._extract_keywords(sentence),
                    'hash': hashlib.md5(sentence.encode()).hexdigest()
                }
                points.append(point)
                print(f"      提取句子: {sentence[:30]}... (词数: {len(words)})")
            else:
                print(f"      跳过短句: {sentence[:30]}... (长度: {len(sentence)})")
        
        return points
    
    def _extract_table_points(self, table: Dict, page_num: int) -> List[Dict]:
        """
        从表格中提取信息点
        :param table: 表格数据
        :param page_num: 页码
        :return: 信息点列表
        """
        points = []
        
        if not table['data']:
            return points
        
        # 提取表格标题（第一行）
        if table['data']:
            header = ' '.join(table['data'][0])
            point = {
                'type': 'table_header',
                'content': f"表格标题: {header}",
                'page_num': page_num,
                'table_rows': table['rows'],
                'table_cols': table['cols'],
                'hash': hashlib.md5(header.encode()).hexdigest()
            }
            points.append(point)
        
        # 提取表格数据点
        for i, row in enumerate(table['data'][1:], 1):
            row_text = ' '.join(row)
            if row_text.strip():
                point = {
                    'type': 'table_data',
                    'content': f"表格数据行{i}: {row_text}",
                    'page_num': page_num,
                    'row_index': i,
                    'hash': hashlib.md5(row_text.encode()).hexdigest()
                }
                points.append(point)
        
        return points
    
    def _extract_image_points(self, image: Dict, page_num: int) -> List[Dict]:
        """
        从图片信息中提取信息点
        :param image: 图片信息
        :param page_num: 页码
        :return: 信息点列表
        """
        points = []
        
        point = {
            'type': 'image',
            'content': f"图片: {image['description']}",
            'page_num': page_num,
            'image_type': image['type'],
            'hash': hashlib.md5(image['description'].encode()).hexdigest()
        }
        points.append(point)
        
        return points
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        提取文本关键词
        :param text: 文本
        :return: 关键词列表
        """
        # 使用jieba提取关键词
        words = jieba.cut(text)
        keywords = [word for word in words if len(word) > 1]  # 过滤单字词
        return keywords[:5]  # 返回前5个关键词
    
    def _ai_summarize_points(self, points: List[Dict]) -> List[Dict]:
        """
        使用AI对信息点进行进一步总结
        :param points: 信息点列表
        :return: AI总结的信息点
        """
        ai_points = []
        
        # 按类型分组
        text_points = [p for p in points if p['type'] == 'text']
        table_points = [p for p in points if p['type'] in ['table_header', 'table_data']]
        image_points = [p for p in points if p['type'] == 'image']
        
        # 总结文本信息点
        if text_points:
            text_summary = self._summarize_text_points(text_points)
            if text_summary:
                ai_points.append({
                    'type': 'ai_summary',
                    'content': f"文本总结: {text_summary}",
                    'page_num': 0,
                    'hash': hashlib.md5(text_summary.encode()).hexdigest()
                })
        
        # 总结表格信息点
        if table_points:
            table_summary = self._summarize_table_points(table_points)
            if table_summary:
                ai_points.append({
                    'type': 'ai_summary',
                    'content': f"表格总结: {table_summary}",
                    'page_num': 0,
                    'hash': hashlib.md5(table_summary.encode()).hexdigest()
                })
        
        return ai_points
    
    def _summarize_text_points(self, text_points: List[Dict]) -> str:
        """
        总结文本信息点
        :param text_points: 文本信息点
        :return: 总结文本
        """
        try:
            # 合并所有文本内容
            all_text = '。'.join([point['content'] for point in text_points])
            
            # 使用AI总结
            success, summary = self.ai_client.summarize_text(all_text, max_length=200)
            
            if success and summary:
                return summary
            else:
                return "文档包含重要文本信息"
                
        except Exception as e:
            print(f"AI总结文本失败: {e}")
            return "文档包含重要文本信息"
    
    def _summarize_table_points(self, table_points: List[Dict]) -> str:
        """
        总结表格信息点
        :param table_points: 表格信息点
        :return: 总结文本
        """
        try:
            # 统计表格信息
            table_count = len([p for p in table_points if p['type'] == 'table_header'])
            data_rows = len([p for p in table_points if p['type'] == 'table_data'])
            
            return f"文档包含{table_count}个表格，共{data_rows}行数据"
            
        except Exception as e:
            print(f"总结表格信息失败: {e}")
            return "文档包含表格数据"
    
    def _store_vectors_to_faiss(self, doc_path: str, summary_points: List[Dict]) -> List[Dict]:
        """
        将信息点存储到FAISS向量数据库
        :param doc_path: 文档路径
        :param summary_points: 信息点列表
        :return: 向量存储结果
        """
        print(f"存储向量到FAISS数据库")
        
        vector_results = []
        
        for i, point in enumerate(summary_points):
            try:
                # 生成向量
                success, vector = self.ai_client.get_embedding(point['content'])
                
                if success and vector is not None:
                    # 准备元数据
                    metadata = {
                        'text': point['content'],
                        'doc_path': doc_path,
                        'doc_name': os.path.basename(doc_path),
                        'point_type': point['type'],
                        'page_num': point['page_num'],
                        'word_count': point.get('word_count', 0),
                        'key_words': point.get('key_words', [])
                    }
                    
                    # 保存到FAISS
                    vector_ids = self.vector_manager.add_vectors([vector], [metadata])
                    vector_id = vector_ids[0] if vector_ids else None
                    
                    vector_results.append({
                        'success': True,
                        'vector_id': vector_id,
                        'point_index': i,
                        'content': point['content'],
                        'type': point['type']
                    })
                    
                    print(f"✅ 向量 {i+1}/{len(summary_points)}: 成功存储")
                else:
                    vector_results.append({
                        'success': False,
                        'point_index': i,
                        'content': point['content'],
                        'error': '向量生成失败'
                    })
                    print(f"❌ 向量 {i+1}/{len(summary_points)}: 生成失败")
                    
            except Exception as e:
                vector_results.append({
                    'success': False,
                    'point_index': i,
                    'content': point['content'],
                    'error': str(e)
                })
                print(f"❌ 向量 {i+1}/{len(summary_points)}: 处理异常 - {e}")
        
        return vector_results
    
    def _store_to_mysql(self, doc_path: str, summary_points: List[Dict], vector_results: List[Dict]) -> bool:
        """
        将信息点存储到MySQL数据库
        :param doc_path: 文档路径
        :param summary_points: 信息点列表
        :param vector_results: 向量结果
        :return: 存储是否成功
        """
        print(f"存储信息点到MySQL数据库")
        
        try:
            # 保存文档分析结果
            analysis_info = {
                'doc_path': doc_path,
                'doc_name': os.path.basename(doc_path),
                'total_points': len(summary_points),
                'success_vectors': len([r for r in vector_results if r['success']]),
                'fail_vectors': len([r for r in vector_results if not r['success']]),
                'processed_time': time.time()
            }
            
            # 保存分析结果到数据库
            self.db_manager.save_analysis_info(analysis_info)
            
            # 保存每个信息点
            for i, (point, vector_result) in enumerate(zip(summary_points, vector_results)):
                point_info = {
                    'doc_path': doc_path,
                    'point_index': i,
                    'point_type': point['type'],
                    'content': point['content'],
                    'page_num': point['page_num'],
                    'hash': point['hash'],
                    'vector_success': vector_result['success'],
                    'vector_id': vector_result.get('vector_id'),
                    'processed_time': time.time()
                }
                
                # 保存信息点到数据库
                self.db_manager.save_point_info(point_info)
            
            print(f"✅ MySQL存储完成")
            return True
            
        except Exception as e:
            print(f"❌ MySQL存储失败: {e}")
            return False
    
    def search_similar_points(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        搜索相似的信息点
        :param query: 查询文本
        :param top_k: 返回结果数量
        :return: 相似信息点列表
        """
        try:
            # 获取查询向量
            success, query_vector = self.ai_client.get_embedding(query)
            if not success or query_vector is None:
                return []
            
            # 从FAISS搜索相似向量
            similar_results = self.vector_manager.search_similar(query_vector, top_k)
            
            return similar_results
            
        except Exception as e:
            print(f"搜索相似信息点失败: {e}")
            return [] 