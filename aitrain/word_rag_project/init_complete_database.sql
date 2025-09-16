-- 完整的数据库初始化脚本
-- 包含所有需要的表结构

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS vectors CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE vectors;

-- 1. 向量数据表（原有）
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

-- 2. 文档信息表（原有）
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

-- 3. 处理统计表（原有）
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

-- 4. 页面信息表（新增）
CREATE TABLE IF NOT EXISTS pages (
    id INT PRIMARY KEY AUTO_INCREMENT,
    doc_path VARCHAR(255) NOT NULL,
    page_num INT NOT NULL,
    text_content TEXT,
    image_count INT DEFAULT 0,
    table_count INT DEFAULT 0,
    paragraph_count INT DEFAULT 0,
    processed_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_doc_path (doc_path),
    INDEX idx_page_num (page_num),
    UNIQUE KEY unique_doc_page (doc_path, page_num)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. 文档信息点表（新增）
CREATE TABLE IF NOT EXISTS document_points (
    id INT PRIMARY KEY AUTO_INCREMENT,
    doc_path VARCHAR(255) NOT NULL,
    point_index INT NOT NULL,
    point_type VARCHAR(50) NOT NULL,  -- text, table_header, table_data, image, ai_summary
    content TEXT NOT NULL,
    page_num INT DEFAULT 0,
    hash_value VARCHAR(64) NOT NULL,  -- MD5哈希值，用于去重
    vector_success BOOLEAN DEFAULT FALSE,
    vector_id INT,
    processed_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_doc_path (doc_path),
    INDEX idx_point_type (point_type),
    INDEX idx_hash (hash_value),
    INDEX idx_vector_id (vector_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. 文档分析结果表（新增）
CREATE TABLE IF NOT EXISTS document_analysis (
    id INT PRIMARY KEY AUTO_INCREMENT,
    doc_path VARCHAR(255) NOT NULL,
    doc_name VARCHAR(255) NOT NULL,
    total_points INT DEFAULT 0,
    success_vectors INT DEFAULT 0,
    fail_vectors INT DEFAULT 0,
    processed_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_doc_path (doc_path),
    INDEX idx_processed_time (processed_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. 图片信息表（新增）
CREATE TABLE IF NOT EXISTS document_images (
    id INT PRIMARY KEY AUTO_INCREMENT,
    doc_path VARCHAR(255) NOT NULL,
    page_num INT NOT NULL,
    image_index INT NOT NULL,
    image_type VARCHAR(50) NOT NULL,  -- inline, table, header, footer
    description TEXT,
    image_hash VARCHAR(64),  -- 图片内容的哈希值
    processed_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_doc_path (doc_path),
    INDEX idx_page_num (page_num),
    INDEX idx_image_hash (image_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. 表格信息表（新增）
CREATE TABLE IF NOT EXISTS document_tables (
    id INT PRIMARY KEY AUTO_INCREMENT,
    doc_path VARCHAR(255) NOT NULL,
    page_num INT NOT NULL,
    table_index INT NOT NULL,
    rows_count INT NOT NULL,
    cols_count INT NOT NULL,
    table_data JSON,  -- 存储表格数据
    processed_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_doc_path (doc_path),
    INDEX idx_page_num (page_num)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. 向量元数据表（新增）
CREATE TABLE IF NOT EXISTS vector_metadata (
    id INT PRIMARY KEY AUTO_INCREMENT,
    vector_id INT NOT NULL,
    doc_path VARCHAR(255) NOT NULL,
    point_type VARCHAR(50) NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    similarity_score FLOAT DEFAULT 0.0,
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_vector_id (vector_id),
    INDEX idx_doc_path (doc_path),
    INDEX idx_point_type (point_type),
    INDEX idx_content_hash (content_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. 分析统计表（新增）
CREATE TABLE IF NOT EXISTS analysis_stats (
    id INT PRIMARY KEY AUTO_INCREMENT,
    doc_path VARCHAR(255) NOT NULL,
    total_pages INT DEFAULT 0,
    total_images INT DEFAULT 0,
    total_tables INT DEFAULT 0,
    total_points INT DEFAULT 0,
    text_points INT DEFAULT 0,
    table_points INT DEFAULT 0,
    image_points INT DEFAULT 0,
    ai_summary_points INT DEFAULT 0,
    vector_success_rate FLOAT DEFAULT 0.0,
    processing_time FLOAT DEFAULT 0.0,
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_doc_path (doc_path),
    INDEX idx_created_time (created_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建视图：文档分析概览
CREATE OR REPLACE VIEW document_analysis_overview AS
SELECT 
    d.doc_path,
    d.doc_name,
    d.total_pages,
    d.total_words,
    d.file_size,
    COALESCE(da.total_points, 0) as total_points,
    COALESCE(da.success_vectors, 0) as success_vectors,
    COALESCE(da.fail_vectors, 0) as fail_vectors,
    COALESCE(da.success_vectors / NULLIF(da.total_points, 0) * 100, 0) as vector_success_rate,
    d.processed_time
FROM documents d
LEFT JOIN document_analysis da ON d.doc_path = da.doc_path
ORDER BY d.processed_time DESC;

-- 创建视图：页面详细信息
CREATE OR REPLACE VIEW page_details AS
SELECT 
    p.doc_path,
    p.page_num,
    p.text_content,
    p.image_count,
    p.table_count,
    p.paragraph_count,
    COUNT(dp.id) as point_count,
    p.processed_time
FROM pages p
LEFT JOIN document_points dp ON p.doc_path = dp.doc_path AND p.page_num = dp.page_num
GROUP BY p.id, p.doc_path, p.page_num
ORDER BY p.doc_path, p.page_num;

-- 创建视图：信息点统计
CREATE OR REPLACE VIEW point_statistics AS
SELECT 
    doc_path,
    point_type,
    COUNT(*) as count,
    AVG(LENGTH(content)) as avg_content_length,
    COUNT(CASE WHEN vector_success = 1 THEN 1 END) as success_count,
    COUNT(CASE WHEN vector_success = 0 THEN 1 END) as fail_count
FROM document_points
GROUP BY doc_path, point_type
ORDER BY doc_path, point_type;

-- 创建视图：文档统计信息（原有）
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

-- 创建视图：处理状态统计（原有）
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

-- 显示所有表
SHOW TABLES;

-- 显示所有视图
SHOW FULL TABLES WHERE Table_type = 'VIEW';

-- 显示表结构
DESCRIBE vectors;
DESCRIBE documents;
DESCRIBE pages;
DESCRIBE document_points;
DESCRIBE document_analysis; 