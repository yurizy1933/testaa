"""
文档分析器主程序 - 解析文档图片、提炼内容并存储向量
"""

import sys
import os
import argparse

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.document_analyzer import DocumentAnalyzer

def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(description='文档分析器 - 解析文档图片、提炼内容并存储向量')
    parser.add_argument('--doc', type=str, required=True, help='文档路径')
    parser.add_argument('--config', type=str, default='config.yaml', help='配置文件路径')
    parser.add_argument('--verbose', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    # 检查文档是否存在
    if not os.path.exists(args.doc):
        print(f"❌ 文档不存在: {args.doc}")
        return
    
    print("=" * 60)
    print("文档分析器")
    print("=" * 60)
    print(f"文档路径: {args.doc}")
    print(f"配置文件: {args.config}")
    print(f"详细输出: {args.verbose}")
    
    try:
        # 初始化文档分析器
        analyzer = DocumentAnalyzer(args.config)
        
        # 分析文档
        print(f"\n开始分析文档...")
        result = analyzer.analyze_document(args.doc)
        
        if 'error' in result:
            print(f"❌ 分析失败: {result['error']}")
            return
        
        # 显示分析结果
        print(f"\n✅ 分析完成!")
        print(f"文档路径: {result['doc_path']}")
        print(f"总页数: {result['total_pages']}")
        print(f"总图片数: {result['total_images']}")
        print(f"信息点数: {result['summary_points']}")
        print(f"向量数量: {result['vector_count']}")
        print(f"MySQL存储: {'成功' if result['mysql_success'] else '失败'}")
        
        # 详细输出
        if args.verbose:
            print(f"\n详细结果:")
            
            # 页面结果
            if 'page_results' in result:
                page_results = result['page_results']
                print(f"  页面处理:")
                print(f"    成功: {page_results.get('success', False)}")
                print(f"    总页数: {page_results.get('total_pages', 0)}")
                print(f"    总图片数: {page_results.get('total_images', 0)}")
            
            # 向量结果
            if 'vector_results' in result:
                vector_results = result['vector_results']
                success_count = len([r for r in vector_results if r['success']])
                fail_count = len([r for r in vector_results if not r['success']])
                
                print(f"  向量存储:")
                print(f"    成功: {success_count}")
                print(f"    失败: {fail_count}")
                print(f"    成功率: {success_count/len(vector_results)*100:.1f}%" if vector_results else "0%")
                
                # 显示前几个成功的向量
                success_vectors = [r for r in vector_results if r['success']]
                print(f"  前3个成功向量:")
                for i, vector in enumerate(success_vectors[:3], 1):
                    print(f"    {i}. 类型: {vector['type']}")
                    print(f"        内容: {vector['content'][:50]}...")
                    print(f"        向量ID: {vector['vector_id']}")
        
        # 测试搜索功能
        print(f"\n测试搜索功能...")
        test_queries = ["学习警告", "定时任务", "请假情况"]
        
        for query in test_queries:
            results = analyzer.search_similar_points(query, top_k=3)
            if results:
                print(f"  查询 '{query}': 找到 {len(results)} 个相似信息点")
            else:
                print(f"  查询 '{query}': 未找到相似信息点")
        
        print(f"\n✅ 文档分析完成!")
        
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()

def interactive_mode():
    """交互模式"""
    print("=" * 60)
    print("文档分析器 - 交互模式")
    print("=" * 60)
    
    try:
        analyzer = DocumentAnalyzer("config.yaml")
        
        while True:
            print(f"\n可用命令:")
            print(f"  analyze <文档路径> - 分析文档")
            print(f"  search <查询文本> - 搜索相似信息点")
            print(f"  quit - 退出")
            
            command = input(f"\n请输入命令: ").strip()
            
            if command.startswith('analyze '):
                doc_path = command[8:].strip()
                if os.path.exists(doc_path):
                    print(f"开始分析文档: {doc_path}")
                    result = analyzer.analyze_document(doc_path)
                    
                    if 'error' not in result:
                        print(f"✅ 分析完成!")
                        print(f"  总页数: {result['total_pages']}")
                        print(f"  信息点数: {result['summary_points']}")
                        print(f"  向量数量: {result['vector_count']}")
                    else:
                        print(f"❌ 分析失败: {result['error']}")
                else:
                    print(f"❌ 文档不存在: {doc_path}")
            
            elif command.startswith('search '):
                query = command[7:].strip()
                print(f"搜索查询: {query}")
                results = analyzer.search_similar_points(query, top_k=5)
                
                if results:
                    print(f"找到 {len(results)} 个相似信息点:")
                    for i, result in enumerate(results, 1):
                        print(f"  {i}. 相似度: {result.get('similarity', 0):.3f}")
                        print(f"     内容: {result.get('text', '')[:50]}...")
                        print(f"     类型: {result.get('metadata', {}).get('point_type', 'unknown')}")
                else:
                    print(f"未找到相似信息点")
            
            elif command == 'quit':
                print(f"再见!")
                break
            
            else:
                print(f"❌ 未知命令: {command}")
    
    except KeyboardInterrupt:
        print(f"\n程序被用户中断")
    except Exception as e:
        print(f"❌ 交互模式失败: {e}")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # 没有参数时进入交互模式
        interactive_mode()
    else:
        # 有参数时使用命令行模式
        main() 