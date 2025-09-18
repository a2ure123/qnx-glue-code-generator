#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化的Gemini向量化系统
支持并行处理、错误重试和高效批量embedding
"""

import os
import sys
import json
import logging
import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import google.generativeai as genai
import chromadb
from dotenv import load_dotenv

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 禁用第三方库的详细日志
logging.getLogger("chromadb.telemetry").setLevel(logging.ERROR)
logging.getLogger("backoff").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)


@dataclass
class VectorizeTask:
    """向量化任务"""
    text: str
    doc_id: str
    metadata: Dict[str, Any]
    retry_count: int = 0


@dataclass
class VectorizeResult:
    """向量化结果"""
    doc_id: str
    embedding: List[float]
    success: bool
    error: Optional[str] = None


class OptimizedGeminiVectorizer:
    """优化的Gemini向量化器"""
    
    def __init__(self, config_path: str = "config.json"):
        """初始化向量化器"""
        # 加载配置
        self.config = self._load_config(config_path)
        
        # AI配置
        ai_config = self.config.get("ai_settings", {})
        gemini_config = ai_config.get("gemini", {})
        
        self.api_key_env = gemini_config.get("api_key_env", "GEMINI_API_KEY")
        self.embedding_model = gemini_config.get("embedding_model", "embedding-001")
        self.batch_size = gemini_config.get("batch_size", 32)
        self.max_workers = min(gemini_config.get("max_workers", 4), 8)  # 限制并发数
        self.max_retries = 3
        self.retry_delay = 1.0
        
        # 初始化Gemini
        self._initialize_gemini()
        
        # ChromaDB设置
        self.persist_dir = "./data/chroma_db/"
        self.collection_name = "qnx_functions_optimized"
        
        # 初始化ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = None
        
        # 统计信息
        self.stats = {
            "total_processed": 0,
            "successful_embeddings": 0,
            "failed_embeddings": 0,
            "retry_count": 0,
            "processing_time": 0.0
        }
        
        logger.info(f"优化Gemini向量化器初始化完成")
        logger.info(f"嵌入模型: {self.embedding_model}")
        logger.info(f"批量大小: {self.batch_size}")
        logger.info(f"最大工作线程: {self.max_workers}")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"配置文件加载失败: {e}")
            return {}
    
    def _initialize_gemini(self):
        """初始化Gemini客户端"""
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise ValueError(f"请设置环境变量 {self.api_key_env}")
        
        genai.configure(api_key=api_key)
        logger.info("Gemini客户端初始化成功")
    
    def get_single_embedding(self, text: str, task_type: str = "semantic_similarity") -> Optional[List[float]]:
        """获取单个文本的embedding"""
        try:
            result = genai.embed_content(
                model=f"models/{self.embedding_model}",
                content=text,
                task_type=task_type
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"获取embedding失败: {e}")
            return None
    
    def get_batch_embeddings_optimized(self, tasks: List[VectorizeTask]) -> List[VectorizeResult]:
        """优化的批量embedding处理"""
        results = []
        start_time = time.time()
        
        # 分批处理
        batches = [tasks[i:i + self.batch_size] for i in range(0, len(tasks), self.batch_size)]
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_batch = {}
            
            for batch_idx, batch in enumerate(batches):
                future = executor.submit(self._process_batch, batch, batch_idx + 1, len(batches))
                future_to_batch[future] = batch_idx
            
            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    batch_results = future.result()
                    results.extend(batch_results)
                    logger.info(f"批次 {batch_idx + 1}/{len(batches)} 处理完成")
                except Exception as e:
                    logger.error(f"批次 {batch_idx + 1} 处理失败: {e}")
        
        # 更新统计信息
        processing_time = time.time() - start_time
        self.stats["processing_time"] += processing_time
        self.stats["total_processed"] += len(tasks)
        
        successful_results = [r for r in results if r.success]
        self.stats["successful_embeddings"] += len(successful_results)
        self.stats["failed_embeddings"] += len(results) - len(successful_results)
        
        logger.info(f"批量处理完成: {len(successful_results)}/{len(tasks)} 成功, 耗时 {processing_time:.2f}s")
        
        return results
    
    def _process_batch(self, batch: List[VectorizeTask], batch_num: int, total_batches: int) -> List[VectorizeResult]:
        """处理单个批次"""
        results = []
        
        logger.info(f"开始处理批次 {batch_num}/{total_batches} ({len(batch)} 个任务)")
        
        for task in batch:
            result = self._process_single_task(task)
            results.append(result)
            
            # 简单的速率限制
            time.sleep(0.1)
        
        return results
    
    def _process_single_task(self, task: VectorizeTask) -> VectorizeResult:
        """处理单个向量化任务"""
        for attempt in range(self.max_retries):
            try:
                embedding = self.get_single_embedding(task.text)
                
                if embedding:
                    return VectorizeResult(
                        doc_id=task.doc_id,
                        embedding=embedding,
                        success=True
                    )
                else:
                    raise Exception("Empty embedding result")
                    
            except Exception as e:
                error_msg = str(e)
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # 指数退避
                    logger.warning(f"任务 {task.doc_id} 尝试 {attempt + 1} 失败: {error_msg}, {wait_time}s后重试")
                    time.sleep(wait_time)
                    self.stats["retry_count"] += 1
                else:
                    logger.error(f"任务 {task.doc_id} 最终失败: {error_msg}")
                    return VectorizeResult(
                        doc_id=task.doc_id,
                        embedding=[],
                        success=False,
                        error=error_msg
                    )
        
        # 不应该到达这里
        return VectorizeResult(
            doc_id=task.doc_id,
            embedding=[],
            success=False,
            error="Unknown error"
        )
    
    def create_or_get_collection(self, reset: bool = False) -> chromadb.Collection:
        """创建或获取ChromaDB collection"""
        if reset:
            try:
                self.chroma_client.delete_collection(name=self.collection_name)
                logger.info(f"已删除现有collection: {self.collection_name}")
            except (ValueError, Exception):
                pass  # Collection不存在
        
        try:
            self.collection = self.chroma_client.get_collection(name=self.collection_name)
            logger.info(f"获取现有collection: {self.collection_name}")
        except (ValueError, Exception):
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"description": "QNX函数文档向量数据库 - 优化版本"}
            )
            logger.info(f"创建新collection: {self.collection_name}")
        
        return self.collection
    
    def vectorize_documents(self, documents: List[Dict[str, Any]], reset_db: bool = False) -> Dict[str, Any]:
        """向量化文档并存储到数据库"""
        logger.info(f"开始向量化 {len(documents)} 个文档")
        
        # 创建或获取collection
        self.create_or_get_collection(reset=reset_db)
        
        # 准备向量化任务
        tasks = []
        for doc in documents:
            task = VectorizeTask(
                text=doc.get("content", ""),
                doc_id=doc.get("id", ""),
                metadata=doc.get("metadata", {})
            )
            tasks.append(task)
        
        # 执行批量向量化
        results = self.get_batch_embeddings_optimized(tasks)
        
        # 准备存储数据
        doc_ids = []
        embeddings = []
        metadatas = []
        documents_to_store = []
        
        for i, result in enumerate(results):
            if result.success:
                doc_ids.append(result.doc_id)
                embeddings.append(result.embedding)
                metadatas.append(documents[i].get("metadata", {}))
                documents_to_store.append(documents[i].get("content", ""))
        
        # 存储到ChromaDB
        if doc_ids:
            try:
                self.collection.add(
                    ids=doc_ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents_to_store
                )
                logger.info(f"成功存储 {len(doc_ids)} 个文档到数据库")
            except Exception as e:
                logger.error(f"存储到数据库失败: {e}")
        
        # 返回统计信息
        return {
            "total_documents": len(documents),
            "successful_vectorized": len([r for r in results if r.success]),
            "failed_vectorized": len([r for r in results if not r.success]),
            "stored_in_db": len(doc_ids),
            "processing_stats": self.stats.copy()
        }
    
    def query_similar(self, query_text: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """查询相似文档"""
        if not self.collection:
            self.create_or_get_collection()
        
        # 获取查询向量
        query_embedding = self.get_single_embedding(query_text)
        if not query_embedding:
            logger.error("无法获取查询向量")
            return []
        
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            formatted_results = []
            for i in range(len(results["documents"][0])):
                formatted_results.append({
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                    "similarity": 1 - results["distances"][0][i]  # 转换为相似度
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"查询失败: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()


def main():
    """主函数 - 测试向量化器"""
    try:
        # 初始化向量化器
        vectorizer = OptimizedGeminiVectorizer()
        
        # 测试文档
        test_docs = [
            {
                "id": "sprintf_test",
                "content": "sprintf函数用于格式化字符串输出到缓冲区",
                "metadata": {"function": "sprintf", "type": "stdio"}
            },
            {
                "id": "printf_test", 
                "content": "printf函数用于格式化输出到标准输出流",
                "metadata": {"function": "printf", "type": "stdio"}
            }
        ]
        
        # 执行向量化
        stats = vectorizer.vectorize_documents(test_docs, reset_db=True)
        print(f"向量化统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")
        
        # 测试查询
        results = vectorizer.query_similar("字符串格式化函数", n_results=2)
        print(f"查询结果: {json.dumps(results, indent=2, ensure_ascii=False)}")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")


if __name__ == "__main__":
    main()