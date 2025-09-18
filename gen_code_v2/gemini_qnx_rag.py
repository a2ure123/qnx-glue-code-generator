#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于Gemini的QNX函数文档RAG系统
支持批量处理和向量化存储
"""

import os
import sys
import json
import logging
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass
import google.generativeai as genai
import chromadb
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 禁用第三方库的详细日志
logging.getLogger("chromadb.telemetry").setLevel(logging.ERROR)
logging.getLogger("backoff").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)


@dataclass
class BatchEmbeddingRequest:
    """批量embedding请求"""
    texts: List[str]
    batch_id: str


class GeminiQNXRAG:
    """基于Gemini的QNX函数文档RAG系统"""
    
    def __init__(self, config_path: str = "config.json"):
        """初始化Gemini RAG系统"""
        # 加载配置
        self.config = self._load_config(config_path)
        
        # AI配置
        ai_config = self.config.get("ai_settings", {})
        self.provider = ai_config.get("provider", "gemini")
        
        if self.provider == "gemini":
            gemini_config = ai_config.get("gemini", {})
            self.api_key_env = gemini_config.get("api_key_env", "GEMINI_API_KEY")
            self.model_name = gemini_config.get("model", "gemini-2.5-flash")
            self.embedding_model = gemini_config.get("embedding_model", "embedding-001")
            self.batch_size = gemini_config.get("batch_size", 32)
            self.max_tokens = gemini_config.get("max_tokens", 2000)
            self.temperature = gemini_config.get("temperature", 0.1)
        else:
            raise ValueError(f"不支持的AI提供商: {self.provider}")
        
        # 初始化Gemini
        self._initialize_gemini()
        
        # ChromaDB设置
        self.persist_dir = "./data/chroma_db/"
        self.collection_name = "qnx_functions_gemini"
        
        # 初始化ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = None
        
        # QNX文档基础URL
        self.base_url = "https://www.qnx.com/developers/docs/7.1/com.qnx.doc.neutrino.lib_ref/topic/"
        
        # 缓存目录
        self.cache_dir = Path("./data/html_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Gemini QNX RAG系统初始化完成")
        logger.info(f"模型: {self.model_name}")
        logger.info(f"批量大小: {self.batch_size}")
    
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
        
        # 初始化模型
        self.chat_model = genai.GenerativeModel(self.model_name)
        
        logger.info("Gemini客户端初始化成功")
    
    def get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量获取文本embedding"""
        embeddings = []
        
        # 分批处理
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            
            try:
                logger.info(f"处理embedding批次 {i//self.batch_size + 1}/{(len(texts)-1)//self.batch_size + 1} ({len(batch)} 个文本)")
                
                batch_embeddings = []
                for text in batch:
                    # Gemini embedding API
                    result = genai.embed_content(
                        model=f"models/{self.embedding_model}",
                        content=text,
                        task_type="semantic_similarity"
                    )
                    batch_embeddings.append(result['embedding'])
                    
                    # 避免API限制
                    time.sleep(0.1)
                
                embeddings.extend(batch_embeddings)
                
                # 批次间稍作等待
                if i + self.batch_size < len(texts):
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"批量embedding失败 (批次 {i//self.batch_size + 1}): {e}")
                # 添加空embedding占位
                batch_embeddings = [[0.0] * 768] * len(batch)  # Gemini embedding维度
                embeddings.extend(batch_embeddings)
        
        return embeddings
    
    def build_index(self, max_functions: int = 100, rebuild: bool = False):
        """构建向量索引 - 使用批量处理"""
        logger.info(f"开始构建向量索引 (最大函数数: {max_functions})")
        
        # 创建或获取集合
        if rebuild:
            try:
                self.chroma_client.delete_collection(name=self.collection_name)
                logger.info("删除现有集合")
            except Exception:
                pass
        
        try:
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"创建新集合: {self.collection_name}")
        except Exception:
            self.collection = self.chroma_client.get_collection(name=self.collection_name)
            logger.info(f"使用现有集合: {self.collection_name}")
        
        # 获取函数列表
        function_urls = self._get_all_function_urls()
        if max_functions > 0:
            function_urls = function_urls[:max_functions]
        
        logger.info(f"准备处理 {len(function_urls)} 个函数")
        
        # 准备批量数据
        batch_ids = []
        batch_documents = []
        batch_metadatas = []
        function_names = []
        
        # 收集所有HTML内容
        logger.info("收集HTML内容...")
        for i, (function_name, url) in enumerate(function_urls):
            try:
                html_content = self._fetch_and_cache_html(function_name, url)
                if html_content:
                    batch_ids.append(function_name)
                    batch_documents.append(html_content)
                    batch_metadatas.append({
                        "function_name": function_name,
                        "url": url,
                        "content_type": "full_html",
                        "source": "qnx_docs"
                    })
                    function_names.append(function_name)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"已收集 {i + 1}/{len(function_urls)} 个函数的HTML内容")
            
            except Exception as e:
                logger.warning(f"跳过函数 {function_name}: {e}")
                continue
        
        if not function_names:
            logger.error("没有成功收集到任何函数内容")
            return
        
        logger.info(f"成功收集 {len(function_names)} 个函数的内容，开始批量向量化...")
        
        # 批量获取embeddings
        embeddings = self.get_batch_embeddings(function_names)
        
        if len(embeddings) != len(function_names):
            logger.error(f"embedding数量不匹配: {len(embeddings)} vs {len(function_names)}")
            return
        
        # 批量存储到ChromaDB
        try:
            logger.info("批量存储到ChromaDB...")
            self.collection.add(
                ids=batch_ids,
                embeddings=embeddings,
                documents=batch_documents,
                metadatas=batch_metadatas
            )
            
            logger.info(f"✅ 批量索引构建完成！成功存储 {len(batch_ids)} 个函数")
            
        except Exception as e:
            logger.error(f"批量存储失败: {e}")
    
    def _get_all_function_urls(self) -> List[tuple]:
        """获取所有函数的URL"""
        # 从A-Z字母索引获取函数列表
        function_urls = []
        
        for letter in "abcdefghijklmnopqrstuvwxyz":
            try:
                index_url = f"{self.base_url}lib-{letter}.html"
                response = requests.get(index_url, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # 查找函数链接
                    for link in soup.find_all('a', href=True):
                        href = link.get('href')
                        if href and href.endswith('.html') and not href.startswith('lib-'):
                            # 提取函数名
                            func_name = href.split('/')[-1].replace('.html', '')
                            if func_name and not func_name.startswith('_'):  # 跳过私有函数
                                full_url = f"{self.base_url}{letter}/{href.split('/')[-1]}"
                                function_urls.append((func_name, full_url))
                
                # 避免请求过快
                time.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"获取字母 {letter} 的函数列表失败: {e}")
                continue
        
        # 去重并排序
        unique_functions = list(set(function_urls))
        unique_functions.sort()
        
        logger.info(f"发现 {len(unique_functions)} 个唯一函数")
        return unique_functions
    
    def _fetch_and_cache_html(self, function_name: str, url: str) -> Optional[str]:
        """获取并缓存HTML内容"""
        cache_file = self.cache_dir / f"{function_name}.html"
        
        # 检查缓存
        if cache_file.exists():
            try:
                return cache_file.read_text(encoding='utf-8')
            except Exception as e:
                logger.warning(f"读取缓存失败 {function_name}: {e}")
        
        # 下载HTML
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                html_content = response.text
                
                # 保存到缓存
                try:
                    cache_file.write_text(html_content, encoding='utf-8')
                except Exception as e:
                    logger.warning(f"保存缓存失败 {function_name}: {e}")
                
                return html_content
            else:
                logger.warning(f"HTTP {response.status_code} for {function_name}: {url}")
        
        except Exception as e:
            logger.warning(f"下载HTML失败 {function_name}: {e}")
        
        return None
    
    def get_function_by_name(self, function_name: str) -> Optional[Dict[str, Any]]:
        """根据函数名精确获取函数信息"""
        if not self.collection:
            try:
                self.collection = self.chroma_client.get_collection(name=self.collection_name)
            except Exception:
                logger.error("集合未构建，请先调用 build_index()")
                return None
        
        try:
            result = self.collection.get(
                ids=[function_name],
                include=['documents', 'metadatas']
            )
            
            if result['ids'] and result['ids'][0]:
                return {
                    "function_name": function_name,
                    "html_content": result['documents'][0],
                    "metadata": result['metadatas'][0],
                    "found_method": "exact_match"
                }
            
            logger.warning(f"函数 {function_name} 不存在于集合中")
            return None
        
        except Exception as e:
            logger.error(f"获取函数 {function_name} 失败: {e}")
            return None
    
    def search_similar_functions(self, function_name: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """基于函数名向量搜索相似函数"""
        if not self.collection:
            logger.error("集合未构建")
            return []
        
        try:
            # 获取查询函数名的向量
            query_embedding = genai.embed_content(
                model=f"models/{self.embedding_model}",
                content=function_name,
                task_type="semantic_similarity"
            )
            
            results = self.collection.query(
                query_embeddings=[query_embedding['embedding']],
                n_results=top_k,
                include=['documents', 'metadatas', 'distances']
            )
            
            formatted_results = []
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        "function_name": results['ids'][0][i],
                        "similarity_score": 1.0 - results['distances'][0][i],
                        "html_content": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i]
                    })
            
            return formatted_results
        
        except Exception as e:
            logger.error(f"相似性搜索失败: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        try:
            if not self.collection:
                self.collection = self.chroma_client.get_collection(name=self.collection_name)
            
            count = self.collection.count()
            
            # 获取样本函数
            sample_result = self.collection.get(limit=10, include=['metadatas'])
            sample_functions = [meta['function_name'] for meta in sample_result['metadatas']] if sample_result['metadatas'] else []
            
            return {
                "status": "ready",
                "collection_name": self.collection_name,
                "total_functions": count,
                "sample_functions": sample_functions,
                "capabilities": [
                    "exact_function_lookup",
                    "similarity_search", 
                    "batch_operations",
                    "full_html_storage",
                    "gemini_powered"
                ]
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "total_functions": 0,
                "sample_functions": []
            }
    
    def list_all_functions(self, limit: int = 50) -> List[str]:
        """列出所有函数名"""
        try:
            if not self.collection:
                self.collection = self.chroma_client.get_collection(name=self.collection_name)
            
            result = self.collection.get(limit=limit, include=['metadatas'])
            return [meta['function_name'] for meta in result['metadatas']] if result['metadatas'] else []
        
        except Exception as e:
            logger.error(f"列出函数失败: {e}")
            return []


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Gemini QNX RAG系统")
    parser.add_argument("--build", action="store_true", help="构建索引")
    parser.add_argument("--rebuild", action="store_true", help="重建索引")
    parser.add_argument("--max-functions", type=int, default=100, help="最大函数数量")
    parser.add_argument("--function", help="测试特定函数")
    parser.add_argument("--config", default="config.json", help="配置文件")
    
    args = parser.parse_args()
    
    rag = GeminiQNXRAG(config_path=args.config)
    
    if args.build or args.rebuild:
        rag.build_index(max_functions=args.max_functions, rebuild=args.rebuild)
    
    if args.function:
        result = rag.get_function_by_name(args.function)
        if result:
            print(f"✅ 找到函数: {args.function}")
            print(f"HTML长度: {len(result['html_content'])}")
        else:
            print(f"❌ 未找到函数: {args.function}")
    
    # 显示统计信息
    stats = rag.get_collection_stats()
    print(f"\n📊 集合状态: {json.dumps(stats, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    main()