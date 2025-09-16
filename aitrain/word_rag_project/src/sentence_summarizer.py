"""
句子总结提炼模块 - 将文档内容总结为关键句子并生成向量
"""

import re
import jieba
from typing import List, Dict, Tuple, Optional
from src.ai_client import AIClient
from src.config import ConfigManager

class SentenceSummarizer:
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
        # 启用jieba的paddle模式
        jieba.enable_paddle()
        jieba.initialize()
    
    def extract_key_sentences(self, content: str, max_sentences: int = 10) -> List[str]:
        """
        从文档内容中提取关键句子
        :param content: 文档内容
        :param max_sentences: 最大句子数量
        :return: 关键句子列表
        """
        # 分句
        sentences = self._split_into_sentences(content)
        
        if len(sentences) <= max_sentences:
            return sentences
        
        # 如果句子数量超过限制，进行总结提炼
        return self._summarize_sentences(sentences, max_sentences)
    
    def _split_into_sentences(self, content: str) -> List[str]:
        """
        将文本分割成句子
        :param content: 文本内容
        :return: 句子列表
        """
        # 使用正则表达式分割句子
        # 支持中文句号、感叹号、问号、分号等
        sentence_pattern = r'[。！？；\n]+'
        sentences = re.split(sentence_pattern, content)
        
        # 清理和过滤句子
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 5:  # 过滤太短的句子
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences
    
    def _summarize_sentences(self, sentences: List[str], max_sentences: int) -> List[str]:
        """
        总结提炼句子
        :param sentences: 原始句子列表
        :param max_sentences: 最大句子数量
        :return: 总结后的句子列表
        """
        if len(sentences) <= max_sentences:
            return sentences
        
        # 使用AI进行总结
        combined_text = "。".join(sentences)
        
        try:
            success, summary = self.ai_client.summarize_text(
                combined_text, 
                max_length=max_sentences * 50  # 根据句子数量调整长度
            )
            
            if success and summary:
                # 将总结结果重新分割成句子
                summarized_sentences = self._split_into_sentences(summary)
                
                # 确保不超过最大句子数量
                if len(summarized_sentences) > max_sentences:
                    summarized_sentences = summarized_sentences[:max_sentences]
                
                return summarized_sentences
            else:
                # 如果AI总结失败，使用简单的句子选择策略
                return self._select_key_sentences(sentences, max_sentences)
                
        except Exception as e:
            print(f"AI总结失败: {e}")
            return self._select_key_sentences(sentences, max_sentences)
    
    def _select_key_sentences(self, sentences: List[str], max_sentences: int) -> List[str]:
        """
        选择关键句子（基于长度和位置）
        :param sentences: 句子列表
        :param max_sentences: 最大句子数量
        :return: 选中的句子列表
        """
        # 按句子长度排序
        sentence_scores = []
        for i, sentence in enumerate(sentences):
            # 计算句子得分（长度 + 位置权重）
            length_score = len(sentence)
            position_score = 1.0 / (i + 1)  # 前面的句子权重更高
            total_score = length_score * position_score
            
            sentence_scores.append((sentence, total_score))
        
        # 按得分排序并选择前N个
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        selected_sentences = [sentence for sentence, _ in sentence_scores[:max_sentences]]
        
        # 按原始顺序排序
        selected_sentences.sort(key=lambda x: sentences.index(x))
        
        return selected_sentences
    
    def create_sentence_vectors(self, sentences: List[str]) -> List[Tuple[bool, Optional[str], Dict]]:
        """
        为句子列表创建向量
        :param sentences: 句子列表
        :return: 向量结果列表，包含元数据
        """
        results = []
        
        for i, sentence in enumerate(sentences):
            try:
                # 获取句子向量
                success, vector = self.ai_client.get_embedding(sentence)
                
                if success and vector is not None:
                    # 创建元数据
                    metadata = {
                        'sentence_index': i,
                        'sentence_text': sentence,
                        'sentence_length': len(sentence),
                        'word_count': len(list(jieba.cut(sentence))),
                        'vector_dimension': vector.shape[0] if hasattr(vector, 'shape') else None,
                        'processed_time': None  # 可以添加时间戳
                    }
                    
                    results.append((True, sentence, metadata))
                    print(f"✅ 句子 {i+1}/{len(sentences)}: 成功生成向量 (长度: {len(sentence)})")
                else:
                    results.append((False, sentence, {'error': '向量生成失败'}))
                    print(f"❌ 句子 {i+1}/{len(sentences)}: 向量生成失败")
                    
            except Exception as e:
                results.append((False, sentence, {'error': str(e)}))
                print(f"❌ 句子 {i+1}/{len(sentences)}: 处理异常 - {e}")
        
        return results
    
    def process_document_to_sentences(self, content: str, max_sentences: int = 10) -> Dict:
        """
        处理文档内容，提取关键句子并生成向量
        :param content: 文档内容
        :param max_sentences: 最大句子数量
        :return: 处理结果
        """
        print(f"开始处理文档内容...")
        print(f"原始内容长度: {len(content)} 字符")
        
        # 提取关键句子
        key_sentences = self.extract_key_sentences(content, max_sentences)
        print(f"提取到 {len(key_sentences)} 个关键句子")
        
        # 生成句子向量
        vector_results = self.create_sentence_vectors(key_sentences)
        
        # 统计结果
        success_count = sum(1 for success, _, _ in vector_results if success)
        fail_count = len(vector_results) - success_count
        
        result = {
            'total_sentences': len(key_sentences),
            'success_sentences': success_count,
            'fail_sentences': fail_count,
            'sentences': key_sentences,
            'vector_results': vector_results,
            'success_rate': success_count / len(vector_results) * 100 if vector_results else 0
        }
        
        print(f"处理完成:")
        print(f"  总句子数: {result['total_sentences']}")
        print(f"  成功向量数: {result['success_sentences']}")
        print(f"  失败向量数: {result['fail_sentences']}")
        print(f"  成功率: {result['success_rate']:.1f}%")
        
        return result 