#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import argparse
from thread_safe_db import ThreadSafeDatabaseManager
from zhipuai_client import ZhipuaiClient
from vector_store import VectorStore
from word_parser import WordParser
from text_summarizer import TextSummarizer

def process_document(file_path):
    """处理单个Word文档的核心函数"""
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"❌ 文档不存在: {file_path}")
        return False
    
    # 检查文件扩展名
    if not file_path.lower().endswith(('.docx', '.doc')):
        print("❌ 错误: 只支持Word文档格式 (.docx, .doc)")
        return False
    
    try:
        print("=" * 50)
        print("Word文档解析和向量化工具")
        print("=" * 50)
        
        # 初始化各个模块
        print("\n1. 初始化数据库连接...")
        db_manager = ThreadSafeDatabaseManager()
        
        print("\n2. 初始化智谱AI客户端...")
        zhipuai_client = ZhipuaiClient()
        
        print("\n3. 初始化向量存储...")
        vector_store = VectorStore()
        
        print("\n4. 初始化Word解析器...")
        word_parser = WordParser(zhipuai_client, use_concurrent=True, max_workers=4)
        
        print("\n5. 初始化文本总结器...")
        text_summarizer = TextSummarizer(zhipuai_client, vector_store, db_manager, use_concurrent=True, max_workers=4)
        
        print("\n" + "=" * 50)
        print("开始处理文档...")
        print("=" * 50)
        
        # 解析Word文档
        print("\n步骤1: 解析Word文档")
        file_name, sections = word_parser.parse_document(file_path)
        
        # 处理每个章节的内容
        print("\n步骤2: 处理文档内容")
        all_processed_content = []
        
        if word_parser.use_concurrent:
            # 并发处理所有章节的内容块
            print("使用并发处理模式")
            
            for section_index, section in enumerate(sections, 1):
                print(f"\n处理第 {section_index} 个章节: {section['title']}，共 {len(section['content'])} 个内容块")
                
                # 并发处理当前章节的所有内容块
                processed_results = word_parser.concurrent_processor.process_content_blocks_concurrent(
                    section['content'],
                    word_parser.process_content_block,
                    file_name, section['title'], section['level'], db_manager
                )
                
                # 收集处理结果
                for paragraph_number, result in enumerate(processed_results, 1):
                    if result:
                        all_processed_content.append(result)
                        print(f"    ✅ 第 {paragraph_number} 个内容块处理成功")
                    else:
                        print(f"    ❌ 第 {paragraph_number} 个内容块处理失败")
        else:
            # 串行处理
            print("使用串行处理模式")
            
            for section_index, section in enumerate(sections, 1):
                print(f"\n处理第 {section_index} 个章节: {section['title']}，共 {len(section['content'])} 个内容块")
                
                for paragraph_number, block in enumerate(section['content'], 1):
                    print(f"  处理第 {paragraph_number} 个内容块，类型: {block['type']}")
                    
                    processed_content = word_parser.process_content_block(
                        block, file_name, section['title'], section['level'], paragraph_number, db_manager
                    )
                    
                    if processed_content:
                        all_processed_content.append(processed_content)
                        print(f"    ✅ 内容块处理成功")
                    else:
                        print(f"    ❌ 内容块处理失败")
        
        print(f"\n内容处理完成，共处理 {len(all_processed_content)} 个内容块")
        
        # 总结和向量化
        print("\n步骤3: 总结和向量化")
        points = text_summarizer.summarize_and_vectorize(file_name)
        
        # 显示统计信息
        print("\n" + "=" * 50)
        print("处理完成！")
        print("=" * 50)
        
        stats = vector_store.get_index_stats()
        print(f"文档名称: {file_name}")
        print(f"总章节数: {len(sections)}")
        print(f"处理的内容块数: {len(all_processed_content)}")
        print(f"生成的要点数: {len(points)}")
        print(f"向量库中的向量总数: {stats.get('total_vectors', 0)}")
        
        print("\n章节结构:")
        for i, section in enumerate(sections, 1):
            print(f"{i}. {section['title']} (级别: {section['level']})")
        
        print("\n生成的要点:")
        for i, point in enumerate(points, 1):
            section_info = f" [{point.get('section', '未知章节')}]" if 'section' in point else ""
            print(f"{i}. {point['text'][:100]}...{section_info}")
        
        print("\n所有数据已保存到数据库和向量库中")
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n用户中断处理")
        return False
    except Exception as e:
        print(f"\n处理过程中发生错误: {e}")
        return False
    finally:
        # 清理资源
        try:
            if 'db_manager' in locals():
                db_manager.close()
            print("\n资源清理完成")
        except Exception as e:
            print(f"资源清理时发生错误: {e}")

def main():
    """主函数 - 支持命令行和直接调用两种方式"""
    # 检查是否通过命令行调用
    if len(sys.argv) > 1:
        # 命令行调用方式
        parser = argparse.ArgumentParser(description='Word文档解析和向量化工具')
        parser.add_argument('file_path', help='Word文档路径')
        parser.add_argument('--config', help='配置文件路径', default='.env')
        
        args = parser.parse_args()
        success = process_document(args.file_path)
        sys.exit(0 if success else 1)
    else:
        # 直接调用方式 - 用于调试
        print("调试模式 - 直接调用主函数")
        
        # 测试文档路径 - 可以在这里修改要处理的文档路径
        # doc_path = "documents/洋么科技需求文档.docx"
        doc_path = "documents/AuthorizationPRDF.docx"
        
        if not os.path.exists(doc_path):
            print(f"❌ 文档不存在: {doc_path}")
            print("请检查文档路径是否正确，或修改main.py中的doc_path变量")
            return
        
        success = process_document(doc_path)
        if success:
            print("✅ 文档处理成功！")
        else:
            print("❌ 文档处理失败！")

if __name__ == "__main__":
    main() 