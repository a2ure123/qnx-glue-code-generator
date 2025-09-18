#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成QNX系统 - 结合Gemini向量化和2.5 Flash JSON提取
提供完整的QNX函数文档处理和查询功能
"""

import os
import sys
import json
import logging
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from optimized_gemini_vectorizer import OptimizedGeminiVectorizer, VectorizeTask
from gemini_flash_json_extractor import GeminiFlashJSONExtractor, QNXFunctionInfo

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 禁用第三方库的详细日志
logging.getLogger("chromadb.telemetry").setLevel(logging.ERROR)
logging.getLogger("backoff").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)


@dataclass
class ProcessingTask:
    """处理任务"""
    file_path: str
    function_name: str
    priority: int = 1  # 1=高优先级, 2=中优先级, 3=低优先级


@dataclass
class ProcessingResult:
    """处理结果"""
    function_name: str
    success: bool
    json_extracted: bool = False
    vectorized: bool = False
    cached: bool = False
    error: Optional[str] = None
    processing_time: float = 0.0


class IntegratedQNXSystem:
    """集成QNX系统"""
    
    def __init__(self, config_path: str = "config.json"):
        """初始化集成系统"""
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 初始化子系统
        self.vectorizer = OptimizedGeminiVectorizer(config_path)
        self.json_extractor = GeminiFlashJSONExtractor(config_path)
        
        # 缓存设置
        self.cache_dir = Path("./data/qnx_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.json_cache_dir = self.cache_dir / "json"
        self.json_cache_dir.mkdir(exist_ok=True)
        
        # 统计信息
        self.stats = {
            "total_processed": 0,
            "json_extracted": 0,
            "vectorized": 0,
            "cached_hits": 0,
            "errors": 0,
            "total_time": 0.0
        }
        
        logger.info("集成QNX系统初始化完成")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"配置文件加载失败: {e}")
            return {}
    
    def _get_cache_path(self, function_name: str, content_hash: str) -> Path:
        """获取缓存文件路径"""
        cache_filename = f"func_{function_name}_{content_hash[:8]}.json"
        return self.json_cache_dir / cache_filename
    
    def _get_content_hash(self, content: str) -> str:
        """获取内容哈希"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _load_from_cache(self, function_name: str, content_hash: str) -> Optional[QNXFunctionInfo]:
        """从缓存加载函数信息"""
        cache_path = self._get_cache_path(function_name, content_hash)
        
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 重构函数信息对象
                function_info = self._dict_to_function_info(data)
                logger.info(f"从缓存加载函数信息: {function_name}")
                return function_info
                
            except Exception as e:
                logger.warning(f"缓存文件损坏 {cache_path}: {e}")
                cache_path.unlink(missing_ok=True)
        
        return None
    
    def _save_to_cache(self, function_info: QNXFunctionInfo, content_hash: str):
        """保存函数信息到缓存"""
        cache_path = self._get_cache_path(function_info.name, content_hash)
        
        try:
            data = asdict(function_info)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"函数信息已缓存: {cache_path}")
        except Exception as e:
            logger.warning(f"缓存保存失败: {e}")
    
    def _dict_to_function_info(self, data: Dict[str, Any]) -> QNXFunctionInfo:
        """将字典转换为QNXFunctionInfo对象"""
        from gemini_flash_json_extractor import FunctionParameter, HeaderFile
        
        # 重构参数列表
        parameters = []
        for param_data in data.get("parameters", []):
            param = FunctionParameter(**param_data)
            parameters.append(param)
        
        # 重构头文件列表
        headers = []
        for header_data in data.get("headers", []):
            header = HeaderFile(**header_data)
            headers.append(header)
        
        # 创建函数信息对象
        function_info = QNXFunctionInfo(
            name=data.get("name", ""),
            synopsis=data.get("synopsis", ""),
            description=data.get("description", ""),
            parameters=parameters,
            return_type=data.get("return_type", ""),
            return_description=data.get("return_description", ""),
            headers=headers,
            libraries=data.get("libraries", []),
            examples=data.get("examples", []),
            see_also=data.get("see_also", []),
            classification=data.get("classification", ""),
            safety=data.get("safety", "")
        )
        
        return function_info
    
    def process_single_function(self, html_content: str, function_name: str) -> ProcessingResult:
        """处理单个函数"""
        start_time = time.time()
        result = ProcessingResult(function_name=function_name, success=False)
        
        try:
            # 计算内容哈希
            content_hash = self._get_content_hash(html_content)
            
            # 尝试从缓存加载
            function_info = self._load_from_cache(function_name, content_hash)
            
            if function_info:
                result.cached = True
                self.stats["cached_hits"] += 1
            else:
                # 使用JSON提取器提取信息
                function_info = self.json_extractor.extract_function_info(html_content, function_name)
                
                if function_info:
                    result.json_extracted = True
                    self.stats["json_extracted"] += 1
                    
                    # 保存到缓存
                    self._save_to_cache(function_info, content_hash)
                else:
                    result.error = "JSON提取失败"
                    self.stats["errors"] += 1
                    return result
            
            # 准备向量化文档
            doc_content = self._prepare_document_content(function_info)
            document = {
                "id": f"qnx_func_{function_name}",
                "content": doc_content,
                "metadata": {
                    "function_name": function_name,
                    "return_type": function_info.return_type,
                    "parameter_count": len(function_info.parameters),
                    "classification": function_info.classification,
                    "source": "qnx_docs"
                }
            }
            
            # 向量化存储
            vectorize_stats = self.vectorizer.vectorize_documents([document])
            
            if vectorize_stats["successful_vectorized"] > 0:
                result.vectorized = True
                self.stats["vectorized"] += 1
            else:
                result.error = "向量化失败"
                self.stats["errors"] += 1
                return result
            
            result.success = True
            
        except Exception as e:
            result.error = str(e)
            self.stats["errors"] += 1
            logger.error(f"处理函数失败 {function_name}: {e}")
        
        finally:
            result.processing_time = time.time() - start_time
            self.stats["total_processed"] += 1
            self.stats["total_time"] += result.processing_time
        
        return result
    
    def _prepare_document_content(self, function_info: QNXFunctionInfo) -> str:
        """准备文档内容用于向量化"""
        content_parts = []
        
        # 基本信息
        content_parts.append(f"函数名: {function_info.name}")
        
        if function_info.synopsis:
            content_parts.append(f"声明: {function_info.synopsis}")
        
        if function_info.description:
            content_parts.append(f"描述: {function_info.description}")
        
        if function_info.return_type:
            content_parts.append(f"返回类型: {function_info.return_type}")
        
        if function_info.return_description:
            content_parts.append(f"返回值说明: {function_info.return_description}")
        
        # 参数信息
        if function_info.parameters:
            params_text = "参数:\n"
            for param in function_info.parameters:
                param_desc = f"  {param.name} ({param.type})"
                if param.description:
                    param_desc += f": {param.description}"
                params_text += param_desc + "\n"
            content_parts.append(params_text.strip())
        
        # 头文件信息
        if function_info.headers:
            headers_text = "头文件: " + ", ".join([h.filename for h in function_info.headers])
            content_parts.append(headers_text)
        
        # 库信息
        if function_info.libraries:
            libs_text = "链接库: " + ", ".join(function_info.libraries)
            content_parts.append(libs_text)
        
        # 分类和安全性
        if function_info.classification:
            content_parts.append(f"分类: {function_info.classification}")
        
        if function_info.safety:
            content_parts.append(f"安全性: {function_info.safety}")
        
        # 相关函数
        if function_info.see_also:
            see_also_text = "相关函数: " + ", ".join(function_info.see_also)
            content_parts.append(see_also_text)
        
        return "\n\n".join(content_parts)
    
    def process_batch_functions(self, tasks: List[ProcessingTask], max_workers: int = 4) -> List[ProcessingResult]:
        """批量处理函数"""
        results = []
        
        logger.info(f"开始批量处理 {len(tasks)} 个函数")
        
        # 按优先级排序
        tasks.sort(key=lambda x: x.priority)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {}
            
            for task in tasks:
                try:
                    # 读取HTML文件
                    with open(task.file_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    # 提交处理任务
                    future = executor.submit(self.process_single_function, html_content, task.function_name)
                    future_to_task[future] = task
                    
                except Exception as e:
                    logger.error(f"无法读取文件 {task.file_path}: {e}")
                    result = ProcessingResult(
                        function_name=task.function_name,
                        success=False,
                        error=f"文件读取失败: {e}"
                    )
                    results.append(result)
            
            # 收集结果
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"处理完成: {task.function_name} - {'成功' if result.success else '失败'}")
                except Exception as e:
                    logger.error(f"任务执行失败 {task.function_name}: {e}")
                    result = ProcessingResult(
                        function_name=task.function_name,
                        success=False,
                        error=f"执行失败: {e}"
                    )
                    results.append(result)
        
        # 更新统计信息
        successful = len([r for r in results if r.success])
        logger.info(f"批量处理完成: {successful}/{len(tasks)} 成功")
        
        return results
    
    def query_functions(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """查询函数"""
        logger.info(f"查询: {query}")
        
        # 使用向量化系统查询
        results = self.vectorizer.query_similar(query, n_results)
        
        # 增强结果信息
        enhanced_results = []
        for result in results:
            metadata = result.get("metadata", {})
            enhanced_result = {
                "function_name": metadata.get("function_name", ""),
                "similarity": result.get("similarity", 0.0),
                "content": result.get("document", ""),
                "return_type": metadata.get("return_type", ""),
                "parameter_count": metadata.get("parameter_count", 0),
                "classification": metadata.get("classification", "")
            }
            enhanced_results.append(enhanced_result)
        
        logger.info(f"查询完成，返回 {len(enhanced_results)} 个结果")
        return enhanced_results
    
    def get_function_details(self, function_name: str) -> Optional[QNXFunctionInfo]:
        """获取函数详细信息"""
        # 在缓存中查找
        cache_files = list(self.json_cache_dir.glob(f"func_{function_name}_*.json"))
        
        if cache_files:
            try:
                with open(cache_files[0], 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return self._dict_to_function_info(data)
            except Exception as e:
                logger.error(f"读取缓存失败: {e}")
        
        return None
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        # 合并统计信息
        combined_stats = self.stats.copy()
        
        # 添加向量化器统计信息
        vectorizer_stats = self.vectorizer.get_stats()
        combined_stats["vectorizer"] = vectorizer_stats
        
        # 添加缓存统计信息
        cache_count = len(list(self.json_cache_dir.glob("*.json")))
        combined_stats["cached_functions"] = cache_count
        
        return combined_stats
    
    def cleanup_cache(self, max_age_days: int = 30):
        """清理过期缓存"""
        import time
        from datetime import datetime, timedelta
        
        cutoff_time = time.time() - (max_age_days * 24 * 3600)
        deleted_count = 0
        
        for cache_file in self.json_cache_dir.glob("*.json"):
            if cache_file.stat().st_mtime < cutoff_time:
                try:
                    cache_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"删除缓存文件失败 {cache_file}: {e}")
        
        logger.info(f"清理完成，删除 {deleted_count} 个过期缓存文件")


def main():
    """主函数 - 测试集成系统"""
    try:
        # 初始化集成系统
        system = IntegratedQNXSystem()
        
        # 测试HTML内容
        test_html = """
        <html>
        <body>
        <div class="content">
        <h1>printf</h1>
        <h2>Synopsis</h2>
        <p>int printf(const char *format, ...);</p>
        <h2>Description</h2>
        <p>The printf() function sends formatted output to stdout.</p>
        <h2>Returns</h2>
        <p>Number of characters printed</p>
        <h2>Header</h2>
        <p>#include &lt;stdio.h&gt;</p>
        </div>
        </body>
        </html>
        """
        
        # 处理单个函数
        result = system.process_single_function(test_html, "printf")
        print(f"处理结果: {result}")
        
        # 查询测试
        query_results = system.query_functions("格式化输出函数", n_results=3)
        print(f"查询结果: {len(query_results)} 个")
        
        # 获取统计信息
        stats = system.get_system_stats()
        print(f"系统统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")


if __name__ == "__main__":
    main()