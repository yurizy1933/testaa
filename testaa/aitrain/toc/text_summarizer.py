import re
from concurrent_processor import ConcurrentProcessor

class TextSummarizer:
    def __init__(self, zhipuai_client, vector_store, db_manager, use_concurrent=True, max_workers=4):
        self.zhipuai_client = zhipuai_client
        self.vector_store = vector_store
        self.db_manager = db_manager
        self.use_concurrent = use_concurrent
        self.concurrent_processor = ConcurrentProcessor(max_workers) if use_concurrent else None
        print(f"文本总结器初始化成功，并发处理: {'启用' if use_concurrent else '禁用'}")
    
    def summarize_and_vectorize(self, file_name, sections=None):
        """对文档章节进行总结和向量化（从数据库读取章节信息）"""
        try:
            print(f"开始总结文档: {file_name}")
            
            # 从数据库读取章节信息
            db_sections = self._get_sections_from_db(file_name)
            
            if not db_sections:
                print(f"数据库中未找到文档 {file_name} 的章节信息")
                return []
            
            if self.use_concurrent:
                return self._summarize_and_vectorize_concurrent(file_name, db_sections)
            else:
                return self._summarize_and_vectorize_sequential(file_name, db_sections)
            
        except Exception as e:
            print(f"文档总结失败: {e}")
            raise
    
    def _get_sections_from_db(self, file_name):
        """从数据库获取章节信息"""
        try:
            # 获取所有章节标题和级别
            sections = self.db_manager.get_sections_by_file(file_name)
            
            # 为每个章节获取内容
            for section in sections:
                section_content = self.db_manager.get_content_by_section(
                    file_name, section['section_title']
                )
                section['content'] = section_content
            
            print(f"从数据库获取到 {len(sections)} 个章节")
            return sections
            
        except Exception as e:
            print(f"从数据库获取章节信息失败: {e}")
            return []
    
    def _summarize_and_vectorize_sequential(self, file_name, db_sections):
        """串行总结和向量化"""
        all_points = []
        
        for section_index, section in enumerate(db_sections, 1):
            print(f"处理第 {section_index} 个章节: {section['section_title']}")
            
            # 收集当前章节的所有文本内容
            section_texts = []
            for content_item in section['content']:
                content_type = content_item['content_type']
                content_text = content_item['content_text']
                
                if content_type == 'text':
                    if isinstance(content_text, str):
                        section_texts.append(content_text)
                    else:
                        section_texts.append(str(content_text))
                elif content_type in ['table', 'image']:
                    # 表格和图片已经通过智谱AI处理过，直接使用处理结果
                    if isinstance(content_text, str):
                        section_texts.append(content_text)
                    else:
                        section_texts.append(str(content_text))
            
            if not section_texts:
                continue
            
            # 合并章节文本
            combined_text = "\n\n".join(section_texts)
            
            # 使用智谱AI进行总结
            summary = self.zhipuai_client.summarize_text(combined_text)
            
            # 提取独立的要点
            points = self._extract_points(summary)
            
            # 为每个要点生成向量并存储
            for point in points:
                if point.strip():
                    # 在要点前添加章节标题
                    point_with_title = f"[{section['section_title']}] {point}"
                    
                    # 获取向量
                    vector = self.zhipuai_client.get_embedding(point_with_title)
                    
                    if vector:
                        # 添加到向量存储
                        faiss_id = self.vector_store.add_vector(vector)
                        
                        if faiss_id is not None:
                            # 保存到数据库
                            success = self.db_manager.insert_point(
                                file_name=file_name,
                                point_text=point_with_title,
                                faiss_id=faiss_id,
                                vector_data=vector
                            )
                            
                            if success:
                                all_points.append({
                                    'text': point_with_title,
                                    'faiss_id': faiss_id,
                                    'section': section['section_title']
                                })
                            else:
                                print(f"    要点数据库插入失败")
        
        print(f"文档总结完成，共生成 {len(all_points)} 个要点")
        return all_points
    
    def _summarize_and_vectorize_concurrent(self, file_name, db_sections):
        """并发总结和向量化"""
        print("使用并发模式进行总结和向量化")
        
        # 并发处理所有章节
        section_results = self.concurrent_processor.process_sections_concurrent(
            db_sections,
            self._process_single_section,
            file_name
        )
        
        # 收集所有要点
        all_points = []
        for result in section_results:
            if result:
                all_points.extend(result)
        
        print(f"文档总结完成，共生成 {len(all_points)} 个要点")
        return all_points
    
    def _process_single_section(self, section, file_name):
        """处理单个章节（用于并发处理）"""
        try:
            print(f"处理章节: {section['section_title']}")
            
            # 收集当前章节的所有文本内容
            section_texts = []
            for content_item in section['content']:
                content_type = content_item['content_type']
                content_text = content_item['content_text']
                
                if content_type == 'text':
                    if isinstance(content_text, str):
                        section_texts.append(content_text)
                    else:
                        section_texts.append(str(content_text))
                elif content_type in ['table', 'image']:
                    # 表格和图片已经通过智谱AI处理过，直接使用处理结果
                    if isinstance(content_text, str):
                        section_texts.append(content_text)
                    else:
                        section_texts.append(str(content_text))
            
            if not section_texts:
                return []
            
            # 合并章节文本
            combined_text = "\n\n".join(section_texts)
            
            # 使用智谱AI进行总结
            summary = self.zhipuai_client.summarize_text(combined_text)
            
            # 提取独立的要点
            points = self._extract_points(summary)
            
            section_points = []
            # 为每个要点生成向量并存储
            for point in points:
                if point.strip():
                    # 在要点前添加章节标题
                    point_with_title = f"[{section['section_title']}] {point}"
                    
                    # 获取向量
                    vector = self.zhipuai_client.get_embedding(point_with_title)
                    
                    if vector:
                        # 添加到向量存储
                        faiss_id = self.vector_store.add_vector(vector)
                        
                        if faiss_id is not None:
                            # 保存到数据库
                            success = self.db_manager.insert_point(
                                file_name=file_name,
                                point_text=point_with_title,
                                faiss_id=faiss_id,
                                vector_data=vector
                            )
                            
                            if success:
                                section_points.append({
                                    'text': point_with_title,
                                    'faiss_id': faiss_id,
                                    'section': section['section_title']
                                })
                            else:
                                print(f"    要点数据库插入失败")
            
            return section_points
            
        except Exception as e:
            print(f"处理章节时发生错误: {e}")
            return []
    
    def _extract_points(self, summary_text):
        """从总结文本中提取独立的要点"""
        points = []
        
        # 尝试按数字编号分割
        numbered_points = re.split(r'\d+[\.、]', summary_text)
        if len(numbered_points) > 1:
            for point in numbered_points[1:]:  # 跳过第一个空字符串
                point = point.strip()
                if self._is_valid_point(point):
                    points.append(point)
        
        # 如果没有数字编号，尝试按换行符分割
        if not points:
            lines = summary_text.split('\n')
            for line in lines:
                line = line.strip()
                if self._is_valid_point(line):
                    points.append(line)
        
        # 如果还是没有，尝试按句号分割
        if not points:
            sentences = re.split(r'[。！？]', summary_text)
            for sentence in sentences:
                sentence = sentence.strip()
                if self._is_valid_point(sentence):
                    points.append(sentence)
        
        # 如果所有方法都失败，返回原文本（如果有效）
        if not points and self._is_valid_point(summary_text):
            points = [summary_text]
        
        return points
    
    def _is_valid_point(self, text):
        """检查要点是否有效"""
        if not text or not text.strip():
            return False
        
        text = text.strip()
        
        # 长度检查：至少15个字符
        if len(text) < 15:
            return False
        
        # 过滤无意义的短词组合
        meaningless_patterns = [
            r'^[A-Z]{1,3}\s+[A-Z]{1,3}$',  # 如 "If DE"
            r'^[A-Z]{1,2}\s*$',  # 单个或两个大写字母
            r'^[a-zA-Z]{1,3}\s+[a-zA-Z]{1,3}$',  # 短词组合
            r'^[^\u4e00-\u9fff]{1,10}$',  # 不包含中文字符的短文本
            r'^[A-Za-z\s]{1,10}$',  # 纯英文短文本
        ]
        
        for pattern in meaningless_patterns:
            if re.match(pattern, text):
                return False
        
        # 检查是否包含有意义的内容
        # 至少包含一个中文字符或完整的英文单词
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))
        has_english_word = bool(re.search(r'\b[a-zA-Z]{4,}\b', text))
        
        if not has_chinese and not has_english_word:
            return False
        
        # 过滤掉只包含标点符号的文本
        if re.match(r'^[^\w\u4e00-\u9fff]+$', text):
            return False
        
        return True
    
    def search_similar_points(self, query_text, k=5):
        """搜索相似的要点"""
        try:
            # 获取查询文本的向量
            query_vector = self.zhipuai_client.get_embedding(query_text)
            
            if query_vector is None:
                print("无法获取查询向量")
                return []
            
            # 搜索相似向量
            similar_results = self.vector_store.search_similar(query_vector, k)
            
            return similar_results
            
        except Exception as e:
            print(f"搜索相似要点失败: {e}")
            return [] 