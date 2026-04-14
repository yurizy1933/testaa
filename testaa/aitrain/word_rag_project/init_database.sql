-- Word文档RAG系统数据库初始化脚本
-- 创建数据库表结构

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS vectors CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE vectors;

-- 向量数据表
CREATE TABLE IF NOT EXISTS vectors (
    id INT PRIMARY KEY AUTO_INCREMENT,
    vector_id INT NOT NULL,
    text TEXT NOT NULL,
    doc_path VARCHAR(255),
    doc_name VARCHAR(255),
    page INT,
    word_count INT,
    processed_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_vector_id (vector_id),
    INDEX idx_doc_path (doc_path),
    INDEX idx_page (page)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 文档信息表
CREATE TABLE IF NOT EXISTS documents (
    id INT PRIMARY KEY AUTO_INCREMENT,
    doc_path VARCHAR(255) UNIQUE,
    doc_name VARCHAR(255),
    total_pages INT,
    total_words INT,
    file_size BIGINT,
    processed_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_doc_path (doc_path),
    INDEX idx_processed_time (processed_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 处理统计表
CREATE TABLE IF NOT EXISTS processing_status (
    id INT PRIMARY KEY AUTO_INCREMENT,
    doc_path VARCHAR(255),
    total_chunks INT,
    success_chunks INT,
    processing_time FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_doc_path (doc_path),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建视图：文档统计信息
CREATE OR REPLACE VIEW document_stats AS
SELECT 
    d.doc_path,
    d.doc_name,
    d.total_pages,
    d.total_words,
    d.file_size,
    d.processed_time,
    COUNT(v.id) as vector_count,
    SUM(v.word_count) as total_word_count
FROM documents d
LEFT JOIN vectors v ON d.doc_path = v.doc_path
GROUP BY d.id, d.doc_path, d.doc_name, d.total_pages, d.total_words, d.file_size, d.processed_time;

-- 创建视图：处理状态统计
CREATE OR REPLACE VIEW processing_stats AS
SELECT 
    doc_path,
    total_chunks,
    success_chunks,
    processing_time,
    created_at,
    ROUND(success_chunks / total_chunks * 100, 2) as success_rate
FROM processing_status
ORDER BY created_at DESC;

-- 插入示例数据（可选）
-- INSERT INTO documents (doc_path, doc_name, total_pages, total_words, file_size) 
-- VALUES ('documents/example.docx', '示例文档', 10, 5000, 1024000);

-- 显示表结构
SHOW TABLES;
DESCRIBE vectors;
DESCRIBE documents;
DESCRIBE processing_status;

-- 显示视图
SHOW FULL TABLES WHERE Table_type = 'VIEW'; 