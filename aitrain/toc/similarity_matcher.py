#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
相似度匹配器
通过正弦相似度和余弦相似度计算相似向量，筛选faiss_index和case_faiss_index中相似的值
"""

import numpy as np
import faiss
import pickle
import os
from typing import List, Dict, Any, Tuple, Optional
from vector_store import VectorStore
from case_to_faiss_processor import TestCaseProcessor
from thread_safe_db import ThreadSafeDatabaseManager
import json

class SimilarityMatcher:
    """相似度匹配器"""
    
    def __init__(self, 
                 faiss_index_path: str = "faiss_index",
                 case_faiss_index_path: str = "case_faiss_index",
                 similarity_threshold: float = 0.7):
        """
        初始化相似度匹配器
        
        Args:
            faiss_index_path: 需求文档FAISS索引路径
            case_faiss_index_path: 测试用例FAISS索引路径
            similarity_threshold: 相似度阈值
        """
        self.faiss_index_path = faiss_index_path
        self.case_faiss_index_path = case_faiss_index_path
        self.similarity_threshold = similarity_threshold
        
        # 初始化组件
        self.vector_store = VectorStore(faiss_index_path)
        self.case_processor = TestCaseProcessor("测试用例.json", case_faiss_index_path)
        self.db_manager = ThreadSafeDatabaseManager()
        
        print("相似度匹配器初始化成功")
    
    def calculate_cosine_similarity(self, vector1: np.ndarray, vector2: np.ndarray) -> float:
        """
        计算余弦相似度
        
        Args:
            vector1: 向量1
            vector2: 向量2
            
        Returns:
            余弦相似度值
        """
        try:
            # 确保向量是1D数组
            if vector1.ndim > 1:
                vector1 = vector1.flatten()
            if vector2.ndim > 1:
                vector2 = vector2.flatten()
            
            # 计算余弦相似度
            dot_product = np.dot(vector1, vector2)
            norm1 = np.linalg.norm(vector1)
            norm2 = np.linalg.norm(vector2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            print(f"计算余弦相似度失败: {e}")
            return 0.0
    
    def calculate_sine_similarity(self, vector1: np.ndarray, vector2: np.ndarray) -> float:
        """
        计算正弦相似度
        
        Args:
            vector1: 向量1
            vector2: 向量2
            
        Returns:
            正弦相似度值
        """
        try:
            # 确保向量是1D数组
            if vector1.ndim > 1:
                vector1 = vector1.flatten()
            if vector2.ndim > 1:
                vector2 = vector2.flatten()
            
            # 计算余弦相似度
            cosine_sim = self.calculate_cosine_similarity(vector1, vector2)
            
            # 正弦相似度 = sqrt(1 - 余弦相似度^2)
            sine_sim = np.sqrt(1 - cosine_sim ** 2)
            return float(sine_sim)
            
        except Exception as e:
            print(f"计算正弦相似度失败: {e}")
            return 0.0
    
    def get_point_by_faiss_id(self, faiss_id: int) -> Optional[Dict[str, Any]]:
        """
        根据FAISS ID获取需求要点信息
        
        Args:
            faiss_id: FAISS向量ID
            
        Returns:
            需求要点信息
        """
        try:
            connection = self.db_manager._get_connection()
            with connection.cursor() as cursor:
                sql = """
                    SELECT file_name, point_text
                    FROM adocument_point 
                    WHERE faiss_id = %s
                """
                cursor.execute(sql, (faiss_id,))
                result = cursor.fetchone()
                
                if result:
                    return {
                        'faiss_id': faiss_id,
                        'file_name': result[0],
                        'point_text': result[1]
                    }
                return None
                
        except Exception as e:
            print(f"获取需求要点信息失败: {e}")
            return None
    
    def get_case_by_faiss_id(self, faiss_id: int) -> Optional[Dict[str, Any]]:
        """
        根据FAISS ID获取测试用例信息
        
        Args:
            faiss_id: FAISS向量ID
            
        Returns:
            测试用例信息
        """
        try:
            connection = self.db_manager._get_connection()
            with connection.cursor() as cursor:
                sql = """
                    SELECT case_title, preconditions, test_steps, expected_results, case_level
                    FROM test_cases 
                    WHERE faiss_id = %s
                """
                cursor.execute(sql, (faiss_id,))
                result = cursor.fetchone()
                
                if result:
                    return {
                        'faiss_id': faiss_id,
                        'case_title': result[0],
                        'preconditions': result[1],
                        'test_steps': result[2],
                        'expected_results': result[3],
                        'case_level': result[4]
                    }
                return None
                
        except Exception as e:
            print(f"获取测试用例信息失败: {e}")
            return None
    
    def find_similar_pairs(self, 
                          top_k: int = 10,
                          min_similarity: float = 0.5) -> List[Dict[str, Any]]:
        """
        查找相似的需求要点和测试用例对
        
        Args:
            top_k: 返回结果数量
            min_similarity: 最小相似度阈值
            
        Returns:
            相似对列表
        """
        try:
            print("开始查找相似的需求要点和测试用例对...")
            
            # 获取所有需求要点向量
            point_vectors = self._get_all_point_vectors()
            if not point_vectors:
                print("未找到需求要点向量")
                return []
            
            # 获取所有测试用例向量
            case_vectors = self._get_all_case_vectors()
            if not case_vectors:
                print("未找到测试用例向量")
                return []
            
            print(f"找到 {len(point_vectors)} 个需求要点向量和 {len(case_vectors)} 个测试用例向量")
            
            # 计算相似度并排序
            similar_pairs = []
            
            for point_info in point_vectors:
                point_vector = point_info['vector']
                point_id = point_info['faiss_id']
                
                for case_info in case_vectors:
                    case_vector = case_info['vector']
                    case_id = case_info['faiss_id']
                    
                    # 计算余弦相似度
                    cosine_sim = self.calculate_cosine_similarity(point_vector, case_vector)
                    
                    # 计算正弦相似度
                    # sine_sim = self.calculate_sine_similarity(point_vector, case_vector)
                    
                    # 综合相似度（可以调整权重）
                    # combined_sim = 0.7 * cosine_sim + 0.3 * sine_sim

                    combined_sim = cosine_sim
                    
                    if combined_sim >= min_similarity:
                        similar_pairs.append({
                            'point_faiss_id': point_id,
                            'case_faiss_id': case_id,
                            'cosine_similarity': cosine_sim,
                            # 'sine_similarity': sine_sim,
                            'combined_similarity': combined_sim
                        })
            
            # 按综合相似度排序
            similar_pairs.sort(key=lambda x: x['combined_similarity'], reverse=True)
            
            # 取前top_k个结果
            top_pairs = similar_pairs[:top_k]
            
            print(f"找到 {len(top_pairs)} 个相似对")
            return top_pairs
            
        except Exception as e:
            print(f"查找相似对失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _get_all_point_vectors(self) -> List[Dict[str, Any]]:
        """获取所有需求要点向量"""
        try:
            # 从FAISS索引获取所有向量
            if not os.path.exists(f"{self.faiss_index_path}.index"):
                print("需求要点FAISS索引文件不存在")
                return []
            
            # 读取FAISS索引
            index = faiss.read_index(f"{self.faiss_index_path}.index")
            
            # 获取所有向量
            vectors = index.reconstruct_n(0, index.ntotal)
            
            # 读取计数器文件获取向量ID映射
            counter_file = f"{self.faiss_index_path}_counter.pkl"
            if os.path.exists(counter_file):
                with open(counter_file, 'rb') as f:
                    vector_id_counter = pickle.load(f)
            else:
                vector_id_counter = index.ntotal
            
            point_vectors = []
            for i in range(index.ntotal):
                point_vectors.append({
                    'faiss_id': i,
                    'vector': vectors[i]
                })
            
            return point_vectors
            
        except Exception as e:
            print(f"获取需求要点向量失败: {e}")
            return []
    
    def _get_all_case_vectors(self) -> List[Dict[str, Any]]:
        """获取所有测试用例向量"""
        try:
            # 从FAISS索引获取所有向量
            if not os.path.exists(f"{self.case_faiss_index_path}.index"):
                print("测试用例FAISS索引文件不存在")
                return []
            
            # 读取FAISS索引
            index = faiss.read_index(f"{self.case_faiss_index_path}.index")
            
            # 获取所有向量
            vectors = index.reconstruct_n(0, index.ntotal)
            
            # 读取计数器文件获取向量ID映射
            counter_file = f"{self.case_faiss_index_path}_counter.pkl"
            if os.path.exists(counter_file):
                with open(counter_file, 'rb') as f:
                    vector_id_counter = pickle.load(f)
            else:
                vector_id_counter = index.ntotal
            
            case_vectors = []
            for i in range(index.ntotal):
                case_vectors.append({
                    'faiss_id': i,
                    'vector': vectors[i]
                })
            
            return case_vectors
            
        except Exception as e:
            print(f"获取测试用例向量失败: {e}")
            return []
    
    def generate_training_data(self, similar_pairs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        根据相似对生成训练数据
        
        Args:
            similar_pairs: 相似对列表
            
        Returns:
            训练数据列表
        """
        try:
            print("开始生成训练数据...")
            
            training_data = []
            
            for pair in similar_pairs:
                point_id = pair['point_faiss_id']
                case_id = pair['case_faiss_id']
                
                # 获取需求要点信息
                point_info = self.get_point_by_faiss_id(point_id)
                if not point_info:
                    continue
                
                # 获取测试用例信息
                case_info = self.get_case_by_faiss_id(case_id)
                if not case_info:
                    continue
                
                # 构建测试用例字符串
                test_point = f"测试点：{case_info['case_title']}"
                operation = f"操作步骤：{case_info['test_steps']}"
                expected_result = f"预期结果：{case_info['expected_results']}"
                
                test_case_str = f"{test_point}\n{operation}\n{expected_result}"
                
                # 构建训练数据格式
                training_item = {
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一名软件测试工程师。你的任务是根据需求内容生成测试用例。"
                        },
                        {
                            "role": "user",
                            "content": "你需要用完整的需求内容来理解业务关联和逻辑，然后结合你对业务的理解针对指定的需求内容生成需要的测试用例，需要考虑测试用例覆盖度，切忌不要生成重复的测试用例，不要创造需求"
                        },
                        {
                            "role": "assistant",
                            "content": "好的，我将生成符合要求的测试用例，同时严格按照python list包含dict的 [{\"testpoint\": \"此处为测试点\", \"operation\": \"此处为操作步骤\", \"expectedresult\": \"此处为预期结果\"},{\"testpoint\": \"此处为测试点\", \"operation\": \"此处为操作步骤\", \"expectedresult\": \"此处为预期结果\"}]格式生成"
                        },
                        {
                            "role": "user",
                            "content": f"完整需求内容为：{point_info['point_text']}"
                        },
                        {
                            "role": "assistant",
                            "content": f"[{test_case_str}]"
                        }
                    ],
                    "label": True
                }
                
                training_data.append(training_item)
            
            print(f"成功生成 {len(training_data)} 条训练数据")
            return training_data
            
        except Exception as e:
            print(f"生成训练数据失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def save_training_data(self, training_data: List[Dict[str, Any]], 
                          output_file: str = "similarity_training_data.json") -> bool:
        """
        保存训练数据到文件
        
        Args:
            training_data: 训练数据列表
            output_file: 输出文件路径
            
        Returns:
            是否保存成功
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(training_data, f, ensure_ascii=False, indent=2)
            
            print(f"训练数据已保存到: {output_file}")
            return True
            
        except Exception as e:
            print(f"保存训练数据失败: {e}")
            return False
    
    def run_similarity_matching(self, 
                               top_k: int = 10,
                               min_similarity: float = 0.5,
                               output_file: str = "similarity_training_data.json") -> bool:
        """
        运行完整的相似度匹配流程
        
        Args:
            top_k: 返回结果数量
            min_similarity: 最小相似度阈值
            output_file: 输出文件路径
            
        Returns:
            是否成功
        """
        try:
            print("=" * 50)
            print("开始运行相似度匹配流程")
            print("=" * 50)
            
            # 1. 查找相似对
            similar_pairs = self.find_similar_pairs(top_k, min_similarity)
            if not similar_pairs:
                print("未找到相似对，流程结束")
                return False
            
            # 2. 显示相似对信息
            print(f"\n找到 {len(similar_pairs)} 个相似对:")
            for i, pair in enumerate(similar_pairs, 1):
                print(f"\n{i}. 相似度: {pair['combined_similarity']:.4f}")
                print(f"   余弦相似度: {pair['cosine_similarity']:.4f}")
                print(f"   正弦相似度: {pair['sine_similarity']:.4f}")
                print(f"   需求要点ID: {pair['point_faiss_id']}")
                print(f"   测试用例ID: {pair['case_faiss_id']}")
            
            # 3. 生成训练数据
            training_data = self.generate_training_data(similar_pairs)
            if not training_data:
                print("生成训练数据失败")
                return False
            
            # 4. 保存训练数据
            success = self.save_training_data(training_data, output_file)
            if not success:
                print("保存训练数据失败")
                return False
            
            print("\n" + "=" * 50)
            print("相似度匹配流程完成")
            print(f"共生成 {len(training_data)} 条训练数据")
            print(f"数据已保存到: {output_file}")
            print("=" * 50)
            
            return True
            
        except Exception as e:
            print(f"运行相似度匹配流程失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def close(self):
        """关闭资源"""
        try:
            self.db_manager.close()
            print("资源已关闭")
        except Exception as e:
            print(f"关闭资源失败: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='相似度匹配器')
    parser.add_argument('-k', '--topk', type=int, default=10, help='返回结果数量')
    parser.add_argument('-t', '--threshold', type=float, default=0.5, help='最小相似度阈值')
    parser.add_argument('-o', '--output', default='similarity_training_data.json', help='输出文件路径')
    
    args = parser.parse_args()
    
    try:
        # 创建相似度匹配器
        matcher = SimilarityMatcher()
        
        # 运行相似度匹配流程
        success = matcher.run_similarity_matching(
            top_k=args.topk,
            min_similarity=args.threshold,
            output_file=args.output
        )
        
        if success:
            print("✅ 相似度匹配流程执行成功")
        else:
            print("❌ 相似度匹配流程执行失败")
        
        matcher.close()
        
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 创建相似度匹配器
    matcher = SimilarityMatcher()
    
    # 运行相似度匹配流程
    success = matcher.run_similarity_matching(
        top_k=10,
        min_similarity=0.5,
        output_file="similarity_training_data.json"
    )
    
    if success:
        print("✅ 相似度匹配流程执行成功")
    else:
        print("❌ 相似度匹配流程执行失败")
    
    matcher.close() 