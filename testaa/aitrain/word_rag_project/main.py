"""
Word文档RAG系统 - 主程序
"""

import os
import sys
import argparse
from typing import List

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.rag_processor import RAGProcessor

def process_single_document(processor: RAGProcessor, doc_path: str):
    """处理单个文档"""
    print(f"\n{'='*50}")
    print(f"处理文档: {doc_path}")
    print(f"{'='*50}")

    try:
        result = processor.process_document(doc_path)
        print(f"处理完成!")
        print(f"状态: {result['status']}")
        if result['status'] == 'success':
            print(f"总页数: {result['total_pages']}")
            print(f"处理页数: {result['processed_pages']}")
            print(f"向量数量: {result['total_vectors']}")
            print(f"处理时间: {result['processing_time']:.2f}秒")
        elif result['status'] == 'completed':
            print(f"文档已处理完成")
            print(f"总页数: {result['total_pages']}")
            print(f"已处理页数: {result['processed_pages']}")
    except Exception as e:
        print(f"处理失败: {str(e)}")

def process_document_by_pages(processor: RAGProcessor, doc_path: str, start_page: int = 1):
    """逐页处理文档"""
    print(f"\n{'='*50}")
    print(f"逐页处理文档: {doc_path}")
    print(f"从第 {start_page} 页开始")
    print(f"{'='*50}")

    try:
        total_vectors = 0
        success_pages = 0

        for page_result in processor.process_document_by_pages(doc_path, start_page):
            if page_result['success']:
                total_vectors += page_result['vector_count']
                success_pages += 1
                print(f"第 {page_result['page']} 页处理完成: {page_result['vector_count']} 个向量")
            else:
                print(f"第 {page_result['page']} 页处理失败: {page_result.get('error', '未知错误')}")

        print(f"\n处理完成!")
        print(f"成功处理页数: {success_pages}")
        print(f"总向量数: {total_vectors}")

    except Exception as e:
        print(f"处理失败: {str(e)}")

def show_document_status(processor: RAGProcessor, doc_path: str):
    """显示文档处理状态"""
    print(f"\n{'='*50}")
    print(f"文档处理状态: {doc_path}")
    print(f"{'='*50}")

    try:
        status = processor.get_document_status(doc_path)
        print(f"状态: {status['status']}")

        if status['status'] == 'in_progress':
            print(f"总页数: {status['total_pages']}")
            print(f"已处理页数: {status['processed_pages']}")
            print(f"最后处理页: {status['last_processed_page']}")
            print(f"进度: {status['progress_percentage']}%")
            print(f"向量数量: {status['total_vectors']}")
        elif status['status'] == 'completed':
            print(f"文档已处理完成")
            print(f"总页数: {status['total_pages']}")
            print(f"向量数量: {status['total_vectors']}")
        elif status['status'] == 'not_started':
            print(f"文档未开始处理")
        else:
            print(f"错误: {status.get('error', '未知错误')}")

    except Exception as e:
        print(f"获取状态失败: {str(e)}")

def search_similar_content(processor: RAGProcessor, query: str):
    """搜索相似内容"""
    print(f"\n{'='*50}")
    print(f"搜索查询: {query}")
    print(f"{'='*50}")

    results = processor.search_similar(query, top_k=5, threshold=0.6)

    if not results:
        print("未找到相似内容")
        return

    for i, result in enumerate(results, 1):
        print(f"\n结果 {i}:")
        print(f"相似度: {result['similarity']:.3f}")
        print(f"页码: {result['metadata']['page']}")
        print(f"文档: {result['metadata']['doc_name']}")
        print(f"内容: {result['metadata']['text'][:200]}...")

def answer_question(processor: RAGProcessor, question: str):
    """回答问题"""
    print(f"\n{'='*50}")
    print(f"问题: {question}")
    print(f"{'='*50}")

    success, answer = processor.answer_question(question)

    if success:
        print(f"答案: {answer}")
    else:
        print(f"无法回答: {answer}")

def get_document_summary(processor: RAGProcessor, doc_path: str):
    """获取文档摘要"""
    print(f"\n{'='*50}")
    print(f"文档摘要: {doc_path}")
    print(f"{'='*50}")

    success, summary = processor.get_document_summary(doc_path)

    if success:
        print(f"摘要: {summary}")
    else:
        print(f"获取摘要失败: {summary}")

def show_index_stats(processor: RAGProcessor):
    """显示索引统计"""
    print(f"\n{'='*50}")
    print("系统统计信息")
    print(f"{'='*50}")

    stats = processor.get_index_stats()
    print(f"FAISS向量数: {stats.get('total_vectors', 0)}")
    print(f"向量维度: {stats.get('vector_dimension', 0)}")
    print(f"索引类型: {stats.get('index_type', 'Unknown')}")
    print(f"内存元数据数量: {stats.get('metadata_count', 0)}")
    print(f"数据库文档数: {stats.get('total_documents', 0)}")
    print(f"数据库向量数: {stats.get('total_vectors', 0)}")

    # 显示最近处理状态
    recent_processing = stats.get('recent_processing', [])
    if recent_processing:
        print(f"\n最近处理记录:")
        for record in recent_processing[:5]:
            print(f"  {record['doc_path']}: {record['success_chunks']}/{record['total_chunks']} 块")

