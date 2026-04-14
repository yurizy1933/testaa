from docx import Document
from docx.document import Document as _Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph
import os
import tempfile
from PIL import Image
import io
import threading
import re
import hashlib
from config import PAGE_SIZE
from concurrent_processor import ConcurrentProcessor

class WordParser:
    def __init__(self, zhipuai_client, use_concurrent=True, max_workers=4):
        self.zhipuai_client = zhipuai_client
        self.use_concurrent = use_concurrent
        self.concurrent_processor = ConcurrentProcessor(max_workers) if use_concurrent else None
        # 图片识别缓存
        self.image_cache = {}
        self.cache_lock = threading.Lock()
        print(f"Word解析器初始化成功，并发处理: {'启用' if use_concurrent else '禁用'}")
    
    def parse_document(self, file_path):
        """解析Word文档，按目录分割"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            print(f"开始解析文档: {file_path}")
            doc = Document(file_path)
            
            # 获取文件名（不含路径）
            file_name = os.path.basename(file_path)
            
            # 解析文档内容，按目录分割
            sections = self._extract_sections_by_toc(doc)
            
            print(f"文档解析完成，共 {len(sections)} 个目录章节")
            return file_name, sections
            
        except Exception as e:
            print(f"文档解析失败: {e}")
            raise
    
    def _is_english_title(self, text: str) -> bool:
        """判断标题是否主要为英文（无中文且字母/数字/标点占主）"""
        if not text:
            return False
        # 含中文直接判定为中文标题
        if re.search(r"[\u4e00-\u9fff]", text):
            return False
        # 含有字母或典型英文结构则认为是英文标题
        if re.search(r"[A-Za-z]", text):
            return True
        return False
    
    def _maybe_translate_title(self, text: str) -> str:
        """若为英文标题则调用智谱AI翻译为中文，失败则返回原文"""
        try:
            if self._is_english_title(text):
                print(f"检测到英文目录标题，准备翻译: {text}")
                translated = self.zhipuai_client.translate_to_chinese(text)
                if translated and translated != text:
                    print(f"标题翻译完成: {text} -> {translated}")
                    return translated
            return text
        except Exception as e:
            print(f"标题翻译过程异常，使用原文: {e}")
            return text
    
    def _extract_sections_by_toc(self, doc):
        """按目录分割文档内容"""
        sections = []
        current_section = None
        current_content = []
        
        # 获取所有图片位置信息（优化版本）
        image_positions = self._collect_image_positions_optimized(doc)
        
        element_index = 0
        for element in doc.element.body:
            # 检查当前位置是否有图片
            while element_index in image_positions:
                image_info = image_positions[element_index]
                if current_section:
                    current_content.append(image_info)
                element_index += 1
            
            if isinstance(element, CT_P):
                paragraph = Paragraph(element, doc)
                text = paragraph.text.strip()
                
                if text:
                    # 检查是否为目录标题
                    toc_level = self._is_toc_heading(paragraph)
                    
                    if toc_level > 0:
                        # 保存当前章节
                        if current_section and current_content:
                            current_section['content'] = current_content
                            sections.append(current_section)
                        
                        # 标题翻译（英文->中文）
                        title_text = self._maybe_translate_title(text)
                        
                        # 开始新章节
                        current_section = {
                            'title': title_text,
                            'level': toc_level,
                            'content': []
                        }
                        current_content = []
                    else:
                        # 普通段落内容
                        if current_section:
                            current_content.append({
                                'type': 'text',
                                'content': text,
                                'element': paragraph
                            })
                        else:
                            # 如果没有目录结构，创建默认章节
                            if not current_section:
                                current_section = {
                                    'title': '默认章节',
                                    'level': 1,
                                    'content': []
                                }
                            current_content.append({
                        'type': 'text',
                        'content': text,
                        'element': paragraph
                    })
                            
            elif isinstance(element, CT_Tbl):
                # 表格
                table = Table(element, doc)
                table_data = self._extract_table_data(table)
                table_text = self._format_table_as_text(table_data)
                
                if current_section:
                    current_content.append({
                        'type': 'table',
                        'content': table_text,
                        'element': table
                    })
                else:
                    # 如果没有目录结构，创建默认章节
                    if not current_section:
                        current_section = {
                            'title': '默认章节',
                            'level': 1,
                            'content': []
                        }
                    current_content.append({
                    'type': 'table',
                    'content': table_text,
                    'element': table
                })
            
            element_index += 1
        
        # 处理文档末尾的图片
        while element_index in image_positions:
            image_info = image_positions[element_index]
            if current_section:
                current_content.append(image_info)
            element_index += 1
        
        # 保存最后一个章节
        if current_section and current_content:
            current_section['content'] = current_content
            sections.append(current_section)
        
        return sections
    
    def _is_toc_heading(self, paragraph):
        """判断段落是否为目录标题，返回目录级别（1-5）"""
        text = paragraph.text.strip()
        if not text:
            return 0
        
        # 只检查段落样式是否为标题样式
        if hasattr(paragraph, 'style') and paragraph.style:
            style_name = paragraph.style.name.lower()
            
            # 检查是否为标题样式
            if 'heading' in style_name or '标题' in style_name:
                # 从样式名称中提取级别
                for i in range(1, 6):
                    if str(i) in style_name:
                        print(f"通过样式识别标题: '{text}' -> 级别 {i} (样式: {style_name})")
                        return i
                # 如果没有数字，默认为1级标题
                print(f"通过样式识别标题: '{text}' -> 级别 1 (样式: {style_name})")
                return 1
        
        return 0
    
    
    
    def _extract_table_data(self, table):
        """提取表格数据"""
        table_data = []
        for row in table.rows:
            row_data = []
            for cell in row.cells:
                row_data.append(cell.text.strip())
            table_data.append(row_data)
        return table_data
    
    def _format_table_as_text(self, table_data):
        """将表格数据格式化为文本"""
        if not table_data:
            return ""
        
        text_lines = []
        for row in table_data:
            if isinstance(row, list):
                # 将行数据连接为字符串
                row_text = " | ".join(str(cell) for cell in row)
                text_lines.append(row_text)
            else:
                text_lines.append(str(row))
        
        return "\n".join(text_lines)
    
    def _optimize_image(self, image_data):
        """优化图片大小和质量"""
        try:
            # 从字节数据创建图片对象
            image = Image.open(io.BytesIO(image_data))
            
            # 获取原始尺寸
            original_width, original_height = image.size
            
            # 如果图片太大，进行压缩
            max_size = (1024, 1024)  # 最大尺寸
            if original_width > max_size[0] or original_height > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
                print(f"图片已压缩: {original_width}x{original_height} -> {image.size[0]}x{image.size[1]}")
            
            # 转换为JPEG格式并压缩
            output_buffer = io.BytesIO()
            image.convert('RGB').save(output_buffer, format='JPEG', quality=85, optimize=True)
            optimized_data = output_buffer.getvalue()
            
            print(f"图片优化完成，大小: {len(image_data)} -> {len(optimized_data)} bytes")
            return optimized_data
            
        except Exception as e:
            print(f"图片优化失败: {e}")
            return image_data  # 如果优化失败，返回原始数据
    
    def _get_image_hash(self, image_data):
        """获取图片数据的哈希值用于缓存"""
        return hashlib.md5(image_data).hexdigest()
    
    def _process_image_with_cache(self, image_data, rel_id):
        """使用缓存处理图片"""
        # 生成图片哈希
        image_hash = self._get_image_hash(image_data)
        
        # 检查缓存
        with self.cache_lock:
            if image_hash in self.image_cache:
                print(f"使用缓存的图片识别结果: {rel_id}")
                return self.image_cache[image_hash]
        
        # 优化图片
        optimized_data = self._optimize_image(image_data)
        
        # 保存优化后的图片到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            temp_file.write(optimized_data)
            temp_image_path = temp_file.name
        
        try:
            # 使用智谱AI识别图片
            image_text = self.zhipuai_client.image_to_text(temp_image_path)
            
            # 缓存结果
            with self.cache_lock:
                self.image_cache[image_hash] = image_text
            
            print(f"图片识别完成并缓存: {rel_id}")
            return image_text
            
        finally:
            # 删除临时文件
            try:
                os.unlink(temp_image_path)
            except:
                pass
    
    def _collect_image_positions_optimized(self, doc):
        """优化的图片位置收集方法"""
        image_positions = {}
        
        try:
            # 收集所有图片关系
            image_rels = []
            for rel_id, rel in doc.part.rels.items():
                if "image" in rel.target_ref:
                    image_rels.append((rel_id, rel))
            
            print(f"找到 {len(image_rels)} 个图片关系")
            
            if not image_rels:
                return image_positions
            
            # 准备图片数据
            image_data_list = []
            for rel_id, rel in image_rels:
                image_data = rel.target_part.blob
                image_data_list.append((rel_id, image_data))
            
            # 并发处理图片识别
            if self.use_concurrent and len(image_data_list) > 1:
                print(f"使用并发模式处理 {len(image_data_list)} 个图片")
                
                # 并发处理图片识别
                recognition_results = self.concurrent_processor.process_images_concurrent(
                    image_data_list,
                    self._process_single_image,
                    doc
                )
                
                # 将结果映射到位置
                for rel_id, image_text in recognition_results:
                    if image_text:
                        # 找到图片在文档中的位置
                        element_index = self._find_image_position(doc, rel_id)
                        if element_index is not None:
                            image_positions[element_index] = {
                                'type': 'image',
                                'content': image_text,                                'original': f"图片识别结果: {image_text}"
                            }
            else:
                # 串行处理
                print(f"使用串行模式处理 {len(image_data_list)} 个图片")
                
                for rel_id, image_data in image_data_list:
                    print(f"处理图片: {rel_id}")
                    image_text = self._process_image_with_cache(image_data, rel_id)
                    
                    if image_text:
                        # 找到图片在文档中的位置
                        element_index = self._find_image_position(doc, rel_id)
                        if element_index is not None:
                            image_positions[element_index] = {
                                'type': 'image',
                                'content': image_text,
                                'original': f"图片识别结果: {image_text}"
                            }
                    
        except Exception as e:
            print(f"图片位置收集失败: {e}")
            import traceback
            print(f"详细错误: {traceback.format_exc()}")
        
        print(f"收集到 {len(image_positions)} 个图片位置")
        return image_positions
    
    def _find_image_position(self, doc, rel_id):
        """查找图片在文档中的位置"""
        element_index = 0
        for element in doc.element.body:
            if hasattr(element, 'xml'):
                xml_str = element.xml
                if rel_id in xml_str:
                    return element_index
            element_index += 1
        return None
    
    def _process_single_image(self, image_data_tuple, doc):
        """处理单个图片（用于并发处理）"""
        rel_id, image_data = image_data_tuple
        try:
            print(f"线程 {threading.current_thread().name} 处理图片: {rel_id}")
            image_text = self._process_image_with_cache(image_data, rel_id)
            return (rel_id, image_text)
        except Exception as e:
            print(f"处理图片 {rel_id} 时发生错误: {e}")
            return (rel_id, None)
    
    def process_content_block(self, block, file_name, section_title, section_level, db_manager, paragraph_number=None):
        """处理单个内容块"""
        try:
            content_type = block['type']
            content = block['content']
            
            # 如果没有提供段落号，使用线程ID作为标识
            if paragraph_number is None:
                paragraph_number = hash(threading.current_thread().name) % 10000
            
            print(f"    处理内容块 - 类型: {content_type}, 内容长度: {len(str(content))}")
            
            if content_type == 'table':
                # 使用智谱AI分析表格
                print(f"    使用智谱AI分析表格...")
                # 确保content是字符串格式
                if isinstance(content, list):
                    table_text = self._format_table_as_text(content)
                else:
                    table_text = str(content)
                processed_content = self.zhipuai_client.table_to_text(table_text)
                original_content = table_text
            elif content_type == 'image':
                # 图片已经通过智谱AI处理过
                print(f"    处理图片识别结果...")
                processed_content = content
                original_content = block.get('original', content)
            else:
                # 普通文本
                print(f"    处理普通文本...")
                processed_content = content
                original_content = content
            
            # 保存到数据库
            print(f"    保存到数据库 - 章节: {section_title}, 段落: {paragraph_number}")
            success = db_manager.insert_content(
                file_name=file_name,
                page_number=section_level,  # 使用目录级别作为页码
                paragraph_number=paragraph_number,
                content_type=content_type,
                content_text=processed_content,
                original_content=original_content,
                section_title=section_title  # 添加章节标题
            )
            
            if success:
                return processed_content
            else:
                print(f"    数据库插入失败")
                return None
            
        except Exception as e:
            print(f"处理内容块失败: {e}")
            import traceback
            print(f"详细错误: {traceback.format_exc()}")
            return None 