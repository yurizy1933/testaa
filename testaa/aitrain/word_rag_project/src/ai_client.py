"""
AI客户端模块 - 智谱AI API调用
"""

from zhipuai import ZhipuAI
import numpy as np
from typing import List, Dict, Optional, Tuple
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

class AIClient:
    def __init__(self, api_key: str, embedding_model: str = "embedding-2", 
                 chat_model: str = "glm-4", max_threads: int = 5, 
                 request_interval: float = 1.0):
        self.api_key = api_key
        self.embedding_model = embedding_model
        self.chat_model = chat_model
        self.max_threads = max_threads
        self.request_interval = request_interval
        self.client = ZhipuAI(api_key=api_key)
    
    def get_embedding(self, text: str) -> Tuple[bool, Optional[np.ndarray]]:
        """
        获取文本的向量表示
        :param text: 输入文本
        :return: (成功标志, 向量数组)
        """
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            vector = np.array(response.data[0].embedding, dtype=np.float32)
            return True, vector
        except Exception as e:
            print(f"获取向量失败: {str(e)}")
            return False, None
    
    def get_embeddings_batch(self, texts: List[str]) -> List[Tuple[bool, Optional[np.ndarray]]]:
        """
        批量获取文本向量
        :param texts: 文本列表
        :return: 向量结果列表
        """
        if not texts:
            return []
        
        # 如果文本数量较少，使用并发处理
        if len(texts) <= self.max_threads * 2:
            return self._get_embeddings_concurrent(texts)
        else:
            # 如果文本数量较多，使用批量处理
            return self._get_embeddings_batch_optimized(texts)
    
    def _get_embeddings_concurrent(self, texts: List[str]) -> List[Tuple[bool, Optional[np.ndarray]]]:
        """
        并发获取文本向量（适用于少量文本）
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            # 提交所有任务，使用索引来避免重复文本的问题
            future_to_index = {}
            for i, text in enumerate(texts):
                future = executor.submit(self.get_embedding, text)
                future_to_index[future] = i
            
            # 初始化结果列表
            results = [(False, None)] * len(texts)
            
            # 收集结果
            completed_count = 0
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                text = texts[index]
                try:
                    result = future.result()
                    results[index] = result
                    completed_count += 1
                    
                    # 每完成一定数量的请求后添加间隔
                    if completed_count % self.max_threads == 0:
                        time.sleep(self.request_interval)
                        print(f"已完成 {completed_count}/{len(texts)} 个向量生成")
                        
                except Exception as e:
                    print(f"处理文本失败 (索引 {index}): {text[:50]}... - {str(e)}")
                    results[index] = (False, None)
                    completed_count += 1
        
        return results
    
    def _get_embeddings_batch_optimized(self, texts: List[str]) -> List[Tuple[bool, Optional[np.ndarray]]]:
        """
        优化的批量获取文本向量（适用于大量文本）
        """
        results = [(False, None)] * len(texts)
        batch_size = self.max_threads * 2  # 批量大小
        
        print(f"使用批量处理模式，批量大小: {batch_size}")
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_start = i
            batch_end = min(i + batch_size, len(texts))
            
            print(f"处理批次 {batch_start+1}-{batch_end}/{len(texts)}")
            
            # 处理当前批次
            batch_results = self._get_embeddings_concurrent(batch_texts)
            
            # 将批次结果复制到总结果中
            for j, result in enumerate(batch_results):
                results[batch_start + j] = result
            
            # 批次间间隔
            if batch_end < len(texts):
                time.sleep(self.request_interval)
        
        return results
    
    def chat_completion(self, messages: List[Dict], temperature: float = 0.1) -> Tuple[bool, Optional[str]]:
        """
        聊天完成
        :param messages: 消息列表
        :param temperature: 温度参数
        :return: (成功标志, 回复内容)
        """
        try:
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                temperature=temperature
            )
            return True, response.choices[0].message.content
        except Exception as e:
            print(f"聊天完成失败: {str(e)}")
            return False, None
    
    def summarize_text(self, text: str, max_length: int = 200) -> Tuple[bool, Optional[str]]:
        """
        文本摘要
        :param text: 输入文本
        :param max_length: 最大长度
        :return: (成功标志, 摘要内容)
        """
        messages = [
            {
                "role": "user",
                "content": f"请对以下文本进行摘要，控制在{max_length}字以内：\n\n{text}"
            }
        ]
        return self.chat_completion(messages)
    
    def extract_keywords(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        提取关键词
        :param text: 输入文本
        :return: (成功标志, 关键词列表)
        """
        messages = [
            {
                "role": "user",
                "content": f"请从以下文本中提取5-10个关键词，用逗号分隔：\n\n{text}"
            }
        ]
        return self.chat_completion(messages)
    
    def answer_question(self, question: str, context: str) -> Tuple[bool, Optional[str]]:
        """
        基于上下文回答问题
        :param question: 问题
        :param context: 上下文
        :return: (成功标志, 答案)
        """
        messages = [
            {
                "role": "user",
                "content": f"基于以下上下文回答问题：\n\n上下文：{context}\n\n问题：{question}"
            }
        ]
        return self.chat_completion(messages)
    
    def test_connection(self) -> bool:
        """测试API连接"""
        try:
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[{"role": "user", "content": "测试连接"}],
                max_tokens=10
            )
            return True
        except Exception as e:
            print(f"API连接测试失败: {str(e)}")
            return False 