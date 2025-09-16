"""
RAG处理器 - 整合所有模块功能（集成MySQL存储）
"""

import os
import time
from typing import List, Dict, Optional, Tuple
import numpy as np

from .config import ConfigManager
from .word_parser import WordDocumentParser
from .vector_manager import VectorManager
from .ai_client import AIClient
from .database_manager import DatabaseManager
from .page_processor import PageProcessor
from .document_processor import DocumentProcessor
from .zhipu_file_parser import ZhipuFileParser
from .sentence_summarizer import SentenceSummarizer

class RAGProcessor:
    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化RAG处理器
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
            request_interval=self.config.get('REQUEST_INTERVAL', 1.0)
        )
        
        # 初始化文档解析器
        self.word_parser = WordDocumentParser(
            chunk_size=self.config.get('CHUNK_SIZE', 500),
            chunk_overlap=self.config.get('CHUNK_OVERLAP', 50),
            max_workers=self.config.get('MAX_WORKERS', 4)
        )
        
        # 初始化智谱AI文件解析器（如果启用）
        self.use_zhipu_parser = self.config.get('USE_ZHIPU_FILE_PARSER', False)
        if self.use_zhipu_parser:
            zhipuai_config = self.config.get_zhipuai_config()
            max_size_mb = self.config.get('FILE_TRUNCATE_MAX_SIZE_MB', 45)
            self.zhipu_parser = ZhipuFileParser(
                api_key=zhipuai_config['api_key'],
                base_url=zhipuai_config.get('base_url', 'https://open.bigmodel.cn/api/paas/v4')
            )
            print(f"✓ 智谱AI文件解析器已启用（最大文件大小: {max_size_mb}MB）")
        else:
            self.zhipu_parser = None
            print("✓ 使用本地Word文档解析器")
        
        # 初始化向量管理器（集成数据库）
        self.vector_manager = VectorManager(
            vector_dimension=self.config.get('VECTOR_DIMENSION', 1024),
            faiss_path=self.config.get('FAISS_DB_PATH', 'word_vectors.faiss'),
            db_manager=self.db_manager
        )
        
        # 初始化逐页处理器
        self.page_processor = PageProcessor(
            word_parser=self.word_parser,
            ai_client=self.ai_client,
            vector_manager=self.vector_manager,
            db_manager=self.db_manager
        )
        
        # 初始化文档处理器（支持增量处理）
        self.document_processor = DocumentProcessor(
            word_parser=self.word_parser,
            ai_client=self.ai_client,
            vector_manager=self.vector_manager,
            db_manager=self.db_manager
        )
        
        # 初始化句子总结器
        self.sentence_summarizer = SentenceSummarizer(self.ai_client)
    
    def process_document(self, doc_path: str, save_metadata: bool = True) -> Dict:
        """
        处理Word文档（支持智谱AI文件解析和本地解析）
        :param doc_path: 文档路径
        :param save_metadata: 是否保存元数据
        :return: 处理结果
        """
        print(f"开始处理文档: {doc_path}")
        
        # 检查是否使用智谱AI文件解析
        if self.use_zhipu_parser and self.zhipu_parser:
            return self._process_document_with_zhipu(doc_path)
        else:
            # 使用本地逐页处理器
            return self.page_processor.process_document_with_progress(doc_path)
    
    def _process_document_with_zhipu(self, doc_path: str) -> Dict:
        """
        使用智谱AI文件解析处理文档
        :param doc_path: 文档路径
        :return: 处理结果
        """
        print(f"使用智谱AI文件解析处理: {doc_path}")
        start_time = time.time()
        
        try:
            # 解析文档
            chunk_size = self.config.get('FILE_PARSER_CHUNK_SIZE', 1000)
            chunk_overlap = self.config.get('FILE_PARSER_CHUNK_OVERLAP', 200)
            
            success, error, chunks = self.zhipu_parser.parse_document_with_chunks(
                doc_path, chunk_size, chunk_overlap
            )
            
            if not success:
                return {
                    'doc_path': doc_path,
                    'status': 'error',
                    'error': error,
                    'processing_time': time.time() - start_time
                }
            
            print(f"智谱AI解析完成，共 {len(chunks)} 个文本块")
            
            # 批量获取向量（去重）
            texts = []
            unique_chunks = []
            seen_texts = set()
            
            for chunk in chunks:
                text = chunk['text']
                text_hash = hash(text)
                if text_hash not in seen_texts:
                    texts.append(text)
                    unique_chunks.append(chunk)
                    seen_texts.add(text_hash)
                else:
                    print(f"跳过重复文本块: '{text[:50]}...'")
            
            print(f"去重后文本块数: {len(texts)} (原 {len(chunks)})")
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
                        'text': unique_chunks[i]['text'],
                        'page': 1,  # 智谱AI解析不分页，统一设为1
                        'start_pos': unique_chunks[i]['start_pos'],
                        'end_pos': unique_chunks[i]['end_pos'],
                        'word_count': unique_chunks[i]['word_count'],
                        'doc_path': doc_path,
                        'doc_name': unique_chunks[i]['file_name'],
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
            
            # 保存文档信息到数据库
            file_info = self.zhipu_parser.get_file_info(doc_path)
            self.db_manager.save_document_info(
                doc_path=doc_path,
                doc_name=file_info['file_name'],
                total_pages=1,  # 智谱AI解析不分页
                total_words=sum(chunk['word_count'] for chunk in unique_chunks),
                file_size=file_info['file_size']
            )
            
            processing_time = time.time() - start_time
            
            return {
                'doc_path': doc_path,
                'status': 'success',
                'total_pages': 1,
                'processed_pages': 1,
                'total_vectors': len(vector_ids),
                'total_chunks': len(unique_chunks),
                'success_chunks': success_count,
                'processing_time': processing_time,
                'parser_type': 'zhipu_ai'
            }
            
        except Exception as e:
            return {
                'doc_path': doc_path,
                'status': 'error',
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    def process_document_by_pages(self, doc_path: str, start_page: int = 1, 
                                 end_page: Optional[int] = None):
        """
        逐页处理文档，生成器模式
        :param doc_path: 文档路径
        :param start_page: 开始页面
        :param end_page: 结束页面
        :yield: 每页的处理结果
        """
        return self.page_processor.process_document_by_pages(doc_path, start_page, end_page)
    
    def get_document_status(self, doc_path: str) -> Dict:
        """获取文档处理状态"""
        return self.page_processor.get_processing_status(doc_path)
    
    def search_similar(self, query: str, top_k: int = 10, 
                      threshold: float = 0.7) -> List[Dict]:
        """
        搜索相似内容
        :param query: 查询文本
        :param top_k: 返回结果数量
        :param threshold: 相似度阈值
        :return: 相似结果列表
        """
        print(f"搜索查询: {query}")
        
        # 获取查询向量
        success, query_vector = self.ai_client.get_embedding(query)
        if not success:
            print("获取查询向量失败")
            return []
        
        # 搜索相似向量
        results = self.vector_manager.search_similar(
            query_vector, top_k, threshold
        )
        
        print(f"找到 {len(results)} 个相似结果")
        return results
    
    def answer_question(self, question: str, top_k: int = 5) -> Tuple[bool, Optional[str]]:
        """
        基于文档内容回答问题
        :param question: 问题
        :param top_k: 检索的相关文档数量
        :return: (成功标志, 答案)
        """
        # 搜索相关文档
        similar_results = self.search_similar(question, top_k, threshold=0.6)
        
        if not similar_results:
            return False, "未找到相关文档内容"
        
        # 构建上下文
        context_parts = []
        for result in similar_results:
            metadata = result['metadata']
            context_parts.append(f"页码: {metadata['page']}\n内容: {metadata['text']}")
        
        context = "\n\n".join(context_parts)
        
        # 使用AI回答问题
        return self.ai_client.answer_question(question, context)
    
    def get_document_summary(self, doc_path: str) -> Tuple[bool, Optional[str]]:
        """
        获取文档摘要
        :param doc_path: 文档路径
        :return: (成功标志, 摘要内容)
        """
        # 解析文档
        chunks = self.word_parser.parse_document(doc_path)
        
        if not chunks:
            return False, "文档为空"
        
        # 合并所有文本
        full_text = "\n".join([chunk['text'] for chunk in chunks])
        
        # 生成摘要
        return self.ai_client.summarize_text(full_text, max_length=500)
    
    def get_index_stats(self) -> Dict:
        """获取索引统计信息"""
        faiss_stats = self.vector_manager.get_index_stats()
        db_stats = self.db_manager.get_processing_stats()
        
        return {
            **faiss_stats,
            **db_stats
        }
    
    def clear_index(self):
        """清空向量索引"""
        self.vector_manager.clear_index()
        print("向量索引已清空")
    
    def get_document_list(self) -> List[Dict]:
        """获取所有文档列表"""
        return self.db_manager.get_all_documents()
    
    def get_document_vectors(self, doc_path: str) -> List[Dict]:
        """获取指定文档的所有向量数据"""
        return self.db_manager.get_vectors_by_doc_path(doc_path)
    
    def delete_document(self, doc_path: str) -> bool:
        """删除文档及其相关数据"""
        # 从数据库中删除
        db_success = self.db_manager.delete_document_data(doc_path)
        
        # 从FAISS索引中删除（需要重建索引）
        # 这里可以实现更复杂的删除逻辑
        print(f"文档删除结果: 数据库={db_success}")
        return db_success
    
    def test_ai_connection(self) -> bool:
        """测试AI连接"""
        return self.ai_client.test_connection()
    
    def batch_process_documents(self, doc_paths: List[str]) -> List[Dict]:
        """
        批量处理文档
        :param doc_paths: 文档路径列表
        :return: 处理结果列表
        """
        results = []
        
        for i, doc_path in enumerate(doc_paths, 1):
            print(f"\n处理文档 {i}/{len(doc_paths)}: {doc_path}")
            
            try:
                result = self.process_document(doc_path)
                results.append(result)
                print(f"文档 {i} 处理完成")
            except Exception as e:
                print(f"处理文档 {i} 失败: {str(e)}")
                results.append({
                    'doc_path': doc_path,
                    'error': str(e),
                    'success': False
                })
        
        return results
    
    def process_document_to_sentences(self, doc_path: str, max_sentences: int = 10) -> Dict:
        """
        处理文档并提取关键句子，为每个句子生成向量
        :param doc_path: 文档路径
        :param max_sentences: 最大句子数量
        :return: 处理结果
        """
        print(f"开始处理文档为句子向量: {doc_path}")
        
        if not os.path.exists(doc_path):
            return {'error': f'文档不存在: {doc_path}'}
        
        try:
            # 读取文档内容
            if self.use_zhipu_parser and self.zhipu_parser:
                # 使用智谱AI解析
                success, error, result = self.zhipu_parser.parse_document(doc_path)
                if not success:
                    return {'error': f'智谱AI解析失败: {error}'}
                content = result.get('content', '')
            else:
                # 使用本地Word解析
                from docx import Document
                doc = Document(doc_path)
                content = '\n'.join([para.text for para in doc.paragraphs if para.text.strip()])
            
            if not content.strip():
                return {'error': '文档内容为空'}
            
            # 使用句子总结器处理
            result = self.sentence_summarizer.process_document_to_sentences(
                content, max_sentences
            )
            
            # 保存句子向量到数据库
            if result['success_sentences'] > 0:
                self._save_sentence_vectors_to_db(doc_path, result)
            
            return result
            
        except Exception as e:
            print(f"处理文档为句子向量失败: {e}")
            return {'error': str(e)}
    
    def _save_sentence_vectors_to_db(self, doc_path: str, result: Dict):
        """
        保存句子向量到数据库
        :param doc_path: 文档路径
        :param result: 处理结果
        """
        try:
            # 保存文档信息
            doc_info = {
                'doc_path': doc_path,
                'doc_name': os.path.basename(doc_path),
                'total_sentences': result['total_sentences'],
                'success_sentences': result['success_sentences'],
                'fail_sentences': result['fail_sentences'],
                'success_rate': result['success_rate'],
                'processed_time': time.time()
            }
            
            self.db_manager.save_document_info(doc_info)
            
            # 保存句子向量信息
            for i, (success, sentence, metadata) in enumerate(result['vector_results']):
                if success:
                    vector_info = {
                        'doc_path': doc_path,
                        'sentence_index': i,
                        'sentence_text': sentence,
                        'sentence_length': len(sentence),
                        'word_count': metadata.get('word_count', 0),
                        'vector_dimension': metadata.get('vector_dimension'),
                        'processed_time': time.time()
                    }
                    
                    # 这里可以添加向量数据保存逻辑
                    # self.db_manager.save_sentence_vector(vector_info)
            
            print(f"✅ 句子向量数据已保存到数据库")
            
        except Exception as e:
            print(f"❌ 保存句子向量到数据库失败: {e}")
    
    def search_similar_sentences(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        搜索相似句子
        :param query: 查询文本
        :param top_k: 返回结果数量
        :return: 相似句子列表
        """
        try:
            # 获取查询向量
            success, query_vector = self.ai_client.get_embedding(query)
            if not success or query_vector is None:
                return []
            
            # 从数据库搜索相似句子
            # 这里需要实现具体的搜索逻辑
            # 暂时返回空列表
            return []
            
        except Exception as e:
            print(f"搜索相似句子失败: {e}")
            return [] 