def show_document_list(processor: RAGProcessor):
    """显示文档列表"""
    print(f"\n{'='*50}")
    print("文档列表")
    print(f"{'='*50}")

    documents = processor.get_document_list()
    if not documents:
        print("暂无文档")
        return

    for i, doc in enumerate(documents, 1):
        print(f"{i}. {doc['doc_name']}")
        print(f"   路径: {doc['doc_path']}")
        print(f"   页数: {doc['total_pages']}, 字数: {doc['total_words']}")
        print(f"   文件大小: {doc['file_size']} bytes")
        print(f"   处理时间: {doc['processed_time']}")
        print()

def delete_document(processor: RAGProcessor, doc_path: str):
    """删除文档"""
    print(f"\n{'='*50}")
    print(f"删除文档: {doc_path}")
    print(f"{'='*50}")

    success = processor.delete_document(doc_path)
    if success:
        print("文档删除成功")
    else:
        print("文档删除失败")

def interactive_mode(processor: RAGProcessor):
    """交互模式"""
    print("\n进入交互模式，输入 'quit' 退出")
    print("可用命令:")
    print("  process <文档路径> - 处理文档")
    print("  pages <文档路径> [起始页] - 逐页处理文档")
    print("  status <文档路径> - 查看文档处理状态")
    print("  search <查询文本> - 搜索相似内容")
    print("  ask <问题> - 基于文档回答问题")
    print("  stats - 显示系统统计")
    print("  prdDocs - 显示文档列表")
    print("  clear - 清空索引")
    print("  delete <文档路径> - 删除文档")
    print("  quit - 退出")

    while True:
        try:
            command = input("\n请输入命令: ").strip()

            if command.lower() == 'quit':
                break
            elif command.lower() == 'stats':
                show_index_stats(processor)
            elif command.startswith('process '):
                doc_path = command[8:].strip()
                if doc_path:
                    process_single_document(processor, doc_path)
                else:
                    print("请输入文档路径")
            elif command.startswith('pages '):
                parts = command[6:].strip().split()
                if len(parts) >= 1:
                    doc_path = parts[0]
                    start_page = int(parts[1]) if len(parts) > 1 else 1
                    process_document_by_pages(processor, doc_path, start_page)
                else:
                    print("请输入文档路径")
            elif command.startswith('status '):
                doc_path = command[7:].strip()
                if doc_path:
                    show_document_status(processor, doc_path)
                else:
                    print("请输入文档路径")
            elif command.lower() == 'clear':
                processor.clear_index()
                print("索引已清空")
            elif command.lower() == 'prdDocs':
                show_document_list(processor)
            elif command.startswith('delete '):
                doc_path = command[7:].strip()
                if doc_path:
                    delete_document(processor, doc_path)
                else:
                    print("请输入文档路径")
            elif command.startswith('search '):
                query = command[7:].strip()
                if query:
                    search_similar_content(processor, query)
                else:
                    print("请输入搜索查询")
            elif command.startswith('ask '):
                question = command[4:].strip()
                if question:
                    answer_question(processor, question)
                else:
                    print("请输入问题")
            else:
                print("未知命令，请重试")

        except KeyboardInterrupt:
            print("\n退出交互模式")
            break
        except Exception as e:
            print(f"错误: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Word文档RAG系统")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("--mode", choices=["process", "pages", "status", "search", "ask", "summary", "stats", "prdDocs", "delete", "interactive"],
                       help="运行模式")
    parser.add_argument("--doc", help="文档路径")
    parser.add_argument("--start_page", type=int, default=1, help="开始页面（用于pages模式）")
    parser.add_argument("--query", help="搜索查询")
    parser.add_argument("--question", help="问题")

    args = parser.parse_args()

    # 初始化RAG处理器
    try:
        processor = RAGProcessor(args.config)
        print("RAG处理器初始化成功")
    except Exception as e:
        print(f"初始化失败: {str(e)}")
        return

    # 测试AI连接
    if not processor.test_ai_connection():
        print("AI连接测试失败，请检查API配置")
        return

    print("AI连接测试成功")

    # 根据模式执行相应操作
    if args.mode == "process":
        if not args.doc:
            print("请指定文档路径")
            return
        process_single_document(processor, args.doc)

    elif args.mode == "pages":
        if not args.doc:
            print("请指定文档路径")
            return
        process_document_by_pages(processor, args.doc, args.start_page)

    elif args.mode == "status":
        if not args.doc:
            print("请指定文档路径")
            return
        show_document_status(processor, args.doc)

    elif args.mode == "search":
        if not args.query:
            print("请指定搜索查询")
            return
        search_similar_content(processor, args.query)

    elif args.mode == "ask":
        if not args.question:
            print("请指定问题")
            return
        answer_question(processor, args.question)

    elif args.mode == "summary":
        if not args.doc:
            print("请指定文档路径")
            return
        get_document_summary(processor, args.doc)

    elif args.mode == "stats":
        show_index_stats(processor)

    elif args.mode == "prdDocs":
        show_document_list(processor)

    elif args.mode == "delete":
        if not args.doc:
            print("请指定要删除的文档路径")
            return
        delete_document(processor, args.doc)

    elif args.mode == "interactive":
        interactive_mode(processor)

    else:
        print("请指定运行模式，或使用 --help 查看帮助")

if __name__ == "__main__":
    main()
