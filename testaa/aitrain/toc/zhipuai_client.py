import zhipuai
import base64
from PIL import Image
import io
import time
import threading
from config import ZHIPUAI_API_KEY

class ZhipuaiClient:
    def __init__(self):
        if not ZHIPUAI_API_KEY:
            raise ValueError("请设置ZHIPUAI_API_KEY环境变量")
        
        self.client = zhipuai.ZhipuAI(api_key=ZHIPUAI_API_KEY)
        self.request_lock = threading.Lock()  # 请求锁，避免并发问题
        self.retry_count = 3  # 重试次数
        self.retry_delay = 1  # 重试延迟（秒）
        print("智谱AI客户端初始化成功")
    
    def image_to_text(self, image_path):
        """将图片转换为文字描述（优化版本）"""
        for attempt in range(self.retry_count):
            try:
                with self.request_lock:  # 使用锁避免并发请求问题
                    # 读取图片并转换为base64
                    with open(image_path, 'rb') as image_file:
                        image_data = image_file.read()
                        base64_image = base64.b64encode(image_data).decode('utf-8')
                    
                    # 调用智谱AI的图片识别API
                    response = self.client.chat.completions.create(
                        model="glm-4v",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "请详细描述这张图片的内容，包括图片中的文字、图表、数据等信息。如果图片包含表格，请以表格形式描述；如果包含图表，请描述图表类型和数据趋势。"
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{base64_image}"
                                        }
                                    }
                                ]
                            }
                        ],
                        max_tokens=1000,  # 限制输出长度
                        temperature=0.3  # 降低随机性，提高准确性
                    )
                    
                    result = response.choices[0].message.content
                    print(f"图片识别成功: {image_path}")
                    return result
                    
            except Exception as e:
                print(f"图片识别失败 (尝试 {attempt + 1}/{self.retry_count}): {e}")
                if attempt < self.retry_count - 1:
                    print(f"等待 {self.retry_delay} 秒后重试...")
                    time.sleep(self.retry_delay)
                    self.retry_delay *= 2  # 指数退避
                else:
                    print(f"图片识别最终失败: {image_path}")
                    return f"图片识别失败: {str(e)}"
        
        return "图片识别失败"
    
    def table_to_text(self, table_data):
        """将表格数据转换为文字描述"""
        try:
            # 将表格数据转换为文本格式
            table_text = self._format_table(table_data)
            
            # 调用智谱AI的文本分析API
            response = self.client.chat.completions.create(
                model="glm-4",
                messages=[
                    {
                        "role": "user",
                        "content": f"请分析以下表格数据并生成详细的文字描述，包括表格的结构、内容和主要信息：\n\n{table_text}"
                    }
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            result = response.choices[0].message.content
            print("表格分析成功")
            return result
            
        except Exception as e:
            print(f"表格分析失败: {e}")
            return f"表格分析失败: {str(e)}"
    
    def summarize_text(self, text):
        """对文本进行总结"""
        try:
            response = self.client.chat.completions.create(
                model="glm-4",
                messages=[
                    {
                        "role": "user",
                        "content": f"""请对以下文本进行总结，生成独立的检查点。要求：
1. 每个检查点必须包含完整的信息，至少15个字符
2. 检查点要有实际意义，不能是简短的字母组合或无意义的内容
3. 优先使用中文表达，如果包含英文术语请确保完整
4. 每个检查点应该是一个完整的句子或短语
5. 检查点应该突出重要的信息、关键概念或行动要点
6. 避免生成类似 "If DE" 这样的无意义内容
7. 使用清晰的表达方式，便于理解和记忆

文本内容：
{text}"""
                    }
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            result = response.choices[0].message.content
            print("文本总结成功")
            return result
            
        except Exception as e:
            print(f"文本总结失败: {e}")
            return f"文本总结失败: {str(e)}"
    
    def translate_to_chinese(self, text: str) -> str:
        """将英文或混合文本翻译为简体中文，保持专业术语（如 PIN/CVC/ISO8583 等）原样或合理保留。
        若失败则返回原文。"""
        try:
            if not text or not text.strip():
                return text
            prompt = (
                "请将以下标题翻译为简体中文，要求：\n"
                "- 保留或合理翻译专业术语（如 PIN、CVC、ISO8583、DE52 等），保持大写缩写\n"
                "- 保持简洁，不要添加额外说明\n"
                "- 仅输出翻译后的标题，不要包含前后多余内容\n\n"
                f"标题：{text}"
            )
            with self.request_lock:
                response = self.client.chat.completions.create(
                    model="glm-4",
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=200,
                    temperature=0.2
                )
            result = response.choices[0].message.content.strip()
            if result:
                return result
            return text
        except Exception as e:
            print(f"标题翻译失败: {e}")
            return text
    
    def get_embedding(self, text):
        """获取文本的向量表示"""
        try:
            if not text or not text.strip():
                print("文本为空，无法获取向量")
                return None
            
            print(f"开始获取文本向量，文本长度: {len(text)}")
            
            response = self.client.embeddings.create(
                model="embedding-2",
                input=text
            )
            
            if not response.data:
                print("API响应中没有向量数据")
                return None
            
            embedding = response.data[0].embedding
            
            if not embedding:
                print("向量数据为空")
                return None
            
            print(f"向量获取成功，维度: {len(embedding)}")
            return embedding
            
        except Exception as e:
            print(f"向量获取失败: {e}")
            import traceback
            print(f"详细错误信息: {traceback.format_exc()}")
            return None
    
    def _format_table(self, table_data):
        """格式化表格数据为文本"""
        if isinstance(table_data, str):
            return table_data
        
        formatted_text = "表格内容：\n"
        for row in table_data:
            if isinstance(row, list):
                formatted_text += " | ".join(str(cell) for cell in row) + "\n"
            else:
                formatted_text += str(row) + "\n"
        
        return formatted_text

if __name__ == '__main__':
    cli = ZhipuaiClient()
    a = cli.get_embedding('我是点点')
    print(a)
