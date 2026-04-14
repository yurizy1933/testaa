import os
import faiss
import mysql.connector
import numpy as np
from PIL import Image
from docx import Document
from tqdm import tqdm
import pytesseract
from openai import OpenAI
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import logging


# 配置参数
class Config:
    # OpenAI
    OPENAI_API_KEY = "your-api-key"
    EMBEDDING_MODEL = "text-embedding-3-large"
    EMBEDDING_DIM = 1536

    # MySQL
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASS = "password"
    DB_NAME = "doc_vectors"

    # 文件处理
    DOCX_PATH = "large_document.docx"
    FAISS_INDEX_PATH = "doc_index.faiss"
    TEMP_IMAGE_DIR = "temp_ocr_images"
    MAX_WORKERS = 4  # 并发线程数

    # 文本处理
    CHUNK_SIZE = 500  # 字符数
    MIN_TEXT_LENGTH = 20  # 忽略短文本


# 初始化日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('doc_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DocumentProcessor:
    def __init__(self):
        # 初始化OCR（Windows需指定路径）
        if os.name == 'nt':
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

        # 初始化MySQL
        self.db_conn = mysql.connector.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASS,
            database=Config.DB_NAME
        )
        self._init_db()

        # 初始化OpenAI
        self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)

        # 初始化FAISS
        self.index = faiss.IndexFlatL2(Config.EMBEDDING_DIM)
        self.vector_ids = []

    def _init_db(self):
        """初始化数据库表结构"""
        cursor = self.db_conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id VARCHAR(32) PRIMARY KEY,
            content TEXT NOT NULL,
            page_num INT NOT NULL,
            chunk_type ENUM('text', 'ocr') NOT NULL,
            source_file VARCHAR(255) NOT NULL,
            embedding BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.db_conn.commit()

    def _get_text_chunks(self, text: str, page_num: int) -> List[Dict]:
        """将长文本分割为适合处理的块"""
        chunks = []
        for i in range(0, len(text), Config.CHUNK_SIZE):
            chunk = text[i:i + Config.CHUNK_SIZE]
            if len(chunk) < Config.MIN_TEXT_LENGTH:
                continue

            chunk_id = hashlib.md5(f"{page_num}_{chunk}".encode()).hexdigest()
            chunks.append({
                "id": chunk_id,
                "content": chunk,
                "page_num": page_num,
                "type": "text"
            })
        return chunks

    def _process_image(self, image_part, page_num: int) -> List[Dict]:
        """处理单个图片并返回OCR结果"""
        os.makedirs(Config.TEMP_IMAGE_DIR, exist_ok=True)
        img_path = os.path.join(Config.TEMP_IMAGE_DIR, f"page_{page_num}_img_{image_part.partname}.png")

        with open(img_path, "wb") as f:
            f.write(image_part.blob)

        try:
            img = Image.open(img_path)
            text = pytesseract.image_to_string(img)
            os.remove(img_path)

            if not text.strip():
                return []

            chunk_id = hashlib.md5(f"img_{page_num}_{image_part.partname}".encode()).hexdigest()
            return [{
                "id": chunk_id,
                "content": text,
                "page_num": page_num,
                "type": "ocr"
            }]
        except Exception as e:
            logger.error(f"OCR处理失败: {e}")
            return []

    def extract_content(self) -> List[Dict]:
        """从Word文档提取所有内容块"""
        doc = Document(Config.DOCX_PATH)
        all_chunks = []

        # 处理文本内容
        for page_num, para in enumerate(tqdm(doc.paragraphs, desc="提取文本")):
            if para.text.strip():
                all_chunks.extend(self._get_text_chunks(para.text, page_num))

        # 处理图片内容（使用多线程加速）
        with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
            futures = []
            for page_num, rel in enumerate(doc.part.rels.values()):
                if "image" in rel.target_ref:
                    futures.append(executor.submit(
                        self._process_image,
                        rel.target_part,
                        page_num
                    ))

            for future in tqdm(futures, desc="OCR处理图片"):
                all_chunks.extend(future.result())

        return all_chunks

    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """批量获取文本向量"""
        try:
            response = self.openai_client.embeddings.create(
                input=texts,
                model=Config.EMBEDDING_MODEL
            )
            return np.array([d.embedding for d in response.data], dtype="float32")
        except Exception as e:
            logger.error(f"获取向量失败: {e}")
            raise

    def process_document(self):
        """主处理流程"""
        try:
            # 1. 提取内容
            chunks = self.extract_content()
            if not chunks:
                raise ValueError("未提取到任何内容！")

            # 2. 分批处理
            cursor = self.db_conn.cursor()
            batch_size = 32  # OpenAI推荐批处理大小
            total_chunks = len(chunks)

            for i in tqdm(range(0, total_chunks, batch_size), desc="生成向量"):
                batch = chunks[i:i + batch_size]
                texts = [item["content"] for item in batch]

                # 3. 获取向量
                embeddings = self.get_embeddings(texts)

                # 4. 存储到MySQL和FAISS
                for j, (chunk, embedding) in enumerate(zip(batch, embeddings)):
                    # MySQL存储
                    cursor.execute("""
                    INSERT INTO document_chunks 
                    (id, content, page_num, chunk_type, source_file, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE content=VALUES(content)
                    """, (
                        chunk["id"],
                        chunk["content"],
                        chunk["page_num"],
                        chunk["type"],
                        Config.DOCX_PATH,
                        embedding.tobytes()
                    ))

                    # FAISS索引
                    self.index.add(np.array([embedding]))
                    self.vector_ids.append(chunk["id"])

                self.db_conn.commit()

            # 5. 保存FAISS索引（包含ID映射）
            index_with_ids = faiss.IndexIDMap2(self.index)
            index_with_ids.add_with_ids(
                np.array([self.index.reconstruct(i) for i in range(len(self.vector_ids))]),
                np.array([hashlib.md5(id.encode()).digest()[:8] for id in self.vector_ids])
            )
            faiss.write_index(index_with_ids, Config.FAISS_INDEX_PATH)

            logger.info(f"处理完成！共处理 {total_chunks} 个文本块")

        except Exception as e:
            logger.error(f"处理失败: {e}")
            raise
        finally:
            # 清理临时文件
            if os.path.exists(Config.TEMP_IMAGE_DIR):
                for f in Path(Config.TEMP_IMAGE_DIR).glob("*"):
                    f.unlink()
                os.rmdir(Config.TEMP_IMAGE_DIR)

            cursor.close()
            self.db_conn.close()


if __name__ == "__main__":
    processor = DocumentProcessor()
    processor.process_document()