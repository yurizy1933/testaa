"""
向量管理模块 - FAISS向量数据库操作（集成MySQL存储）
"""

import faiss
import numpy as np
from typing import List, Dict, Tuple, Optional
import os
import pickle
from .database_manager import DatabaseManager

class VectorManager:
    def __init__(self, vector_dimension=1024, faiss_path="word_vectors.faiss", db_manager=None):
        self.vector_dimension = vector_dimension
        self.faiss_path = faiss_path
        self.index = None
        self.metadata = []
        self.db_manager = db_manager
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        """加载现有索引或创建新索引"""
        if os.path.exists(self.faiss_path):
            print(f"加载现有FAISS索引: {self.faiss_path}")
            self.index = faiss.read_index(self.faiss_path)
            # 加载元数据
            metadata_path = self.faiss_path.replace('.faiss', '_metadata.pkl')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'rb') as f:
                    self.metadata = pickle.load(f)
        else:
            print("创建新的FAISS索引")
            # 使用内积相似度（更适合余弦相似度）
            self.index = faiss.IndexFlatIP(self.vector_dimension)
            self.metadata = []
    
    def add_vectors(self, vectors: List[np.ndarray], metadata: List[Dict]) -> List[int]:
        """
        添加向量到索引
        :param vectors: 向量列表
        :param metadata: 对应的元数据列表
        :return: 向量ID列表
        """
        if not vectors:
            return []
        
        # 转换为numpy数组
        vectors_array = np.array(vectors, dtype=np.float32)
        
        # 归一化向量（用于余弦相似度）
        faiss.normalize_L2(vectors_array)
        
        # 获取当前索引大小作为起始ID
        start_id = self.index.ntotal
        
        # 添加到索引
        self.index.add(vectors_array)
        
        # 保存元数据到内存和数据库
        vector_ids = []
        for i, meta in enumerate(metadata):
            vector_id = start_id + i
            meta['vector_id'] = vector_id
            self.metadata.append(meta)
            vector_ids.append(vector_id)
            
            # 保存到数据库
            if self.db_manager:
                try:
                    self.db_manager.save_vector_data(
                        vector_id=vector_id,
                        text=meta.get('text', ''),
                        doc_path=meta.get('doc_path', ''),
                        doc_name=meta.get('doc_name', ''),
                        page=meta.get('page', 1),
                        word_count=meta.get('word_count', 0)
                    )
                except Exception as e:
                    print(f"保存向量数据到数据库失败: {e}")
        
        # 保存索引
        self._save_index()
        
        return vector_ids
    
    def search_similar(self, query_vector: np.ndarray, top_k: int = 10, 
                      threshold: float = 0.7) -> List[Dict]:
        """
        搜索相似向量
        :param query_vector: 查询向量
        :param top_k: 返回结果数量
        :param threshold: 相似度阈值
        :return: 相似结果列表
        """
        if self.index.ntotal == 0:
            return []
        
        # 归一化查询向量
        query_vector = query_vector.reshape(1, -1).astype(np.float32)
        faiss.normalize_L2(query_vector)
        
        # 搜索相似向量
        similarities, indices = self.index.search(query_vector, min(top_k, self.index.ntotal))
        
        results = []
        for sim, idx in zip(similarities[0], indices[0]):
            if sim >= threshold and idx < len(self.metadata):
                result = {
                    'similarity': float(sim),
                    'vector_id': int(idx),
                    'metadata': self.metadata[idx].copy()
                }
                results.append(result)
        
        return results
    
    def get_vector_by_id(self, vector_id: int) -> Optional[Dict]:
        """根据向量ID获取元数据"""
        # 优先从内存获取
        if 0 <= vector_id < len(self.metadata):
            return self.metadata[vector_id]
        
        # 从数据库获取
        if self.db_manager:
            try:
                db_result = self.db_manager.get_vector_by_id(vector_id)
                if db_result:
                    return {
                        'vector_id': db_result['vector_id'],
                        'text': db_result['text'],
                        'doc_path': db_result['doc_path'],
                        'doc_name': db_result['doc_name'],
                        'page': db_result['page'],
                        'word_count': db_result['word_count']
                    }
            except Exception as e:
                print(f"从数据库获取向量数据失败: {e}")
        
        return None
    
    def get_all_metadata(self) -> List[Dict]:
        """获取所有元数据"""
        return self.metadata.copy()
    
    def get_index_stats(self) -> Dict:
        """获取索引统计信息"""
        return {
            'total_vectors': self.index.ntotal,
            'vector_dimension': self.vector_dimension,
            'index_type': type(self.index).__name__,
            'metadata_count': len(self.metadata)
        }
    
    def _save_index(self):
        """保存索引和元数据"""
        # 保存FAISS索引
        faiss.write_index(self.index, self.faiss_path)
        
        # 保存元数据
        metadata_path = self.faiss_path.replace('.faiss', '_metadata.pkl')
        with open(metadata_path, 'wb') as f:
            pickle.dump(self.metadata, f)
        
        print(f"索引已保存: {self.faiss_path}")
    
    def clear_index(self):
        """清空索引"""
        self.index = faiss.IndexFlatIP(self.vector_dimension)
        self.metadata = []
        self._save_index()
        print("索引已清空")
    
    def rebuild_index(self, vectors: List[np.ndarray], metadata: List[Dict]):
        """重建索引"""
        self.clear_index()
        self.add_vectors(vectors, metadata) 