#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试用例处理器
解析JSON文件，生成FAISS向量，存储到MySQL数据库
"""

import json
import os
import sys
from typing import List, Dict, Any, Optional
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# 导入项目现有功能
from vector_store import VectorStore
from thread_safe_db import ThreadSafeDatabaseManager
from zhipuai_client import ZhipuaiClient
from config import VECTOR_DIMENSION

class TestCaseProcessor:
    """测试用例处理器"""
    
    def __init__(self, json_file_path: str, case_faiss_index_path: str = "case_faiss_index"):
        """
        初始化测试用例处理器
        
        Args:
            json_file_path: JSON文件路径
            case_faiss_index_path: 测试用例FAISS索引路径
        """
        self.json_file_path = json_file_path
        self.case_faiss_index_path = case_faiss_index_path
        
        # 初始化组件
        self.vector_store = VectorStore(case_faiss_index_path)
        self.db_manager = ThreadSafeDatabaseManager()
        self.zhipuai_client = ZhipuaiClient()
        
        # 创建测试用例表
        self._create_test_case_table()
        
        print("测试用例处理器初始化成功")
    
    def _create_test_case_table(self):
        """创建测试用例表"""
        try:
            connection = self.db_manager._get_connection()
            with connection.cursor() as cursor:
                # 创建测试用例表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS test_cases (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        case_title VARCHAR(1000) NOT NULL COMMENT '用例标题',
                        preconditions TEXT COMMENT '前置条件',
                        test_steps TEXT COMMENT '测试步骤',
                        expected_results TEXT COMMENT '预期结果',
                        case_level VARCHAR(50) COMMENT '用例等级',
                        faiss_id INT COMMENT 'FAISS向量ID',
                        vector_data JSON COMMENT '向量数据',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_case_title (case_title(255)),
                        INDEX idx_faiss (faiss_id),
                        INDEX idx_case_level (case_level)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试用例表'
                """)
            connection.commit()
            print("测试用例表创建成功")
        except Exception as e:
            print(f"创建测试用例表失败: {e}")
            raise
    
    def load_json_data(self) -> List[Dict[str, Any]]:
        """
        加载JSON数据
        
        Returns:
            测试用例列表
        """
        try:
            if not os.path.exists(self.json_file_path):
                raise FileNotFoundError(f"JSON文件不存在: {self.json_file_path}")
            
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"成功加载JSON数据，共 {len(data)} 个测试用例")
            return data
            
        except Exception as e:
            print(f"加载JSON数据失败: {e}")
            raise
    
    def process_single_test_case(self, test_case: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        处理单个测试用例
        
        Args:
            test_case: 测试用例数据
            
        Returns:
            处理结果
        """
        try:
            # 提取用例标题
            case_title = test_case.get('用例标题', '')
            if not case_title:
                print("⚠️  跳过测试用例：缺少用例标题")
                return None
            
            # 获取用例标题的向量表示
            print(f"🔄 处理测试用例: {case_title[:50]}...")
            vector = self.zhipuai_client.get_embedding(case_title)
            
            if vector is None:
                print(f"❌ 获取向量失败: {case_title[:50]}...")
                return None
            
            # 添加到FAISS索引
            faiss_id = self.vector_store.add_vector(vector)
            if faiss_id is None:
                print(f"❌ 添加向量到FAISS失败: {case_title[:50]}...")
                return None
            
            # 准备数据库数据
            db_data = {
                'case_title': case_title,
                'preconditions': test_case.get('前置条件', ''),
                'test_steps': test_case.get('测试步骤', ''),
                'expected_results': test_case.get('预期结果', ''),
                'case_level': test_case.get('用例等级', ''),
                'faiss_id': faiss_id,
                'vector_data': vector
            }
            
            # 存储到数据库
            success = self._store_to_database(db_data)
            if not success:
                print(f"❌ 存储到数据库失败: {case_title[:50]}...")
                return None
            
            print(f"✅ 测试用例处理成功: {case_title[:50]}... (FAISS ID: {faiss_id})")
            return {
                'faiss_id': faiss_id,
                'case_title': case_title,
                'success': True
            }
            
        except Exception as e:
            print(f"❌ 处理测试用例失败: {e}")
            return None
    
    def _store_to_database(self, db_data: Dict[str, Any]) -> bool:
        """
        存储测试用例到数据库
        
        Args:
            db_data: 数据库数据
            
        Returns:
            是否成功
        """
        try:
            connection = self.db_manager._get_connection()
            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO test_cases 
                    (case_title, preconditions, test_steps, expected_results, case_level, faiss_id, vector_data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    db_data['case_title'],
                    db_data['preconditions'],
                    db_data['test_steps'],
                    db_data['expected_results'],
                    db_data['case_level'],
                    db_data['faiss_id'],
                    json.dumps(db_data['vector_data'])
                ))
            connection.commit()
            return True
            
        except Exception as e:
            print(f"存储到数据库失败: {e}")
            return False
    
    def process_all_test_cases(self, max_workers: int = 5) -> Dict[str, Any]:
        """
        处理所有测试用例
        
        Args:
            max_workers: 最大工作线程数
            
        Returns:
            处理结果统计
        """
        try:
            # 加载JSON数据
            test_cases = self.load_json_data()
            
            if not test_cases:
                print("没有找到测试用例数据")
                return {'total': 0, 'success': 0, 'failed': 0}
            
            print(f"🚀 开始处理 {len(test_cases)} 个测试用例...")
            
            # 统计信息
            total_count = len(test_cases)
            success_count = 0
            failed_count = 0
            
            # 使用线程池并发处理
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                future_to_case = {
                    executor.submit(self.process_single_test_case, case): case 
                    for case in test_cases
                }
                
                # 处理完成的任务
                for future in as_completed(future_to_case):
                    case = future_to_case[future]
                    try:
                        result = future.result()
                        if result and result.get('success'):
                            success_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        print(f"❌ 任务执行失败: {e}")
                        failed_count += 1
            
            # 保存FAISS索引
            self.vector_store.save_index()
            
            # 统计结果
            stats = {
                'total': total_count,
                'success': success_count,
                'failed': failed_count,
                'success_rate': f"{(success_count / total_count * 100):.2f}%" if total_count > 0 else "0%"
            }
            
            print(f"\n🎉 处理完成！")
            print(f"📊 统计信息:")
            print(f"   总数量: {stats['total']}")
            print(f"   成功: {stats['success']}")
            print(f"   失败: {stats['failed']}")
            print(f"   成功率: {stats['success_rate']}")
            
            # 显示FAISS索引统计
            faiss_stats = self.vector_store.get_index_stats()
            print(f"🔍 FAISS索引统计:")
            print(f"   总向量数: {faiss_stats.get('total_vectors', 0)}")
            print(f"   向量维度: {faiss_stats.get('dimension', 0)}")
            print(f"   下一个向量ID: {faiss_stats.get('next_vector_id', 0)}")
            
            return stats
            
        except Exception as e:
            print(f"❌ 处理所有测试用例失败: {e}")
            import traceback
            traceback.print_exc()
            return {'total': 0, 'success': 0, 'failed': 0}
    
    def search_similar_cases(self, query_text: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索相似测试用例
        
        Args:
            query_text: 查询文本
            k: 返回结果数量
            
        Returns:
            相似测试用例列表
        """
        try:
            # 获取查询文本的向量
            query_vector = self.zhipuai_client.get_embedding(query_text)
            if query_vector is None:
                print("获取查询向量失败")
                return []
            
            # 搜索相似向量
            similar_vectors = self.vector_store.search_similar(query_vector, k)
            
            # 获取测试用例详情
            similar_cases = []
            for vector_result in similar_vectors:
                case_info = self._get_case_by_faiss_id(vector_result['id'])
                if case_info:
                    case_info['similarity_score'] = vector_result['score']
                    similar_cases.append(case_info)
            
            print(f"🔍 搜索完成，找到 {len(similar_cases)} 个相似测试用例")
            return similar_cases
            
        except Exception as e:
            print(f"搜索相似测试用例失败: {e}")
            return []
    
    def _get_case_by_faiss_id(self, faiss_id: int) -> Optional[Dict[str, Any]]:
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
    
    parser = argparse.ArgumentParser(description='测试用例处理器')
    parser.add_argument('-j', '--json', required=True, help='JSON文件路径')
    parser.add_argument('-i', '--index', default='case_faiss_index', help='FAISS索引路径')
    parser.add_argument('-w', '--workers', type=int, default=5, help='工作线程数')
    parser.add_argument('-s', '--search', help='搜索相似测试用例的查询文本')
    parser.add_argument('-k', '--topk', type=int, default=5, help='搜索结果数量')
    
    args = parser.parse_args()
    
    try:
        # 创建处理器
        processor = TestCaseProcessor(args.json, args.index)
        
        if args.search:
            # 搜索模式
            print(f"🔍 搜索相似测试用例: {args.search}")
            similar_cases = processor.search_similar_cases(args.search, args.topk)
            
            print(f"\n📋 搜索结果:")
            for i, case in enumerate(similar_cases, 1):
                print(f"\n{i}. 相似度: {case['similarity_score']:.4f}")
                print(f"   用例标题: {case['case_title']}")
                print(f"   前置条件: {case['preconditions'][:100]}{'...' if len(case['preconditions']) > 100 else ''}")
                print(f"   测试步骤: {case['test_steps'][:100]}{'...' if len(case['test_steps']) > 100 else ''}")
                print(f"   预期结果: {case['expected_results'][:100]}{'...' if len(case['expected_results']) > 100 else ''}")
                print(f"   用例等级: {case['case_level']}")
        else:
            # 处理模式
            processor.process_all_test_cases(args.workers)
        
        processor.close()
        
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # 创建处理器
    processor = TestCaseProcessor("测试用例.json", "case_faiss_index")

    # 处理所有测试用例
    stats = processor.process_all_test_cases(max_workers=5)

    # 搜索相似测试用例
    # similar_cases = processor.search_similar_cases("幂等校验", k=5)
    # main()