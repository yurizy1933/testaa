import faiss
import numpy as np
import pickle
import os
from config import VECTOR_DIMENSION

class VectorStore:
    def __init__(self, index_path="faiss_index"):
        self.index_path = index_path
        self.index = None
        self.vector_id_counter = 0
        self.load_or_create_index()
        print("向量存储初始化成功")
    
    def load_or_create_index(self):
        """加载或创建FAISS索引"""
        try:
            if os.path.exists(f"{self.index_path}.index"):
                # 加载现有索引
                self.index = faiss.read_index(f"{self.index_path}.index")
                with open(f"{self.index_path}_counter.pkl", 'rb') as f:
                    self.vector_id_counter = pickle.load(f)
                print(f"加载现有FAISS索引，当前向量数量: {self.index.ntotal}")
            else:
                # 创建新索引
                self.index = faiss.IndexFlatIP(VECTOR_DIMENSION)  # 使用内积相似度
                print("创建新的FAISS索引")
        except Exception as e:
            print(f"索引加载失败: {e}")
            # 创建新索引作为备选
            self.index = faiss.IndexFlatIP(VECTOR_DIMENSION)
            self.vector_id_counter = 0
    
    def add_vector(self, vector):
        """添加向量到索引"""
        try:
            if vector is None:
                print("向量为空，跳过添加")
                return None
            
            print(f"开始处理向量，类型: {type(vector)}")
            
            # 确保向量是numpy数组
            if not isinstance(vector, np.ndarray):
                print(f"转换向量为numpy数组，原始类型: {type(vector)}")
                vector = np.array(vector, dtype=np.float32)
            
            print(f"向量形状: {vector.shape}, 数据类型: {vector.dtype}")
            
            # 检查向量维度
            if vector.size == 0:
                print("向量为空数组")
                return None
            
            # 确保向量是2D数组
            if vector.ndim == 1:
                print("重塑向量为2D数组")
                vector = vector.reshape(1, -1)
            
            # 检查向量维度是否匹配
            if vector.shape[1] != VECTOR_DIMENSION:
                print(f"向量维度不匹配: 期望 {VECTOR_DIMENSION}, 实际 {vector.shape[1]}")
                return None
            
            # 检查向量是否包含NaN或无穷大值
            if np.any(np.isnan(vector)) or np.any(np.isinf(vector)):
                print("向量包含NaN或无穷大值")
                return None
            
            # 添加到索引
            print("添加向量到FAISS索引")
            self.index.add(vector)
            
            # 分配向量ID
            vector_id = self.vector_id_counter
            self.vector_id_counter += 1
            
            # 保存索引和计数器
            self.save_index()
            
            print(f"向量添加成功，ID: {vector_id}")
            return vector_id
            
        except Exception as e:
            print(f"向量添加失败: {e}")
            import traceback
            print(f"详细错误信息: {traceback.format_exc()}")
            return None
    
    def search_similar(self, query_vector, k=5):
        """搜索相似向量"""
        try:
            if query_vector is None:
                print("查询向量为空")
                return []
            
            # 确保向量是numpy数组
            if not isinstance(query_vector, np.ndarray):
                query_vector = np.array(query_vector, dtype=np.float32)
            
            # 确保向量是2D数组
            if query_vector.ndim == 1:
                query_vector = query_vector.reshape(1, -1)
            
            # 搜索相似向量
            scores, indices = self.index.search(query_vector, k)
            
            results = []
            for i in range(len(scores[0])):
                if indices[0][i] != -1:  # FAISS返回-1表示没有找到结果
                    results.append({
                        'id': int(indices[0][i]),
                        'score': float(scores[0][i])
                    })
            
            print(f"搜索完成，找到 {len(results)} 个相似向量")
            return results
            
        except Exception as e:
            print(f"向量搜索失败: {e}")
            return []
    
    def save_index(self):
        """保存索引到文件"""
        try:
            faiss.write_index(self.index, f"{self.index_path}.index")
            with open(f"{self.index_path}_counter.pkl", 'wb') as f:
                pickle.dump(self.vector_id_counter, f)
            print("索引保存成功")
        except Exception as e:
            print(f"索引保存失败: {e}")
    
    def get_index_stats(self):
        """获取索引统计信息"""
        try:
            return {
                'total_vectors': self.index.ntotal,
                'dimension': self.index.d,
                'next_vector_id': self.vector_id_counter
            }
        except Exception as e:
            print(f"获取索引统计失败: {e}")
            return {} 
    
    def get_vector_by_id(self, vector_id):
        """根据向量ID获取向量"""
        try:
            if self.index is None:
                print("索引未初始化")
                return None
            
            if vector_id < 0 or vector_id >= self.index.ntotal:
                print(f"向量ID超出范围: {vector_id}, 总向量数: {self.index.ntotal}")
                return None
            
            # 使用FAISS的reconstruct方法获取向量
            vector = self.index.reconstruct(vector_id)
            
            # 确保返回的是numpy数组
            if not isinstance(vector, np.ndarray):
                vector = np.array(vector, dtype=np.float32)
            
            print(f"成功获取向量 ID {vector_id}")
            return vector
            
        except Exception as e:
            print(f"获取向量失败 (ID: {vector_id}): {e}")
            return None
    
    def get_all_vectors(self):
        """获取所有向量"""
        try:
            if self.index is None:
                print("索引未初始化")
                return None
            
            total_vectors = self.index.ntotal
            if total_vectors == 0:
                print("索引中没有向量")
                return None
            
            # 获取所有向量
            vectors = self.index.reconstruct_n(0, total_vectors)
            
            print(f"成功获取所有 {total_vectors} 个向量")
            return vectors
            
        except Exception as e:
            print(f"获取所有向量失败: {e}")
            return None 