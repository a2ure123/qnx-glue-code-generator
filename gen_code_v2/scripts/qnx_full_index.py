#!/usr/bin/env python3
"""
完整QNX函数索引构建脚本
处理所有QNX函数文档，包括重复函数名的情况
"""

import os
import sys
import json
import hashlib
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qnx_rag import QNXFunctionRAG
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QNXFullIndexer(QNXFunctionRAG):
    """完整QNX索引构建器，处理重复函数名"""
    
    def __init__(self):
        super().__init__()
        # 修改集合名称避免冲突
        self.collection_name = "qnx_functions_full"
        
        # 重新初始化集合
        try:
            self.collection = self.chroma_client.get_collection(name=self.collection_name)
            logger.info(f"加载完整函数集合: {self.collection_name}")
        except (ValueError, Exception):
            self.collection = None
            logger.info("将创建完整函数集合")
    
    def _discover_all_functions_with_duplicates(self):
        """发现所有QNX函数，保留重复函数的所有URL"""
        # 检查缓存
        cache_file = self.cache_dir / "function_urls_full.json"
        if cache_file.exists():
            logger.info("从缓存加载完整函数URL映射")
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        logger.info("发现所有QNX函数文档（包含重复）...")
        function_urls = {}  # Dict[func_name, List[url]]
        
        import string
        import requests
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin
        
        # 遍历所有字母页面
        for letter in string.ascii_lowercase:
            list_url = f"{self.base_url}lib-{letter}.html"
            logger.info(f"处理字母页面: {letter}")
            
            try:
                response = requests.get(list_url, timeout=15)
                if response.status_code != 200:
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找函数链接
                content_div = soup.find('div', class_='related-links')
                if not content_div:
                    continue
                
                for link in content_div.find_all('a', href=True):
                    href = link['href']
                    link_text = link.get_text().strip()
                    
                    # 检查是否是函数链接
                    if '()' in link_text and href.endswith('.html'):
                        # 构建完整URL
                        if href.startswith('../../'):
                            full_url = f"https://www.qnx.com/developers/docs/7.1/com.qnx.doc.neutrino.lib_ref/topic/{href.split('/')[-2]}/{href.split('/')[-1]}"
                        elif href.count('/') == 1:
                            full_url = urljoin(list_url, href)
                        else:
                            full_url = urljoin(list_url, href)
                        
                        # 提取函数名 - 可能有多个函数在同一链接中
                        func_names = link_text.replace('()', '').split(',')
                        for func_name in func_names:
                            func_name = func_name.strip()
                            if func_name:
                                if func_name not in function_urls:
                                    function_urls[func_name] = []
                                if full_url not in function_urls[func_name]:
                                    function_urls[func_name].append(full_url)
                
            except Exception as e:
                logger.error(f"处理字母 {letter} 时出错: {e}")
                continue
        
        # 统计
        total_functions = len(function_urls)
        total_urls = sum(len(urls) for urls in function_urls.values())
        duplicates = {name: urls for name, urls in function_urls.items() if len(urls) > 1}
        
        logger.info(f"发现 {total_functions} 个不同函数名")
        logger.info(f"总共 {total_urls} 个文档URL")
        logger.info(f"有 {len(duplicates)} 个函数名有多个文档")
        
        # 显示重复函数的例子
        if duplicates:
            logger.info("重复函数示例:")
            for name, urls in list(duplicates.items())[:5]:
                logger.info(f"  {name}: {len(urls)} 个文档")
                for url in urls:
                    logger.info(f"    - {url}")
        
        # 保存到缓存
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(function_urls, f, indent=2, ensure_ascii=False)
        
        return function_urls
    
    def build_full_index(self, force_rebuild: bool = False):
        """构建包含所有函数文档的完整索引"""
        if self.collection and not force_rebuild:
            count = self.collection.count()
            logger.info(f"完整函数集合已存在，包含 {count} 个文档。使用 force_rebuild=True 重建")
            return
        
        logger.info("开始构建完整QNX函数RAG索引...")
        
        # 重建时删除现有集合
        if force_rebuild and self.collection:
            try:
                self.chroma_client.delete_collection(name=self.collection_name)
            except:
                pass
        
        # 创建新集合
        self.collection = self.chroma_client.create_collection(
            name=self.collection_name,
            metadata={
                "hnsw:space": "cosine", 
                "description": "All QNX functions with all document variants"
            }
        )
        
        # 发现所有函数（包含重复）
        function_urls_map = self._discover_all_functions_with_duplicates()
        
        # 准备批量处理
        from tqdm import tqdm
        
        batch_size = 10  # 减小批次大小以处理更多文档
        successful_count = 0
        failed_count = 0
        
        # 展开所有函数文档
        all_function_docs = []
        for func_name, urls in function_urls_map.items():
            for i, url in enumerate(urls):
                # 为重复函数创建唯一标识
                doc_id = f"{func_name}_{i}" if len(urls) > 1 else func_name
                all_function_docs.append((doc_id, func_name, url))
        
        logger.info(f"准备处理 {len(all_function_docs)} 个函数文档")
        
        # 批量处理所有文档
        for i in tqdm(range(0, len(all_function_docs), batch_size), desc="构建完整索引"):
            batch = all_function_docs[i:i + batch_size]
            
            # 收集批次数据
            batch_ids = []
            batch_embeddings = []
            batch_documents = []
            batch_metadatas = []
            
            for doc_id, func_name, url in batch:
                # 获取函数文档
                func_info = self._fetch_and_parse_function(func_name, url)
                if not func_info or len(func_info['full_content']) < 50:
                    failed_count += 1
                    continue
                
                # 对函数名进行向量化
                embedding = self._get_function_name_embedding(func_name)
                if not embedding:
                    failed_count += 1
                    continue
                
                # 准备数据
                batch_ids.append(doc_id)
                batch_embeddings.append(embedding)
                batch_documents.append(func_info['full_content'])
                batch_metadatas.append({
                    "function_name": func_name,
                    "doc_id": doc_id,
                    "url": url,
                    "synopsis": func_info.get('synopsis', ''),
                    "description": func_info.get('description', ''),
                    "parameter_count": len(func_info.get('parameters', [])),
                    "return_value_count": len(func_info.get('return_values', [])),
                    "has_examples": len(func_info.get('examples', [])) > 0,
                    "headers": json.dumps(func_info.get('headers', [])),
                    "parameters": json.dumps(func_info.get('parameters', [])),
                    "return_values": json.dumps(func_info.get('return_values', []))
                })
            
            # 批量添加到集合
            if batch_ids:
                try:
                    self.collection.add(
                        ids=batch_ids,
                        embeddings=batch_embeddings,
                        documents=batch_documents,
                        metadatas=batch_metadatas
                    )
                    successful_count += len(batch_ids)
                except Exception as e:
                    logger.error(f"批量添加文档时出错: {e}")
                    failed_count += len(batch_ids)
        
        logger.info(f"完整索引构建完成:")
        logger.info(f"  成功: {successful_count} 个文档")
        logger.info(f"  失败: {failed_count} 个文档")
    
    def get_function_all_variants(self, function_name: str):
        """获取函数的所有文档变体"""
        if not self.collection:
            raise ValueError("集合未构建，请先调用 build_full_index()")
        
        try:
            # 查询所有匹配该函数名的文档
            results = self.collection.get(
                where={"function_name": function_name},
                include=['documents', 'metadatas']
            )
            
            variants = []
            if results['ids']:
                for i, doc_id in enumerate(results['ids']):
                    metadata = results['metadatas'][i]
                    # 反序列化JSON字段
                    if isinstance(metadata.get('headers'), str):
                        metadata['headers'] = json.loads(metadata['headers'])
                    if isinstance(metadata.get('parameters'), str):
                        metadata['parameters'] = json.loads(metadata['parameters'])
                    if isinstance(metadata.get('return_values'), str):
                        metadata['return_values'] = json.loads(metadata['return_values'])
                    
                    variants.append({
                        "doc_id": doc_id,
                        "function_name": function_name,
                        "content": results['documents'][i],
                        "metadata": metadata
                    })
            
            return variants
            
        except Exception as e:
            logger.error(f"获取函数变体时出错 '{function_name}': {e}")
            return []
    
    def get_full_collection_stats(self):
        """获取完整集合统计信息"""
        if not self.collection:
            return {"status": "not_built"}
        
        try:
            count = self.collection.count()
            
            # 统计函数名分布
            all_metadata = self.collection.get(include=['metadatas'])['metadatas']
            function_names = [meta['function_name'] for meta in all_metadata]
            
            from collections import Counter
            name_counts = Counter(function_names)
            
            duplicates = {name: count for name, count in name_counts.items() if count > 1}
            
            return {
                "status": "ready",
                "total_documents": count,
                "unique_functions": len(name_counts),
                "functions_with_variants": len(duplicates),
                "sample_duplicates": dict(list(duplicates.items())[:5]),
                "collection_name": self.collection_name
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


def main():
    """运行完整索引构建"""
    # 检查环境变量
    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("请设置 OPENAI_API_KEY 环境变量")
        logger.info("运行: export OPENAI_API_KEY=your_api_key_here")
        return
    
    logger.info("开始QNX完整函数索引构建...")
    
    # 初始化完整索引器
    indexer = QNXFullIndexer()
    
    # 显示当前状态
    stats = indexer.get_full_collection_stats()
    logger.info(f"当前集合状态: {stats}")
    
    if stats["status"] != "ready":
        # 构建完整索引
        indexer.build_full_index()
        
        # 显示最终统计
        final_stats = indexer.get_full_collection_stats()
        logger.info(f"索引构建完成: {final_stats}")
    else:
        logger.info("索引已存在，跳过构建")
    
    # 测试几个函数
    test_functions = ["malloc", "printf", "open", "close", "pthread_create"]
    
    logger.info("\n=== 测试函数查询 ===")
    for func_name in test_functions:
        variants = indexer.get_function_all_variants(func_name)
        if variants:
            logger.info(f"\n函数 '{func_name}' 找到 {len(variants)} 个文档变体:")
            for i, variant in enumerate(variants):
                logger.info(f"  变体 {i+1}: {variant['metadata']['url']}")
                logger.info(f"    描述: {variant['metadata']['description'][:100]}...")
        else:
            logger.info(f"\n函数 '{func_name}' 未找到")


if __name__ == "__main__":
    main()