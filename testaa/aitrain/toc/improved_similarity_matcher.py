#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进版相似度匹配器
解决PIN检查被误匹配到CVC检查的问题
增加关键词权重和精确匹配机制
"""

import numpy as np
import faiss
import pickle
import os
import re
from typing import List, Dict, Any, Tuple, Optional
from vector_store import VectorStore
from case_to_faiss_processor import TestCaseProcessor
from thread_safe_db import ThreadSafeDatabaseManager
import json

class ImprovedSimilarityMatcher:
    """改进版相似度匹配器"""
    
    def __init__(self, 
                 faiss_index_path: str = "faiss_index",
                 case_faiss_index_path: str = "case_faiss_index",
                 similarity_threshold: float = 0.7):
        """
        初始化改进版相似度匹配器
        
        Args:
            faiss_index_path: 需求文档FAISS索引路径
            case_faiss_index_path: 测试用例FAISS索引路径
            similarity_threshold: 相似度阈值
        """
        self.faiss_index_path = faiss_index_path
        self.case_faiss_index_path = case_faiss_index_path
        self.similarity_threshold = similarity_threshold
        
        # 初始化组件
        # 分别为需求要点与测试用例使用各自的向量索引
        self.point_vector_store = VectorStore(faiss_index_path)
        self.case_vector_store = VectorStore(case_faiss_index_path)
        self.case_processor = TestCaseProcessor("测试用例.json", case_faiss_index_path)
        self.db_manager = ThreadSafeDatabaseManager()
        
        # 关键词权重配置
        self.keyword_weights = {
            'PIN': 2.0,
            'CVC': 2.0,
            'CVC2': 2.0,
            '冲正': 2.0,
            '激活': 2.0,
            '增量交易': 2.0,
            '正向交易': 2.0,
            '反向交易': 2.0,
            '卡封锁码': 1.5,
            '取现': 1.3,
            '卡状态': 1.5,
            'ARQC': 1.5,
            'UCAF': 1.5,
            '反欺诈': 1.5,
            '安全开关': 1.5,
            '流量': 1.5,
        }
        
        print("改进版相似度匹配器初始化成功")
    
    def extract_keywords(self, text: str) -> List[str]:
        """
        提取文本中的关键词
        
        Args:
            text: 输入文本
            
        Returns:
            关键词列表
        """
        keywords = []
        
        # 提取关键词
        for keyword in self.keyword_weights.keys():
            if keyword in text:
                keywords.append(keyword)
        
        # 提取其他重要词汇
        patterns = [
            r'[A-Z]+\d*',  # 大写字母+数字组合
            r'DE\d+',      # DE开头的数字
            r'Phase\s*\d+', # Phase + 数字
            r'检查点\d+',    # 检查点 + 数字
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            keywords.extend(matches)
        
        return list(set(keywords))  # 去重
    
    def calculate_keyword_similarity(self, text1: str, text2: str) -> float:
        """
        计算关键词相似度
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            关键词相似度
        """
        keywords1 = set(self.extract_keywords(text1))
        keywords2 = set(self.extract_keywords(text2))
        
        if not keywords1 and not keywords2:
            return 0.0
        
        if not keywords1 or not keywords2:
            return 0.0
        
        # 计算交集和并集
        intersection = keywords1.intersection(keywords2)
        union = keywords1.union(keywords2)
        
        # Jaccard相似度
        jaccard_sim = len(intersection) / len(union) if union else 0.0
        
        # 关键词权重加权
        weighted_score = 0.0
        total_weight = 0.0
        
        for keyword in intersection:
            weight = self.keyword_weights.get(keyword, 1.0)
            weighted_score += weight
            total_weight += weight
        
        for keyword in union:
            if keyword not in intersection:
                weight = self.keyword_weights.get(keyword, 1.0)
                total_weight += weight
        
        if total_weight > 0:
            weighted_similarity = weighted_score / total_weight
        else:
            weighted_similarity = 0.0
        
        # 结合Jaccard相似度和权重相似度
        final_similarity = 0.6 * jaccard_sim + 0.4 * weighted_similarity
        
        return final_similarity
    
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
            sine_sim = np.sqrt(max(0, 1 - cosine_sim ** 2))
            return float(sine_sim)
            
        except Exception as e:
            print(f"计算正弦相似度失败: {e}")
            return 0.0
    
    def calculate_enhanced_similarity(self, 
                                   vector1: np.ndarray, vector2: np.ndarray,
                                   text1: str, text2: str) -> Dict[str, float]:
        """
        计算增强型相似度（结合向量相似度和关键词相似度）
        
        Args:
            vector1: 向量1
            vector2: 向量2
            text1: 文本1
            text2: 文本2
            
        Returns:
            包含各种相似度的字典
        """
        # 计算向量相似度
        cosine_sim = self.calculate_cosine_similarity(vector1, vector2)
        sine_sim = self.calculate_sine_similarity(vector1, vector2)
        
        # 计算关键词相似度
        keyword_sim = self.calculate_keyword_similarity(text1, text2)
        
        # 计算综合相似度（启用动态权重，纳入关键词相似度）
        if keyword_sim > 0.8:
            combined_sim = 0.3 * cosine_sim + 0.2 * sine_sim + 0.5 * keyword_sim
        elif keyword_sim > 0.5:
            combined_sim = 0.4 * cosine_sim + 0.2 * sine_sim + 0.4 * keyword_sim
        else:
            combined_sim = 0.6 * cosine_sim + 0.3 * sine_sim + 0.1 * keyword_sim

        return {
            'cosine_similarity': cosine_sim,
            'sine_similarity': sine_sim,
            'keyword_similarity': keyword_sim,
            'combined_similarity': combined_sim
        }
    
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
    
    def find_similar_pairs_enhanced(self, top_k: int = 1000, min_similarity: float = 0.8,
                                   batch_size: int = 50) -> List[Dict[str, Any]]:
        """
        增强版相似对查找（分批计算，确保覆盖每条point）
        
        Args:
            top_k: 每个point最多返回的相似case数量
            min_similarity: 最小相似度阈值
            batch_size: 每批处理的point数量
            
        Returns:
            相似对列表
        """
        try:
            print(f"开始查找相似的需求要点和测试用例对（分批计算，批次大小：{batch_size}）...")
            
            # 获取所有point和case数据
            point_data = self.get_all_points()
            case_data = self.get_all_cases()
            
            if not point_data or not case_data:
                print("❌ 没有找到point或case数据")
                return []
            
            print(f"找到 {len(point_data)} 个需求要点和 {len(case_data)} 个测试用例")
            
            # 分批处理point
            all_similar_pairs = []
            total_points = len(point_data)
            
            for batch_start in range(0, total_points, batch_size):
                batch_end = min(batch_start + batch_size, total_points)
                batch_points = point_data[batch_start:batch_end]
                
                print(f"处理第 {batch_start//batch_size + 1} 批: point {batch_start+1}-{batch_end} (共{total_points}个)")
                
                batch_pairs = []
                calculation_count = 0
                
                # 限制每批的计算数量以提高性能
                max_calculations_per_batch = min(top_k * 20, len(batch_points) * len(case_data))
                
                for point in batch_points:
                    point_faiss_id = point['faiss_id']
                    point_embedding = point['embedding']
                    point_text = point['point_text']
                    
                    # 为每个point计算与所有case的相似度
                    for case in case_data:
                        if calculation_count >= max_calculations_per_batch:
                            break
                            
                        case_faiss_id = case['faiss_id']
                        case_embedding = case['embedding']
                        case_title = case['case_title']
                        
                        # 计算增强相似度
                        similarities = self.calculate_enhanced_similarity(
                            point_embedding, case_embedding, point_text, case_title
                        )
                        
                        # 只保留满足阈值的相似对
                        combined_sim = similarities['combined_similarity']
                        if combined_sim >= min_similarity:
                            batch_pairs.append({
                                'point_faiss_id': point_faiss_id,
                                'case_faiss_id': case_faiss_id,
                                'combined_similarity': combined_sim,
                                'cosine_similarity': similarities['cosine_similarity'],
                                'sine_similarity': similarities['sine_similarity'],
                                'keyword_similarity': similarities['keyword_similarity'],
                                'point_text': point_text,
                                'case_title': case_title
                            })
                        
                        calculation_count += 1
                    
                    if calculation_count >= max_calculations_per_batch:
                        break
                
                # 对当前批次的结果进行排序和限制
                if batch_pairs:
                    # 按point分组，每个point最多保留top_k个case
                    point_to_cases = {}
                    for pair in batch_pairs:
                        point_id = pair['point_faiss_id']
                        if point_id not in point_to_cases:
                            point_to_cases[point_id] = []
                        point_to_cases[point_id].append(pair)
                    
                    # 对每个point的case按相似度排序，取前top_k个
                    for point_id in point_to_cases:
                        point_to_cases[point_id].sort(
                            key=lambda x: x['combined_similarity'], 
                            reverse=True
                        )
                        point_to_cases[point_id] = point_to_cases[point_id][:top_k]
                    
                    # 合并所有case
                    batch_result = []
                    for cases in point_to_cases.values():
                        batch_result.extend(cases)
                    
                    all_similar_pairs.extend(batch_result)
                    
                    print(f"  批次完成: 找到 {len(batch_result)} 个相似对")
                else:
                    print(f"  批次完成: 未找到相似对")
            
            # 最终统计
            print(f"分批计算完成，总共找到 {len(all_similar_pairs)} 个相似对")
            
            # 按相似度排序
            all_similar_pairs.sort(key=lambda x: x['combined_similarity'], reverse=True)
            
            return all_similar_pairs
            
        except Exception as e:
            print(f"查找相似对失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_all_points(self) -> List[Dict[str, Any]]:
        """获取所有需求要点数据"""
        try:
            # 使用数据库管理器的现有方法
            point_records = self.db_manager.get_all_points()
            
            if not point_records:
                return []
            
            # 从FAISS获取对应的向量
            point_data = []
            for record in point_records:
                faiss_id = record['faiss_id']
                point_text = record['point_text']
                
                # 获取向量
                vector = self.point_vector_store.get_vector_by_id(faiss_id)
                if vector is not None:
                    point_data.append({
                        'faiss_id': faiss_id,
                        'point_text': point_text,
                        'embedding': vector
                    })
            
            return point_data
            
        except Exception as e:
            print(f"获取point数据失败: {e}")
            return []
    
    def get_all_cases(self) -> List[Dict[str, Any]]:
        """获取所有测试用例数据"""
        try:
            # 使用数据库管理器的现有方法
            case_records = self.db_manager.get_all_cases()
            
            if not case_records:
                return []
            
            # 从FAISS获取对应的向量
            case_data = []
            for record in case_records:
                faiss_id = record['faiss_id']
                case_title = record['case_title']
                
                # 获取向量
                vector = self.case_vector_store.get_vector_by_id(faiss_id)
                if vector is not None:
                    case_data.append({
                        'faiss_id': faiss_id,
                        'case_title': case_title,
                        'embedding': vector
                    })
            
            return case_data
            
        except Exception as e:
            print(f"获取case数据失败: {e}")
            return []
    
    def generate_training_data(self, similar_pairs: List[Dict[str, Any]], cases_per_point: int = 5) -> List[Dict[str, Any]]:
        """
        根据相似对生成训练数据（按point分组，一对多case，允许case重复使用）
        
        Args:
            similar_pairs: 相似对列表（包含point和case的匹配）
            cases_per_point: 每个point最多选取的case数量（上限10）
            
        Returns:
            训练数据列表（每条为一个point，assistant内容包含多个case，允许case重复）
        """
        try:
            print("开始生成训练数据（按point聚合，允许case重复使用）...")
            
            # 统一限制每个point的case数量上限为10
            cases_limit = min(max(1, cases_per_point), 10)
            
            # 1) 按 point 分组，收集所有匹配到的 case，并按综合相似度排序
            point_to_cases: Dict[int, List[Dict[str, Any]]] = {}
            for pair in similar_pairs:
                point_id = pair['point_faiss_id']
                point_to_cases.setdefault(point_id, []).append(pair)
            
            # 2) 确保point的维度，优先选择case数量适中的point
            min_points = 20  # 最少需要20个不同的point
            max_points = 600  # 最多处理600个不同的point
            
            # 按point的case数量排序，优先处理case数量适中的point（避免过多或过少）
            def point_score(item):
                case_count = len(item[1])
                # 优先选择case数量在5-50之间的point
                if 5 <= case_count <= 50:
                    return case_count  # case数量适中，按数量排序
                elif case_count < 5:
                    return case_count + 1000  # case数量太少，优先级低
                else:
                    return case_count + 2000  # case数量太多，优先级低
            
            sorted_points = sorted(point_to_cases.items(), key=point_score)
            
            # 确保至少选择min_points个point
            if len(sorted_points) < min_points:
                print(f"⚠️  警告：只有 {len(sorted_points)} 个point，少于最小要求 {min_points}")
                selected_points = sorted_points
            else:
                # 选择前max_points个point
                selected_points = sorted_points[:max_points]
            
            print(f"从 {len(point_to_cases)} 个point中选择 {len(selected_points)} 个point进行处理")
            
            training_data: List[Dict[str, Any]] = []
            used_cases = set()  # 记录已使用的case，但不限制重复使用
            
            # 3) 逐个 point 生成一条训练数据，包含多个测试用例
            for point_id, case_pairs in selected_points:
                # 按综合相似度降序排序
                sorted_pairs = sorted(case_pairs, key=lambda x: x.get('combined_similarity', 0), reverse=True)
                
                # 取前 N 个（上限cases_limit）
                top_pairs = sorted_pairs[:cases_limit]
                
                # 获取需求要点信息
                point_info = self.get_point_by_faiss_id(point_id)
                if not point_info or not point_info.get('point_text'):
                    continue
                
                # 组装测试用例列表（list of dict）
                test_cases: List[Dict[str, Any]] = []
                case_details = []  # 保存case的详细信息
                
                for tp in top_pairs:
                    case_id = tp['case_faiss_id']
                    case_info = self.get_case_by_faiss_id(case_id)
                    if not case_info:
                        continue
                    
                    # 记录使用的case（用于统计，但不限制重复）
                    used_cases.add(case_id)
                    
                    # 构建测试用例
                    test_case = {
                        "testpoint": case_info['case_title'],
                        "operation": case_info['test_steps'] if case_info['test_steps'] else "执行测试步骤",
                        "expectedresult": case_info['expected_results'] if case_info['expected_results'] else "验证预期结果"
                    }
                    test_cases.append(test_case)
                    
                    # 保存case详细信息
                    case_details.append({
                        "case_id": case_id,
                        "case_title": case_info['case_title'],
                        "similarity_scores": {
                            "combined": tp.get('combined_similarity', 0),
                            "cosine": tp.get('cosine_similarity', 0),
                            "sine": tp.get('sine_similarity', 0),
                            "keyword": tp.get('keyword_similarity', 0)
                        }
                    })
                
                if not test_cases:
                    continue
                
                # assistant 内容为 JSON 数组字符串
                assistant_content = json.dumps(test_cases, ensure_ascii=False)
                
                # 构建完整的训练数据JSON对象
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
                            "content": assistant_content
                        }
                    ],
                    "label": True
                }
                
                training_data.append(training_item)
            
            # 统计信息
            total_cases_used = len(used_cases)
            total_training_items = len(training_data)
            # avg_cases_per_point = sum(item['metadata']['case_count'] for item in training_data) / total_training_items if total_training_items > 0 else 0
            
            print(f"成功生成 {len(training_data)} 条训练数据")
            print(f"  - 使用了 {total_cases_used} 个不同的测试用例")
            # print(f"  - 平均每条数据包含 {avg_cases_per_point:.1f} 个测试用例")
            print(f"  - 允许测试用例重复使用，提高point维度")
            print(f"  - 每条训练数据包含完整的JSON结构")
            
            return training_data
            
        except Exception as e:
            print(f"生成训练数据失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def run_enhanced_similarity_matching(self, top_k: int = 1000, min_similarity: float = 0.3, 
                                       output_file: str = "enhanced_similarity_output.jsonl", 
                                       cases_per_point: int = 5, batch_size: int = 50) -> bool:
        """
        运行增强型相似度匹配流程
        
        Args:
            top_k: 每个point最多返回的相似case数量
            min_similarity: 最小相似度阈值
            output_file: 输出文件名（JSONL格式）
            cases_per_point: 每个point最多选取的case数量
            batch_size: 每批处理的point数量
            
        Returns:
            是否成功
        """
        try:
            print("🚀 开始增强型相似度匹配流程")
            print(f"参数: top_k={top_k}, min_similarity={min_similarity}, cases_per_point={cases_per_point}, batch_size={batch_size}")
            
            # 1. 查找相似对（分批计算）
            similar_pairs = self.find_similar_pairs_enhanced(
                top_k=top_k, 
                min_similarity=min_similarity,
                batch_size=batch_size
            )
            
            if not similar_pairs:
                print("❌ 未找到相似对")
                return False
            
            # 2. 生成训练数据
            training_data = self.generate_training_data(similar_pairs, cases_per_point)
            
            if not training_data:
                print("❌ 生成训练数据失败")
                return False
            
            # 3. 保存结果为JSONL格式
            with open(output_file, 'w', encoding='utf-8') as f:
                for item in training_data:
                    json_line = json.dumps(item, ensure_ascii=False)
                    f.write(json_line + '\n')
            
            print(f"✅ 增强型相似度匹配完成！")
            print(f"   - 找到 {len(similar_pairs)} 个相似对")
            print(f"   - 生成 {len(training_data)} 条训练数据")
            print(f"   - 结果保存到: {output_file} (JSONL格式)")
            
            return True
            
        except Exception as e:
            print(f"❌ 增强型相似度匹配失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def save_training_data(self, training_data: List[Dict[str, Any]], 
                          output_file: str = "enhanced_similarity_training_data.jsonl") -> bool:
        """
        保存训练数据到文件（JSONL格式）
        
        Args:
            training_data: 训练数据列表
            output_file: 输出文件路径（JSONL格式）
            
        Returns:
            是否保存成功
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for item in training_data:
                    json_line = json.dumps(item, ensure_ascii=False)
                    f.write(json_line + '\n')
            
            print(f"训练数据已保存到: {output_file} (JSONL格式，{len(training_data)} 行)")
            return True
            
        except Exception as e:
            print(f"保存训练数据失败: {e}")
            return False
    
    def close(self):
        """关闭资源"""
        try:
            self.db_manager.close()
            print("资源已关闭")
        except Exception as e:
            print(f"关闭资源失败: {e}")


if __name__ == "__main__":
    # 创建改进版相似度匹配器
    matcher = ImprovedSimilarityMatcher()
    
    # 运行增强型相似度匹配流程（分批计算，确保覆盖每条point）
    success = matcher.run_enhanced_similarity_matching(
        top_k=10000,  # 大幅增加计算范围以确保有足够多的相似对
        min_similarity=0.75,  # 进一步降低阈值以获得更多匹配
        output_file="documents/enhanced_similarity_output.jsonl",
        cases_per_point=10,
        batch_size=30  # 每批处理30个point，确保覆盖所有point
    )
    
    if success:
        print("✅ 增强型相似度匹配流程执行成功")
    else:
        print("❌ 增强型相似度匹配流程执行失败")
    
    matcher.close() 